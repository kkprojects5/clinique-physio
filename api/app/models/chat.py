"""Chatbot conversation log (B-BOT-04, B-BOT-05).

Questions are stored with personal details masked, and every row is deleted after 30 days
(data-classification.md). The log is used to measure answer quality and read feedback.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

CHAT_KINDS = ("answer", "unknown", "emergency", "medical", "injection", "private")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('answer', 'unknown', 'emergency', 'medical', 'injection', 'private')",
            name="ck_chat_messages_kind",
        ),
        CheckConstraint("language IN ('fr', 'en')", name="ck_chat_messages_language"),
        CheckConstraint("mode IN ('passage', 'ai')", name="ck_chat_messages_mode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    language: Mapped[str] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text)  # personal details masked
    answer: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    mode: Mapped[str] = mapped_column(Text, server_default=text("'passage'"))
    helpful: Mapped[bool | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
