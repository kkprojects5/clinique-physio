"""Similarity search with embeddings in PostgreSQL (pgvector), spec section 8.

The question is turned into a vector by the AI provider and compared with the stored passage
vectors (cosine similarity). Like the keyword search, both languages are searched and the
best score per passage id is kept.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chatbot.openai_client import OpenAIClient
from app.chatbot.search import Hit
from app.models import DocumentChunk


def search(
    db: Session, client: OpenAIClient, question: str, min_similarity: float, limit: int = 3
) -> list[Hit] | None:
    """Best passages, or None when no embeddings are stored yet (use keyword search)."""
    stored = db.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.embedding.is_not(None))
    )
    if not stored:
        return None
    vector = client.embed([question])[0]
    distance = DocumentChunk.embedding.cosine_distance(vector)
    rows = db.execute(
        select(DocumentChunk.passage_id, (1 - distance).label("similarity"))
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit * 2)
    ).all()
    best: dict[str, float] = {}
    for passage_id, similarity in rows:
        best[passage_id] = max(best.get(passage_id, 0.0), float(similarity))
    ranked = sorted(best.items(), key=lambda item: item[1], reverse=True)
    return [Hit(i, s) for i, s in ranked[:limit] if s >= min_similarity]
