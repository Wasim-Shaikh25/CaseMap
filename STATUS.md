# Status

> **Picking this up cold? Read `HANDOFF.md` first.** It is the single orientation
> document. This file is the running state; the handoff is the map.

**2026-09-09 — Governance initialized on top of an existing POC.** This is not a
brand-new project: the extraction/graph pipeline, the mandatory OpenNyAI ML layer, and a
26-bug ledger already exist (see `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md`). Governance docs
(`FORBIDDEN.md`, `AGENTS.md`, `THESIS.md`, `HEART.md`, `HANDOFF.md`, `STATUS.md`,
`FINDINGS.md`, `CHANGELOG.md`, `docs/spec/`) were scaffolded and seeded with real project
content from the existing handoff/ML-layer/POC documents. No code changed in this
session.

**Confirmed present in the working directory (2026-09-09), now in their governance-structure
locations:** `src/casemap_pipeline.py`, `src/document_profile.py`, `src/opennyai_bridge.py`
(library code, under `src/`); `scripts/poc_run.py` (a POC runner script, not library code
— under `scripts/`); `tests/test_opennyai_bridge.py` + `tests/conftest.py`;
`docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md`,
`docs/research/existing-approach/CaseMap_Mandatory_ML_Layer_v7.md`,
`docs/research/existing-approach/poc_report.md`.

**Referenced elsewhere but not found in this working directory:** `layout_structure.py`
is at `src/layout_structure.py`; `case_symbols.py` is at `src/case_symbols.py`;
`real_pdfs/` exists (entry 30). Still missing: `test_logic.py`, `test_layout.py`,
`test_profile_symbols.py`, `dryrun_real.py`, `dryrun_fallbacks.py`, `blueprint1.md`,
`blueprint2.md`, `make_real_pdfs.py`, `real_docs/` — verify before relying on them
(see `HANDOFF.md` §6).

**Last updated:** 2026-09-11 (entry 65: confirmed en_legal_ner_sm mandatory NER model already wired + active, and the F-9 party-furniture bug already fixed — two stale STATUS.md claims corrected, no code changed)

## Current phase

**Tier 1's original blocking item is now closed (see 2026-09-11 update below):** the
real mandatory OpenNyAI model (`en_legal_ner_sm`) is installed in this project's own
`.venv` and is wired into `get_ml_nlp()`/`process_document()` — confirmed active
(`[+] ML layer: active`) on every real run this session, not the `--allow-degraded`
regex fallback described when this phase note was first written (2026-09-09, see
`HEART.md` §2).

**2026-09-09 (later same day) — that blocking item was attempted for the first time,**
outside `poc_run.py`: `en_legal_ner_sm` was installed (in a standalone venv,
`temp/2026-09-09-mini-llm-poc/venv_ner/`, with a working Windows install recipe) and
run against 20 fresh real documents (`testdata/`). It loads and produces correct,
verbatim, char-offset-backed entities — confirming the model itself is usable. At the
time of writing it had **not** been wired into `opennyai_bridge.py`/`poc_run.py` in
this working directory. See
`docs/research/new-directions/mini-llm-extraction-assessment.md` Part 2 and
`FINDINGS.md` F-2 for what was learned (real role-label noise that the pipeline's
mandatory Layer 2 deterministic refinement already exists to catch).

**Update 2026-09-11:** this is now stale — `en_legal_ner_sm` IS installed in this
project's own `.venv` (not just the standalone `venv_ner`) and IS wired: every
`process_document()` call loads it via `get_ml_nlp()` →
`bridge.load_opennyai_ner("sm", allow_degraded=True)` (`src/casemap_service.py`),
and every real run this session (server boots, CLI runs, tests) logged `[+] ML
layer: active` — real weights, not the degraded regex fallback. `allow_degraded=True`
is just a graceful-fallback flag for machines where the model isn't installed; it
does not mean degraded mode runs by default. Tier 1's blocking item is closed.

**2026-09-09 (still later) — two requirement folders formalized, both ready for
implementation, neither started:**
- `docs/requirements/2026-09-09-verbatim-fallback-nodes/` — low-confidence sections
  become graph nodes instead of being dropped. `TASKS.md` has 5 tasks (T1-T5).
- `docs/requirements/2026-09-09-structure-and-embedding-layers/` — Docling recovers
  the still-missing `layout_structure.py` via a real, already-existing seam in
  `casemap_pipeline.segment_document_layered()`; Qwen3-Embedding evaluated as a
  `make_similarity_fn()` upgrade. `TASKS.md` has 4 tasks (T1-T4); T1 (page-numbering
  verification) blocks the rest and should go first.

`testdata/` grew from 20 to 22 documents (a genuinely connected 3-document same-matter
insolvency bundle added to test graph edge formation honestly — see `FINDINGS.md`
F-3). `HANDOFF.md` was rewritten in full to reflect all of the above — read it, not
just this file, for orientation.

**2026-09-09 (Cursor-readiness review) —** `requirements.txt` and
`requirements-docling.txt` added at root (dependency pins verified against this
session's actual working venvs, not guessed — see each file's own header). Still
**not a git repo** — owner chose to do that themselves before/during implementation,
not this session. See `CHANGELOG.md` entries 5-13 for the complete, dated record.

**2026-09-10 — mandatory NER install path + Docling page_no T1.**
`scripts/install_en_legal_ner_sm.py`; default `load_opennyai_ner()` works on
`venv_ner`. Structure T1: Docling pages are 1-indexed (4/4). Structure T2:
`src/layout_structure.py` shipped with three degrade paths; real fixture PDF
returned `docling_layout`. Next: T3 (Qwen via `sentence_transformers`) then T4
(`poc_run` wiring). Docling remains optional, not a `requirements.txt` pin.

**2026-09-10 (later) — entity-noise fully closed; UI moved to Claude-published
Artifacts; HANDOFF.md rewritten.** `entity-extraction-header-noise` +
`residual-false-edges` closed F-8 for real: false cross-document edges 60→0,
correct bundle edges 10→16. A live case-file/event-graph viewer
(`temp/2026-09-10-ui-poc/casemap_viewer.html`) was built and published as an
Artifact against real `poc_run.py`/`document_profile.py` output — **UI work is
now explicitly out of scope for `src/`/Cursor, see `HANDOFF.md` §0.** A second
real bug was found in `document_profile.extract_parties_layered()` (header-parsing
noise, same family as F-8) — closed later the same day as F-9, see the entry
below and `docs/requirements/2026-09-10-party-ladder-header-furniture/`.
`HANDOFF.md` was rewritten in full — it had drifted behind F-5 through F-8 and 4 requirement
folders. See `CHANGELOG.md` entries 19-27.

**2026-09-10 (later) — F-9 party furniture + structure T4.** Caption
`Author:`/`CITATION` no longer become parties (`extract_parties_layered` +
hybrid filter). Structure T4: `poc_graph.json` `documents[]` carries
`structure_tier`. Qwen T3 not started. See `CHANGELOG.md` entry 28.

**2026-09-10 (later still) — `real_pdfs/` built and validated.** The corpus flagged
missing every session since governance init now exists at project root: 22 PDFs (15
digital, 7 genuinely scanned/degraded, verified zero-text-layer). Ran
`scripts/poc_run.py real_pdfs --ocr tesseract` with the real mandatory model, not
`--allow-degraded` — 37 pages, 12 genuinely OCR'd (32%), 39 event nodes, 76 edges.
Built specifically to support Cursor's Tier 1 proof work. `real_docs/` (plain-text)
is still absent; `testdata/` remains its closest substitute. See `CHANGELOG.md`
entry 30 and `real_pdfs/README.md`.

**2026-09-10 (even later) — `src/important_lines.py` shipped (F-11), implemented by
Claude on the owner's direct dated go-ahead.** Extractive "important line" nodes per
paragraph — Qwen3-Embedding centrality ranking, no-ML deterministic fallback, opt-in
`--important-lines` flag on `poc_run.py`. F-11 had already ruled out every generative
option tested (5 models, all distorted at least one real fact). Real 22-document run:
52 nodes, 0 fragments — down from 21% fragments in the first real run, fixed via 3
real bugs found only by running against the full corpus (abbreviation/name-initial
mis-splitting, short-fragment nodes, a near-miss verbatim-offset reconstruction bug).
11 new tests, full suite still green. Requirements folder written retroactively —
`docs/requirements/2026-09-10-important-lines/REQUIREMENTS.md` explains why. See
`CHANGELOG.md` entry 34.

**2026-09-10 (later) — UI updated to match.** The published Artifact
(`casemap_viewer.html`, same URL) now has a "Document tree" — every extracted
detail per document, sorted by page/paragraph, click for a quick preview or the
full evidence card, which now shows document name and paragraph number as the
owner asked for directly. Re-ran against the viewer's 5-doc sample: 26 real
nodes (15 important-line, up from 11 total). See `CHANGELOG.md` entry 35.

**2026-09-10 (real petition test) — F-12, 3 real bugs found and fixed on the
project's first-ever real filed petition.** Owner supplied a real personal
writ petition and asked to run the pipeline against it — every prior test
document was a published judgment, none had a real Prayer/Grounds section.
Found and fixed: `ANNEXURE_PATTERN` missed all numbered headings
(`VII. GROUNDS`, `XI. INTERIM PRAYER`); `_segment_by_headings()` couldn't
split a single-page `.txt` at all, so even fixed headings collapsed into one
section. Both fixed and tested (8 new tests). Real before/after: 48
`IMPORTANT_LINE` nodes across 10 correctly-labeled sections (was 6, all
mislabeled), including 16 genuine grounds-of-challenge sentences pulled
straight from the real arguments. Runtime 1131s → 354s (3.2x) as a side
effect. Also measured, not fixed: Qwen3-Embedding is ~112x slower than
MiniLM on this CPU per sentence; switching isn't safe yet (real 4/6
disagreement on badly-segmented input, now worth re-testing on the fixed
segmentation). See `FINDINGS.md` F-12, `CHANGELOG.md` entries 36-37.

**2026-09-10 (pipeline, same day) — `.venv` NER default, `case_symbols.py`, F-7.**
Project-root `.venv` loads `en_legal_ner_sm` without `--allow-degraded`.
`src/case_symbols.py` recovered (tier-1 API). F-7 cue poison/fuzzy misses fixed
in `src/rhetorical_roles.py`. See `CHANGELOG.md` entry 31.

**2026-09-10 (HANDOFF §9 follow-ups) — F-13.** All four F-12 next steps
measured. No second petition in the public corpus; MiniLM/Qwen still 28/47
on the same filing. Official SC form headings and petition cause-title noise
fixed in `src/`; multi-page digital PDF heading split verified. See
`CHANGELOG.md` entry 41 and `FINDINGS.md` F-13.

**2026-09-10 (later still) — local web app shipped, HANDOFF §0 no-FastAPI
rule reversed by direct owner instruction.** `server/app.py` (FastAPI,
wraps existing `src/` functions, no pipeline logic duplicated) +
`ui/` (plain HTML/CSS/JS, no framework) — upload PDFs/DOCX, get back a
case dashboard with a chronological timeline, condensed "key points" per
document, a document tree, cross-document provision/statute linking, an
evidence drawer with page/paragraph/verbatim-context, and a downloadable
counsel report. No server retention: uploads processed in a deleted temp
dir, `localStorage` in the browser is the only persistence. Verified
end-to-end against real `testdata/` (single doc + the 3-doc insolvency
bundle, cross-doc edges and cross-doc provision linking both confirmed) and
in the actual rendered browser. Run: `uvicorn server.app:app --port 8756`.
See `HANDOFF.md` §0 and `CHANGELOG.md` entry 42.

**2026-09-11 — full-repo line-by-line audit; two unused-but-beneficial
capabilities wired into the product; stale design docs synced; dead code
removed.** Audited every source file (5787 lines) + the design-governance
docs. Confirmed the pipeline is genuinely document-type-agnostic (not
petition-specific) but India-specialised (Rupee-only amounts, OpenNyAI
Indian NER, Indian forum/case regexes) — see `FINDINGS.md` F-14. Tested the
four unused-but-beneficial features flagged by the audit against all 22
`testdata/` docs and **wired the two that produced good, safe results**:
(1) **rhetorical-role labelling** (`rhetorical_roles.tag_paragraphs`) — each
fact now carries the FACTS/ISSUES/ARGUMENTS/ANALYSIS/RULING role of its
paragraph (46 events across 9 docs), shown in the evidence drawer; a
classifier, never a generator, so the verbatim guarantee holds. (2)
**amounts-in-words** (`case_symbols.find_word_amounts`, new) — "Rupees One
Crore" and similar now extracted (figure regex only saw digits). **Rejected
the other two, with evidence:** bi-temporal invalidation fires on 0 edges
(needs two edges per node-pair, which the graph never makes) and its
`persist_edges` would break the no-persistence privacy contract; GLiNER-multi
entity extraction is 6–10× slower (218s cold-start) and reintroduces
court-name noise the entity gate exists to remove. Also fixed a pre-existing
`AMOUNT_PATTERN` bug found while testing (matched a bare "Rs," with no
digits). Full suite 62 passed / 1 skipped (was 57/1; +5 new tests). Synced
`README.md`, `THESIS.md` §2, `HEART.md` §2 (dated banners, past text kept).
See `CHANGELOG.md` entry 62 and `FINDINGS.md` F-14.

**2026-09-11 (audit follow-ups) — esc() attribute-injection fix; the pipeline
unified into one shared module.** (1) `ui/app.js` `esc()` now escapes quotes
too (`"`/`'`), so a document/party name with a `"` can no longer break out of
a `title="…"` attribute. (2) Ended the poc_run drift flagged in F-14 by
extracting the whole per-document + graph pipeline into **`src/casemap_service.py`**
(moved verbatim): `process_document()` + `build_case_graph()` + helpers +
the lazy model loaders. `server/app.py` and `scripts/poc_run.py` are now both
thin wrappers over it — one source of truth, so poc_run's proof report finally
reflects the real pipeline. Bi-temporal edges stay poc-only. Removed poc_run's
`--important-lines` (always on now) and `--gliner` (rejected) flags. Server
boots + `/api/health` verified; end-to-end on the insolvency bundle unchanged
(4 cross-doc edges within the connected bundle); full suite 62 passed / 1
skipped. See `CHANGELOG.md` entry 63.

**2026-09-11 (last F-14 item) — drawer evidence highlight now uses exact
offsets instead of a text search.** The evidence drawer's `<mark>` highlight
used to relocate itself inside its wider context via a literal
`String.replace(esc(s.text), ...)` — silent no-op whenever `s.text` wasn't an
exact substring of `s.context`, and vulnerable to `.replace()`'s `$`-pattern
semantics. The backend already computes exact offsets for this
(`_attach_context()`'s `context_start`, alongside `char_start`/`char_end`) but
the frontend never read them. New `highlightSpan()` (`ui/app.js`) slices by
those offsets, self-verified against the actual text before trusting them, and
falls back to the old search when they don't line up (the one real case:
`_section_fallback_event`'s `char_end` spans the whole section, not just its
400-char displayed excerpt). Verified against real pipeline output (16 real
event sources from the insolvency bundle): 12 hit the precise path, 4 fall
back correctly, 0 no-ops. Full suite still 62 passed / 1 skipped. See
`CHANGELOG.md` entry 64 — F-14's punch list is now fully closed.
