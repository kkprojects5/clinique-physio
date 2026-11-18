"""Public chatbot (B-BOT-01 to 05). No login; rate-limited per IP (NFR-05)."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.chatbot import service
from app.core import rate_limit
from app.core.rate_limit import limiter
from app.dependencies import DbSession
from app.schemas.chat import ChatIn, ChatOut, FeedbackIn, SourceOut

router = APIRouter(prefix="/chat", tags=["chatbot"])


@router.post("/messages")
@limiter.limit(rate_limit.CHAT_LIMIT)
def ask(request: Request, body: ChatIn, db: DbSession) -> ChatOut:
    """Ask a practical question. Answers come only from the clinic's documents.

    `kind` says what happened: `answer`, `unknown` (not in the documents), `emergency`
    (911 / 811 / 9-8-8 only), `medical` (diagnosis or treatment refused), `injection` or
    `private` (refused). Never send health information: the chat is not a medical service.
    """
    writer, finder = service.tools_from_settings(db)
    reply = service.ask(db, body.message, body.language, writer, finder)
    return ChatOut(
        id=reply.id,
        kind=reply.kind.value,
        answer=reply.answer,
        sources=[SourceOut(id=p.id, title=p.title) for p in reply.sources],
    )


@router.post("/feedback", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(rate_limit.CHAT_LIMIT)
def feedback(request: Request, body: FeedbackIn, db: DbSession) -> Response:
    """Was this answer helpful? Once per answer (B-BOT-05)."""
    try:
        service.give_feedback(db, body.message_id, body.helpful)
    except service.FeedbackError as error:
        raise HTTPException(error.status_code, error.detail) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
