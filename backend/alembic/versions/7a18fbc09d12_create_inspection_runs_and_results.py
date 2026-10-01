"""create_inspection_runs_and_results

Revision ID: 7a18fbc09d12
Revises: 4e96a8e722f1
Create Date: 2026-10-01 10:37:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a18fbc09d12'
down_revision: Union[str, Sequence[str], None] = '4e96a8e722f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create inspection_runs table
    op.create_table(
        'inspection_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('dataset_identifier', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=100), nullable=False),
        sa.Column('feature_config_version', sa.String(length=50), nullable=False),
        sa.Column('policy_version', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('total_images', sa.Integer(), nullable=False),
        sa.Column('passed_count', sa.Integer(), nullable=False),
        sa.Column('defect_count', sa.Integer(), nullable=False),
        sa.Column('evaluation_summary', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_runs_id'), 'inspection_runs', ['id'], unique=False)
    op.create_index(op.f('ix_inspection_runs_dataset_identifier'), 'inspection_runs', ['dataset_identifier'], unique=False)
    op.create_index(op.f('ix_inspection_runs_model_version'), 'inspection_runs', ['model_version'], unique=False)
    op.create_index(op.f('ix_inspection_runs_created_at'), 'inspection_runs', ['created_at'], unique=False)

    # 2. Create inspection_results table
    op.create_table(
        'inspection_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('split', sa.String(length=20), nullable=False),
        sa.Column('defect_class', sa.String(length=50), nullable=False),
        sa.Column('source_image_path', sa.String(length=500), nullable=False),
        sa.Column('source_image_filename', sa.String(length=100), nullable=False),
        sa.Column('image_level_score', sa.Float(), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('ground_truth_label', sa.String(length=20), nullable=False),
        sa.Column('heatmap_path', sa.String(length=500), nullable=True),
        sa.Column('overlay_path', sa.String(length=500), nullable=True),
        sa.Column('ground_truth_mask_path', sa.String(length=500), nullable=True),
        sa.Column('inference_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['inspection_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_results_id'), 'inspection_results', ['id'], unique=False)
    op.create_index(op.f('ix_inspection_results_run_id'), 'inspection_results', ['run_id'], unique=False)
    op.create_index(op.f('ix_inspection_results_defect_class'), 'inspection_results', ['defect_class'], unique=False)
    op.create_index(op.f('ix_inspection_results_image_level_score'), 'inspection_results', ['image_level_score'], unique=False)
    op.create_index(op.f('ix_inspection_results_decision'), 'inspection_results', ['decision'], unique=False)
    op.create_index(op.f('ix_inspection_results_created_at'), 'inspection_results', ['created_at'], unique=False)
    op.create_index('ix_inspection_results_run_decision', 'inspection_results', ['run_id', 'decision'], unique=False)
    op.create_index('ix_inspection_results_run_defect_class', 'inspection_results', ['run_id', 'defect_class'], unique=False)


def downgrade() -> None:
    op.drop_table('inspection_results')
    op.drop_table('inspection_runs')
