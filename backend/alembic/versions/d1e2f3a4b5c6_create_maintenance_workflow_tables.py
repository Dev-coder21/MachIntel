"""create_maintenance_workflow_tables

Revision ID: d1e2f3a4b5c6
Revises: 9b23fa11c08d
Create Date: 2026-10-01 17:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = '9b23fa11c08d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create maintenance_work_orders table
    op.create_table(
        'maintenance_work_orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('machine_id', sa.String(length=100), nullable=True),
        sa.Column('source_domain', sa.String(length=50), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=False),
        sa.Column('deduplication_key', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('risk_state_at_creation', sa.String(length=50), nullable=True),
        sa.Column('predicted_rul_at_creation', sa.Float(), nullable=True),
        sa.Column('health_index_at_creation', sa.Float(), nullable=True),
        sa.Column('anomaly_score_at_creation', sa.Float(), nullable=True),
        sa.Column('policy_version', sa.String(length=50), nullable=False),
        sa.Column('evidence_references', sa.JSON(), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('assigned_to_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_maintenance_work_orders_id', 'maintenance_work_orders', ['id'])
    op.create_index('ix_maintenance_work_orders_machine_id', 'maintenance_work_orders', ['machine_id'])
    op.create_index('ix_maintenance_work_orders_source_domain', 'maintenance_work_orders', ['source_domain'])
    op.create_index('ix_maintenance_work_orders_source_type', 'maintenance_work_orders', ['source_type'])
    op.create_index('ix_maintenance_work_orders_source_reference', 'maintenance_work_orders', ['source_reference'])
    op.create_index('ix_maintenance_work_orders_deduplication_key', 'maintenance_work_orders', ['deduplication_key'])
    op.create_index('ix_maintenance_work_orders_priority', 'maintenance_work_orders', ['priority'])
    op.create_index('ix_maintenance_work_orders_status', 'maintenance_work_orders', ['status'])
    op.create_index('ix_maintenance_work_orders_created_by_id', 'maintenance_work_orders', ['created_by_id'])
    op.create_index('ix_maintenance_work_orders_assigned_to_id', 'maintenance_work_orders', ['assigned_to_id'])
    op.create_index('ix_maintenance_work_orders_created_at', 'maintenance_work_orders', ['created_at'])
    op.create_index('ix_maintenance_domain_status', 'maintenance_work_orders', ['source_domain', 'status'])
    op.create_index('ix_maintenance_machine_status', 'maintenance_work_orders', ['machine_id', 'status'])

    # 2. Create maintenance_events table
    op.create_table(
        'maintenance_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('work_order_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('from_status', sa.String(length=30), nullable=True),
        sa.Column('to_status', sa.String(length=30), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('event_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['work_order_id'], ['maintenance_work_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_maintenance_events_id', 'maintenance_events', ['id'])
    op.create_index('ix_maintenance_events_work_order_id', 'maintenance_events', ['work_order_id'])
    op.create_index('ix_maintenance_events_event_type', 'maintenance_events', ['event_type'])
    op.create_index('ix_maintenance_events_actor_id', 'maintenance_events', ['actor_id'])
    op.create_index('ix_maintenance_events_created_at', 'maintenance_events', ['created_at'])


def downgrade() -> None:
    op.drop_table('maintenance_events')
    op.drop_table('maintenance_work_orders')
