"""Find the clinic passage that answers a question (keyword search, TF-IDF).

Words are compared without accents, and cut to their first 5 letters so that close forms
match ("annuler" / "annulation", "cancel" / "cancellation"). The question is compared with
the passages of BOTH languages: an English question asked on the French site still finds
its passage, and the answer is shown in the visitor's language (same ids in both files).

This search is the free fallback that always works. When an AI provider is configured, it
can be replaced by embeddings (pgvector, spec section 8) without changing the rest.
"""

import math
from collections import Counter
from dataclasses import dataclass
from functools import cache

from app.chatbot.knowledge import LANGUAGES, Passage, passages
from app.chatbot.text import words

STEM = 5
# Below this similarity, the bot says it does not know instead of guessing.
MIN_SCORE = 0.12

STOPWORDS = set(
    """
    a au aux avec ce ces c d de des du elle en est et etre il ils je j l la le les leur lui ma
    mais me mes moi mon ne nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton
    tu un une vos votre vous y est-ce quoi quel quelle quels quelles comment ai as avez
    peut peux puis-je dois doit faut fait faire si oui non bonjour merci svp est-il
    the an and or of to in on at for with is are be do does did i me my you your we our it this
    that what which how can could should would will there here have has from by as if please
    hello hi thanks am
    clinique clinic montreal physio physiotherapie physiotherapy
    """.split()
)


def tokens(text: str) -> list[str]:
    return [w[:STEM] for w in words(text) if w not in STOPWORDS and len(w) > 1]


@dataclass(frozen=True)
class Hit:
    id: str
    score: float


class Index:
    def __init__(self, items: list[Passage]) -> None:
        self._docs = {p.id: Counter(tokens(f"{p.title} {p.keywords} {p.text}")) for p in items}
        count = len(self._docs)
        frequency: Counter[str] = Counter()
        for counts in self._docs.values():
            frequency.update(counts.keys())
        self._idf = {t: math.log((1 + count) / (1 + n)) + 1 for t, n in frequency.items()}
        self._vectors = {i: self._weigh(c) for i, c in self._docs.items()}

    def _weigh(self, counts: Counter[str]) -> dict[str, float]:
        vector = {t: (1 + math.log(n)) * self._idf.get(t, 0.0) for t, n in counts.items()}
        norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        return {t: v / norm for t, v in vector.items()}

    def search(self, question: str) -> list[Hit]:
        query = self._weigh(Counter(tokens(question)))
        hits = [
            Hit(i, sum(w * vector.get(t, 0.0) for t, w in query.items()))
            for i, vector in self._vectors.items()
        ]
        return sorted((h for h in hits if h.score > 0), key=lambda h: h.score, reverse=True)


@cache
def _indexes() -> dict[str, Index]:
    return {language: Index(list(passages()[language].values())) for language in LANGUAGES}


def search(question: str, limit: int = 3) -> list[Hit]:
    """Best passages, best first: for each id, the better score of the two languages."""
    best: dict[str, float] = {}
    for index in _indexes().values():
        for hit in index.search(question):
            best[hit.id] = max(best.get(hit.id, 0.0), hit.score)
    ranked = sorted(best.items(), key=lambda item: item[1], reverse=True)
    return [Hit(i, s) for i, s in ranked[:limit] if s >= MIN_SCORE]
