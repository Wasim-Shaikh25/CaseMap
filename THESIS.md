# CaseMap — Thesis

> The reason this project exists. If a proposed change can't be justified from here, it
> doesn't belong here.

---

## 0. The mission (one sentence — everything hangs off this)

> A source-grounded, LLM-free-in-the-core visual case-file map for legal document
> bundles — every extracted fact traces to a verbatim source span with page/char
> provenance, and nothing is invented.

---

## 1. What this project is

- Upload a folder of case documents (plaints, affidavits, orders, contracts, notices) →
  extract entities, dates, amounts, provisions, and parties with exact page/character
  provenance → build a graph of events and connections across documents → surface a
  timeline, a click-through evidence map, and flagged (never asserted) potential
  contradictions.
- Depends on: OpenNyAI's Legal NER (mandatory extraction/labelling model, not
  generative), spaCy, PyMuPDF, an OCR ladder (Paddle→Surya→Tesseract), rapidfuzz,
  dateparser, sentence-transformers, SQLite.
- This project depends on external code (OpenNyAI `en_legal_ner_sm`/`trf` pipelines,
  spaCy, PyMuPDF, PaddleOCR/Surya/Tesseract, rapidfuzz, dateparser,
  sentence-transformers) — record any new external dependency taken on in
  `CHANGELOG.md` when added.

## 2. What it is NOT

> **Amended 2026-09-11 (CHANGELOG 62):** the last bullet below is now out of date.
> A local **FastAPI backend (`server/app.py`) and a browser frontend (`ui/`, plain
> HTML/CSS/JS — not Next.js/React Flow) are built and working** (owner reversed the
> earlier no-UI rule by direct instruction, CHANGELOG 42 / `STATUS.md`). `poc_run.py`
> still exists as the CLI path but has drifted behind the web pipeline. Still not a
> *hosted* multi-tenant product — it runs locally. Original bullet kept below unedited.

- Not a generative legal-drafting or summarization tool. It never invents text.
- Not a citation checker or a source of legal advice.
- Not built on a generic graph database (Neo4j/Graphiti rejected — SQLite bi-temporal
  edges cover the same need at hackathon/demo scale without an extra service).
- Not (yet) a hosted product — currently a CLI proof-of-concept (`scripts/poc_run.py`); FastAPI
  backend and Next.js/React Flow frontend are unbuilt, see `HEART.md` tiers.

## 3. Scope boundary

No LLM (generative model) may ever generate, paraphrase, or infer party names, dates,
amounts, provisions, events, or graph edges in the extraction/graph core — only select
verbatim spans that validate against source text with char offsets. See
`docs/spec/SCOPE.md` for the full statement.

## 4. Why this boundary is the whole product (not a preference)

The core sales pitch, informed by a real July 2026 Indian Supreme Court ruling treating
unverified AI citations as advocate misconduct, is: **"every fact links to a source page;
nothing is generated."** An LLM in the core extraction/graph loop breaks that claim even
if it would be more accurate — this is the exact failure mode the build spent 26
documented bugs avoiding (see `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §4). OpenNyAI's Legal NER is
exempt because it is an extraction/labelling model (selects spans, does not generate
text) — see `docs/research/existing-approach/CaseMap_Mandatory_ML_Layer_v7.md` §1.

## 5. What "correct" means here (the committed standard)

- **Real documents are the only valid test oracle.** Synthetic tests can all pass while
  real documents still find new bugs (this happened twice, 11 bugs). A fix is not trusted
  until verified against `real_docs/` (8 real Indian court documents) and, for anything
  touching OCR, `real_pdfs/` (6 real judgments rendered to PDF, 2 genuinely rasterised).
- **A confidently-wrong result is worse than an honest "don't know."** Every fallback
  ladder (OCR, structure, parties) must terminate in an honest low/none-confidence
  result rather than a confident guess (BUG-24 — see `FORBIDDEN.md` §E15).
- **"No effect / no result found" is a valid, successful outcome** for a document that
  genuinely has no extractable parties — it is not a failure to be papered over.
- **Every finding must be walkable back to raw source text/logs/code.**

## 6. Success

CaseMap succeeds when a real litigator or disputes team can point it at a folder of real
case documents and get a graph/timeline where every node is one click from the exact
source page it came from, with the mandatory OpenNyAI model actually installed and its
accuracy verified against `real_docs/`/`real_pdfs/` (not run in `--allow-degraded` mode).
"We built a lot of stuff" does not count — the open item in `HANDOFF.md` §8.1 (installing
and verifying the real model end-to-end) is the current bar for success, not a nice-to-have.

---

## 7. Standing constraints (what has been established — grows over time)

> Measured facts / settled decisions, not opinions. Each row **binds** future work: a
> proposal that contradicts one must say so explicitly and argue its exemption before
> being tried again.

| # | constraint | consequence for new work |
|---|---|---|
| 1 | OpenNyAI's Legal NER is mandatory, not a fallback tier; `load_opennyai_ner()` raises by default if unavailable | never make it optional without a dated owner decision |
| 2 | SQLite (no Neo4j/Graphiti) covers bi-temporal edges at this scale | do not reintroduce a graph DB service without new evidence it's needed |
| 3 | Real documents (`real_docs/`, `real_pdfs/`) are the only valid test oracle; synthetic tests alone never prove a fix | any "fixed" claim touching extraction/OCR/structure must cite a real-doc run |
| 4 | The mandatory OpenNyAI model has never been loaded with real weights in any session to date (network-blocked sandboxes) | do not claim ML-layer accuracy is verified until this happens — see `HANDOFF.md` §8.1 |

---

**Status of this document:** written 2026-09-09, at governance-init (project code and
POC predate this document). Amend by adding a dated banner above the section that
changed — never silently rewrite a past section (see `AGENTS.md` §5 / `FORBIDDEN.md`
§A5).
