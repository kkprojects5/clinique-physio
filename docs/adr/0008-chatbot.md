# ADR-0008: Chatbot that answers only from clinic passages, with OpenAI and a safe fallback

- Status: Accepted (D3)
- Requirements: B-BOT-01 to 05, objective O7, BR-8, spec section 8

## Context

Visitors ask the front desk the same practical questions (hours, parking, prices, cancellation,
insurance). A chatbot can answer them at any time, but in a clinic it must never give medical
advice, must react correctly to an emergency, must not be manipulated by the visitor (prompt
injection), and must never see or reveal patient data (Law 25). The spec asks for answers
grounded in the clinic's documents, with embeddings stored in PostgreSQL (pgvector).

## Decision

1. **Knowledge base in the repository.** `api/app/knowledge/fr.md` and `en.md` hold the same
   sections, each with an id (`[parking]`). They are public information only and are reviewed
   like code. `python -m app.chatbot.ingest` loads them into `kb_documents` and
   `document_chunks`, with one OpenAI embedding (`text-embedding-3-small`, 1536 numbers) per
   passage. Unchanged passages keep their embedding (idempotent, no extra cost). It runs at each
   start of the API on Render.
2. **Safety rules first, before any search or AI call** (`app/chatbot/safety.py`): emergency
   signs get only 911 / Info-Santé 811 / 9-8-8; diagnosis, treatment and medication requests
   are refused; attempts to change the instructions and questions about a person or a file are
   refused. These answers are fixed texts, never generated.
3. **Search.** With an API key: embedding similarity in PostgreSQL (pgvector, cosine). Without a
   key, before the first ingestion, or if OpenAI fails: keyword search (TF-IDF, accents ignored).
   Below a minimum score the bot says it does not know and gives the clinic's phone number; it
   never guesses.
4. **Answer.** With an API key, OpenAI (`gpt-5.4-mini`, configurable) rewrites the answer from
   the 3 best passages only. The rules are in the system message; passages and question are
   sent as marked data, and the visitor cannot close the tags. The answer is accepted only if it
   cites a given passage id, is short, and passes the safety rules again; otherwise the passage
   itself is shown. If the AI replies `NO_ANSWER` (the passages found do not answer the
   question) and the keyword search finds nothing either, the bot says it does not know instead
   of showing a passage that only looks close; if the keyword search does find a passage, that
   passage is shown (the AI can be too cautious). Without a key, the passage is always shown as written.
5. **Privacy.** Emails, phones, health insurance, card numbers and postal codes are masked
   before the question is logged or sent to OpenAI. The chatbot has no access to any patient
   table. The log (`chat_messages`) keeps the masked question, the answer, its sources and the
   visitor's feedback for 30 days, then rows are deleted.
6. **Measured.** `api/eval/chatbot_eval.json` (40 questions, French and English) runs in CI:
   100% of emergencies and medical requests must be handled safely, at least 90% overall.
   `python scripts/eval_chatbot.py --ai` measures the OpenAI mode on the same set.

## Alternatives considered

- **AI only, no fallback.** Rejected: the chatbot would stop when the provider is down or the
  key is missing, and CI would need a paid key.
- **Let the AI decide what is medical.** Rejected: refusals and emergency answers must be
  predictable and testable, so they are fixed rules checked before the AI is called.
- **Anthropic for the answers.** Equivalent quality, but it offers no embeddings; OpenAI gives
  both with one key, matching the ERD.
- **A vector database service.** Not needed for about 40 passages: pgvector in the existing
  PostgreSQL (Neon) is enough.

## Consequences

- Works without any key (keyword mode); the key is set only in `.env` and in Render.
- Pattern rules can miss unusual wording; the evaluation set grows whenever a real answer is
  wrong, and the bot's wording always says it gives no medical advice.
- Proven by `api/tests/test_chatbot.py` and `api/tests/test_chatbot_ai.py` (no real OpenAI
  call in tests).
