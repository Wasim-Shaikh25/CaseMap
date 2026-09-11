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

**Referenced elsewhere but not found in this working directory:** `case_symbols.py` is
at `src/case_symbols.py`; `layout_structure.py` was removed 2026-09-11 (entry 75) — do
not re-add it without re-reading `FINDINGS.md` F-21 first; `real_pdfs/` exists (entry
30). Still missing: `test_logic.py`, `test_layout.py`,
`test_profile_symbols.py`, `dryrun_real.py`, `dryrun_fallbacks.py`, `blueprint1.md`,
`blueprint2.md`, `make_real_pdfs.py`, `real_docs/` — verify before relying on them
(see `HANDOFF.md` §6).

**Last updated:** 2026-09-11 (entry 80: deployed to Render, found free tier OOM-crashes under real load, moving to a VPS; versioning + per-model health status + startup model warm-load added)

**2026-09-11 — Counsel-report PDF: fixed statute text rendering unstyled (same-day regression from entry 78).**
Owner asked to verify the "Download counsel report (PDF)" output (`window.print()` on a self-contained HTML document
`ui/app.js` builds, no server PDF library) before finalizing this session. The new India Code statute-text box from
entry 78 was only styled in `ui/styles.css`, which the report never loads — it rendered as plain body text with no
visual separation. Verified by capturing the real `downloadReport()` output in a live browser session, before and
after. Fixed by adding matching CSS to the report's own embedded stylesheet. Full writeup: `FINDINGS.md` F-24
addendum.

**2026-09-11 — Provision lookup switched from IndianKanoon judgment-search to India Code's own statute text; one
HTTP call, verbatim exact text (supersedes F-17).** Owner wanted the EXACT text of a cited provision and asked
whether a free search engine could do it in one call, accepting that unresolvable citations skip. Found
`indiacode.ecourtsindia.com` — a free, no-key JSON mirror of India Code (836 Central Acts) built for programmatic
retrieval; its section endpoint returns the Act's own verbatim text, confirmed against several real provisions.
Kept it to one HTTP call per provision by resolving the Act name against a LOCAL bundled index
(`src/indiacode_acts.json`, fetched once by `scripts/build_indiacode_acts_index.py`, never at request time) via
rapidfuzz instead of a second network round-trip; only the section-text fetch itself touches the network. Skips
honestly (zero network calls, confirmed by tests) when an Act reference is genuinely ambiguous, unnamed, or outside
the Central-Act index. UI disclosure text and the provisions render (both sites) updated from IndianKanoon to India
Code; verified end-to-end via a live server + real browser upload with the lookup checkbox on. Full suite: 83
passed. Full writeup: `FINDINGS.md` F-24.

**2026-09-11 — Structural fix for F-22's residual party-extraction noise; found and fixed a real GLiNER gap on
"State of Maharashtra" along the way.** Owner asked to fix the address-fragment noise ("Grampanchayat Tiroda",
"Sindhunagri, Oras") that F-22's addendum traced to a document-structure problem after a GLiNER-label attempt was
rejected. Fixed in `document_profile._group_entries()`: once inside a NUMBERED party entry, an unmatched line now
defaults to "continuation of this entry" instead of "new party" — gated so the common unnumbered VERSUS caption is
unaffected. Fixed all 3 of F-22's residual strings in one change (better than the rejected GLiNER attempt, which
only fixed 1 of 3). Surfaced two more real bugs along the way: a page-break line mid-entry was wrongly resetting the
entry (split into its own transparent-skip pattern), and — once the structural fix let a real "State of Maharashtra"
respondent through cleanly — the already-shipped GLiNER judge turned out to drop it anyway (zero entities, while
"State of U.P." judges fine) — a genuine, previously-invisible gap on the single most common Indian-litigation
respondent pattern, fixed with a deterministic regex bypass ahead of the model call. 6 new tests; full 22-doc sweep:
21/22 identical, 1 doc improved (10 -> 7 parties, verified as pure noise removal, not a regression). Full suite: 81
passed. Full writeup: `FINDINGS.md` F-23.

**2026-09-11 — Real fetched documents (writ petition, NGT appeal, affidavit, agreements) surfaced 2 party-extraction
bugs, both fixed.** Owner asked to fetch real public documents outside `testdata/` and see how the pipeline performs.
Event/fact extraction generalized well with zero tuning; party extraction missed 2 real cases: (1) tribunal
`BETWEEN: ... AND ...` captions (no VERSUS) returned zero parties — fixed with a gated fallback anchor, plus a
sharper bug it surfaced (a blank-line heuristic built for an unknown boundary truncated a known one on a PDF layout
artifact, dropping 3 real Appellants); (2) the GLiNER party judge blanked its own prediction for a real name
("N. RAM & ORS") purely because of the "& Ors." suffix, and separately rejected a name it split into two adjacent
spans covering 94% combined because neither span alone hit the old single-span 70% threshold — both fixed. 9 new
tests; re-swept all 22 `testdata/` docs directly, no regression. Full suite: 75 passed. Full writeup: `FINDINGS.md`
F-22.

**2026-09-11 — Docling layout layer removed (closes F-15 item 2).** Owner asked why
Docling was needed given the project's own infra, and to close the question. It was
never installed in this project's own `.venv` — every real document this pipeline has
ever processed went through the legacy text-pattern detector only. Its credited OCR
handling of scans (F-10) fully duplicates the pipeline's own first-class OCR stage
(three engines, caching, page classification). Its one distinct capability (generic
ML layout-based heading detection) was only ever measured on heading-text correctness,
never on a downstream extraction-accuracy gain. Removed `src/layout_structure.py`,
`tests/test_layout_structure.py`, `requirements-docling.txt`, `run.ps1
-IncludeDocling`; `segment_document_layered()` now calls the legacy detector directly
with the same return shape, so no other file needed changes. Full suite: 66 passed.
Full writeup: `FINDINGS.md` F-21.

**2026-09-11 — Rhetorical roles: pushed further after (73), via WSL — real fixes, still no usable model.** Owner
correctly pushed back that (73)'s `opennyai` blocker was a platform gap, not a broken model, and asked to actually
try fixing it. AllenNLP (the original baseline's dependency) is confirmed genuinely dead — its own `spacy<3.4` pin
needs a `distutils` API modern `setuptools` removed entirely, not a version choice. But Hier_BiLSTM_CRF (the
LegalSeg paper's best model, F1 0.77) really was a platform issue: its `sent2vec` C++ dependency failed to build
under Windows/MSVC (GCC-only flags) and built cleanly under WSL/Ubuntu with zero patching. Got the whole pipeline
running after fixing 4 real bugs (an `argparse type=bool` footgun, PyTorch 2.6's new `weights_only=True` default,
a CUDA-only checkpoint with no GPU here, and a genuine bug in the paper's own code where `device` never reached
two submodules). Tested against 2 real judgments with this project's own sentence splitter — caught one real
argument the phrase-matcher would have missed, but otherwise collapsed to near-all-Facts/None, missing every other
role. InLegalBERT(i) (plain `transformers`, no platform issue) loaded perfectly but its predictions look close to
random — the label order had to be inferred from the paper's prose (no label-mapping file shipped), and this
result casts real doubt on whether that inference is right. Verdict: `RHETORICAL_ROLE_CUES` stays on the plain
phrase/fuzzy matcher; the WSL fix path is documented in case a better-labeled checkpoint appears later. No
changes to `src/` or the project's own `.venv`. Full writeup: `FINDINGS.md` F-20.

**2026-09-11 — `opennyai`'s rhetorical-role model evaluated and blocked (upstream, not fixable here).** The
"unconfirmed inference entrypoint" `opennyai_bridge.py:122` flagged turns out to be real:
`pip install opennyai` + `Pipeline(components=['Rhetorical_Role'])` is a documented, working API — but it requires
Python >=3.13. Owner approved installing Python 3.13 system-wide (isolated from the project's Python 3.11
`.venv`) specifically to evaluate it in a throwaway venv (`temp/2026-09-11-opennyai-rhetorical-role-poc/`, never
committed). Blocked there: `spacy-curated-transformers`, a hard runtime dependency (loads `en_core_web_trf` for
internal preprocessing, not optional), needs `thinc>=9.0`, and `thinc`'s own Cython source fails to compile under
Python 3.13's toolchain on this machine — an upstream build problem, not a version-pin choice we can fix. Every
other dependency (torch, transformers, spacy-transformers) installed fine in isolation, so this is narrowly
`spacy-curated-transformers`/`thinc`'s fault. `opennyai` is also still "Pre-Alpha" on PyPI. Verdict: not viable
right now, not pursued further. `RHETORICAL_ROLE_CUES` stays on the plain phrase/fuzzy matcher, unchanged. No
changes to the project's own `requirements*.txt` or `.venv`.

**2026-09-11 — Three items closed: test coverage, a rejected experiment, and a long-open decision.**
`tests/test_provision_lookup.py` (8 new tests, fake network responses) closes the one gap noted in F-17 — full
suite now 70 passed, 1 skipped. A rhetorical-role embedding fallback (same pattern as the event/polarity fixes:
reuse `all-MiniLM-L6-v2` against `RHETORICAL_ROLE_CUES`'s own phrases) was built, tested against all 22 real
`testdata/*.txt` judgments via a new tuning script BEFORE wiring it in, found to mislabel roughly half its matches
(header/caption noise mistaken for arguments, wrong roles on real content), and reverted rather than shipped —
`RHETORICAL_ROLE_CUES` remains open, genuinely needs a trained classifier, not another parse trick. See
`FINDINGS.md` F-19 for the full writeup and examples. Separately, the long-open Qwen3-Embedding-0.6B adoption
question is now closed: owner's decision is to keep `all-MiniLM-L6-v2` (`FINDINGS.md` F-15, struck through in
place, not deleted).

**2026-09-11 — Polarity classification: dependency-parse signal added alongside `DENIAL_MARKERS`/`ASSERTION_MARKERS`.**
Same fixed-phrase-list gap as entry (68)'s event detection fix, this time in `_classify_polarity()` — the function
conflict detection keys off. `en_core_web_sm`'s `neg` dependency tag (real syntactic negation on any verb) plus two
new small verb-lemma sets now run as a second pass after the existing phrase lists (kept, unchanged — idiomatic
phrases like "false and baseless" have no verb to key off). Catches "has not received", "refutes the claim",
"counsel contends that" — all previously NEUTRAL, meaning a real denial phrased slightly differently than the
enumerated list never became a conflict. No new model. Verified with direct unit checks; `pytest`: 62 passed, 1
skipped.

**2026-09-11 — New capability: opt-in provision lookup, first outbound network call in this pipeline.** Owner
asked for a free web lookup so a cited provision's own text shows up next to it, scoped explicitly to "only the
provision, not client details." `src/provision_lookup.py` queries IndianKanoon.org's free search with the bare
citation string, one call per unique provision, skips (returns `None`) on anything not confidently a bare-statute
match rather than guessing. Wired through `casemap_service.process_document(lookup_provisions=False)` (default
off) → `server/app.py`'s `/api/process` form field → a checkbox on the upload screen, unchecked by default with
its own disclosure text. Dashboard privacy paragraph updated to state the toggle's effect rather than leave the
old absolute claim technically wrong once it exists. Rendered in both the printable report and the live
Provisions tab, verified in both themes. See FINDINGS.md F-17 for full detail. `pytest`: 62 passed, 1 skipped.

**2026-09-11 — Event detection: WHO/ACTION/WHAT/WHEN from the dependency parse, not a phrase list.** Owner
asked whether `EVENT_KEYWORDS` ("paid", "terminated", "filed on", ...) was hardcoded — confirmed yes — and
whether the pipeline could get more accurate without a heavy generative LLM. Measured first
(`scripts/poc_srl_events.py`): `en_core_web_sm`, already mandatory-loaded for entity extraction, produces a
full dependency parse per sentence that was never being used for events, only literal phrase matching. Real
gap on actual judgments: 23% of event-bearing sentences invisible to the old scanner. Fixed:
`casemap_pipeline.detect_events_srl()` reads WHO/ACTION/WHAT/WHEN/MODAL straight off that existing parse, wired
into `casemap_service.py` right after the existing uncovered-dates fallback, additive only (never duplicates
what earlier stages already found). `EVENT_VERB_LEMMAS` (new, tiny) replaces `EVENT_KEYWORDS` for type
labeling only — an unmatched verb becomes an untyped `FACT` event instead of vanishing. Re-verified against all
22 `testdata/*.txt` docs post-fix: ~0% real gap left. `DENIAL_MARKERS`/`ASSERTION_MARKERS` and
`RHETORICAL_ROLE_CUES` are the same class of fixed-phrase hardcoding and were deliberately left alone this
pass (see F-16 for why each is a different kind of follow-up). Full `pytest`: 62 passed, 1 skipped.

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

**2026-09-11 (verification pass, no code changed) — two items this file called
"still open" turned out to already be resolved.** (1) `en_legal_ner_sm`: this
file's 2026-09-09 entry above said it had "not been wired into
`opennyai_bridge.py`/`poc_run.py` in this working directory" — that's stale.
It's installed in this project's own `.venv` and `get_ml_nlp()`/
`process_document()` (`src/casemap_service.py`) load it on every run; every
server boot / CLI run / test this session logged `ml_layer: active`. Both
paragraphs above are corrected in place. (2) The `document_profile.
extract_parties_layered()` header-noise bug flagged below as "not yet its own
requirements folder" already had one, the same day (F-9,
`docs/requirements/2026-09-10-party-ladder-header-furniture/`) — verified
clean across all 22 `testdata/*.txt` docs and the ML hybrid path. See
`CHANGELOG.md` entry 65 and `FINDINGS.md` F-15.

**2026-09-11 (one-command run script + docs pass) — `run.ps1` added;
`README.md` fully detailed; remaining open items consolidated in one place.**
`run.ps1` creates `.venv` if missing, installs both requirement files, installs
the mandatory NER model + `en_core_web_sm` if absent, checks for system
Tesseract (warns, doesn't fail, if missing — only scanned PDFs need it), then
starts `server/app.py` — which already serves `ui/` as static files, so this
one script and one process is the whole app, frontend included. Verified
end-to-end (idempotent against the existing `.venv`; `/api/health` responds
after start). `README.md` rewritten with a real quick-start, a by-hand
fallback, a using-the-app walkthrough, and a fixed architecture summary (the
old copy still described `poc_run.py` as drifted behind the web pipeline —
stale since entry 63). `FINDINGS.md` F-15 is now the one place listing what's
genuinely still open project-wide (Qwen3-Embedding adoption decision; Docling
not installed in this `.venv`; `important_lines.py` needs a second real
petition) versus what several docs still called open but code already
resolved. See `CHANGELOG.md` entry 66.

**2026-09-11 (dashboard honesty pass) — the app now says plainly what it is
and carries a standing correctness warning.** The dashboard intro now states
directly that CaseMap is "a verbatim document-indexing assistant, not a
legal-research or drafting tool" that "doesn't summarize, paraphrase,
generate, or reason about your case." A new, non-dismissible correctness
notice sits right below it: extraction can miss or misread a fact (poor
scans, non-English text, unusual formatting), never checks whether a cited
provision is still good law, and every date/amount/citation is a first pass
to verify, not a second opinion. Verified live in the browser, both themes.
See `CHANGELOG.md` entry 67.
