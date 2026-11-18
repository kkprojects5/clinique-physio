"""Load the clinic passages into the database with their embeddings (spec section 8).

    cd api
    python -m app.chatbot.ingest

Idempotent: a passage whose text did not change keeps its embedding, so running it again
costs nothing. Passages removed from the files are removed from the database. Without
OPENAI_API_KEY the passages are stored without embeddings (keyword search still works).
It never stops the API from starting: any provider error is reported and the old rows stay.
"""

import hashlib
import logging
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chatbot.knowledge import FOLDER, LANGUAGES, Passage, passages
from app.chatbot.openai_client import OpenAIClient, OpenAIError, client_from_settings
from app.models import DocumentChunk, KbDocument

log = logging.getLogger(__name__)
TITLES = {"fr": "Base de connaissances (français)", "en": "Knowledge base (English)"}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embedding_text(passage: Passage) -> str:
    """What is turned into a vector: title, keywords and text."""
    return f"{passage.title}\n{passage.keywords}\n{passage.text}"


def ingest(db: Session, client: OpenAIClient | None) -> dict[str, int]:
    """Returns counts: added, updated, embedded, removed, unchanged."""
    counts = dict.fromkeys(("added", "updated", "embedded", "removed", "unchanged"), 0)
    for language in LANGUAGES:
        file_text = (FOLDER / f"{language}.md").read_text("utf-8")
        document = db.scalar(select(KbDocument).where(KbDocument.language == language))
        if document is None:
            document = KbDocument(
                title=TITLES[language], language=language, version="0", content_hash=""
            )
            db.add(document)
            db.flush()
        existing = {
            c.passage_id: c
            for c in db.scalars(
                select(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )
        }
        wanted = list(passages()[language].values())
        to_embed: list[DocumentChunk] = []
        for index, passage in enumerate(wanted):
            content = embedding_text(passage)
            digest = _hash(content)
            chunk = existing.pop(passage.id, None)
            if chunk is None:
                chunk = DocumentChunk(
                    document_id=document.id, passage_id=passage.id, content_hash=""
                )
                db.add(chunk)
                counts["added"] += 1
            elif chunk.content_hash != digest:
                counts["updated"] += 1
            else:
                counts["unchanged"] += 1
            chunk.chunk_index = index
            if chunk.content_hash != digest:
                chunk.content = content
                chunk.content_hash = digest
                chunk.embedding = None
            if chunk.embedding is None:
                to_embed.append(chunk)
        for chunk in existing.values():
            db.delete(chunk)
            counts["removed"] += 1
        if client is not None and to_embed:
            vectors = client.embed([c.content for c in to_embed])
            for chunk, vector in zip(to_embed, vectors, strict=True):
                chunk.embedding = vector
            counts["embedded"] += len(to_embed)
        if document.content_hash != _hash(file_text):
            # A new version each time the file changes: 1 for the first load.
            document.content_hash = _hash(file_text)
            document.version = str(int(document.version) + 1)
            document.updated_at = func.now()
    db.commit()
    return counts


def main() -> None:
    from app.db.session import SessionLocal

    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        try:
            counts = ingest(db, client_from_settings())
        except OpenAIError as error:
            db.rollback()
            print(f"Knowledge base not updated (AI provider error: {error}).", file=sys.stderr)
            return
    print("Knowledge base:", ", ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
