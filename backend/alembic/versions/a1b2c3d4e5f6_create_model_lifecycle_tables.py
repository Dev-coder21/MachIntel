"""create_model_lifecycle_tables

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-10-02 00:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend model_registry table with lifecycle & integrity metadata
    op.add_column('model_registry', sa.Column('domain', sa.String(length=50), nullable=False, server_default='MACHINE_HEALTH'))
    op.add_column('model_registry', sa.Column('model_family', sa.String(length=50), nullable=False, server_default='RUL_REGRESSION'))
    op.add_column('model_registry', sa.Column('version', sa.String(length=50), nullable=False, server_default='1.0.0'))
    op.add_column('model_registry', sa.Column('status', sa.String(length=50), nullable=False, server_default='REGISTERED'))
    op.add_column('model_registry', sa.Column('framework', sa.String(length=50), nullable=False, server_default='scikit-learn'))
    op.add_column('model_registry', sa.Column('dataset_version', sa.String(length=50), nullable=True))
    op.add_column('model_registry', sa.Column('feature_version', sa.String(length=50), nullable=True))
    op.add_column('model_registry', sa.Column('artifact_sha256', sa.String(length=64), nullable=True))
    op.add_column('model_registry', sa.Column('artifact_size_bytes', sa.BigInteger(), nullable=True))
    op.add_column('model_registry', sa.Column('training_manifest', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('model_registry', sa.Column('evaluation_manifest', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('model_registry', sa.Column('description', sa.String(length=1000), nullable=True))
    op.add_column('model_registry', sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('model_registry', sa.Column('parent_model_id', sa.String(length=100), nullable=True))
    op.add_column('model_registry', sa.Column('registered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')))

    op.create_index(op.f('ix_model_registry_domain'), 'model_registry', ['domain'], unique=False)
    op.create_index(op.f('ix_model_registry_model_family'), 'model_registry', ['model_family'], unique=False)
    op.create_index(op.f('ix_model_registry_status'), 'model_registry', ['status'], unique=False)

    # 2. Create model_evaluations table
    op.create_table(
        'model_evaluations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('model_version_id', sa.UUID(), nullable=False),
        sa.Column('evaluation_type', sa.String(length=50), nullable=False),
        sa.Column('dataset_identifier', sa.String(length=100), nullable=False),
        sa.Column('split', sa.String(length=50), nullable=False),
        sa.Column('metrics', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('manifest', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('gate_result', sa.String(length=50), nullable=False, server_default='PASSED'),
        sa.Column('gate_details', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('evaluator', sa.String(length=100), nullable=False, server_default='automated-evaluator'),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_registry.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_evaluations_id'), 'model_evaluations', ['id'], unique=False)
    op.create_index(op.f('ix_model_evaluations_model_version_id'), 'model_evaluations', ['model_version_id'], unique=False)
    op.create_index(op.f('ix_model_evaluations_evaluated_at'), 'model_evaluations', ['evaluated_at'], unique=False)

    # 3. Create model_promotions table
    op.create_table(
        'model_promotions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('model_version_id', sa.UUID(), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=False),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('promoted_by_id', sa.UUID(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('promotion_policy_version', sa.String(length=50), nullable=False, server_default='policy-v1.0.0'),
        sa.Column('gate_results', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_registry.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['promoted_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_promotions_id'), 'model_promotions', ['id'], unique=False)
    op.create_index(op.f('ix_model_promotions_model_version_id'), 'model_promotions', ['model_version_id'], unique=False)
    op.create_index(op.f('ix_model_promotions_promoted_at'), 'model_promotions', ['promoted_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_promotions_promoted_at'), table_name='model_promotions')
    op.drop_index(op.f('ix_model_promotions_model_version_id'), table_name='model_promotions')
    op.drop_index(op.f('ix_model_promotions_id'), table_name='model_promotions')
    op.drop_table('model_promotions')

    op.drop_index(op.f('ix_model_evaluations_evaluated_at'), table_name='model_evaluations')
    op.drop_index(op.f('ix_model_evaluations_model_version_id'), table_name='model_evaluations')
    op.drop_index(op.f('ix_model_evaluations_id'), table_name='model_evaluations')
    op.drop_table('model_evaluations')

    op.drop_index(op.f('ix_model_registry_status'), table_name='model_registry')
    op.drop_index(op.f('ix_model_registry_model_family'), table_name='model_registry')
    op.drop_index(op.f('ix_model_registry_domain'), table_name='model_registry')

    op.drop_column('model_registry', 'registered_at')
    op.drop_column('model_registry', 'parent_model_id')
    op.drop_column('model_registry', 'metadata_json')
    op.drop_column('model_registry', 'description')
    op.drop_column('model_registry', 'evaluation_manifest')
    op.drop_column('model_registry', 'training_manifest')
    op.drop_column('model_registry', 'artifact_size_bytes')
    op.drop_column('model_registry', 'artifact_sha256')
    op.drop_column('model_registry', 'feature_version')
    op.drop_column('model_registry', 'dataset_version')
    op.drop_column('model_registry', 'framework')
    op.drop_column('model_registry', 'status')
    op.drop_column('model_registry', 'version')
    op.drop_column('model_registry', 'model_family')
    op.drop_column('model_registry', 'domain')
