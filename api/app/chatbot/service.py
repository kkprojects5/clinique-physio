"""Answer a visitor's question (B-BOT-01 to 05).

Order of the steps (each one can stop the chain):
1. mask personal details in the question (Law 25);
2. safety rules: emergency, medical request, prompt injection, personal data (safety.py);
3. search the clinic passages (search.py); nothing close enough: "I don't know";
4. optional AI wording from the passages only (writer.py), else the passage itself;
5. log the masked question and the answer for 30 days, with the sources.
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.chatbot import knowledge, search, semantic
from app.chatbot.openai_client import OpenAIError, OpenAIWriter, client_from_settings
from app.chatbot.safety import MESSAGES, Kind, classify, redact
from app.chatbot.writer import NO_ANSWER, Writer, accept
from app.core.config import settings
from app.models import ChatMessage

MAX_QUESTION_CHARS = 500
RETENTION_DAYS = 30
MASK_LABEL = re.compile(r"\[[^\]]{1,40}\]")


@dataclass
class Reply:
    id: uuid.UUID
    kind: Kind
    answer: str
    sources: list[knowledge.Passage] = field(default_factory=list)
    mode: str = "passage"


Finder = Callable[[str], list[search.Hit]]


def _decide(
    question: str, language: str, writer: Writer | None, finder: Finder | None = None
) -> Reply:
    refusal = classify(question)
    if refusal is not None:
        return Reply(uuid.uuid4(), refusal, MESSAGES[refusal][language])
    find = finder or search.search
    hits = find(MASK_LABEL.sub(" ", question))  # "[courriel/email]" is not a topic
    if not hits:
        return Reply(uuid.uuid4(), Kind.UNKNOWN, MESSAGES[Kind.UNKNOWN][language])
    by_id = knowledge.passages()[language]
    passages = [by_id[h.id] for h in hits]
    if writer is not None:
        try:
            raw = writer.write(question, language, passages)
        except Exception:  # noqa: BLE001 - any provider problem: use the passage instead
            raw = None
        if raw is not None and raw.strip() == NO_ANSWER:
            # The AI found no answer in the passages. If the keyword search agrees (nothing
            # found), say so; if it found a passage, show that passage as written (the AI can
            # be too cautious, a wrong "I don't know" is better avoided).
            keyword_hits = search.search(MASK_LABEL.sub(" ", question))
            if not keyword_hits:
                return Reply(uuid.uuid4(), Kind.UNKNOWN, MESSAGES[Kind.UNKNOWN][language], [], "ai")
            best = by_id[keyword_hits[0].id]
            return Reply(uuid.uuid4(), Kind.ANSWER, best.text, [best])
        written = accept(raw, passages)
        if written:
            cited = [p for p in passages if f"[{p.id}]" in written]
            return Reply(uuid.uuid4(), Kind.ANSWER, written, cited, "ai")
    best = passages[0]
    return Reply(uuid.uuid4(), Kind.ANSWER, best.text, [best])


def ask(
    db: Session,
    question: str,
    language: str,
    writer: Writer | None = None,
    finder: Finder | None = None,
) -> Reply:
    """Answer and log. The question must already be at most MAX_QUESTION_CHARS long."""
    masked = redact(question.strip())
    reply = _decide(masked, language, writer, finder)
    db.add(
        ChatMessage(
            id=reply.id,
            language=language,
            question=masked,
            answer=reply.answer,
            kind=reply.kind.value,
            sources=[p.id for p in reply.sources],
            mode=reply.mode,
        )
    )
    db.commit()
    delete_old_messages(db)  # keep the log at most 30 days (cheap: indexed on created_at)
    return reply


def tools_from_settings(db: Session) -> tuple[Writer | None, Finder | None]:
    """With OPENAI_API_KEY: AI wording and embedding search, each falling back on its own.

    Without it: (None, None), i.e. keyword search and the passage as written.
    """
    client = client_from_settings()
    if client is None:
        return None, None

    def find(question: str) -> list[search.Hit]:
        try:
            hits = semantic.search(db, client, question, settings.chat_min_similarity)
        except OpenAIError:
            hits = None
        return hits or search.search(question)

    return OpenAIWriter(client), find


class FeedbackError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def give_feedback(db: Session, message_id: uuid.UUID, helpful: bool) -> None:
    """Thumbs up or down on one answer, once (B-BOT-05)."""
    message = db.get(ChatMessage, message_id)
    if message is None:
        raise FeedbackError(404, "Not found.")
    if message.helpful is not None:
        raise FeedbackError(409, "Feedback already given for this answer.")
    message.helpful = helpful
    db.commit()


def delete_old_messages(db: Session, now: datetime | None = None) -> int:
    """Delete conversation rows older than 30 days (retention rule). Returns the count."""
    limit = (now or datetime.now(UTC)) - timedelta(days=RETENTION_DAYS)
    result = db.execute(delete(ChatMessage).where(ChatMessage.created_at < limit))
    db.commit()
    return result.rowcount
