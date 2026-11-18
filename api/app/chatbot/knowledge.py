"""The clinic's documents the chatbot answers from (B-BOT-01).

app/knowledge/fr.md and en.md hold the same sections, each with an id in brackets:

    ## [parking] Stationnement
    Mots-clés: stationnement, parking, ...
    Il n'y a pas de stationnement privé...

The "Mots-clés" / "Keywords" line helps the search and is never shown to the visitor.
These documents are public information and never contain patient data.
"""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "knowledge"
LANGUAGES = ("fr", "en")
HEADING = re.compile(r"^## \[([a-z0-9-]+)\] (.+)$")
KEYWORDS = re.compile(r"^(Mots-clés|Keywords):\s*(.*)$")


@dataclass(frozen=True)
class Passage:
    id: str
    language: str
    title: str
    text: str  # what the visitor sees
    keywords: str  # helps the search only


def parse(markdown: str, language: str) -> list[Passage]:
    passages: list[Passage] = []
    current: dict | None = None

    def close() -> None:
        if current is not None:
            text = "\n".join(current["lines"]).strip()
            passages.append(Passage(current["id"], language, current["title"], text, current["kw"]))

    for line in markdown.splitlines():
        heading = HEADING.match(line)
        if heading:
            close()
            current = {"id": heading[1], "title": heading[2].strip(), "kw": "", "lines": []}
            continue
        if current is None:
            continue  # introduction before the first section
        keywords = KEYWORDS.match(line)
        if keywords:
            current["kw"] = keywords[2]
        else:
            current["lines"].append(line)
    close()
    return passages


@cache
def passages() -> dict[str, dict[str, Passage]]:
    """{language: {id: passage}}, read once."""
    return {
        language: {p.id: p for p in parse((FOLDER / f"{language}.md").read_text("utf-8"), language)}
        for language in LANGUAGES
    }
