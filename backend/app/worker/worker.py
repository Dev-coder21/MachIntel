import asyncio
from datetime import datetime, timedelta, timezone
import os
import signal
import socket
import sys
import time
from typing import Dict, Optional
import uuid

# Ensure root is in path when run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from backend.app.core.config import settings
from backend.app.core.logging import logger, setup_logging
from backend.app.db.session import SessionLocal
from backend.app.models.job import JobType
from backend.app.services.job_service import JobService
from backend.app.worker.handlers import JOB_HANDLERS


class BackgroundWorker:
    """
    Dedicated local background worker process.
    Claims jobs via atomic row locking, executes domain handlers, heartbeats,
    and runs the periodic scheduler loop when enabled.
    """

    def __init__(self):
        self.worker_id = f"worker-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._current_job_id: Optional[uuid.UUID] = None
        self._last_scheduled_times: Dict[str, datetime] = {}

    def _setup_signal_handlers(self):
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._handle_signal, sig)
            except NotImplementedError:
                # Windows fallback
                signal.signal(sig, lambda s, f: self._handle_signal(s))

    def _handle_signal(self, sig):
        logger.info(f"Worker {self.worker_id} received signal {sig}. Initiating graceful shutdown...")
        self.running = False
        self._shutdown_event.set()

    async def start(self):
        setup_logging()
        self.running = True
        self._setup_signal_handlers()

        logger.info(
            f"Starting MachIntel BackgroundWorker [{self.worker_id}] (PID: {self.pid}) on {self.hostname}"
        )
        logger.info(
            f"Configuration: Poll={settings.WORKER_POLL_INTERVAL_SECONDS}s, "
            f"Heartbeat={settings.WORKER_HEARTBEAT_INTERVAL_SECONDS}s, "
            f"SchedulerEnabled={settings.SCHEDULER_ENABLED}"
        )

        # Initial heartbeat
        self._update_worker_heartbeat("ACTIVE")

        # Spawn concurrent tasks
        poll_task = asyncio.create_task(self._job_polling_loop())
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        scheduler_task = asyncio.create_task(self._scheduler_loop())

        await self._shutdown_event.wait()

        logger.info(f"Stopping worker tasks for {self.worker_id}...")
        poll_task.cancel()
        heartbeat_task.cancel()
        scheduler_task.cancel()
        await asyncio.gather(poll_task, heartbeat_task, scheduler_task, return_exceptions=True)

        # Final heartbeat update: mark STOPPED
        self._update_worker_heartbeat("STOPPED")
        logger.info(f"Worker {self.worker_id} cleanly stopped.")

    def _update_worker_heartbeat(self, status: str):
        db = SessionLocal()
        try:
            svc = JobService(db)
            svc.update_worker_heartbeat(
                worker_id=self.worker_id,
                hostname=self.hostname,
                pid=self.pid,
                status=status,
                current_job_id=self._current_job_id,
                metadata={
                    "worker_enabled": settings.WORKER_ENABLED,
                    "scheduler_enabled": settings.SCHEDULER_ENABLED,
                },
            )
        except Exception as e:
            logger.error(f"Failed to update worker heartbeat: {e}")
        finally:
            db.close()

    async def _heartbeat_loop(self):
        """Periodically refreshes worker heartbeat and reaps stale jobs."""
        while self.running:
            try:
                self._update_worker_heartbeat("ACTIVE")

                # Reclaim stale jobs every heartbeat interval
                db = SessionLocal()
                try:
                    svc = JobService(db)
                    recovered = svc.recover_stale_jobs(
                        timeout_seconds=settings.WORKER_STALE_JOB_TIMEOUT_SECONDS
                    )
                    if recovered > 0:
                        logger.info(f"Reclaimed {recovered} stale jobs during heartbeat cycle.")
                finally:
                    db.close()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

            await asyncio.sleep(settings.WORKER_HEARTBEAT_INTERVAL_SECONDS)

    async def _job_polling_loop(self):
        """Continuously checks for QUEUED jobs and executes them."""
        while self.running:
            try:
                claimed_job = None
                db = SessionLocal()
                try:
                    svc = JobService(db)
                    claimed_job = svc.claim_next_job(worker_id=self.worker_id)
                finally:
                    db.close()

                if claimed_job:
                    self._current_job_id = claimed_job.id
                    await self._execute_job(claimed_job.id, claimed_job.job_type, claimed_job.payload)
                    self._current_job_id = None
                else:
                    await asyncio.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in job polling loop: {e}")
                await asyncio.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)

    async def _execute_job(self, job_id: uuid.UUID, job_type: str, payload: dict):
        """Executes a single job with runtime isolation and timing."""
        logger.info(f"Worker {self.worker_id} starting job {job_id} ({job_type})")
        start_time = time.perf_counter()

        handler = JOB_HANDLERS.get(job_type)
        if not handler:
            db = SessionLocal()
            try:
                svc = JobService(db)
                svc.record_job_failure(
                    job_id=job_id,
                    worker_id=self.worker_id,
                    error_code="UNSUPPORTED_JOB_TYPE",
                    error_message=f"No handler registered for job type '{job_type}'",
                    duration_ms=0.0,
                    is_retryable=False,
                )
            finally:
                db.close()
            return

        db = SessionLocal()
        try:
            # Execute handler in a separate thread if blocking CPU/IO
            loop = asyncio.get_running_loop()
            output_summary = await loop.run_in_executor(None, handler, db, payload)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            svc = JobService(db)
            svc.record_job_success(
                job_id=job_id,
                worker_id=self.worker_id,
                output_summary=output_summary,
                duration_ms=duration_ms,
            )
            logger.info(
                f"Worker {self.worker_id} completed job {job_id} ({job_type}) in {duration_ms}ms"
            )

        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(f"Worker {self.worker_id} failed job {job_id} ({job_type}): {e}")
            db.rollback()

            svc = JobService(db)
            svc.record_job_failure(
                job_id=job_id,
                worker_id=self.worker_id,
                error_code="EXECUTION_ERROR",
                error_message=str(e),
                duration_ms=duration_ms,
                is_retryable=True,
            )
        finally:
            db.close()

    async def _scheduler_loop(self):
        """Periodically triggers scheduled background refresh jobs."""
        if not settings.SCHEDULER_ENABLED:
            logger.info("Scheduler disabled via SCHEDULER_ENABLED=false")
            return

        logger.info("Scheduler loop active.")
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                schedule_configs = [
                    (
                        JobType.EVIDENCE_REFRESH.value,
                        settings.EVIDENCE_REFRESH_INTERVAL_MINUTES,
                    ),
                    (
                        JobType.RISK_REFRESH.value,
                        settings.RISK_REFRESH_INTERVAL_MINUTES,
                    ),
                    (
                        JobType.MAINTENANCE_RECOMMENDATION_REFRESH.value,
                        settings.MAINTENANCE_REFRESH_INTERVAL_MINUTES,
                    ),
                    (
                        JobType.ANALYTICS_REFRESH.value,
                        settings.ANALYTICS_REFRESH_INTERVAL_MINUTES,
                    ),
                ]

                db = SessionLocal()
                try:
                    svc = JobService(db)
                    for job_type, interval_minutes in schedule_configs:
                        last_time = self._last_scheduled_times.get(job_type)
                        should_run = False

                        if last_time is None:
                            # Check database for last completed job of this type
                            summary = svc.get_summary()
                            last_completed = summary.last_refresh_by_type.get(job_type)
                            if (
                                last_completed is None
                                or (now - last_completed).total_seconds() >= interval_minutes * 60
                            ):
                                should_run = True
                            else:
                                self._last_scheduled_times[job_type] = last_completed
                        elif (now - last_time).total_seconds() >= interval_minutes * 60:
                            should_run = True

                        if should_run:
                            exec_key = f"scheduled:{job_type}:{now.strftime('%Y-%m-%d-%H')}"
                            job, created = svc.trigger_job(
                                job_type=job_type,
                                payload={"trigger": "scheduler", "scheduled_at": now.isoformat()},
                                execution_key=exec_key,
                            )
                            self._last_scheduled_times[job_type] = now
                            if created:
                                logger.info(f"Scheduler enqueued {job_type} job {job.id}")
                finally:
                    db.close()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")

            # Sleep 15 seconds between scheduler evaluations
            await asyncio.sleep(15)


def run_worker():
    """Main worker entry point."""
    worker = BackgroundWorker()
    asyncio.run(worker.start())


if __name__ == "__main__":
    run_worker()
