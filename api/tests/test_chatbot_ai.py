"""Chatbot with the AI provider (spec section 8): OpenAI calls, ingestion, embedding search.

No real call is made: the HTTP layer and the embeddings are faked.
"""

import io
import json
import urllib.error

import pytest
from sqlalchemy import func, select

from app.chatbot import ingest, knowledge, semantic, service
from app.chatbot.openai_client import OpenAIClient, OpenAIError, OpenAIWriter
from app.models import DocumentChunk, KbDocument

DIMENSIONS = 1536
TOPICS = [("parking", "stationnement", "garer"), ("annul", "cancel"), ("assurance", "insurance")]


def fake_vector(text: str) -> list[float]:
    """A tiny fake 'meaning': one direction per topic found in the text."""
    vector = [0.0] * DIMENSIONS
    folded = text.lower()
    for direction, words in enumerate(TOPICS):
        vector[direction] = float(sum(folded.count(w) for w in words))
    vector[DIMENSIONS - 1] = 0.05  # never a zero vector
    return vector


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.embedded = []

    def embed(self, texts):
        if self.fail:
            raise OpenAIError("URLError")
        self.embedded.extend(texts)
        return [fake_vector(t) for t in texts]


# --- HTTP calls to OpenAI -----------------------------------------------------------------------


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def recording_opener(answer):
    sent = []

    def opener(request, timeout):
        sent.append((request, timeout))
        return FakeResponse(json.dumps(answer).encode())

    return opener, sent


def test_chat_call_sends_rules_as_system_and_data_as_user():
    reply = {"choices": [{"message": {"content": "Rue Rivard [parking]."}}]}
    opener, sent = recording_opener(reply)
    client = OpenAIClient("sk-test-key", "chat-model", "embed-model", 7, opener)
    passage = knowledge.passages()["fr"]["parking"]

    answer = OpenAIWriter(client).write("Où se garer ?", "fr", [passage])

    assert answer == "Rue Rivard [parking]."
    request, timeout = sent[0]
    assert request.full_url == "https://api.openai.com/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer sk-test-key"
    assert timeout == 7
    payload = json.loads(request.data)
    assert payload["model"] == "chat-model"
    system, user = payload["messages"]
    assert system["role"] == "system" and "Answer in French" in system["content"]
    assert "NO_ANSWER" in system["content"]
    assert user["role"] == "user"
    assert '<document id="parking"' in user["content"]
    assert "<question>\nOù se garer ?\n</question>" in user["content"]


def test_embeddings_come_back_in_the_order_asked():
    opener, sent = recording_opener(
        {"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]}
    )
    client = OpenAIClient("sk-test-key", "chat-model", "embed-model", 7, opener)

    assert client.embed(["a", "b"]) == [[1.0], [2.0]]
    assert json.loads(sent[0][0].data) == {"model": "embed-model", "input": ["a", "b"]}


def test_provider_errors_never_reveal_the_key_or_the_question():
    def opener(request, timeout):
        raise urllib.error.URLError("sk-test-key Où se garer ?")

    client = OpenAIClient("sk-test-key", "chat-model", "embed-model", 7, opener)

    with pytest.raises(OpenAIError) as error:
        client.chat("system", "Où se garer ?")
    assert str(error.value) == "URLError"


# --- Ingestion ----------------------------------------------------------------------------------


def chunk_count(db, with_embedding=False):
    query = select(func.count()).select_from(DocumentChunk)
    if with_embedding:
        query = query.where(DocumentChunk.embedding.is_not(None))
    return db.scalar(query)


def test_ingestion_stores_every_passage_with_an_embedding(db):
    total = sum(len(p) for p in knowledge.passages().values())

    counts = ingest.ingest(db, FakeClient())

    assert counts["added"] == counts["embedded"] == total
    assert chunk_count(db) == chunk_count(db, with_embedding=True) == total
    assert db.scalar(select(func.count()).select_from(KbDocument)) == 2


def test_ingestion_again_changes_nothing_and_costs_nothing(db):
    ingest.ingest(db, FakeClient())
    client = FakeClient()

    counts = ingest.ingest(db, client)

    assert counts["added"] == counts["embedded"] == counts["updated"] == 0
    assert client.embedded == []


def test_changed_and_removed_passages_are_updated(db, monkeypatch):
    ingest.ingest(db, FakeClient())
    current = knowledge.passages()
    fr = dict(current["fr"])
    fr["parking"] = knowledge.Passage("parking", "fr", "Stationnement", "Nouveau texte.", "")
    del fr["children"]
    monkeypatch.setattr(ingest, "passages", lambda: {"fr": fr, "en": current["en"]})
    client = FakeClient()

    counts = ingest.ingest(db, client)

    assert counts["updated"] == 1 and counts["removed"] == 1 and counts["embedded"] == 1
    assert "Nouveau texte." in client.embedded[0]


def test_ingestion_without_a_key_stores_passages_without_embeddings(db):
    ingest.ingest(db, None)

    assert chunk_count(db) > 0
    assert chunk_count(db, with_embedding=True) == 0


# --- Embedding search ---------------------------------------------------------------------------


def test_embedding_search_finds_the_closest_passage(db):
    ingest.ingest(db, FakeClient())

    hits = semantic.search(db, FakeClient(), "Where do I leave my car? parking", 0.3)

    assert hits[0].id == "parking"


def test_embedding_search_waits_for_the_first_ingestion(db):
    assert semantic.search(db, FakeClient(), "parking", 0.3) is None


def test_with_a_key_the_chat_uses_embeddings_and_ai_wording(db, monkeypatch):
    ingest.ingest(db, FakeClient())
    monkeypatch.setattr(service, "client_from_settings", lambda: FakeClient())

    writer, finder = service.tools_from_settings(db)

    assert isinstance(writer, OpenAIWriter)
    assert finder("parking question")[0].id == "parking"


def test_provider_down_falls_back_to_keyword_search(db, monkeypatch):
    ingest.ingest(db, FakeClient())
    monkeypatch.setattr(service, "client_from_settings", lambda: FakeClient(fail=True))

    _, finder = service.tools_from_settings(db)

    assert finder("Où puis-je me garer ?")[0].id == "parking"


def test_without_a_key_there_is_no_ai_at_all(db, monkeypatch):
    monkeypatch.setattr(service, "client_from_settings", lambda: None)

    assert service.tools_from_settings(db) == (None, None)
