# Scope

> The boundary: what this project is in scope to do, and what it is forever out of scope
> to do, until an explicit, dated owner decision changes it. Cited before any change that
> could widen scope (`AGENTS.md` §2, `FORBIDDEN.md` §C).

## In scope

- OCR ingestion of a document bundle (digital text / hybrid / fully scanned), via the
  3-tier OCR ladder.
- Structure detection (bookmarks / layout signals / index inference / separator pages /
  per-page fallback), via the 5-tier structure ladder.
- Party extraction via the mandatory two-layer approach: OpenNyAI Legal NER (names +
  rough side) combined with deterministic `CASE_TYPE_ROLES` refinement (precise role),
  with a regex-only ladder as the documented degraded/no-ML fallback path.
- Deterministic extraction of dates, amounts (incl. words-to-number), provisions, case
  numbers, and generic entities — always as verbatim, offset-validated spans.
- Cross-document entity/event linking via inverted-index blocking, weighted multi-signal
  scoring, and bi-temporal SQLite edges — flagging potential contradictions, never
  asserting them.
- A case symbol table (definition sites, aliases, find-all-references) in the spirit of
  an IDE's symbol table, applied to case documents.
- Eventually: a FastAPI backend and a React Flow + PDF.js frontend for the above
  (unbuilt — see `HEART.md` tier 3). When that service exists, processing is
  **ephemeral**: a multi-document upload is processed, the payload is returned to
  the client for local persistence, and uploaded PDFs plus server working copies
  are deleted after the response. The server is not a case-file archive. See
  `docs/requirements/2026-09-09-ephemeral-client-results/` and amendment below.

## Forever out of scope (unless the owner explicitly amends this file, dated)

No LLM (generative model) may ever generate, paraphrase, or infer party names, dates,
amounts, provisions, events, or graph edges in the extraction/graph core — only select
verbatim spans that validate against source text with char offsets. OpenNyAI's Legal NER
is an extraction/labelling model, not generative, and is exempt; any future model added
to the core must be extraction/labelling only, never generative, and this decision
requires an explicit dated owner decision to change.

Also explicitly out of scope, per the original product-scoping work
(`docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §1, `blueprint1.md`/`blueprint2.md` if present):

- Legal advice, citation checking, or any output presented as a legal conclusion rather
  than a flagged/sourced fact.
- A generic graph database service (Neo4j/Graphiti) — SQLite bi-temporal edges cover the
  need at this scale; reintroducing one needs new evidence, not just preference.
- A broad, general-purpose "CaseGraph"-style product — this project was deliberately
  narrowed from that broader concept to a disciplined MVP for a solo-litigator/B2B
  disputes-team scope.

## Amendment log

- **2026-09-09 — Ephemeral processing (owner).** Uploaded documents are processed and
  the result is returned to the user's machine (client storage such as IndexedDB or a
  downloaded JSON file — **not** cookies for the graph). PDFs and server-side working
  copies are removed after processing. This does not skip `HEART.md` tier order: the
  upload UI remains unbuilt until tier 1 is proven. Full requirement:
  `docs/requirements/2026-09-09-ephemeral-client-results/`.
