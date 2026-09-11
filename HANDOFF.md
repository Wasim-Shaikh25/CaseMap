# Project handoff

**Written:** 2026-09-09 (governance initialization)
**Last substantially updated:** 2026-09-10 (entry 40: real petition test, F-10/F-11/F-12,
`important_lines.py` shipped, MiniLM default, `make_similarity_fn()` cache-key
bug fixed — session close-out)
**For:** the next agent (or human) picking this project up cold.
**Read after:** `FORBIDDEN.md`, then `AGENTS.md`. Those are binding; this file is
orientation.

This is the single document that says where the project actually stands, what is broken,
what is proved, what you may not do, and what to do first.

---

## 0. UI boundary — read this first if you are Cursor or any coding agent

**SUPERSEDED 2026-09-10 (later, F-13+).** The no-FastAPI rule below (originally
dated 2026-09-10 earlier the same day) was an explicit, dated owner instruction —
and the owner has now explicitly reversed it, also dated the same day: *"We are now
building designing full working UI as backend is full ready"* / *"server means our
backend"*. A real local backend now exists. Treat this the same way the original
rule was treated: as a dated fact to work from, not a preference to infer around.

**What actually exists now:** `server/app.py` (FastAPI) + `ui/` (vanilla HTML/CSS/JS,
no framework, no build step) — a real local web app, not a published Artifact.
`server/app.py` is a thin HTTP wrapper around the *existing* `src/` pipeline
functions (`extract_pages`, `segment_document_layered`, `extract_deterministic`,
`extract_entities`, `detect_events`, `extract_important_lines`,
`extract_parties_hybrid`, the graph-building stage, `case_symbols` for
cross-document provision linking) — it does not reimplement any pipeline logic, only
orchestrates + serializes. Verified end-to-end against real `testdata/` documents
this session, single-doc and the 3-doc insolvency bundle (cross-doc edges and
cross-doc provision linking both confirmed in the live response). Run with:
`uvicorn server.app:app --port 8756` (from `.venv`, project root) — serves the API
at `/api/*` and the `ui/` folder itself at `/`.

**No-server-retention (F-5) still applies, and is now load-bearing, not aspirational:**
`server/app.py`'s docstring states the contract — uploads land in a per-request temp
dir, deleted in a `finally` block every time, nothing is written to
`poc_graph.json`/`casemap.db`/anywhere on disk, and the server keeps no in-memory
history across requests. The browser's own `localStorage` (`ui/app.js`, `Store`) is
the *only* persistence layer — per the owner's explicit framing, this holds whether
the server is `127.0.0.1` today or a real internet-facing deployment later; the
contract is "never persist the document," not "only promise that on localhost."

**What this means for your work:** pipeline correctness, extraction quality, and
`src/` work generally are unaffected and still yours — `server/app.py` only calls
existing functions, it doesn't ask for new pipeline behavior. If you touch a
function's signature or return shape that `server/app.py` relies on (listed above),
check `server/app.py` doesn't break, the same way you'd check `poc_run.py`. New
frontend/API work belongs in `ui/`/`server/`, not scattered elsewhere.

---

## 1. The answer, in one page

**This is not a brand-new codebase — it's an existing, heavily-tested POC that got a
governance layer added, then two full days of research/POC/implementation work on top
of that (2026-09-09 to 2026-09-10).** The pipeline code, the 26-bug ledger, the
mandatory ML layer, and a real POC run predate governance (see
`docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md`, the pre-governance
handoff, for the full technical picture — still authoritative for implementation
detail not covered here).

**Twelve requirement folders exist. Current state of each:**

| Folder | Status |
|---|---|
| `2026-09-09-ephemeral-client-results` | T1 done (spec recorded — `SCOPE.md` amendment, `ARCHITECTURE.md` G4, `FINDINGS.md` F-5). T2-T4 **not started** — blocked on Tier 1/2 *and* the UI boundary in §0. |
| `2026-09-09-verbatim-fallback-nodes` | **T1-T5 all done.** Fallback nodes, ML role-instability trigger, identity-key normalization, confidence rendering, `poc_run.py` wiring — all implemented and tested. |
| `2026-09-09-structure-and-embedding-layers` | T1-T2 done; **T4 done** (`poc_graph.json` `documents[].structure_tier`). **T3 (Qwen via `sentence_transformers`) not started** — owner deprioritized (evaluation only). |
| `2026-09-10-entity-extraction-header-noise` | T1-T4 done, but left a residual 24 false cross-document edges — see next row. |
| `2026-09-10-residual-false-edges` | Follow-up to the above. **Done** — false cross-document edges 24→**0**, correct bundle edges 14→**16**. `FINDINGS.md` F-8 is effectively closed by this folder, not the first one. |
| `2026-09-10-wire-opennyai-ner` | **T1-T3 done** (installer + `venv_ner`). Follow-up: **`2026-09-10-ner-project-default` T1-T2 done** — project-root `.venv` is now the documented default; `load_opennyai_ner()` succeeds there without `--allow-degraded`. |
| `2026-09-10-rhetorical-role-cues` | **T1-T2 done** after F-7 fixes. `src/rhetorical_roles.py` — heuristic only. |
| `2026-09-10-party-ladder-header-furniture` | **T1-T3 done.** `Author:`/`CITATION` no longer become parties (layered + hybrid). FINDINGS F-9. |
| `2026-09-10-ner-project-default` | **T1-T2 done.** `.venv` + README. |
| `2026-09-10-case-symbol-table` | **T1-T3 done.** `src/case_symbols.py`. |
| `2026-09-10-important-lines` | **Done, written retroactively** — see the folder's own `REQUIREMENTS.md` process note. `src/important_lines.py`, F-11/F-12. |
| `2026-09-10-petition-followups` | **T1-T8 done (F-13).** §9.1 blocked on a second real petition (none in corpus). Official-form headings + layered cause-title + digital multi-page PDF split shipped. |

**Note on `2026-09-10-important-lines` — implemented ahead of its own folder, but shipped and
tested anyway on the owner's direct, dated go-ahead, and not through the usual
Cursor/`src/` path:** `src/important_lines.py` (F-11/F-12) and 3 real bugs fixed
directly in `src/casemap_pipeline.py` (`ANNEXURE_PATTERN`, `_segment_by_headings()`)
**were implemented by Claude, not Cursor** — an explicit exception to the usual
"Cursor owns `src/`" split. Do not duplicate them. F-13 follow-ups (this session)
are Cursor `src/` work on top of that, not a rewrite of `important_lines.py`.

**Thirteen findings logged** (`FINDINGS.md` F-1 through F-13) — see `FINDINGS.md`
itself for full detail/decisions/evidence links. One-line map:
- **F-1:** generic small LLM (Qwen2.5 1.5B) tested — evidence *for* the
  no-generative-LLM-in-the-core rule (non-termination + noise-as-fact failures).
- **F-2:** `en_legal_ner_sm` installed and run for the first time ever — works, fast,
  ~3.6% role-label noise, confirms why Layer 2 refinement is mandatory.
- **F-3:** fallback-nodes mechanism + edge formation validated → became the
  `verbatim-fallback-nodes` requirement (now T1-T5 done).
- **F-4:** Docling + Qwen3-Embedding compose correctly, including against genuinely
  scanned/degraded PDFs → became the `structure-and-embedding-layers` requirement.
- **F-5:** owner constraint — no server retention of uploads, ephemeral processing
  only → `ephemeral-client-results` requirement (T1 done, T2-4 blocked, see §0).
- **F-6:** OpenNyAI's real rhetorical-role classifier API exists now (an outdated
  handoff note said otherwise) but is **not installable on this machine** — an
  unmaintained 2019 dependency (`pytorch-transformers`) needs a Rust `tokenizers`
  build that fails even with a period-matched old Rust toolchain installed. Not a
  governance objection (it's a non-generative classifier) — a real Windows toolchain
  wall. Unresolved; WSL/Linux untried.
- **F-7:** deterministic rhetorical-role cue tagging — two POC bugs **fixed** in
  `src/rhetorical_roles.py` (generic `"in the case of"` removed; PRECEDENT does
  not carry; fuzzy match for longer cues). Heuristic, not the F-6 classifier.
- **F-8:** dense fact-node coverage + a real bug in `extract_entities()` (generic
  spaCy NER mislabelling header-block boilerplate as entities) — **now fixed** via
  `entity-extraction-header-noise` + `residual-false-edges` (false edges 60→0).
- **F-9:** `extract_parties_layered()` (and hybrid ML lists) treated indiankanoon
  `Author:` / `CITATION` as parties — **fixed** without skipping the cause title
  (`party-ladder-header-furniture`).
- **F-10:** Docling proven on `real_pdfs/` (real headings, both digital and
  OCR'd-scanned) — real POC: `temp/2026-09-10-docling-qwen-poc/poc_docling.py`,
  `poc_docling_headings.py`. Qwen3-Embedding separated same-matter docs better
  than MiniLM in a small early test (`poc_qwen.py`, `poc_qwen_only.py`) — later
  superseded in practice by F-12's real-hardware speed measurement. Found and
  found and **fixed** a real `make_similarity_fn()` model-switch caching bug —
  `_EMBED`/`_EMBED_CACHE` weren't keyed by `model_name` (entry 40).
- **F-11:** extractive "important lines" (embedding centrality) beat every
  generative summarizer tested — 5 models, 60M-568M
  (`temp/2026-09-10-docling-qwen-poc/poc_important_lines.py`,
  `poc_more_models.py`, `poc_more_models2.py`, `poc_pegasus_only.py`), every one
  distorted at least one real fact at least once (a hallucinated date, two
  sentences fused into a claim neither made, a reversed procedural outcome). A
  hybrid Docling+Qwen POC (`poc_hybrid_lexrank.py`) additionally confirmed
  proper LexRank (power-iteration centrality) picks the same sentence as the
  simpler mean-similarity method on real documents — no reason to prefer the
  heavier algorithm. **Implemented** as `src/important_lines.py`.
- **F-13:** HANDOFF §9 follow-ups. No second petition in `testdata/`/`real_pdfs/`.
  MiniLM/Qwen reconfirm 28/47 on the BCI filing. Official SC form headings
  (`MAIN PRAYER`, `GROUNDS FOR INTERIM RELIEF`, `Question(s) of Law`) now
  match; lettered prefixes still unmatched (no real hit). Layered petition
  parties now keep BCI/UOI/UGC and drop PAPER BOOK/contact lines. Hybrid
  still `ml_role_unstable`. Multi-page digital PDF heading split verified.
  Evidence: `temp/2026-09-10-petition-followups/`.
  (not a published judgment — owner-supplied, personal, processed only in
  `temp/2026-09-10-real-petition-run/`, never added to `testdata/`) found and
  fixed 3 real bugs: (1) `ANNEXURE_PATTERN` missed every numbered heading
  (`VII. GROUNDS`, `XI. INTERIM PRAYER`) — real petitions number these
  sections; (2) deeper — `_segment_by_headings()` only ever created a section
  boundary at a PAGE boundary, so a `.txt` input (loaded as one page) collapsed
  ALL headings into one section regardless of (1)'s fix; (3) Qwen3-Embedding is
  ~112x slower than MiniLM per sentence on real CPU hardware (32.7s vs 0.29s
  for 50 sentences) — measured, not estimated. Re-tested Qwen-vs-MiniLM pick
  agreement on the (2)-fixed real segmentation: 28/47 (60%) same, spot-checked
  disagreements as consistently real/substantive either way (not a correctness
  regression, more like two reasonable rankers on paragraphs with more than one
  legitimately central sentence). Owner's dated decision: switched
  `important_lines.EMBED_MODEL_NAME` to MiniLM. Real before/after on the same
  petition: 1131s → 354s (segmentation fix alone) → **16.5s** (MiniLM switch),
  48 real IMPORTANT_LINE nodes across 10 correctly-labeled sections including
  16 genuine grounds-of-challenge sentences, same output shape throughout. 16
  new tests across this finding's 3 bugs.

**`testdata/`** — 22 real Indian court judgments (indiankanoon.org, public-domain),
including a genuinely connected 3-document same-matter bundle (docs 09/21/22) — see
`testdata/README.md`. Reusable for any future POC/testing work.

**`real_pdfs/`** — the same 22 documents as real PDFs (15 digital, 7 genuinely
scanned/degraded, verified zero-text-layer), validated end to end against the real
mandatory-model pipeline (37 pages, 12 genuinely OCR'd). Built 2026-09-10 specifically
to support Tier 1 proof work — see `real_pdfs/README.md` and §6.

**POC/temp folders this session, kept for reference (none are `src/`, all
findings above trace back to real scripts + real output in these):**
- `temp/2026-09-10-docling-qwen-poc/` — F-10/F-11 (Docling, Qwen, LexRank,
  5-model summarizer comparison). `venv_docling_qwen/` is a real working
  Docling+sentence-transformers environment if you need to re-run any of it.
- `temp/2026-09-10-important-lines-e2e/` — first real 22-document
  `--important-lines` run (F-11) + the batching-speedup benchmark (F-12,
  `bench_batching.py`, real 2.26x measured).
- `temp/2026-09-10-real-petition-run/` — F-12's real petition test: input,
  `poc_report.md`/`poc_graph.json` at each stage (pre-fix, post-segmentation-fix,
  post-MiniLM-switch), plus `compare_models_post_fix.py` (the real Qwen-vs-MiniLM
  agreement test on correctly-segmented paragraphs). The petition document
  itself is NOT in this folder's `.txt` form in the repo root or `testdata/` —
  it stays under `temp/` only, per the owner's privacy (personal document).
- `temp/2026-09-10-petition-followups/` — F-13 §9 follow-ups (corpus sweep,
  MiniLM/Qwen reconfirm, official SC form PDFs, parties/symbols, multi-page
  PDF). Personal petition not copied to `testdata/`.
- `temp/2026-09-10-ui-poc/` — the published UI (`casemap_viewer.html`) and the
  real pipeline output it renders.
- `docs/requirements/2026-09-10-important-lines/` — written retroactively;
  its own `REQUIREMENTS.md` explains why (see the note above §1's table).

**First thing to do:** see §9 (Owner-approved next steps for Cursor) below —
concrete, prioritized, not just "resume normal work."

---

## 2. Environment and operating constraints

| thing | value |
|---|---|
| project root | `C:\python_project\CaseMap` |
| datastore | SQLite (`casemap.db`) — case symbol table + bi-temporal event-graph edges. No Neo4j. |
| git | **Not a git repo as of 2026-09-10.** Deliberately deferred by the owner — they will init it themselves. |
| stack | Python 3.11+; PyMuPDF, PaddleOCR/Surya/Tesseract, OpenCV, spaCy + OpenNyAI legal NER (mandatory), rapidfuzz, dateparser, sentence-transformers, SQLite. FastAPI backend and Next.js/React Flow/PDF.js frontend **not to be started — see §0.** |
| tests | `pytest tests/` — 57 passed, 1 skipped as of entry 41. |
| dependency manifests | `requirements.txt` (core pipeline, with the exact spaCy/pydantic/numpy/thinc chain verified working for `en_legal_ner_sm`) and `requirements-docling.txt` (optional, ~1.5GB, structure-and-embedding-layers work only — never tested combined with `requirements.txt` in one environment). |
| **Ollama** | Installed, with `qwen2.5:1.5b` and `qwen3-embedding:0.6b` pulled (used for F-1/F-4 research — neither wired into `src/`). |
| **venvs** | Multiple standalone venvs exist under `temp/*/venv_*` for POC/research work, each with its own dependency set — do not assume any one has everything installed. `temp/2026-09-09-mini-llm-poc/venv_ner/` is the one with `en_legal_ner_sm` working and is reused across sessions for real-pipeline test runs. |

**Traps already hit:** see the full 26-bug ledger in `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §4 —
do not re-derive these from scratch. The two worth memorizing before touching OCR or
party extraction: BUG-24 (OCR garbage extracted as a party at high confidence) and
BUG-26 (OCR line-break loss silently broke every line-based rule). F-4 independently
observed the same *class* of OCR word-boundary damage in Docling's own OCR path —
confirms this is structural, not specific to this project's OCR stack.

**Windows-specific dependency traps hit this project** (each has a documented
recipe — read before re-fighting them):
- `en_legal_ner_sm` install: two pre-existing conflicting spaCy installs, an invalid
  PEP 440 version in the HuggingFace wheel, a `pydantic`/Python 3.11 incompatibility
  in spaCy 3.2.x. Recipe: `docs/research/new-directions/mini-llm-extraction-assessment.md`
  Part 2, or just run `scripts/install_en_legal_ner_sm.py` (already automates it).
- `opennyai` package (F-6): needs Rust to build `tokenizers`, and the crate's 2019-era
  code doesn't compile against a modern Rust toolchain even after installing one — an
  old pinned toolchain was tried and still failed. Unresolved; do not re-attempt
  without a new idea (WSL, a prebuilt wheel mirror) — repeating the same install is a
  known dead end.

---

## 3. The map — what exists and where

See `AGENTS.md` §9 for the full folder map. Pipeline code lives under `src/`
(`casemap_pipeline.py`, `document_profile.py`, `opennyai_bridge.py`,
`layout_structure.py`, `rhetorical_roles.py`, `case_symbols.py`,
`important_lines.py` — the last shipped 2026-09-10, F-11/F-12); `scripts/` has
`poc_run.py` (now takes `--important-lines`) and `install_en_legal_ner_sm.py`;
tests under `tests/`; the deep technical handoff, ML-layer spec, and latest
pre-governance POC output live under `docs/research/existing-approach/`.

**Added since governance init:**
- `testdata/` — 22 real documents.
- `docs/research/new-directions/` — `mini-llm-extraction-assessment.md` (F-1, F-2),
  `layer-additions-assessment.md` (F-4).
- `docs/requirements/` — 11 folders, see §1's table.
- `docs/plan/verbatim-fallback-graph-nodes.md` — the plan behind the fallback-nodes requirement.
- `temp/2026-09-09-mini-llm-poc/` — F-1/F-2 scripts + a working `venv_ner/`.
- `temp/2026-09-09-verbatim-fallback-poc/` — F-3 scripts.
- `temp/2026-09-09-layer-additions-poc/` — F-4 scripts + a working `venv_docling/` (~1.5GB).
- `temp/2026-09-10-fact-nodes-poc/`, `temp/2026-09-10-node-count-check/` — F-8 scripts (superseded by the real `src/` fix, kept for the raw numbers).
- `temp/2026-09-10-rhetorical-role-poc/` — F-6/F-7 scripts (abandoned installs, cue-tagger POC).
- `temp/2026-09-10-ui-poc/` — **the published UI** (`casemap_viewer.html`), the real `poc_graph.json`/`full_case_data.json` it renders, and the scripts that generated them (`gather_full_data.py`).
- `requirements.txt`, `requirements-docling.txt` — added for Cursor-readiness (see §2).

---

## 4. What sessions have done

- **2026-09-09, early** — Governance scaffolded. No code changed.
- **2026-09-09, mid** — Pre-existing pipeline files relocated into `src/`/`scripts/`/`tests/`, no logic changes.
- **2026-09-09 through 2026-09-10** — Research (F-1 through F-8), real implementation
  work (fallback-nodes T1-T5, structure-and-embedding-layers T1-T2, the two
  entity-noise fix rounds, the NER install path), and this file's own UI (§0). Two
  agents have been working this project concurrently — Cursor on `src/`
  implementation, this session on research/requirements/UI — coordinating entirely
  through this governance system (`CHANGELOG.md`, `FINDINGS.md`, `TRACKER.md` files),
  not direct communication. Check `CHANGELOG.md` for the full, dated, append-only
  record before assuming what's been done — this section is a summary, that file is
  the source of truth.

---

## 5. Governance — what you may not do

See `FORBIDDEN.md` in full. The ones that bind day to day:

- Never make a change without a stated reason that predates seeing the result.
- Never make a change without appending to `CHANGELOG.md` and updating `STATUS.md`.
- Never write code before a `docs/requirements/<date>-<slug>/` folder exists for it.
- Never let a generative LLM into the extraction/graph core (`FORBIDDEN.md` §C11) —
  F-1 is evidence for this rule, not a proposal to revisit it.
- Never make OpenNyAI's Legal NER optional again without a dated owner decision
  (`FORBIDDEN.md` §E16).
- Never trust a fix against synthetic tests alone — real documents are the oracle
  (`FORBIDDEN.md` §E17) — this is why `testdata/` and the connected 09/21/22 bundle
  exist.
- **Never build UI** (§0) — new as of 2026-09-10, binds the same as any other item here.

---

## 6. Verified invariants — re-check these before trusting this file

- **`real_pdfs/` now exists** (2026-09-10, root of the working directory) — 22 PDFs
  (15 digital, 7 genuinely scanned/degraded with a verified zero-character text
  layer), built from the same `testdata/` content, validated end to end against
  `scripts/poc_run.py --ocr tesseract` with the real mandatory model (37 pages, 12
  genuinely OCR'd). See `real_pdfs/README.md`. `real_docs/` (plain-text) is still not
  present — `testdata/` remains the closest usable substitute for that specific
  format.
- Files referenced in `CaseMap_AGENT_HANDOFF.md` but **still not found**:
  `test_logic.py`, `test_layout.py`, `test_profile_symbols.py`,
  `dryrun_real.py`, `dryrun_fallbacks.py`, `blueprint1.md`, `blueprint2.md`,
  `make_real_pdfs.py`, `real_docs/`. (`layout_structure.py` recovered 2026-09-10;
  `real_pdfs/` built 2026-09-10; `case_symbols.py` recovered 2026-09-10.)
- `en_legal_ner_sm` loads by default in **project `.venv`** (`ner-project-default`)
  and in `venv_ner`. Do not use system Python. Fresh env: `pip install -r
  requirements.txt` then `scripts/install_en_legal_ner_sm.py`.
- `important_lines.py`'s default embedding model is **MiniLM** (`all-MiniLM-L6-v2`),
  not Qwen — changed 2026-09-10 (F-12, CHANGELOG entry 38), a dated owner
  decision after measuring a real ~112x per-sentence speed gap on real
  hardware. `important_lines.EMBED_MODEL_NAME` is the one constant if this
  needs revisiting; do not change it back without another dated decision.
- `casemap_pipeline.ANNEXURE_PATTERN` and `_segment_by_headings()` changed
  2026-09-10 (F-12) — verified against `testdata/`'s existing match (`INDEX`,
  unchanged) and a real filed petition (10 real headings now correctly split
  into 10 real sections, was 1). F-13 additionally matches official SC form
  headings (`MAIN PRAYER`, `GROUNDS FOR INTERIM RELIEF`, `INTERIM RELIEF`,
  `Question(s) of Law`). Lettered/parenthetical prefixes (`A. GROUNDS`,
  `(vii) GROUNDS`) are still unmatched — no real document used them.
  Multi-page digital PDF heading detection was verified on a heading-paginated
  copy of the real petition (`temp/2026-09-10-petition-followups/`); scanned
  OCR petition PDFs are still untested.

---

## 7. Open items — summary

See §1's tables for the authoritative state of all 12 requirement folders and 13
findings. Remaining unblocked pipeline work (as of this section's last edit,
2026-09-10):
1. `structure-and-embedding-layers` T3 — Docling structure detection is proven
   (F-10) but still not installed by default; wiring it into the actual `.venv`
   default pipeline (vs. evaluation-only in a side venv) needs a dated owner
   decision (§10) before it's a `requirements.txt` pin.
2. See §9 for the specific, owner-approved next steps that came out of this
   session's real-petition test (F-12) — these are more concrete and more
   immediately valuable than #1 above.

`make_similarity_fn()`'s model-switch caching bug (F-10) is **fixed** as of
entry 40 — no longer open.

`CaseMap_AGENT_HANDOFF.md` §7 ("Open gaps, ordered by value") is the pre-governance
open-items list — still live, not yet transcribed into `FINDINGS.md`.

**Correction, 2026-09-11 (CHANGELOG 66) — this section had drifted, item by item:**

- **Item 1 above (T3) is half-resolved, not open.** The `sentence_transformers`
  path WAS run (`FINDINGS.md` F-10's 2026-09-10 update): Qwen3-Embedding-0.6B
  loads and separates same-matter vs. unrelated document pairs by roughly
  double the margin of the current default (~0.41 vs. ~0.24 spread). What's
  still genuinely open is only the **adoption decision** — `EMBED_MODEL` in
  `src/casemap_service.py` is still `"all-MiniLM-L6-v2"`; switching the
  pipeline's default needs the owner's explicit sign-off per §10, not more
  evaluation. `docs/requirements/2026-09-09-structure-and-embedding-layers/
  TRACKER.md`'s "T3 — Not started" row is itself stale and should read
  "Evaluated, decision pending" — left as-is here rather than silently
  rewritten, per this project's own append-only convention for tracked state.
- **`docs/requirements/2026-09-09-verbatim-fallback-nodes/` is fully done**
  (its own `TRACKER.md`: T1-T5 all `Done`, dated 2026-09-09/10) — it was never
  actually an open item by the time this section was last written, just not
  reflected here.
- **The Tier 1 blocking item (mandatory `en_legal_ner_sm`, `STATUS.md`
  2026-09-09) is now closed.** The model is installed in this project's own
  `.venv` (not just a side venv) and wired into `get_ml_nlp()` in
  `src/casemap_service.py` — confirmed active (`ml_layer: active`) on every
  real run. See `STATUS.md`'s 2026-09-11 update for the full verification.
- **The `document_profile.extract_parties_layered()` header-noise bug**
  flagged as "not yet its own requirements folder" (`STATUS.md` 2026-09-10)
  already had one, same day: `docs/requirements/2026-09-10-party-ladder-
  header-furniture/` (F-9). Verified clean across all 22 `testdata/*.txt`
  docs, both the regex ladder and the ML hybrid path.
- **The project is now a git repository**, pushed to
  `https://github.com/Wasim-Shaikh25/CaseMap` — see the correction to §10
  below; this was previously reserved for the owner and has now been done by
  the owner's explicit instruction.
- **`server/app.py` + `ui/` are the shipped product, not a stopgap.** This
  section's item 2 (§9 follow-ups) and the rest of this file below still
  describe 2026-09-10 state; the `casemap_service.py` extraction (CHANGELOG
  63), the drawer highlight fix (CHANGELOG 64), and the reprocess/rhetorical-
  role/word-amounts features (CHANGELOG 62) all landed after this file was
  last substantially rewritten and are **not** reflected in §§1-6, 8-9 below.
  Treat those sections as historical background, not current state — `STATUS.md`
  and `CHANGELOG.md` are current; this file's body has not been fully rewritten
  to match (a full rewrite, per this project's own precedent — see the
  2026-09-10 entries in `STATUS.md` — is a bigger task than this correction
  pass; flagging it here rather than silently doing a partial one).

---

## 8. Recommended work order

1. **§9 first** — the real-petition-test follow-ups are concrete, already
   scoped, and directly requested.
2. `structure-and-embedding-layers` T3 / Docling-as-default (optional,
   evaluation only until a dated decision — §10).
3. Do **not** start `ephemeral-client-results` T2-T4, and do **not** build any UI —
   see §0.

---

## 9. Owner-approved next steps for Cursor (from the 2026-09-10 real-petition test, F-12)

**Status 2026-09-10 (F-13):** executed, with honest leftovers. Detail:
`FINDINGS.md` F-13, `docs/requirements/2026-09-10-petition-followups/`.

1. **Re-run `important_lines.py` model comparison on a SECOND real petition.**
   **Done as far as the corpus allows.** `testdata/`/`real_pdfs/` have no
   petition-shaped filing. Re-ran on the same BCI petition: 28/47 (59.6%)
   same MiniLM/Qwen pick — same as F-12. Needs a second real petition from
   the owner or a public filed pleading added to `testdata/` with provenance.
2. **`case_symbols.py` / entity linking across the newly-segmented sections.**
   **Measured and partially fixed.** Layered cause title now keeps the three
   numbered respondents and drops PAPER BOOK/contact lines. Hybrid remains
   `ml_role_unstable` (F-2). `normalize_name` aliases for BCI match.
3. **`ANNEXURE_PATTERN`/`_segment_by_headings()` — related edge cases.**
   **Official SC form headings fixed.** Lettered/parenthetical prefixes
   (`A. GROUNDS`, `(vii) GROUNDS`) not expanded — no real document used them.
4. **Multi-page PDF petition ingestion.**
   **Digital text-layer path verified** (one heading/page and two headings on
   one page). Scanned/OCR petition PDF still untested.

None of the leftovers are blocking. Do not duplicate `important_lines.py`.
Do not build UI (§0).

---

## 10. Decisions reserved for the project owner — never do these unasked

- Widening `docs/spec/SCOPE.md`'s boundary (no generative LLM in the core).
- Making OpenNyAI's Legal NER optional/non-mandatory again.
- ~~`git init` for this project (owner will do it themselves).~~ **Done,
  2026-09-11, by explicit owner instruction:** initialized and pushed to
  `https://github.com/Wasim-Shaikh25/CaseMap`, with `.gitignore` excluding
  `.venv/`, `casemap.db`, OCR/pytest caches, and — importantly — `temp/`
  (which holds the owner's own real, personal petition document; that must
  never enter version control, see `FORBIDDEN.md`).
- Adopting the two-judge law / global trial counter (declined at governance init).
- **Adopting Docling, Qwen3-Embedding, or any other layer-additions-research tool as
  a permanent `src/`/`requirements.txt` dependency** — validated as POCs, not
  formally adopted. Choosing Docling over MinerU without a head-to-head, or pinning
  either into `requirements.txt`, needs a dated decision first.
- **Building UI of any kind** (§0) — FastAPI, React/React Flow, upload endpoints,
  anything under a `frontend/`/`ui/`/`web/` directory. This is being done directly
  by Claude as published Artifacts instead. Dated 2026-09-10.
- **Skipping HEART build tiers** — Tier 3 (the eventual real FastAPI/React build,
  if ever needed beyond the Artifact viewers) still needs a proven Tier 1/2 first.

**Already exercised, for reference on how this looks in practice:**
`important_lines.py`'s default embedding model (Qwen → MiniLM, F-12) was
exactly this kind of decision — evaluated as a POC first (F-10/F-11), never
silently defaulted, made only after the owner saw real measured numbers
(112x speed gap, 60% pick agreement, spot-checked quality) and said so
explicitly in conversation. That's the bar for anything else on this list.

---

## 11. Commands

```bash
# Tests (from the working venv with en_legal_ner_sm — see §2)
pytest tests/

# Install the mandatory model into a fresh venv:
python scripts/install_en_legal_ner_sm.py

# Full pipeline against a folder of .txt or .pdf documents:
python scripts/poc_run.py <folder> --allow-degraded   # regex-only party fallback
python scripts/poc_run.py <folder>                    # real mandatory model, needs it installed
python scripts/poc_run.py <folder> --important-lines  # + extractive important-line nodes (F-11/F-12)

# Core dependencies:
pip install -r requirements.txt
# Optional, only for structure-and-embedding-layers work (~1.5GB):
pip install -r requirements-docling.txt

# 2026-09-09/10 POC environments (not the project's real dependency set):
# temp/2026-09-09-mini-llm-poc/venv_ner/            — spaCy 3.8.16 + en_legal_ner_sm, working
# temp/2026-09-09-layer-additions-poc/venv_docling/ — Docling 2.126.0 + models, working (~1.5GB)
# temp/2026-09-10-docling-qwen-poc/venv_docling_qwen/ — Docling 2.126.0 + sentence-transformers, working
# All expensive to rebuild — see each POC's assessment doc for the install recipe.
```

See `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §8-9 for the full dependency list and tech stack summary.
