from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AIInvestigation(Base):
    """
    Persisted record of an AI Inspector investigation session.
    Tracks authenticated actor, query, context, tool traces, consulted domains,
    grounded evidence citations, and structured response.
    """
    __tablename__ = "ai_investigations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    context_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    tool_calls: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    domains_consulted: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_ids_referenced: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    structured_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user = relationship("User")

    __table_args__ = (
        Index("ix_ai_investigations_user_time", "user_id", "started_at"),
        Index("ix_ai_investigations_status", "status"),
    )
