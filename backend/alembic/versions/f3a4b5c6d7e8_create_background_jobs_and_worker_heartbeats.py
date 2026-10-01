"""create_background_jobs_and_worker_heartbeats
Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-10-01 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('job_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('execution_key', sa.String(length=255), nullable=True),
        sa.Column('requested_by_id', sa.UUID(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('output_summary', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('retry_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('worker_id', sa.String(length=128), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_background_jobs_id'), 'background_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_background_jobs_job_type'), 'background_jobs', ['job_type'], unique=False)
    op.create_index(op.f('ix_background_jobs_status'), 'background_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_background_jobs_execution_key'), 'background_jobs', ['execution_key'], unique=False)
    op.create_index(op.f('ix_background_jobs_worker_id'), 'background_jobs', ['worker_id'], unique=False)
    op.create_index(op.f('ix_background_jobs_created_at'), 'background_jobs', ['created_at'], unique=False)

    op.create_table(
        'worker_heartbeats',
        sa.Column('worker_id', sa.String(length=128), nullable=False),
        sa.Column('hostname', sa.String(length=128), nullable=False),
        sa.Column('pid', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_job_id', sa.UUID(), nullable=True),
        sa.Column('metadata_info', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('worker_id')
    )
    op.create_index(op.f('ix_worker_heartbeats_heartbeat_at'), 'worker_heartbeats', ['heartbeat_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_worker_heartbeats_heartbeat_at'), table_name='worker_heartbeats')
    op.drop_table('worker_heartbeats')

    op.drop_index(op.f('ix_background_jobs_created_at'), table_name='background_jobs')
    op.drop_index(op.f('ix_background_jobs_worker_id'), table_name='background_jobs')
    op.drop_index(op.f('ix_background_jobs_execution_key'), table_name='background_jobs')
    op.drop_index(op.f('ix_background_jobs_status'), table_name='background_jobs')
    op.drop_index(op.f('ix_background_jobs_job_type'), table_name='background_jobs')
    op.drop_index(op.f('ix_background_jobs_id'), table_name='background_jobs')
    op.drop_table('background_jobs')
