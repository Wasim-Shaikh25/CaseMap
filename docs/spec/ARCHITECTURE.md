# Architecture

> The build spec and its guardrails. §-numbered so other documents can cite it
> (`AGENTS.md` §1, `FORBIDDEN.md`). Transcribed from `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §2-3 at
> governance init (2026-09-09) — that document remains the deeper source; this is the
> citable, §-numbered summary.

## §1. Overview

> Filenames below are bare (e.g. `casemap_pipeline.py`) for readability; all pipeline
> source actually lives under `src/` — see §2's table for exact paths.

```
PDFs (bundle)
   │
   ▼
[0] OCR / PAGE INGESTION — 3-tier ladder (casemap_pipeline.py)
   digital text layer / hybrid (merge) / scanned (full OCR: Paddle→Surya→Tesseract)
   │
   ▼
[1] STRUCTURE DETECTION — 5-tier ladder (layout_structure.py)
   PDF bookmarks / layout signals (font+bold+centered+gap, works on OCR too) /
   index-page inference / separator pages / one-section-per-page
   │
   ▼
[2] PARTY EXTRACTION — MANDATORY two-layer (document_profile.py + opennyai_bridge.py)
   Layer 1 (mandatory): OpenNyAI ML NER — party NAMES + rough side
   Layer 2 (mandatory): deterministic CASE_TYPE_ROLES — precise role refinement
   (falls through to a 5-tier regex-only ladder + tier-4.5 "verbatim block" only
    when a document genuinely has no ML/regex-findable parties, or when the ML
    model is running in explicit --allow-degraded development mode)
   │
   ▼
[3] DETERMINISTIC EXTRACTION — dates, amounts (+ words-to-number), provisions,
    case numbers, entities (spaCy generic NER + rapidfuzz normalization)
   │
   ▼
[4] SYMBOL TABLE (case_symbols.py) — Cursor/IDE-style: definition sites,
    aliases, find-all-references, go-to-definition, cross-document merging
   │
   ▼
[5] EFFICIENT EVENT-GRAPH CONSTRUCTION (casemap_pipeline.py)
    inverted-index blocking (avoid O(n²)) → weighted multi-signal scoring
    (entity/temporal/semantic) → top-K sparsify → Union-Find clustering →
    bi-temporal edges (SQLite, no Neo4j) with invalidation semantics
   │
   ▼
[6] OUTPUT — React Flow JSON + evidence cards + PDF.js click-to-source
```

**Why this shape:** each of the three ladders (OCR, structure, parties) was built
because a binary "works / doesn't work" check kept breaking on real documents. Each
ladder's tiers were earned one real-document failure at a time — see the full bug ledger
in `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §4.

## §2. Components

| File | Purpose |
|---|---|
| `src/casemap_pipeline.py` | OCR (3-tier), deterministic extraction (dates/amounts/provisions/entities), event detection, efficient graph construction, bi-temporal SQLite edges |
| `layout_structure.py`* | Structure detection (5-tier ladder), dual feeder (PyMuPDF font signals + OCR word-box geometry), noise filtering, contents-page detection |
| `src/document_profile.py` | Document-type profiling, party extraction (5-tier regex ladder + tier-4.5 verbatim block + mandatory ML-hybrid path), role cascade, OCR-tolerant matching, name validation |
| `case_symbols.py` | The Case Symbol Table: definition sites, alias resolution, cross-document entity merging, `go_to_definition()`/`find_all_references()` — recovered 2026-09-10 at `src/case_symbols.py` (tier-1 API only; act-name inheritance still HEART tier 2) |
| `src/opennyai_bridge.py` | Mandatory OpenNyAI Legal NER integration: eager loading, raises by default if model missing, `allow_degraded` escape hatch, offset-preserving entity extraction |
| `scripts/poc_run.py` | CLI proof runner — loads the ML model eagerly, runs all pipeline stages, writes `docs/research/existing-approach/poc_report.md` + `poc_graph.json` |

\* `layout_structure.py` recovered 2026-09-10 at `src/layout_structure.py`.
`case_symbols.py` recovered 2026-09-10 at `src/case_symbols.py`.

## §3. Data flow / control flow

See §1's diagram. Key control-flow guarantee: every stage's fallback ladder always
terminates (never crashes, never silently returns nothing without saying why), and no
stage may report a result with higher confidence than the evidence supports — see §4
guardrail G1.

## §4. Guardrails

> The structural rules that keep `FORBIDDEN.md`'s scars from recurring at the code level.

- **G1 (from FORBIDDEN §E15, BUG-24):** OCR-damaged or low-confidence input must never
  produce a high-confidence result. `_ocr_probe()`/`_ocr_mangled_ratio()`-style
  detection must run before any tier is allowed to report `confidence=high`.
- **G2 (from FORBIDDEN §C11/§E16):** No generative-LLM call path may exist anywhere in
  stages [2]-[5] above. `src/opennyai_bridge.py` must remain the only ML entry point in the
  core, and it must remain an extraction/labelling model, not a generative one.
  `load_opennyai_ner()` must keep its eager-raise-by-default behavior.
- **G3 (from FORBIDDEN §E18, BUG-26):** any OCR-path text reconstruction must preserve
  line structure (row-grouping by y-coordinate), since every line-based rule downstream
  (`is_versus_line()`, TOC detection, etc.) silently depends on it. A future refactor of
  the OCR text-join logic must be tested against `real_pdfs/`, not `real_docs/` (which
  is plain text and does not exercise this path).
- **G4 (owner, 2026-09-09):** a processing service must not retain user PDFs or the
  processed case payload after the response is returned. Results persist on the
  client. Cookies are not the graph store. OCR/temp caches must be request-scoped.
  See `docs/requirements/2026-09-09-ephemeral-client-results/`.

_Guardrails are added here as real structural rules are needed — this list grows with
the project, per the process this governance system inherited from the pre-existing
bug ledger._
