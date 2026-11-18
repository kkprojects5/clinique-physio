"""Text helpers shared by the search and the safety rules."""

import re
import unicodedata

WORD = re.compile(r"[a-z0-9]+")


def fold(text: str) -> str:
    """Lowercase without accents or typographic apostrophes: "Qu’est-ce" -> "qu'est-ce"."""
    text = unicodedata.normalize("NFKD", text.replace("’", "'"))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def words(text: str) -> list[str]:
    return WORD.findall(fold(text))
