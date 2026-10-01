"""create_ai_investigations_table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-10-01 18:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_investigations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('context_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('tool_calls', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('domains_consulted', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('evidence_ids_referenced', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('structured_response', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_investigations_id'), 'ai_investigations', ['id'], unique=False)
    op.create_index(op.f('ix_ai_investigations_user_id'), 'ai_investigations', ['user_id'], unique=False)
    op.create_index(op.f('ix_ai_investigations_status'), 'ai_investigations', ['status'], unique=False)
    op.create_index(op.f('ix_ai_investigations_started_at'), 'ai_investigations', ['started_at'], unique=False)
    op.create_index('ix_ai_investigations_user_time', 'ai_investigations', ['user_id', 'started_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ai_investigations_user_time', table_name='ai_investigations')
    op.drop_index(op.f('ix_ai_investigations_started_at'), table_name='ai_investigations')
    op.drop_index(op.f('ix_ai_investigations_status'), table_name='ai_investigations')
    op.drop_index(op.f('ix_ai_investigations_user_id'), table_name='ai_investigations')
    op.drop_index(op.f('ix_ai_investigations_id'), table_name='ai_investigations')
    op.drop_table('ai_investigations')
