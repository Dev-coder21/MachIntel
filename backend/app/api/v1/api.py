from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    admin,
    analytics,
    auth,
    datasets,
    health,
    machines,
    models,
    predictions,
    risk,
    alerts,
    inspections,
    inspection_analytics,
    evidence,
    maintenance,
    ai_inspector,
    jobs,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(analytics.router)
api_router.include_router(machines.router)
api_router.include_router(datasets.router)
api_router.include_router(models.router)
api_router.include_router(predictions.router)
api_router.include_router(risk.router)
api_router.include_router(alerts.router)
api_router.include_router(inspections.router)
api_router.include_router(inspection_analytics.router)
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(maintenance.router)
api_router.include_router(ai_inspector.router)
api_router.include_router(jobs.router)


