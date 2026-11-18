import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.chatbot.service import MAX_QUESTION_CHARS


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    language: Literal["fr", "en"] = "fr"


class SourceOut(BaseModel):
    id: str
    title: str


class ChatOut(BaseModel):
    id: uuid.UUID
    kind: Literal["answer", "unknown", "emergency", "medical", "injection", "private"]
    answer: str
    sources: list[SourceOut]


class FeedbackIn(BaseModel):
    message_id: uuid.UUID
    helpful: bool
