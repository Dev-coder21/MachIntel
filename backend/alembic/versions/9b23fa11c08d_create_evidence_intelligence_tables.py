"""create_evidence_intelligence_tables

Revision ID: 9b23fa11c08d
Revises: 7a18fbc09d12
Create Date: 2026-10-01 11:38:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9b23fa11c08d'
down_revision: Union[str, Sequence[str], None] = '7a18fbc09d12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evidence_records table
    op.create_table(
        'evidence_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('domain', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=False),
        sa.Column('observation_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observation_cycle', sa.Integer(), nullable=True),
        sa.Column('value', sa.JSON(), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('quality_state', sa.String(length=50), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('model_version', sa.String(length=100), nullable=True),
        sa.Column('feature_version', sa.String(length=100), nullable=True),
        sa.Column('policy_version', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_records_id', 'evidence_records', ['id'], unique=False)
    op.create_index('ix_evidence_records_domain', 'evidence_records', ['domain'], unique=False)
    op.create_index('ix_evidence_records_entity_type', 'evidence_records', ['entity_type'], unique=False)
    op.create_index('ix_evidence_records_entity_id', 'evidence_records', ['entity_id'], unique=False)
    op.create_index('ix_evidence_records_evidence_type', 'evidence_records', ['evidence_type'], unique=False)
    op.create_index('ix_evidence_records_source', 'evidence_records', ['source'], unique=False)
    op.create_index('ix_evidence_records_observation_time', 'evidence_records', ['observation_time'], unique=False)
    op.create_index('ix_evidence_records_observation_cycle', 'evidence_records', ['observation_cycle'], unique=False)
    op.create_index('ix_evidence_records_quality_state', 'evidence_records', ['quality_state'], unique=False)
    op.create_index('ix_evidence_records_model_version', 'evidence_records', ['model_version'], unique=False)
    op.create_index('ix_evidence_records_policy_version', 'evidence_records', ['policy_version'], unique=False)
    op.create_index('ix_evidence_records_created_at', 'evidence_records', ['created_at'], unique=False)
    op.create_index('ix_evidence_domain_entity', 'evidence_records', ['domain', 'entity_type', 'entity_id'], unique=False)
    op.create_index('ix_evidence_type_source', 'evidence_records', ['evidence_type', 'source'], unique=False)

    # 2. Create evidence_relationships table
    op.create_table(
        'evidence_relationships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_evidence_id', sa.UUID(), nullable=False),
        sa.Column('target_evidence_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('relationship_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['source_evidence_id'], ['evidence_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_evidence_id'], ['evidence_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_relationships_id', 'evidence_relationships', ['id'], unique=False)
    op.create_index('ix_evidence_relationships_source_evidence_id', 'evidence_relationships', ['source_evidence_id'], unique=False)
    op.create_index('ix_evidence_relationships_target_evidence_id', 'evidence_relationships', ['target_evidence_id'], unique=False)
    op.create_index('ix_evidence_relationships_relationship_type', 'evidence_relationships', ['relationship_type'], unique=False)
    op.create_index('ix_evidence_rel_pair', 'evidence_relationships', ['source_evidence_id', 'target_evidence_id'], unique=False)

    # 3. Create evidence_bundles table
    op.create_table(
        'evidence_bundles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('bundle_name', sa.String(length=100), nullable=False),
        sa.Column('domain', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_bundles_id', 'evidence_bundles', ['id'], unique=False)
    op.create_index('ix_evidence_bundles_domain', 'evidence_bundles', ['domain'], unique=False)
    op.create_index('ix_evidence_bundles_entity_type', 'evidence_bundles', ['entity_type'], unique=False)
    op.create_index('ix_evidence_bundles_entity_id', 'evidence_bundles', ['entity_id'], unique=False)

    # 4. Create evidence_bundle_items table
    op.create_table(
        'evidence_bundle_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('bundle_id', sa.UUID(), nullable=False),
        sa.Column('evidence_id', sa.UUID(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('role_in_bundle', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['bundle_id'], ['evidence_bundles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_bundle_items_id', 'evidence_bundle_items', ['id'], unique=False)
    op.create_index('ix_evidence_bundle_items_bundle_id', 'evidence_bundle_items', ['bundle_id'], unique=False)
    op.create_index('ix_evidence_bundle_items_evidence_id', 'evidence_bundle_items', ['evidence_id'], unique=False)
    op.create_index('ix_bundle_evidence_unique', 'evidence_bundle_items', ['bundle_id', 'evidence_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_bundle_evidence_unique', table_name='evidence_bundle_items')
    op.drop_index('ix_evidence_bundle_items_evidence_id', table_name='evidence_bundle_items')
    op.drop_index('ix_evidence_bundle_items_bundle_id', table_name='evidence_bundle_items')
    op.drop_index('ix_evidence_bundle_items_id', table_name='evidence_bundle_items')
    op.drop_table('evidence_bundle_items')

    op.drop_index('ix_evidence_bundles_entity_id', table_name='evidence_bundles')
    op.drop_index('ix_evidence_bundles_entity_type', table_name='evidence_bundles')
    op.drop_index('ix_evidence_bundles_domain', table_name='evidence_bundles')
    op.drop_index('ix_evidence_bundles_id', table_name='evidence_bundles')
    op.drop_table('evidence_bundles')

    op.drop_index('ix_evidence_rel_pair', table_name='evidence_relationships')
    op.drop_index('ix_evidence_relationships_relationship_type', table_name='evidence_relationships')
    op.drop_index('ix_evidence_relationships_target_evidence_id', table_name='evidence_relationships')
    op.drop_index('ix_evidence_relationships_source_evidence_id', table_name='evidence_relationships')
    op.drop_index('ix_evidence_relationships_id', table_name='evidence_relationships')
    op.drop_table('evidence_relationships')

    op.drop_index('ix_evidence_type_source', table_name='evidence_records')
    op.drop_index('ix_evidence_domain_entity', table_name='evidence_records')
    op.drop_index('ix_evidence_records_created_at', table_name='evidence_records')
    op.drop_index('ix_evidence_records_policy_version', table_name='evidence_records')
    op.drop_index('ix_evidence_records_model_version', table_name='evidence_records')
    op.drop_index('ix_evidence_records_quality_state', table_name='evidence_records')
    op.drop_index('ix_evidence_records_observation_cycle', table_name='evidence_records')
    op.drop_index('ix_evidence_records_observation_time', table_name='evidence_records')
    op.drop_index('ix_evidence_records_source', table_name='evidence_records')
    op.drop_index('ix_evidence_records_evidence_type', table_name='evidence_records')
    op.drop_index('ix_evidence_records_entity_id', table_name='evidence_records')
    op.drop_index('ix_evidence_records_entity_type', table_name='evidence_records')
    op.drop_index('ix_evidence_records_domain', table_name='evidence_records')
    op.drop_index('ix_evidence_records_id', table_name='evidence_records')
    op.drop_table('evidence_records')
