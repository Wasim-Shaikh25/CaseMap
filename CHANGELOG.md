# Changelog

All notable changes to `CaseMap`. Newest first. Append an entry as part of
every change (see `AGENTS.md` §5). **Never renumber or edit a past entry** — if two
entries collide on a number, suffix the later one (`3` → `3b`).

## 2026-09-11 (78) — provision lookup switched from IndianKanoon judgment-search to India Code's own statute text; one HTTP call, verbatim exact text

Owner wanted the EXACT text of a cited provision ("if we say UGC Act sec 23
I just want exact text for that sec 23"), asked whether a free search
engine could do it in one call, and accepted skipping the unresolvable
cases. Full writeup: `FINDINGS.md` F-24 (supersedes F-17).

Found `indiacode.ecourtsindia.com` — a free, no-key JSON mirror of India
Code (Government of India's own statute repository, 836 Central Acts),
built for programmatic retrieval. Its section endpoint returns the Act's
own verbatim text, not a judgment that cites it — confirmed against the
real UGC Act s.23, Prevention of Corruption Act s.7, NIA Act s.21, PWDV Act
s.12, NI Act s.138.

"One call, not two or three": added `scripts/build_indiacode_acts_index.py`
(one-time, never run from the request path) which fetches all 836 Central
Acts' `{id, short_title, act_year}` into bundled `src/indiacode_acts.json`
(~125KB). `provision_lookup.py` rewritten to fuzzy-match (rapidfuzz,
already a dependency) the citation's Act name against this LOCAL file —
zero network calls — narrowing by year first when present; only the
section-text fetch itself touches the network. Handles Act names
`_find_act_name()` truncates (e.g. "Corruption Act, 1988" for "The
Prevention of Corruption Act, 1988") via fuzzy matching against the full
local title. Skips honestly (never guesses) when an Act reference has no
year and is genuinely ambiguous in the corpus ("Income Tax Act" — both a
1961 and a 2025 Act exist), when no Act name was detected at all, or when
the Act isn't in the 836-row Central index — all confirmed by tests to
make zero network calls in those cases.

`ui/app.js` (both render sites), `ui/index.html` (both disclosure
paragraphs) updated from IndianKanoon.org to India Code / eCourtsIndia.
`ui/styles.css`'s statute-lookup box given a max-height + scroll since real
section text runs much longer than the old search snippet. `tests/
test_provision_lookup.py` fully rewritten (10 tests, fake local index + fake
`requests.get`, no real network). Verified end-to-end via a live server +
real browser: uploaded a real fetched judgment with the provisions checkbox
on, confirmed the real India Code text renders correctly and scrolls inside
its own box on the actual Provisions tab. Full suite: 83 passed.

## 2026-09-11 (77) — structural fix for F-22's residual address-fragment noise, plus a real GLiNER gap on "State of Maharashtra"

Owner asked to fix the residual party-extraction noise F-22's addendum
identified as a document-structure problem after a GLiNER-label attempt was
rejected there. Full writeup: `FINDINGS.md` F-23.

1. **`document_profile._group_entries()`**: once inside a NUMBERED party
   entry, a line now defaults to "continuation of this entry" instead of
   "new party" unless it's itself a new numbered entry. Gated on the
   current entry actually being numbered, so the unnumbered 2-party VERSUS
   caption (the common case) is unaffected. Fixed all 3 of F-22's residual
   noise strings in one structural change.
2. `Page N of M` page-break lines split out of `_is_caption_furniture_line`
   into their own `_PAGE_BREAK_RE`, handled as a transparent skip instead
   of resetting the current entry.
3. **`casemap_service._judge_party_name()`**: GLiNER returns zero entities
   for "State of Maharashtra"/"State of Madhya Pradesh" (but judges "State
   of U.P." fine) — a genuine, previously-invisible false negative on the
   single most common Indian-litigation respondent pattern, unrelated to
   F-22. Given a small zero-shot model's demonstrated per-state
   inconsistency, added a deterministic regex bypass (`_GOVT_LITIGANT_RE`)
   for "State of X"/"Union of India"/"Government of X" ahead of the model
   call.

6 new tests. Full 22-doc `testdata/` sweep: 21/22 docs identical to the
F-22 baseline; doc09 went from 10 to 7 parties, verified by hand as pure
noise removal (address fragments that had been wrongly split off Bank of
Baroda/Sunil Kumar Gupta's own entries), not a regression. Full suite: 81
passed (was 75).

## 2026-09-11 (76) — real fetched affidavits/agreements/petitions surfaced 2 party-extraction bugs; both fixed and tested

Owner asked to fetch real public documents outside `testdata/` and see how
the pipeline performs. Fetched 5 real documents (real filed SC writ
petition, real filed NGT appeal, a real affidavit format, two RERA
Agreement-for-Sale forms) into `temp/2026-09-11-real-docs-fetch-test/`
(gitignored). Full writeup: `FINDINGS.md` F-22.

1. **`document_profile.extract_parties()`**: added a `BETWEEN: ... AND ...`
   caption path (tribunal captions with no VERSUS) alongside the existing
   VERSUS ladder, gated on `BETWEEN:` actually being present. Fixed a second
   bug this surfaced: `_block_bounds_above()`'s blank-line heuristic (built
   for an unknown VERSUS block boundary) truncated a known-boundary BETWEEN
   block on a PDF layout artifact, dropping 3 real Appellants — now skipped
   when the boundary is already known. `ADDRESS_LINE_RE` extended with
   `tal.`/`taluka`/`tehsil`/`village` and page-break lines
   (`Page N of M`) added to caption furniture.
2. **`casemap_service._judge_party_name()`** (GLiNER): a trailing `& Ors.`/
   `& Anr.` suffix was blanking the model's prediction entirely for an
   otherwise-recognized real name ("N. RAM & ORS" -> 0 entities, "N. RAM"
   alone -> correctly tagged). Now stripped before judging only. Also fixed
   the coverage check to sum ALL returned entity spans instead of requiring
   one single span to cover ≥70% — a name GLiNER split into two adjacent
   spans covering 94% combined was previously rejected.

9 new tests (`tests/test_between_and_caption.py`,
`tests/test_gliner_party_judge_suffix.py`); re-swept all 22 `testdata/`
docs directly — identical tier/party-count, no regression. Full suite: 75
passed (was 66).

## 2026-09-11 (75) — Docling layout layer removed: never active, redundant with existing OCR, no measured benefit

Owner asked why Docling was needed given the project's own infra, and to
close the question rather than leave it as an "optional, accepted" gap.
Full analysis: `FINDINGS.md` F-21 (closes F-15 item 2).

Found: `docling` was never installed in this project's own `.venv` (by
design, never revisited) — every real document this pipeline has ever
processed went through the legacy text-pattern detector only, so the
Docling code path had never once run outside an isolated eval venv. Its
credited OCR handling of scanned PDFs (F-10) is fully duplicated by the
pipeline's own first-class OCR stage (three engines, caching, page
classification — `casemap_pipeline.py` STAGE 0). Its one distinct
capability (generic ML layout-based heading detection vs. the legacy
detector's fixed `ANNEXURE_PATTERN` vocabulary) was only ever measured on
heading-text correctness, never on a downstream extraction-accuracy gain —
no test in this project compared results with vs. without it. Against a
~1.5GB weight and the project's own small-model design center (same
reasoning that already closed Qwen3-Embedding, F-15/F-19), the case to keep
it evaluating-but-uninstalled forever was weak.

Removed: `src/layout_structure.py`, `tests/test_layout_structure.py`,
`requirements-docling.txt`, `run.ps1 -IncludeDocling`. Simplified
`casemap_pipeline.segment_document_layered()` to call `detect_structure()`/
`segment_document()` directly — same `(sections, {tier, confidence,
tier_reason, stats})` return shape, so `casemap_service.py`, the report, and
`tests/test_poc_structure_t4.py` (literal-tier-string contract test, never
imported `docling`) needed no changes. Fixed a dangling comment in
`requirements.txt` pointing at the deleted file. Full suite: 66 passed (was
70 passed/1 skipped — the 4 mocked-Docling tests and 1 self-skipping real-PDF
test are gone with the file).

## 2026-09-11 (74) — three more rhetorical-role models run for real via WSL; two platform issues genuinely fixed, none produce usable output

Owner pushed back on (73)'s conclusion: the `opennyai` blocker looked like a
platform gap, not proof the model doesn't work, and asked to actually try
fixing it. Right instinct — WSL/Ubuntu (already installed) has real GCC,
sidestepping the whole MSVC-flag problem. Full writeup: `FINDINGS.md` F-20.

1. **AllenNLP** (original OpenNyAI baseline dependency): confirmed dead, not
   a version-pin issue — its own `spacy<3.4` pin needs `distutils.
   msvccompiler`, removed from modern `setuptools`. Not pursued further.
2. **Hier_BiLSTM_CRF** (the paper's best model, F1 0.77): **the platform fix
   worked.** Built the real `sent2vec` (C++) clean under WSL after it failed
   under MSVC on Windows. Found and fixed 4 real bugs to get inference
   running (`argparse type=bool` footgun, PyTorch 2.6's new
   `weights_only=True` default, a CUDA-only checkpoint on a CPU machine, and
   a genuine bug in the paper's own code — `device` never passed through to
   two submodules). Ran clean. Tested against 2 real `testdata/*.txt`
   judgments with this project's own sentence splitter (to rule out bad
   input): caught one real `Arguments of Petitioner` the phrase-matcher
   would have missed, but otherwise collapsed to near-all-`Facts`/`None`,
   zero Issue/Arguments of Respondent/Reasoning/Decision predictions across
   both documents.
3. **InLegalBERT(i)** (plain `transformers`, no platform issue at all):
   loaded with zero missing/unexpected keys — architecture guess confirmed
   exactly right. Real predictions on the same 2 documents look close to
   random ("The High Court confirmed the conviction..." → `Issue` at 0.85;
   a table-of-contents fragment → `Arguments of Respondent` at 0.55) — the
   HF repo ships no label-mapping file, so the assumed label order may not
   match their actual training encoding, and there's no way to confirm it
   from outside their training code.

Verdict: `RHETORICAL_ROLE_CUES` stays on the plain phrase/fuzzy matcher.
Real, useful platform fixes (WSL + `sent2vec`) now exist as a documented
path if a future, better-labeled checkpoint shows up. No changes to
`src/`, `requirements*.txt`, or the project's own `.venv` — everything for
this evaluation lived in `temp/2026-09-11-*-poc/`, never committed.
`pytest`: unaffected, still 70 passed, 1 skipped.

## 2026-09-11 (73) — evaluated `opennyai`'s real rhetorical-role model; blocked on an upstream Python 3.13 build failure, not pursued further

Owner asked to check whether `opennyaiorg/InRhetoricalRoles` (flagged in
`opennyai_bridge.py:122` as an "unconfirmed inference entrypoint") actually
has a working, installable API now, and approved installing Python 3.13
(`winget install Python.Python.3.13`, isolated from the project's Python
3.11 `.venv`) to evaluate it in a throwaway venv first.

Found: yes, `pip install opennyai` + `Pipeline(components=['Rhetorical_Role'])`
is real and documented — but it needs Python >=3.13 (the Python-3.11-
compatible release hard-pins a spaCy version that conflicts with this
project's mandatory `en_legal_ner_sm` spaCy 3.8.16 pin either way). Set up
`temp/2026-09-11-opennyai-rhetorical-role-poc/venv_opennyai/` (never
committed) on the new Python 3.13 and tried installing it there.

**Blocked**: `spacy-curated-transformers` (a hard runtime dependency of
`Rhetorical_Role`, not optional — it loads `en_core_web_trf` for internal
preprocessing) requires `thinc>=9.0`, whose own Cython source fails to
compile under Python 3.13's toolchain on this machine. Every other declared
dependency (torch, transformers, spacy-transformers, pytorch-transformers)
installed cleanly in isolation — this is narrowly a `spacy-curated-
transformers`/`thinc` upstream build problem, not a broader Python 3.13
issue, and not something fixable from this project's side. `opennyai` is
also still labeled "Pre-Alpha" on PyPI.

Verdict: not viable right now. `RHETORICAL_ROLE_CUES` stays on the plain
phrase/fuzzy matcher. No changes to the project's own `requirements*.txt`
or `.venv` — Python 3.13 stays installed system-wide (harmless, isolated)
in case a future `opennyai` release fixes this. Full writeup in
`FINDINGS.md` F-19's addendum.

## 2026-09-11 (72) — provision lookup gets test coverage; rhetorical-role embedding fallback tried and rejected; Qwen3-vs-MiniLM decision closed

Owner asked to tackle the two remaining "what's next" items (rhetorical-role
fixed phrases, provision-lookup test coverage) and close out the long-open
Qwen3 embedding decision.

1. **`tests/test_provision_lookup.py` (new, 8 tests).** Fake `requests.get`
   (real regex/confidence-gate/cache logic, faked network response) —
   confident match, judgment-result correctly skipped, wrong-section-number
   correctly skipped, no results, non-OK response, `ConnectionError` never
   crashes, cache hits exactly once per unique query. Full suite: 70 passed
   (up from 62), 1 skipped.
2. **Rhetorical-role embedding fallback: tried, tested against real data,
   rejected.** Same fix pattern as (68)/(70) — reuse `all-MiniLM-L6-v2`
   against `RHETORICAL_ROLE_CUES`'s own phrases as anchors. Built
   `scripts/tune_rhetorical_embedding.py`, ran it against all 22 real
   `testdata/*.txt` judgments before wiring it in, and roughly half the
   matches were wrong (header/caption noise mistaken for arguments, wrong
   role on real content). Reverted (`git checkout -- src/rhetorical_roles.py`)
   rather than ship something less trustworthy than the plain phrase
   matcher it would have replaced. Full writeup + examples in `FINDINGS.md`
   F-19. `RHETORICAL_ROLE_CUES` stays a genuinely open item — needs an
   actual trained classifier, not another parse-based trick.
3. **Qwen3-Embedding-0.6B decision: closed, rejected.** Owner's call: stay
   on `all-MiniLM-L6-v2`. ~112x the per-sentence cost for a ~40%-different
   (not more correct, just different) pick isn't worth it given this
   pipeline's design center is small, CPU-friendly models throughout.
   `FINDINGS.md` F-15 updated in place (struck through, not deleted).

## 2026-09-11 (71) — correction to (70): remove the `neg`-dependency polarity signal, keep only verb lemmas

(70)'s dependency-parse polarity fix was tested immediately after landing
against a real document — the owner's own writ petition
(`temp/2026-09-10-real-petition-run/BCI_NOC_WP.txt`, never committed, local
run only) — via `casemap_service.process_document(lookup_provisions=...)`.
Result: the blanket "any negated verb = DENIES" half of that fix mislabeled
**20 of 111 events (18%)** DENIES, almost all of them ordinary negated legal
argument ("does not maintain", "cannot accomplish"), not one party denying
another's fact. `label_edge()`'s POTENTIAL_CONFLICT pairing is what
DENIES/ASSERTS actually feeds — this was real noise, not a fix.

Removed the `neg`-dependency tag check from `_classify_polarity()`; kept
`DENIAL_VERB_LEMMAS`/`ASSERTION_VERB_LEMMAS` (still catches "refutes the
claim", "counsel contends that" — real gaps in the old phrase list — without
the flood). Re-ran the same real document post-fix: DENIES 20 → 1, ASSERTS
unchanged at 3. See `FINDINGS.md` F-18's correction note. `pytest`: 62
passed, 1 skipped, no regressions.

## 2026-09-11 (70) — polarity (DENIES/ASSERTS) gets a dependency-parse signal alongside the fixed phrase lists, same fix class as (68)

Owner asked to fix `DENIAL_MARKERS`/`ASSERTION_MARKERS` the same way as (68)
— they're the same fixed-phrase-list problem, just for conflict-detection
polarity instead of event detection. See `FINDINGS.md` F-18.

1. **`casemap_pipeline._classify_polarity()`**: after the existing
   `DENIAL_MARKERS`/`ASSERTION_MARKERS` phrase checks (kept, unchanged —
   idiomatic phrases like "false and baseless" have no verb to key off), a
   second pass checks `en_core_web_sm`'s own `neg` dependency tag (real
   syntactic negation on any verb) and two small new verb-lemma sets
   (`DENIAL_VERB_LEMMAS`, `ASSERTION_VERB_LEMMAS`) — same model already
   loaded for entity extraction, no new dependency.
2. Catches phrasing the old list missed: "has not received", "is denying",
   "refutes the claim" → DENIES; "counsel contends that" → ASSERTS.
3. Verified with direct unit checks on both the newly-caught cases and the
   existing phrase-list cases (unaffected). Full `pytest`: 62 passed, 1
   skipped, no regressions.

## 2026-09-11 (69) — new, opt-in: cited provisions' own text fetched from IndianKanoon.org

Owner asked for a free web lookup showing what a cited provision actually
says, explicitly scoped to "only the provision, not client details." First
outbound network call anywhere in this pipeline — recorded and disclosed
accordingly (see `FINDINGS.md` F-17 for the full writeup).

1. **`src/provision_lookup.py` (new).** `lookup_provision(section_raw, act)`
   — one call per unique provision, query is the citation string alone.
   Confidence-gated against IndianKanoon's own statute/judgment type marker
   plus a section-number match in the result title; returns `None` (skips)
   rather than guessing on anything less than a clear match.
2. **`casemap_service.process_document(lookup_provisions=False)`** (default
   off) — runs the lookup once per unique provision per document, attaches
   `statute_lookup` to each `provisions_detail` entry and to the
   cross-document `provisions` aggregation.
3. **`server/app.py`**'s `/api/process` takes `lookup_provisions` as a form
   field (`Form(False)`).
4. **`ui/index.html`**: new checkbox on the upload screen, unchecked by
   default, with its own disclosure text ("sends only the citation itself
   ... never any document content"). Dashboard's privacy paragraph updated
   to state the toggle's effect plainly rather than leave the older
   absolute "only thing that ever leaves this device" claim technically
   wrong once it exists. `ui/app.js`/`ui/styles.css`: rendered in both the
   printable counsel report and the live **Provisions** tab.
5. `requests` (already present transitively) pinned explicitly in
   `requirements-webapp.txt` now that `provision_lookup.py` imports it
   directly.

Verified end-to-end against real `testdata/` documents through the running
server — confident matches return correct statute text + source link,
genuinely ambiguous citations skip cleanly. Screenshot-checked in both
themes. Full `pytest`: 62 passed, 1 skipped, no regressions.

## 2026-09-11 (68) — event detection: dependency-parse (SRL) layer replaces reliance on the fixed `EVENT_KEYWORDS` phrase list, no new model

Owner asked whether event detection was hardcoded ("paid"/"terminated"/"filed
on" — yes, `EVENT_KEYWORDS` in `casemap_pipeline.py`) and whether structured
who/what/when/modal detection could raise accuracy without a heavy
generative LLM. `scripts/poc_srl_events.py` proved it: `en_core_web_sm`
(already mandatory-loaded for entity extraction on every document) already
produces a full dependency parse and POS tags per sentence — none of that
was being used for event detection, only literal phrase matching.

1. **`casemap_pipeline.detect_events_srl()` (new).** WHO (nsubj/nsubjpass),
   ACTION (root verb lemma), WHAT (dobj/attr/prep-object), WHEN (DATE
   entities), MODAL (MD-tagged will/would/could/shall/may/should/must) read
   directly off the existing parse. Fires only for a date- or modal-bearing
   sentence no earlier stage already turned into an event (`covered_spans`,
   accumulated per-section by the caller) — additive, never duplicates.
   Header/citation furniture excluded via the same `_header_exclude_end()`
   entity extraction already uses.
2. **`EVENT_VERB_LEMMAS` (new, replaces `EVENT_KEYWORDS` for TYPE LABELING
   only — `EVENT_KEYWORDS` itself is untouched, still used by
   `detect_events()`'s own keyword-hit scan).** One verb lemma ("pay") covers
   every inflection/phrasing a multi-word phrase list had to enumerate one at
   a time. A verb not in the map isn't dropped — it becomes an untyped
   `FACT` event, still shown with its real WHO/WHAT/WHEN.
3. **Wired into `casemap_service.py`**'s per-section loop, right after the
   existing `_events_for_uncovered_dates()` fallback, sharing its
   `covered_spans` bookkeeping so nothing is double-counted.
4. **Measured, not assumed** — see `FINDINGS.md` F-16 for the full before/
   after numbers (23% of real event sentences missing pre-fix on real
   judgments; ~0% post-fix, re-verified against all 22 `testdata/*.txt`
   documents). Full `pytest`: 62 passed, 1 skipped, no regressions.

Deliberately NOT touched this pass (same class of fixed-phrase hardcoding,
flagged in F-16 as open follow-ups): `DENIAL_MARKERS`/`ASSERTION_MARKERS`
(polarity) and `RHETORICAL_ROLE_CUES` (Facts/Issues/Ruling tagging).

## 2026-09-11 (67) — dashboard: sharper "what this is" framing + a standing correctness disclaimer

Owner reviewed a counselor-style critique of the tool (verbatim-indexing
assistant, not a legal-AI tool; no independent legal validation; date/OCR
misses possible; English-only) and asked for the same framing and an
explicit correctness warning to go on the dashboard itself, not just in
conversation.

1. **`ui/index.html`'s intro paragraph sharpened.** Now states directly that
   CaseMap is "a verbatim document-indexing assistant, not a legal-research
   or drafting tool" and that it "doesn't summarize, paraphrase, generate, or
   reason about your case" — setting the right expectation up front instead
   of only implying it.
2. **New standing correctness notice** on the dashboard (not dismissible —
   this is a permanent fact about the tool, not a one-time tip): extraction
   can miss or misread a fact, especially on poor-quality scans, non-English
   text, or unusual formatting; it never checks whether a cited provision is
   still good law; every date/amount/citation is a first pass to verify
   against the original document, not a second opinion. New `.correctness-
   notice` style in `ui/styles.css` (uses the existing `--warn`/`--warn-soft`
   tokens already in the palette, left-border accent, both themes checked
   live in the browser).

## 2026-09-11 (66) — one-command setup+run script; README fully detailed; open-items pass across HANDOFF/FINDINGS/TRACKER

Owner asked for all open items/findings to be marked down with proper
comments, and for the README to detail how to run the project, including one
script that installs all dependencies and runs both frontend and backend.

1. **New `run.ps1`** — one PowerShell script that creates `.venv` if missing,
   installs `requirements.txt` + `requirements-webapp.txt`, installs the
   mandatory `en_legal_ner_sm` model and `en_core_web_sm` if not already
   present, checks (warns, does not fail) for the system Tesseract OCR
   binary, then starts `server/app.py` on port 8756. There's only one process
   to run either way — `server/app.py` mounts `ui/` as static files, so the
   backend already serves the frontend; the script makes that one command.
   Flags: `-Port`, `-NoBrowser`, `-IncludeDocling` (optional heavy structure
   layer). Verified end-to-end against the existing `.venv` (idempotent —
   detects already-installed models, doesn't reinstall) and confirmed
   `/api/health` responds after it starts the server. One real bug fixed
   while writing it: `$ErrorActionPreference = "Stop"` at the top made a
   harmless spaCy stderr warning during the model-presence check abort the
   whole script (PowerShell treats native-process stderr as a terminating
   error under "Stop") — removed the global setting, check `$LASTEXITCODE`
   explicitly after the installs that actually matter instead.
2. **`README.md` rewritten** with a full quick-start (`run.ps1`), a by-hand
   fallback for non-Windows/troubleshooting, a "using the app" walkthrough,
   test-running instructions, and a one-paragraph architecture summary. The
   old "run it" section still described `poc_run.py` as drifted behind the
   web pipeline — stale since entry 63's refactor; corrected.
3. **Open-items pass** — `FINDINGS.md` F-15 (new) consolidates what's
   genuinely still open (Qwen3-Embedding adoption decision; Docling not
   installed in this `.venv`; `important_lines.py` needs a second real
   petition) versus what several docs still called "open" but code proves
   is already resolved (Tier 1's NER blocking item; the `extract_parties_
   layered()` header-furniture bug; the verbatim-fallback-nodes and
   structure-T3 requirement folders). `HANDOFF.md` §7 got a dated correction
   block (its own historical text left intact, per this project's
   conventions) and §10's `git init` item marked done. `docs/requirements/
   2026-09-09-structure-and-embedding-layers/TRACKER.md`'s stale "T3 — Not
   started" row corrected in place (that file is living state, not
   append-only history).

## 2026-09-11 (65) — verified two "still open" STATUS.md items are actually already done; no code changed

Owner asked to check whether `en_legal_ner_sm` (the mandatory OpenNyAI NER
model) was ever wired in, and about the "un-triaged" `document_profile.
extract_parties_layered()` header-noise bug flagged 2026-09-10.

1. **`en_legal_ner_sm` — already installed and active, STATUS.md was stale.**
   `spacy.load('en_legal_ner_sm')` succeeds directly in this project's own
   `.venv` (not just the standalone `venv_ner`), and `get_ml_nlp()` →
   `bridge.load_opennyai_ner("sm", allow_degraded=True)`
   (`src/casemap_service.py`) is called by every `process_document()` run.
   Every server boot / CLI run / test this session logged `[+] ML layer:
   active` — real weights, not the regex-only degraded fallback.
   `allow_degraded=True` is only a graceful-fallback flag for machines
   without the model installed, not a signal that degraded mode is the
   default outcome. Tier 1's original blocking item (`STATUS.md`,
   2026-09-09) is closed; the note describing it as still open was outdated
   and has been corrected in place.
2. **The F-9 header-furniture bug was already fixed same-day (2026-09-10),
   just never marked as such.** `docs/requirements/2026-09-10-party-ladder-
   header-furniture/` implements exactly this fix; `tests/
   test_party_ladder_header_furniture.py` covers it. Verified directly: ran
   `extract_parties_layered()` on all 22 `testdata/*.txt` docs — zero
   `Author:`/`CITATION`/`CITATOR` names leak in as parties; also ran
   `extract_parties_hybrid()` with the real `en_legal_ner_sm` model loaded
   (doc 09) — clean, only real litigant names. STATUS.md's "not yet its own
   requirements folder" line was stale; corrected in place.

No source code changed — both items were real, already-shipped fixes that
the running status log had simply never caught up to.

## 2026-09-11 (64) — drawer evidence highlight: exact offsets instead of a fragile text search (F-14's last open item)

Owner: fix the drawer highlight no-op on boundary-trimmed `s.text` (flagged
entry 62/63, F-14).

`ui/app.js`'s evidence drawer used to relocate the highlighted span inside its
wider context by a literal `String.replace(esc(s.text), ...)` search — fragile
by construction: it silently no-ops whenever `s.text` isn't found as an exact
substring of `s.context`, can highlight the wrong occurrence of a repeated
phrase, and a `text` containing `$&`/`$1`/etc. hits `.replace()`'s special
replacement-pattern syntax and corrupts the output. The backend already
computes exact character offsets for this — `_attach_context()`
(`src/casemap_service.py`) sets `context_start` alongside `char_start`/
`char_end` — but the frontend never read it. New `highlightSpan()` helper
(`ui/app.js`) slices `ctx` directly at `char_start - context_start` /
`char_end - context_start`, **self-verified** against `ctx.slice(lo, hi) ===
text` before trusting it, so a source whose offsets don't correspond to the
displayed text (the one real case: `_section_fallback_event`'s `char_end`
spans the whole section while `text` is only its first ~400 boundary-trimmed
chars) falls back to the old search instead of mis-highlighting. Verified
against real pipeline output (insolvency bundle, 16 real event sources): 12
now hit the precise offset path (previously search-only), 4 fall back
correctly, 0 no-ops — and against synthetic cases for `$`-in-text and
no-match-at-all. Full suite still 62 passed / 1 skipped.

## 2026-09-11 (63) — audit follow-ups: esc() attribute-injection fix; the pipeline unified into one shared module (server + CLI both wrap it), ending the poc_run drift

Owner: two audit follow-ups, one at a time — (1) fix the `esc()` quote bug,
(2) decide poc_run.py's fate (refactor to shared core vs retire). Owner chose
refactor to shared core.

1. **`esc()` now escapes quotes.** `ui/app.js`'s `esc()` escaped only `&<>`,
   but its output is interpolated into HTML *attributes* too (e.g.
   `title="${esc(...)}"`), so a `"` in a document or party name could break
   out of the attribute. Now also escapes `"`→`&quot;` and `'`→`&#39;`.
   Verified: `Smith "Bob" & O'Neil <x>` → fully entity-escaped.

2. **One pipeline, two thin wrappers — the poc_run drift is over.** All the
   2026-09 pipeline improvements had lived ONLY in `server/app.py`, so
   `scripts/poc_run.py` silently ran an older, weaker pipeline while its
   report claimed to prove "the pipeline" (flagged in entry 62 / F-14).
   Extracted the entire per-document + graph pipeline into a new
   **`src/casemap_service.py`** (moved verbatim — no logic changes):
   `process_document()` (was server's `_process_one`, now also accepts
   `ocr_lang`/`force_ocr` for the CLI) and `build_case_graph()` (was the body
   of the server's `/api/process`, incl. the cross-document entity gate), plus
   all their helpers and the lazy SaT/GLiNER/NER model loaders.
   - `server/app.py` is now a thin HTTP wrapper (upload → temp dir → 
     `service.process_document` → `service.build_case_graph` → add
     runtime_s/ml_layer; `/api/health` → `service.layer_status()`). No
     pipeline logic remains in it. Boots clean; `/api/health` verified.
   - `scripts/poc_run.py` is now a thin CLI wrapper over the same
     `process_document`/`build_case_graph` (with `return_details=True` to get
     the scoring internals its cross-doc/bi-temporal report sections need).
     Its Markdown proof report + `poc_graph.json` now reflect the REAL
     pipeline. The bi-temporal `TemporalEdge`/`apply_invalidation`/
     `persist_edges` (SQLite) experiment stays poc-only, deliberately out of
     the server (privacy contract; and F-14 showed it fires on ~0 real edges).
   - **CLI change:** `--important-lines` and `--gliner` flags removed —
     important-line extraction is now always on (part of the one pipeline),
     and GLiNER entity extraction was rejected (entry 62 / F-14), so a flag
     that silently did nothing would be worse than none.
   - Verified: full suite **62 passed / 1 skipped** (one T4 test rewrote to
     assert the real `build_case_graph` documents[] contract instead of a
     removed poc-only helper); end-to-end on the insolvency bundle still gives
     4 cross-doc edges all WITHIN the genuinely-connected 09/21/22 bundle, 20
     nodes with rhetorical roles, 4 provisions — i.e. behavior-preserving.

## 2026-09-11 (62) — full-repo audit; two unused-but-beneficial features tested against the whole corpus and wired in; two rejected with evidence; stale design docs synced; dead code removed

Owner: (1) do a deterministic line-by-line audit of the whole repo — find
dead code, find unused-but-beneficial functionality, find refactor scope,
and above all confirm it isn't accidentally built to work on only one
petition; (2) test the unused-but-beneficial features against every document
we have and wire in the ones that produce good results; (3) sync the stale
design docs; (4) delete the genuinely-dead code.

**Petition-generality verdict (the headline ask): it is NOT single-petition.**
Read line-by-line, `document_profile.py` carries 7 declarative document
profiles and a 5-tier party ladder; `server/app.py` dispatches PDF/DOCX/TXT
and builds a real cross-document graph; nothing hardcodes any specific party,
case number, date or filename. It IS India-specialised (Rupee-only amounts,
OpenNyAI Indian NER, Indian forum/case-number regexes, DMY date bias) — the
correct scope for its market, now stated in `FINDINGS.md` F-14 rather than
assumed.

**Tested all four "unused-but-beneficial" candidates against all 22
`testdata/` docs; wired the two that earned it:**

1. **Rhetorical-role labelling — WIRED.** `rhetorical_roles.tag_paragraphs`
   was defined and tested but never used by the product (only `split_paragraphs`
   was). `server/app.py` `_attach_rhetorical_roles()` now labels each event with
   the FACTS/ISSUES/ARGUMENTS/ANALYSIS/RULING/PRECEDENT role of the paragraph
   it sits in, written onto `sources[0]` (so `to_react_flow` passes it through
   untouched). The evidence drawer shows it ("Argument role", with an
   "inferred from section" note when carried-forward). Corpus result: 46 events
   across 9 docs, sensible distribution (FACTS 26, ARGUMENTS_PETITIONER 12,
   ISSUES 4, ANALYSIS 4). A classifier, never a generator — verbatim guarantee
   intact.
2. **Amounts-written-in-words — WIRED.** `case_symbols.amount_from_words` was
   tested but unreachable from product or CLI. Added `case_symbols.find_word_amounts()`
   (conservative: currency anchor + a scale word + a clean parse), called in
   `_process_one` to augment `det["amounts"]`, deduped against figure amounts.
   Corpus result: correctly added "rupees one crore" (doc 13) with zero false
   positives. Low yield on appellate judgments; higher on the contracts/notices
   the tool also targets.
3. **Bi-temporal invalidation — REJECTED (evidence).** `apply_invalidation`
   fired on **0** edges across the connected insolvency bundle: it needs two
   distinct edges on the same node-pair (one SUPPORTS + one POTENTIAL_CONFLICT),
   which the current graph never produces. It also depends on `persist_edges`
   writing to `casemap.db`, which would break `server/app.py`'s stated
   "nothing is persisted" privacy contract. Left in `poc_run.py` only.
4. **GLiNER-multi entity extraction — REJECTED (evidence).** 218s cold-start
   and ~6–10× slower than spaCy warm; surfaces court-name noise ("HIGH COURT OF
   KERALA", "MUNSIFF'S COURT") the entity gate exists to remove, which would
   reintroduce the false cross-document edges fixed in entry 58; its label set
   doesn't map to the PERSON/ORG/GPE scheme the graph is built on. No ground
   truth showed it links *better*. spaCy stays the default (THESIS §5: don't
   swap a proven component for an unproven slower one).

**Pre-existing bug found while testing feature 2 and fixed:** `AMOUNT_PATTERN`
(and `case_symbols._AMOUNT_NUM`) used `[\d,]+`, which matched a bare comma —
so "Rs.," / "Rs," (a currency marker with no figure, common in real filings)
became a junk "amount". Now `\d[\d,]*` (must start with a digit). 5 new tests
in `tests/test_word_amounts.py` cover both new-feature and the fix.

**Genuinely-dead code removed** (see entry body's audit): the unused,
wrong-geometry `image_area` computation in `classify_page`; dead
`detect_structure`/`segment_document` imports in `poc_run.py`; a no-op
`current_role = current_role` self-assignment in `rhetorical_roles.py`; and
five dead CSS rule-sets in `ui/styles.css` left over from removed features
(`.tl-doc-group`/`.tl-doc-title`/`.tl-note`, `.tl-dot.gold`/`.undated`, the
`.keypoints`/`.kp-*` block, `.expand-toggle`, `footer.reportfoot`).

**Docs synced:** `README.md` ("do not build UI" → how to run the app),
`THESIS.md` §2 and `HEART.md` §2 (dated correction banners noting the built
backend/UI; past text kept unedited per THESIS §8 / FORBIDDEN A5). Full suite:
**62 passed, 1 skipped** (was 57/1).

## 2026-09-11 (61) — anonymous page-load counter (real, verified), a "Reprocess" option using real re-readable file handles (not a saved path — browsers don't expose those), and a dashboard description

Owner: (1) a simpler usage-counting mechanism ("increase on screen load")
than what was discussed and declined last entry, (2) a way to reprocess
the same files without re-browsing, explicitly requesting "save the path
in a cookie", (3) a description of what the app does on the landing page,
(4) confirmation the company URL was actually added (it was, entry 60).

1. **Page-load counter, built this time**, with the same "screen load,
   nothing else" framing the owner asked for. Verified a real, live,
   no-signup counting service directly via curl (not just fetched once —
   confirmed it actually increments across three real calls: 1→2→3) before
   wiring anything in, after a first candidate (countapi.xyz) turned out to
   be dead. `ui/app.js` `App.init()` fires one `fetch()` to it per real
   page load, wrapped in `.catch(() => {})` so an unreachable counter never
   affects the app. This remains the ONLY network call this app makes to
   anywhere that isn't its own local backend — disclosed directly on the
   dashboard, not hidden.
2. **"Save the path in a cookie" isn't something a browser will do** —
   `<input type=file>` deliberately never exposes a real filesystem path
   to JavaScript, cookie or otherwise; that's a security boundary, not a
   missing feature. Built the closest real equivalent instead: Chrome/
   Edge's File System Access API hands back a `FileSystemFileHandle` the
   browser itself can re-read later after a one-click permission re-grant
   — no path ever touches this code, stored/retrieved from IndexedDB
   (`HandleStore` in `ui/app.js` — localStorage can't hold a handle
   object, only strings). Wired into the upload flow: picking files via
   the file browser (not drag-and-drop — that path doesn't reliably offer
   a re-readable handle) now uses `showOpenFilePicker()` when available,
   saves the handles after a successful process, and a "↻ Reprocess"
   button appears on the case view (only when a handle was actually
   saved) that re-requests permission, re-reads the SAME files fresh from
   disk, and re-runs extraction in place. Verified: IndexedDB save/get/
   remove round-trip works; the button correctly stays hidden for a case
   with no saved handle. Real, disclosed limitation: Chrome/Edge only —
   Firefox and Safari don't implement this API at all, and drag-and-drop
   uploads don't get a re-readable handle either; both are stated in the
   button's own tooltip, not hidden.
3. **Dashboard now explains what the app does** before a new user uploads
   anything — added an intro paragraph above the existing privacy note.
4. Company URL confirmed already live (entry 60) — EcoCode Solutions /
   ecocodes.in in the footer of every page and the PDF report.

## 2026-09-11 (60) — page estimation now length-aware (not just explicit breaks); two real date-format gaps closed plus a real ISO-date parsing bug found; company branding added

Owner: page counting via explicit Word breaks alone was wrong (a real
document only breaks 9 times for 10 sections, leaving everything after the
last break in one ~35,000-character "page" — obviously not one real page),
and date-format coverage needed auditing against known variants rather
than just the one format already fixed.

1. **Page estimation** — `_docx_to_pages()` in `server/app.py` now
   combines explicit breaks (still the strongest signal, kept as hard
   boundaries) with a ~3000-char/page estimate that sub-divides any block
   too long to plausibly be one real page, splitting only at paragraph
   boundaries. Explicitly an ESTIMATE, documented as such — true
   pagination would require actually rendering the document (fonts,
   margins, tables), which python-docx cannot do. Verified on the real
   petition: 10 pages → 25, with the former 35,633-character mega-page
   correctly sub-divided into ~12 realistic ones.
2. **Date formats** — audited `DATE_CANDIDATE_PATTERN` directly against
   known real-world variants rather than assuming the dot-date fix
   (entry 44) was complete. Found and closed two real gaps: month-name
   FIRST ("December 5, 2025" — the pattern only matched day-then-month),
   and ISO 8601 ("2025-12-05" — not matched at all). Found a THIRD, more
   serious bug while verifying the ISO fix: `extract_deterministic()`
   forces `DATE_ORDER: "DMY"` on every match including unambiguous ISO
   dates, which made dateparser silently swap month/day — "2025-12-05"
   (Dec 5) parsed to `2025-05-12` (May 12), wrong, with no error. Fixed by
   parsing ISO-format matches directly via `date.fromisoformat()`,
   bypassing the DMY-biased settings meant only for the ambiguous
   DD/MM/YYYY-style formats. Full suite re-run: 57 passed, 1 skipped.
3. **Branding** — "EcoCode Solutions" / ecocodes.in added to the app
   footer (every page) and the PDF report's own footer.

Usage-count tracking (owner's other ask) intentionally NOT built yet —
flagged back to the owner rather than silently wired in, since any
cross-machine "how many people are using this" count requires a ping to
somewhere off the user's machine, which is a real, direct tension with
this app's own "nothing leaves your machine" privacy design (`FINDINGS.md`
F-5) that deserves an explicit decision, not an assumption.

## 2026-09-11 (59) — conflict detection actually wired up: polarity now reaches Key Facts/dated entries, a real context-bleed bug found and fixed, and a Conflicts tab shipped

Owner asked to confirm conflict detection was fixable and then, once shown
it fires, to surface it in the UI. Did both, in that order, verifying at
each step rather than assuming:

1. **Extended polarity classification beyond keyword-triggered events.**
   `important_lines.py` hardcodes every `IMPORTANT_LINE`'s polarity to
   NEUTRAL; the `SECTION`/`DATED_EVENT` fallback events in `server/app.py`
   did too — meaning most of what a user actually sees (Key Facts, dated
   entries) could never participate in conflict detection, only the
   keyword-triggered ORDER/NOTICE/PAYMENT/... types could. Reused
   `casemap_pipeline._classify_polarity()` (already tested, no new
   dependency) uniformly across every event type in `server/app.py`,
   layered on top rather than editing `important_lines.py`.
2. **Built two synthetic documents with a genuine assert/deny conflict to
   verify the whole mechanism fires end-to-end** — first attempt scored
   0.303 against the 0.35 threshold (an IDF-weighting artifact of a
   too-small 2-event test, noted and corrected for, not a real bug) after
   adding realistic event density. Found a REAL bug while verifying:
   detect_events()'s ±400-char display window was ALSO being used for
   polarity, and in a short document that window spans multiple unrelated
   sentences — one real "denies" contaminated the polarity of every other
   nearby event (AGREEMENT, FILING, ...) in the same short document,
   producing a false conflict flag alongside the genuine one. Fixed by
   reclassifying polarity from each event's own (SaT-tightened, entry 56)
   sentence text instead of the wide window — false conflict gone, the one
   genuine conflict (a stated payment vs. a denial of that same payment)
   still fires correctly. Full suite re-run: 57 passed, 1 skipped.
3. **Shipped the Conflicts tab** (`ui/index.html`/`app.js`/`styles.css`):
   reads `POTENTIAL_CONFLICT`-labeled edges (real, computed data that was
   simply never rendered before), shows each pair as a side-by-side
   comparison card with document/page for both sides, a badge count on the
   tab itself, and a warning banner framed the same way the original
   pre-web-UI markdown report always framed this feature — "flagged for
   review, not confirmed contradictions." Verified end-to-end against the
   real API response: exactly 1 conflict surfaced, correctly.

## 2026-09-10 (58) — real root cause of the false cross-document connections found: entity IDs were never stable identities; fixed at the source, plus a hard gate as defense in depth

Owner pushed on the cross-document false-positive finding from entry
55's batch test with a concrete proposal: require shared party name as
the trusted connector, not just one weighted term among several. Testing
that led to a deeper, pre-existing bug — not something this session's
work introduced, inherited from `poc_run.py`'s original design too.

`normalize_entities()` (`casemap_pipeline.py`) assigned IDs from a
LOCAL counter (`ent_0001`, `ent_0002`, ...) that resets every time the
function is called — and it's called fresh once per SECTION, for every
document, by both `poc_run.py` and `server/app.py`. Verified directly:
the exact same real entity, "Bank of Baroda", got `ent_0003` in one
isolated call and `ent_0001` in another — same identity, two different
IDs, purely dependent on what else happened to be in that call. This is
why `build_inverted_index()`'s entity-overlap scoring produced the false
positives found in entry 55: a civil property case and an unrelated
financial cheque-bounce case scored `entity_overlap: 1.0` with zero real
shared parties, because their local counters happened to collide.
Fixed at the root: IDs now derive from the canonical name itself
(`f"{etype}:{key}"`, e.g. `"ORG:bank of baroda"`) instead of a counter —
a pure function of what the entity IS, stable across any section, any
document, any call, no shared state needed. No test asserted the exact
`ent_NNNN` string format (checked), only relational connectivity, so this
only makes existing behavior more correct — full suite re-run: 57 passed,
1 skipped, no regressions.

Then added the owner's actual proposal on top, in `server/app.py`, as a
second layer now that entity IDs are trustworthy: cross-document edges
now REQUIRE real shared-entity overlap as a hard gate, not just a high
semantic-similarity score among several weighted terms. Verified in three
stages: (1) the specific false-positive pair from entry 55 — 6 spurious
edges → 0; (2) the real connected insolvency bundle (09/21/22, genuinely
the same matter) still correctly shows cross-document edges — the gate
doesn't kill real connections; (3) the full 30-document batch re-run —
false cross-matter edges **132 → 0** (the 4 remaining cross-document
edges are all within the real 09/21/22 bundle, not false positives —
confirmed by checking which real parties they share). Total edges 291→121,
the removed 170 being exactly the spurious semantic-only noise.

## 2026-09-10 (57) — provisions no longer split by Act-name spelling variance; chronology no longer repeats the same event under near-identical wording or across two dates it happens to mention

Owner asked me to actually read the generated report as a lawyer would
before answering "is this good now" — found two real issues doing that,
fixed both:

1. **Provisions cited fragmented one real citation into several report
   lines.** "Section 22" showed up three times because the Act name was
   spelled differently at different mentions ("UGC Act" vs "UGC Act,
   1956") and `provision_key()` keys on that text verbatim. Added
   `_normalize_act_for_key()` in `server/app.py` — strips a trailing
   ", YYYY" for KEYING only, so those two spellings now group together;
   display still shows the fuller (year-bearing) spelling, preferring the
   longest variant seen rather than first-seen. Verified this doesn't
   over-merge: "Section 22 of the Advocates Act" and "Section 22 of the
   UGC Act" correctly stayed as two separate entries — they're genuinely
   different statutes that happen to share a section number.
2. **Chronology repeated the same real event multiple times.** Two
   distinct causes, both real: (a) several different sentences across
   SYNOPSIS/PRAYER/the PROFORMA form all mention the same Circular date in
   different words — topically redundant even though not literal
   duplicates; (b) a genuine bug — one table row naming two dates
   (21.07.2026 and 25.08.2026) produced a separate `DATED_EVENT` node per
   date, both showing the identical row text, and because they carry
   different dates they never even got compared against each other. Added
   `dedupeByDateSimilarity()` in `ui/app.js`: a global exact-text pass
   first (catches (b) — regardless of date), then a same-date
   word-overlap pass keeping the fullest text per cluster (softens (a)).
   Wired into both the Timeline tab and the PDF report's per-document
   chronology. Verified on the real petition: Timeline dated items 7→6
   (the literal cross-date duplicate gone); the topically-redundant but
   differently-worded trio around 2024-09-24 still shows separately —
   noted honestly as a real, harder remaining limitation, not silently
   claimed as solved.

## 2026-09-10 (56) — SaT boundary judge layered on top of important_lines.py's sentence selection too, not just the date-snippet path

Owner asked whether the SaT judge from entry 55 could also improve the
main sentence detection (important_lines.py's own splitter), and picked
"add a layer on top" over swapping it in outright — the safer choice,
since that splitter is a validated component with its own real-bug
history (F-11/F-12) and stays the source of truth for WHICH sentence gets
selected as important. Added `_refine_bounds_with_sat()` in
`server/app.py`: runs after `detect_events()`/`extract_important_lines()`
already chose their sentences, and only adjusts the CHARACTER BOUNDARIES
of what was already picked — finds the SaT sentence with the most overlap
against an event's existing span and adopts it if different, guarded
against SaT merging multiple sentences into one span (`_sat_sentence_spans`
computed once per section, shared with entry 55's date-snippet path
instead of computed twice). Ranking happens on the ORIGINAL span before
this runs, so it cannot change which sentence was selected, only how
cleanly it displays. Verified on the real petition: several `IMPORTANT_LINE`
nodes are now genuinely longer, complete single sentences (200-280 chars)
that the original splitter's own boundary logic wouldn't have produced —
real refinement, not a no-op — while node count and content stayed sane
(27 IMPORTANT_LINE nodes, all real legal sentences, nothing garbled). Full
test suite re-run: 57 passed, 1 skipped, no regressions.

## 2026-09-10 (55) — two small local "judge" models added: sentence-boundary judge (SaT) and party-name judge (GLiNER) — neither generates text, both only select/classify what already exists

Owner asked whether a small LLM could help, specifically framed as "only
judge and fix, nothing much." That framing matters: `FINDINGS.md` F-11
rejected generative LLMs in this pipeline after 5 summarization models
each distorted at least one real fact. A judge that only picks an offset
or a keep/drop label — never generates the fact text itself — carries a
different, much narrower risk: it can produce a worse cut point or a
wrong keep/drop call, but it can't hallucinate a new fact, because it's
never asked to write one. Researched real fine-tuned models for each job
(not a general instruct LLM prompted narrowly, per the owner's ask) and
verified both directly before wiring them in:

- **`segment-any-text/sat-3l-sm`** (via `wtpsplit-lite`, ONNX, ~0.2B
  params) — fine-tuned specifically for sentence-boundary detection,
  trained to be robust on messy/corrupted text. Verified on the real
  petition's own worst case: correctly kept a tab-separated table row with
  TWO embedded dates as one unit (`21.07.2026\tSupreme Court in W.P.(C)
  No. 31/2025 ... final disposal on 25.08.2026.`), which entry 54's regex
  heuristics could not do. **Also caught it being wrong**: it misread the
  Indian legal abbreviation "SLP(Crl.)" as a sentence end, cutting a
  different real table row short in a way `_line_bounds()` didn't.
  Resolved by testing, not assuming — `_line_bounds()` (the document's own
  real paragraph structure) now runs FIRST when it applies (a short
  single-paragraph row), with SaT as the fallback for genuine prose too
  long to be one structural row, and `_sentence_bounds()` last.
- **`urchade/gliner_small-v2.1`** — a small zero-shot span classifier,
  used as a pure keep/drop filter on party names `extract_parties_hybrid()`
  already produced (never asked to propose a name of its own). Verified
  directly on the real garbage from F-13: `"Vehicle Number (Motor
  Accident): NA"` → empty (drop), `"I. NATURE OF THE"` → empty (drop),
  `"BCI Rules of Legal Education"` → only 3 of 28 characters matched, below
  the 70%-coverage keep threshold (drop — partial containment isn't the
  same as the whole candidate BEING a name), `"BAR COUNCIL OF INDIA"` →
  full match, real org (keep), `"Sunil Kumar Gupta"` → full match, real
  person (keep). Wired into `server/app.py`'s party list build as a filter
  step, `party_tier`/`party_confidence` (the document-level confidence
  flag from entry 43) left untouched so the "verify these" warning still
  shows when the underlying extraction was genuinely unstable, regardless
  of how clean the judged list looks.

Both models are optional layers with the same graceful-degradation pattern
already used for the mandatory NER layer (`allow_degraded`) — on load
failure, boundary judging falls back to the regex heuristics and party
judging fails open (keeps names rather than silently dropping data with no
judge available). `/api/health` now reports `boundary_judge`/`party_judge`
status alongside the existing `ml_layer`. New deps
(`wtpsplit-lite`, `gliner`) added to `requirements-webapp.txt` with the
same "why this doesn't reopen F-11" reasoning inline. Full test suite
re-run after installing (transformers got downgraded by gliner's pin):
57 passed, 1 skipped, no regressions. Verified end-to-end on the real
petition: parties 9 (mostly noise) → 3 (all real: BAR COUNCIL OF INDIA,
UNION OF INDIA, UNIVERSITY GRANTS COMMISSION), and the specific table-row
case from entry 54 confirmed correct again after the priority-order fix.

## 2026-09-10 (54) — dated-entry snippets now use the document's real paragraph/line structure instead of guessing sentence boundaries; PDF report text justified

Owner correctly rejected entry 53's remaining known gap instead of
accepting it as inherent: LIST OF DATES AND EVENTS is a real table (one
row per Word paragraph, literally "DATE\tDescription" — confirmed
directly), not prose, and sentence-boundary guessing was the wrong tool
for it — a real reported example had one table row (`21.07.2026 Supreme
Court in W.P.(C) No. 31/2025 ... final disposal on 25.08.2026.`) split
into two fragments because both dates it mentions are in the SAME row,
and the sentence search treated the second date as a hard stop for the
first. Fixed with `_line_bounds()` in `server/app.py`: prefer the
document's own real newline-delimited paragraph as the snippet boundary
(the actual structural unit the author wrote this content in) over a
period search, falling back to `_sentence_bounds()` only when the line
doesn't look like a real row (too short, or long enough to more likely be
a normal wrapped paragraph). Verified on the real petition: that exact
row now renders as one complete, correct unit for both dates it contains.

Also: the downloaded PDF report had ragged-right, unevenly spaced text —
added `text-align:justify` (with `hyphens:auto`) to the report's body
copy, left-aligned headings/metadata unaffected.

## 2026-09-10 (53) — real per-page page numbers for .docx (found and fixed a real section-boundary bug along the way); sentence-clean highlighted spans everywhere, not just the two spots fixed in entry 52; IMPORTANT_LINE/DATED_EVENT/SECTION type labels made readable

Owner asked five things in one message. Two were already correct and just
confirmed: Timeline already sorts every dated fact across ALL uploaded
documents together (not grouped per-document — `dated = (g.nodes ||
[]).filter(...)` runs over the whole case), and Documents insights already
never mixes documents (`groupBy(..., n => sources[0].document)`).

Three were real:

1. **Every fact showed page 1**, always — because `.docx` has no fixed
   page grid the way a PDF does, and `_docx_to_pages()` was building one
   giant page for the whole file. Real filings built as Word docs almost
   always have explicit page breaks the author inserted — checked, this
   one has 9, lining up with its 10 real sections. Rewrote
   `_docx_to_pages()` to split on those (`<w:br w:type="page"/>` via
   `docx.oxml.ns.qn`), reusing the exact same `segment_document_layered`/
   `_segment_by_headings` multi-page path already proven on real PDFs in
   F-13 — not new logic. **Found a real bug while verifying this**: the
   old single-page version's "LIST OF DATES AND EVENTS" section was
   19,845 characters — checked directly, it ran straight through "Hence
   this Writ Petition" into an unrelated repeated cover-page block that
   actually opens the *next* page, because nothing stopped the
   offset-based split until it hit another recognized heading much later.
   The real per-page boundary correctly isolates it to 4,907 characters —
   its actual content. So the visible fact-count drop this caused (61→41
   on this document) is a correctness fix, not data loss: content that
   was being mislabeled under the wrong heading is now attributed
   correctly (verified: `VII. GROUNDS` unchanged at 16, unaffected either
   way). One known remaining gap: content after the last page break (this
   template stops inserting them partway through) still lands on one
   large shared page — real per-paragraph pagination would need actually
   rendering the document, which needs a much heavier tool than reading
   the DOCX XML.
2. **Highlighted/marked spans could start or end mid-word** — entry 52
   fixed this for `DATED_EVENT` snippets specifically; this pass found
   the same class of bug in two more places and fixed both: `SECTION`
   fallback events' `text` field was a hard `text[:400]` slice
   (`server/app.py`), and — in the shared pipeline itself —
   `detect_events()`'s own `"text": context.strip()[:300]` in
   `casemap_pipeline.py` (affects every ORDER/NOTICE/PAYMENT/... keyword
   event, not just this app's own node types). Added
   `_trim_display_text()` there: ends at a real sentence within range,
   else the last whole word, never mid-word — full test suite re-run
   after touching shared code, 57 passed, 1 skipped, no regressions. Also
   tightened `_sentence_bounds()` in `server/app.py`: it was searching
   for a sentence-ending period arbitrarily far back, which could land on
   an unrelated EARLIER sentence in a period-sparse bracketed clause
   (a real one in this petition runs 500+ characters with no period at
   all) — now searches only inside the capped window and falls back to a
   word boundary there, never past it. Known remaining limitation, stated
   honestly rather than hidden: LIST OF DATES AND EVENTS' own tab-separated
   "DATE \t description" format isn't prose, so a couple of its
   `DATED_EVENT` snippets still end mid-clause (e.g. cut before a case
   number) — real sentence boundaries genuinely don't exist to find there.
3. **"IMPORTANT_LINE" as a type label meant nothing to a reader.** Added
   `friendlyType()` in `ui/app.js` (`IMPORTANT_LINE` → "Key Fact",
   `SECTION` → "Document Section", `DATED_EVENT` → "Dated Event",
   `fallback_party_block` → "Case Parties"; anything else Title-Cased
   rather than shown as a raw token) — applied to the Timeline card badge
   and the evidence drawer's type header.

Verified end-to-end on the real petition: distinct pages now
`[1,2,4,5,6,7,8,9]` (was always `[1]`), Timeline badges read "Dated
Event" not "DATED_EVENT", a representative highlighted span
("Attendance: Annexure P-15.\n03.11.2025\tDelhi High Court delivers
judgment...") now starts cleanly after a real sentence boundary.

## 2026-09-10 (52) — LIST OF DATES AND EVENTS was still only surfacing 2 of its 7+ real dates — important_lines' relevance ranking was silently dropping the rest

Owner pointed at the real petition's own LIST OF DATES AND EVENTS section —
it visibly has many dates, Timeline still only showed 2. Root cause, on
top of entry 51's two fixes: `extract_important_lines()` only keeps the
top-few "most central" sentences per paragraph (embedding-centrality
ranking — the F-11 design, correct for an ordinary argument paragraph). For
a section whose entire job is being a flat list of dates, that ranking
throws away most of the list — real check: this section has 7 real
DD.MM.YYYY dates, 0 of them survived into any event at all, because none
of the sentences containing them happened to rank as "central" against the
others. Entry 51's date-linking had nothing to attach to. Fixed with
`_events_for_uncovered_dates()` in `server/app.py`: after normal event
extraction for a section, any real date `extract_deterministic()` found
that isn't already covered by some event's sentence span gets its own
`DATED_EVENT` node, built directly from the text around the date (not
routed through important_lines' ranking at all — a real date is
inherently worth keeping regardless of "centrality"). Caught and fixed a
second bug while building this: the ±100-char window around a date cut
mid-word at both edges ("es of Legal Education" instead of "Rules of Legal
Education") — snapped to the nearest word boundary without crossing the
date itself. Verified on the real petition: dated facts 2→10, now
including the real chronology entries (`2025-11-03`, `2026-05-26`,
`2026-07-21`, `2026-08-25`) that were previously invisible; "10 dated
events" stat confirmed in the rendered UI; word-boundary fix confirmed
("of Legal Education, 2008 (Rule 6; Rule 12) Impugned Order..." now reads
cleanly from its start).

## 2026-09-10 (51) — two real date-extraction bugs found and fixed (owner was right); Timeline is now pure chronology, Key points folded into Documents insights

Owner pushed back on "no dated events" being the document's fault — asked
whether the backend should be finding dates that are actually in the text
and building the timeline from those. Checked, and they were right, two
separate real bugs stacked on top of each other:

1. **`important_lines.py` hardcodes every `IMPORTANT_LINE` event's
   `linked_date` to `None`**, unconditionally — it never checks whether the
   sentence it just extracted contains a date, even an obvious one ("BCI
   issued Circular No. 13/2024 ... on 24.09.2024" was sitting in the real
   petition's own key points, shown as "undated"). `detect_events()` only
   links dates to keyword-triggered events (ORDER/NOTICE/...) within a
   fixed window of the keyword — a sentence with a date but no recognized
   keyword nearby got no dated event either. Fixed in `server/app.py`
   (`_link_dates_in_place()`) rather than the shared module: reuses
   `extract_deterministic()`'s own already-computed per-section date list
   and attaches the nearest one when it falls inside (or right at the edge
   of) an event's own sentence span. Applied to both `IMPORTANT_LINE` and
   the `SECTION` fallback events from entry 44.
2. **The actual root cause underneath that: `DATE_CANDIDATE_PATTERN` in
   `casemap_pipeline.py` never matched dot-separated dates at all** —
   `\d{1,2}[/-]\d{1,2}[/-]\d{2,4}` only accepted `/` and `-` as separators,
   never `.`, even though `DD.MM.YYYY` is the standard numeric-date format
   in Indian court filings and circulars. The real petition uses dots
   throughout ("24.09.2024", "06.05.2017", "13.09.2017", ...) — every one
   of them was invisible to date extraction, for every consumer of this
   regex, not just important-lines. This is why the document showed zero
   dated events even before fix (1). Fixed by adding `.` to the separator
   class; verified it does NOT start matching ordinary paragraph numbering
   ("3.1.", "7A.2.") since those never have a trailing 4-digit year group.
   Full test suite re-run after the change: 57 passed, 1 skipped, no
   regressions.

Frontend restructured to match: `renderTimeline()` in `ui/app.js` no longer
shows a "Key points" list at all (that's Documents insights' job now,
per entry 49) — Timeline is purely every dated fact across every document
in the case, in date order, one flowing list, not grouped/duplicated per
document. A case with zero dated facts says so plainly instead of showing
an empty-looking block. Verified on the real petition: dated facts 0→2
("BCI issued Circular No. 13/2024 ... on 24.09.2024", correctly parsed to
`2024-09-24`), "2 dated events" stat correct, Timeline shows exactly the
one that isn't also a GROUNDS/PRAYER/QUESTIONS OF LAW node (design from
entry 49 — that one stays in Documents insights/Provisions instead),
Documents insights still shows all 53 facts.

## 2026-09-10 (50) — browser tab now shows the case name; ML badge and technical labels removed; key points no longer capped/collapsed; timeline explains itself when a document has no dates

Owner: five things. (1) The browser tab title never changed from the
static "CaseMap" — now `document.title` updates to the open case's name
(and back to "CaseMap"/"CaseMap — new case" on dashboard/upload).
(2) Topbar tagline ("verbatim timelines, page & paragraph proof — for
counsel") replaced with "Check your case insights". (3) Documents insights
was printing the raw internal tier token `legacy_fallback_internal`
(`layout_structure.py`'s label for "Docling isn't installed, used the regex
fallback") straight into the UI — added `friendlyTier()` mapping every
known tier to "Layout-detected" / "Standard", labeled "parsing quality",
applied everywhere the raw value leaked through (Documents insights stat,
Timeline's per-document badge, the PDF report's doc-meta line).
(4) Timeline's "Key points" list capped at 3 with a "Show N more points"
click — removed the cap, full list renders immediately, plus real hover
interactivity (cards lift/shift, dots scale) instead of a flat list.
(5) `● ML layer active` badge removed from the topbar entirely (the
`/api/health` check still runs, just logs to console instead of showing a
permanent technical status light). Also: when a document has zero dated
events (common for a draft petition, nothing's been filed yet) the
timeline now says so explicitly — "No dated events in this document —
shown below in document order" — with dashed undated dots, instead of
looking sparse/broken with no explanation. Verified on the real petition:
tab title reads the file name, Documents insights shows "Standard" not
the raw tier string, all 31 key points render with no "show more",
Timeline shows the no-dates note for this document.

## 2026-09-10 (49) — Documents insights now grouped by heading (same structure as Provisions used to have); Provisions pared back to statute citations only

Owner: GROUNDS/QUESTIONS OF LAW/etc. were still showing under Provisions
(intentionally kept there in entry 48 — only SYNOPSIS/ANNEXURE/EXHIBIT/
AFFIDAVIT were removed), and wanted that same "grouped by heading, with a
count" structure applied inside Documents insights instead, then removed
from Provisions entirely. `renderTree()` in `ui/app.js` previously printed
one long flat row list per document (sorted by page/paragraph, headings
interleaved and undifferentiated); now groups those same rows by
`sources[0].section` into nested `<details>` (open by default, matching
entry 48), so a document's real shape — INDEX, SYNOPSIS, LIST OF DATES,
QUESTIONS OF LAW, GROUNDS, PRAYER, AFFIDAVIT, VAKALATNAMA, whatever it
actually has — reads at a glance per document, the same way Provisions used
to show it cutting across documents. `renderProvisions()`'s
heading-grouped block (the part that duplicated GROUNDS/PRAYER/QUESTIONS
OF LAW there) removed outright — that tab is statute citations
("Provisions cited") only now, no duplication between tabs.
`PROVISION_HEADING_RE`'s other two uses (keeping those headings out of the
main Timeline, and grouping them separately in the PDF report) are
unaffected — this was UI-tab-only. Verified on the real petition: Documents
insights lists `INDEX(2) / VI. QUESTIONS OF LAW(1) / XI. INTERIM PRAYER(1)
/ XII. FINAL PRAYER(1) / VAKALATNAMA(1) / cause_title_block(1) /
SYNOPSIS(5) / LIST OF DATES AND EVENTS(21) / VII. GROUNDS(16) /
AFFIDAVIT(4)`; Provisions tab now shows only "Provisions cited".

## 2026-09-10 (48) — SYNOPSIS misfiled under Provisions; everything defaulted collapsed; a real double-print bug likely explains "can't even refresh"

Owner: SYNOPSIS content was showing under the Provisions tab, every
`<details>` group (documents, provisions, headings) opened collapsed
requiring a click each time, and separately reported the browser felt
stuck / wouldn't refresh. Three fixes:

1. `PROVISION_HEADING_RE` in `ui/app.js` listed `SYNOPSIS`/`ANNEXURE`/
   `EXHIBIT`/`AFFIDAVIT` alongside `PRAYER`/`GROUNDS`/`RELIEF`/`QUESTIONS OF
   LAW` — copied from `casemap_pipeline.ANNEXURE_PATTERN`'s heading
   vocabulary without noticing that regex answers a different question
   ("is this a document-structure heading at all") than the UI's Provisions
   tab ("is this a legal provision/ground/prayer"). Narrowed to just
   `PRAYER|GROUNDS|RELIEF|QUESTIONS? OF LAW`. SYNOPSIS was never lost — it
   was always in Documents insights too (that tab shows every node,
   unfiltered) — it just also, wrongly, showed a second time under
   Provisions.
2. `det.open`/`wrap.open` were conditional (`items.length <= 6` etc.) or
   simply never set (Documents insights), so anything with more than a
   handful of rows loaded collapsed. Set unconditionally `true` everywhere
   in `renderTree()`/`renderProvisions()`.
3. Likely real explanation for "can't refresh": `downloadReport()` armed
   BOTH `win.onload = () => win.print()` AND a 400ms `setTimeout(() =>
   win.print())` "as a fallback" — onload reliably fires for a
   `document.write()`'d page, so both fired, opening two native print
   dialogs back to back. Some browsers make that dialog application-modal
   (blocks every tab in the browser, not just the report window) until
   dismissed — which is exactly "the browser won't even refresh." Reduced
   to one single `print()` call. Also added a `no-cache` middleware in
   `server/app.py` for all non-`/api/` routes, since aggressive static-file
   caching during active iteration can independently make a real refresh
   look like it did nothing. Verified: Provisions tab now lists only
   `VI. QUESTIONS OF LAW`, `VII. GROUNDS`, `XI. INTERIM PRAYER`,
   `XII. FINAL PRAYER` (+ Provisions cited) on the real petition, all open
   on load; `cache-control: no-cache, no-store, must-revalidate` confirmed
   on `/app.js`.

## 2026-09-10 (47) — counsel report is now a real PDF with full details, not an HTML download

Owner: the report button downloaded a `.html` file, not a properly
formatted PDF. Rewrote `downloadReport()` in `ui/app.js` to open the report
in a fresh window and hand off to the browser's native print pipeline
(`win.print()`, with "Save as PDF" as a destination) rather than a Blob
download — no external PDF library, no CDN-load risk, and the browser's own
print engine paginates and typesets far better than a screenshot-based
generator would. Added real `@page`/print CSS (A4, margins, avoid awkward
page breaks mid-list-item or mid-heading). Content itself is now genuinely
complete, not just chronology + key points: parties (flagged the same
`ml_role_unstable` warning the Parties tab shows), provisions cited WITH
the Act name from entry 45's fix, and — new — every PRAYER/GROUNDS/
QUESTIONS OF LAW/other detected-heading section in full, using each node's
untruncated `sources[0].text` rather than the possibly-shortened display
label. Verified against the real petition (stubbing `window.open` to
inspect the generated markup without triggering a live print dialog under
automation): 17KB of real report HTML, Provisions cited lists section +
Act per entry, `XI. INTERIM PRAYER` appears with its full verbatim text.

## 2026-09-10 (46) — tabs renamed to Timeline / Documents insights / Provisions / Parties; text now truncates at sentence/word boundaries, not mid-word

Owner: wanted exactly these four sections (already roughly what existed,
renamed for clarity — "Document tree" → "Documents insights", "Provisions
& grounds" → "Provisions"), and flagged that truncated previews looked
"weird" — cut off mid-word ("...resul...", "...charact..."). Root cause:
`important_lines.py`/the SECTION-fallback event both pre-truncate `label`
at a fixed character count server-side with no regard for word or sentence
boundaries, and `ui/app.js` was displaying that pre-cut label as-is (or
re-truncating it a second time the same crude way). Fixed client-side
without touching the backend truncation: added `previewText()` (prefers
the FULL untruncated `sources[0].text` over the pre-cut `data.label`) and
`smartTruncate()` (stops at the last complete sentence within budget when
one exists; falls back to the last full word, never mid-word) — applied
everywhere a label is shown (key points, timeline cards, document-insights
rows, provisions rows, drawer title). Verified against the real petition:
short sentences now show complete with their own period and no ellipsis;
longer ones cut cleanly at a word ("...Stay the operation of the…") with
no fragment. Also added a per-document insight strip (pages, headings
found, citations, amounts, parties, structure tier) at the top of each
Documents-insights entry, before its row list — a real summary instead of
only a flat dump.

## 2026-09-10 (45) — highlight contrast fixed; "Provisions cited" now shows the Act, not just a bare section number

Owner: highlight in the evidence drawer wasn't visible enough, and
"Provisions cited" listed `Section 22` etc. with no indication of which
Act. Highlight: `.evidence-text mark` was `--gold-soft` background with
`color: inherit` — too close to the surrounding paper tone, especially in
dark mode. Now a solid `--gold` background with fixed dark text and
font-weight 600, same in both themes. Provisions: `server/app.py` now
looks in a ±160-char window around each bare "Section N" citation for a
named Act, reusing `case_symbols._ACT_IN_SPAN` (not reimplemented) rather
than guessing or inheriting an Act name from elsewhere in the document —
when no Act is named nearby the UI says so explicitly ("Act not named
nearby") instead of leaving it ambiguous. Two real bugs found building
this, both fixed before shipping: (1) `_ACT_IN_SPAN` is compiled
case-insensitive, correct for the short clean citation strings it was
written for elsewhere, but scanning open prose with it matched "act" as a
lowercase substring of ordinary words — "no fact", "disciplinary act", "in
charact[er]" all matched. Fixed with a post-match guard requiring the
literal capitalized word `Act` in what was found, in `server/app.py`
(`_find_act_name()`), without touching the shared regex other callers
already rely on. (2) Even after that, the non-greedy match could walk back
through an entire clause to the nearest earlier capital letter ("within the
statutory scheme of the Advocates Act"). Added `_TIGHT_ACT_RE` to trim to
just the capitalized run immediately before "Act" ("Advocates Act").
Verified against the real petition: Provisions cited 7→15 correct entries
(`Advocates Act, 1961`, `UGC Act, 1956`, etc.), zero garbage entries,
highlight visually confirmed in-browser. `ui/app.js` `renderProvisions()` /
`ui/styles.css` updated to show section + act as two-part chips.

## 2026-09-10 (44) — real bug: evidence-drawer context sliced from the wrong text; headings with zero events were invisible; UI zoomed up

Owner processed the real petition again and reported the drawer's
"Verbatim text" panel for an important line from SYNOPSIS showed unrelated
cause-title/party text instead. Root cause in `server/app.py`
`_process_one()`: every event's `char_start`/`char_end` is an offset into
that event's own *section_text* (see `important_lines.py:272-273`,
`casemap_pipeline.py`'s `detect_events()` — both compute offsets against
the section they were called with, never the whole document), but the
context-window code was slicing `full_text` (the whole document) with
those numbers. For a section near the top of the document this coincided
closely enough to look plausible; for anything later (SYNOPSIS, GROUNDS,
...) it silently returned text from a different, earlier part of the
document. Fixed by computing context inside the per-section loop against
`section_text` itself via a new `_attach_context()` helper, and against
`party_result_to_fallback_event()`'s own `span` for the cause-title
fallback node — both are now sliced from the same text their offsets were
actually computed against.

Same report also flagged that PRAYER/QUESTIONS OF LAW/VAKALATNAMA headings
were missing from the UI entirely, despite `ANNEXURE_PATTERN` correctly
detecting them (confirmed in F-12/F-13). Cause: those sections are real but
short — too few sentences for `extract_important_lines`'s `min_sentences`
gate, no `EVENT_KEYWORDS` hit for `detect_events` — so they produced zero
events and vanished from every tab. Added `_section_fallback_event()`: any
section that ends its loop iteration with zero events gets one verbatim
`SECTION`-type node carrying the section's own text, so a detected heading
always surfaces somewhere in the UI. Re-ran the real petition: 53 nodes (up
from 48), with `XI. INTERIM PRAYER`, `XII. FINAL PRAYER`,
`VI. QUESTIONS OF LAW`, and `VAKALATNAMA` now all present and correctly
grouped into Provisions & grounds; Provisions cited went 3→7 (the earlier
run's docx extraction had already been through `_docx_to_pages`, this
wasn't a table-vs-paragraph issue). Also bumped `ui/styles.css` (`zoom:1.12`
on `html`, larger evidence-text font) per the owner's "zoom everything a
little" ask. Verified by re-processing the real petition against the fixed
backend and inspecting both the raw response and the rendered drawer/tabs
in-browser.

## 2026-09-10 (43) — Parties tab now flags `ml_role_unstable` documents instead of presenting the noise as fact

Owner processed their real petition through the new UI and reported the
extracted text "doesn't make sense." Checked directly against the real
`.docx`: the timeline/key-points text is genuine (real sentences from
GROUNDS/SYNOPSIS, correctly attributed) — the actual problem is the Parties
tab, which was rendering `ml_role_unstable`-tier hybrid NER output
(`"Vehicle Number (Motor Accident): NA"` as Respondent, `"I. NATURE OF
THE"` as Petitioner, etc.) as plain chips with no confidence signal. This
exact noise pattern was already known and disclosed — `FINDINGS.md` line 21
(F-13) calls it out verbatim ("hybrid is still `ml_role_unstable`... still
emits some first-listing/heading fragments") — so this was never a silent
regression, just data the UI wasn't honest about. `ui/app.js`
`renderParties()` now shows a "⚠ unstable" tab badge and an explicit
warning banner on any document whose `party_tier === "ml_role_unstable"`,
and styles those chips in the warn color instead of the normal accent.
Verified by re-processing the real petition and confirming the banner + styled
chips render correctly (48 nodes, same count as F-12/13).

## 2026-09-10 (42) — local web app shipped: `server/app.py` + `ui/`, HANDOFF §0 no-FastAPI rule reversed

Owner explicitly reversed entry 39's UI-boundary rule the same day
("We are now building designing full working UI as backend is full ready" /
"server means our backend") after clarifying the earlier "no data saved on
our server" question actually meant a *local* backend, not none at all.
Built `server/app.py` — a FastAPI wrapper (not a reimplementation) around
the existing `src/` pipeline: `POST /api/process` accepts multi-file
PDF/DOCX/TXT upload, runs the same stages `poc_run.py` runs
(`extract_pages` → `segment_document_layered` → `extract_deterministic` /
`extract_entities` / `detect_events` / `extract_important_lines` →
`extract_parties_hybrid` → graph stage), adds a `case_symbols`-based
cross-document provision table (same "Section 7" cited in two filings
resolves to one entry), and attaches a ±450-char context window per event
source for the UI's "expand to paragraph" view. Uploads are processed in a
per-request temp dir deleted in a `finally` block — nothing persists
server-side (F-5, now enforced in real code, not just policy). Built
`ui/` — plain HTML/CSS/JS, no framework: dashboard of saved cases
(`localStorage` only), upload flow, and a case view with Timeline (dated
events on a per-document spine, `IMPORTANT_LINE` nodes condensed into a
collapsible "key points" list instead of clutter), Document tree,
Provisions & grounds (crowd-collapsed, PRAYER/GROUNDS/ANNEXURE headings
grouped separately from statute citations), Parties, an evidence drawer
(document/page/paragraph/section + highlighted verbatim text in context),
and a downloadable formatted counsel report. Verified end-to-end against
real `testdata/`: single document (7 nodes, ML layer active, real party
extraction) and the 3-doc insolvency bundle (14 nodes, 8 cross-document
edges, provisions `Section 7` and `Section 12A` each correctly linked
across two filings) — response inspected directly, then rendered in the
actual browser (dashboard → case view → timeline → key-point drawer →
provisions tab → download) via `.claude/launch.json`. `fastapi`,
`uvicorn[standard]`, `python-multipart`, `python-docx` installed into
`.venv` and pinned in new `requirements-webapp.txt`. See `HANDOFF.md` §0.

## 2026-09-10 (41) — HANDOFF §9 petition follow-ups measured; official SC headings + petition cause-title noise fixed (F-13)

Owner asked to run all four F-12 follow-ups and keep validating. Corpus
sweep: no second filed petition in `testdata/`/`real_pdfs/` (only an
`INDEX` line on doc 03). MiniLM vs Qwen re-run on the same real petition:
28/47 same (59.6%), matching F-12 — default not changed. Official Supreme
Court e-filing PDFs (WP format + SLP form) used as the second *heading*
oracle: `ANNEXURE_PATTERN` now matches `MAIN PRAYER`, `GROUNDS FOR INTERIM
RELIEF`, `INTERIM RELIEF`, and `Question(s) of Law`; lettered/parenthetical
prefixes left unmatched (no real document used them). Petition cause title:
stop at `PAPER BOOK`/`COUNSEL FOR PETITIONER`; furniture filter drops
INDEX/SYNOPSIS/citations/contact lines; `FORUM_RE` no longer treats
`University Grants Commission` as a court forum. Multi-page digital PDF
path: 10 headings across pages, and two headings on one page, both recover
the same 10 labels via `extract_pages`. Personal petition stays in `temp/`.
Tests: 57 passed, 1 skipped. Folder:
`docs/requirements/2026-09-10-petition-followups/`.

## 2026-09-10 (40) — `make_similarity_fn()` model-cache-key bug fixed (F-10)

Owner asked specifically for this backend fix (clarifying an earlier "some
fixes here and there" as backend, not UI). `_EMBED`/`_EMBED_CACHE` were
single globals keyed only by text, not by `model_name` — a second
`make_similarity_fn(model_name=B)` call inside the same process silently
reused the first model's loaded weights and any embeddings it had already
cached, returning wrong scores for B with no error (confirmed by the F-10 POC
that first found this: a second "Qwen" call returned bit-identical scores to
a prior MiniLM call in 0.0s). Fixed: `_EMBED_MODELS: dict[str, model]` and
`_EMBED_CACHE: dict[(model_name, text), embedding]`, both keyed by
`model_name`. Harmless in the pipeline's actual usage today (one model per
process) but a real bug the moment that stops being true. 1 new test,
`tests/test_similarity_fn_model_cache_key.py`. Full suite: 50 passed.
`FINDINGS.md` F-10 updated to reflect this is now fixed, not open.

## 2026-09-10 (39) — Session close-out: HANDOFF.md consolidated, viewer refreshed with the MiniLM-based run

Wrap-up per owner request. `HANDOFF.md` rewritten to reflect the full session
(§1 findings map to F-12, POC/temp folder references for every finding, a new
§9 "Owner-approved next steps for Cursor" with 4 concrete, prioritized
follow-ups from the real-petition test, §6 invariants updated for the MiniLM
default and the `ANNEXURE_PATTERN`/`_segment_by_headings()` changes, section
numbering fixed throughout). Re-ran `poc_run.py --important-lines` against the
viewer's 5-document sample with the new MiniLM default: 20s (was ~2min with
Qwen), same output (26 nodes, 15 important-line, 0 fragments) — republished to
the same Artifact URL, no link change. No `src/` change this entry — docs and
UI data refresh only.

## 2026-09-10 (38) — `important_lines.py` default switched to MiniLM: 112x faster, real petition run 1131s → 16.5s

Owner's dated decision, after seeing real numbers: re-tested Qwen vs MiniLM
agreement on the now-correctly-segmented real petition (47 eligible
paragraphs, real headings) -- 28/47 (60%) same top pick, 19/47 differ.
Spot-checked several disagreements: both models' picks were consistently
real, substantive sentences (a case citation vs a terse conclusion; a
statutory cite vs a procedural point) -- never nonsense. Legal paragraphs
here often contain multiple legitimately "central" sentences, so this reads
as two reasonable rankers leaning differently, not one being wrong. Given
that and the measured 112x per-sentence speed gap (F-12), owner chose to
switch the default. `important_lines.EMBED_MODEL_NAME`:
`Qwen/Qwen3-Embedding-0.6B` → `all-MiniLM-L6-v2`, one constant, no other
code change. Full suite still green (49 passed). Real end-to-end
re-confirmation on the same petition: **16.5s** (was 1131s pre-F-12, 354s
after the segmentation fix alone) -- same output shape, same 48 nodes, same
16 real GROUNDS sentences, same section coverage. `EMBED_MODEL_NAME` is the
one knob if this trade needs revisiting later.

## 2026-09-10 (37) — `_segment_by_headings()` fixed to split within a single page; GROUNDS/PRAYER/AFFIDAVIT now genuinely separate sections (F-12)

Owner chose "fix segmentation first" over the two speed workarounds proposed
after entry (36) (switch to MiniLM outright, or add multiprocessing) --
correctness over speed. Root cause: `_segment_by_headings()` only ever
created a new section boundary at a PAGE boundary; a `.txt` input loads its
whole filing as one page, so even with entry (36)'s regex fix, all 10 real
headings on the real petition's one "page" collapsed into a single section
labeled after whichever heading came first. Fixed: `detect_structure()` now
records each heading's character offset within its page; `_segment_by_headings()`
slices a page with >1 heading into one sub-page per heading (same page_number,
correct provenance). PDF documents (Docling headings, one per physical page,
no offset key) are unaffected -- verified with a dedicated test. 3 new tests,
`tests/test_multi_heading_single_page_segmentation.py`. Full suite: 49 passed.

**Real before/after on the actual petition:** `VII. GROUNDS` is now its own
15,805-char section (was invisible, merged into `[INDEX]`). Re-ran
`poc_run.py --important-lines` end to end: **48 real IMPORTANT_LINE nodes
across 10 correctly-labeled sections** (was 6, all mislabeled `[INDEX]`),
including 16 genuine, substantive grounds-of-challenge sentences (e.g. "7A.2.
The employer NOC has no rational connection with the regulatory objective of
verifying attendance...") and 4 from AFFIDAVIT, cleanly separated. Runtime
also dropped from 1131s to **354s** (3.2x) as a side effect of smaller,
better-bounded per-section embedding batches -- not from any model change.
Full detail: `FINDINGS.md` F-12. Output: `temp/2026-09-10-real-petition-run/`
(personal document, not added to `testdata/`).

Still open: Qwen-vs-MiniLM model-choice question, now worth re-testing on
correctly-segmented paragraphs instead of the confounded blended-blob ones;
multiprocessing across documents not attempted.

## 2026-09-10 (36) — Real petition test: `ANNEXURE_PATTERN` numbering-prefix bug fixed; batched embedding calls (2.26x, real-measured); real Qwen-vs-MiniLM speed gap found

Owner supplied a real, personal Supreme Court writ petition (BCI NOC challenge,
outside the repo, processed in `temp/2026-09-10-real-petition-run/`, not added
to `testdata/`) and asked to run the pipeline against it -- the first real
*filed petition* (not a published judgment) this project has ever tested,
directly relevant since every prior test document lacked a real Prayer/Grounds
section. Two real findings:

1. **`ANNEXURE_PATTERN` bug**: only matched a bare heading word ("PRAYER",
   "GROUNDS") with no numbering prefix. Real petitions number these sections
   ("VII. GROUNDS", "XI. INTERIM PRAYER", "XII. FINAL PRAYER") -- the pattern
   silently matched none of them. Fixed: optional roman-numeral/numeric prefix,
   PRAYER qualifiers (INTERIM/FINAL/ADDITIONAL), "LIST OF DATES AND EVENTS"
   variant. Verified against the real petition (10 real headings now matched,
   up from 0 for the ones that mattered) and re-verified `testdata/`'s existing
   single match (`INDEX`) is unchanged -- no regression. 5 new tests,
   `tests/test_annexure_pattern_numbered_headings.py`.

2. **Speed**: the real petition (293 eligible important-line sentences) took
   1131s end to end on this machine. Diagnosed for real, not guessed: Qwen3-
   Embedding-0.6B (`important_lines.py`'s default) encodes 50 short sentences
   in 32.7s on this CPU vs all-MiniLM-L6-v2's 0.29s -- a ~112x gap, consistent
   with the 27x parameter-count difference (600M vs 22M). Batched
   `important_lines.py`'s embedding calls (one call per section instead of one
   per paragraph) -- real measured speedup **2.26x** (771s vs 1745s on the same
   17-paragraph test), real but nowhere near enough to close a 100x gap alone.
   Whether MiniLM can safely replace Qwen as `important_lines.py`'s default
   tested directly against every eligible paragraph in the real petition:
   **it cannot, not without more work** -- MiniLM picked a DIFFERENT top
   sentence than Qwen in 4 of 6 real eligible paragraphs (majority
   disagreement), contradicting the earlier hybrid-LexRank result (same
   algorithm, same model, different question) and the F-10 document-
   similarity test (different task entirely). Likely confounded by a THIRD
   real gap this run exposed: `poc_run.py` loads a `.txt` input as a single
   giant "page", so a real petition's `split_paragraphs()` fallback (blank-
   line splitting) collapsed this document into only 6 eligible "paragraphs"
   -- several of which blend Grounds/Prayer/Affidavit content together in one
   blob because the document doesn't use consistent blank-line separation.
   Ranking within a blob that large is a noisier signal for either model, so
   this 4/6 disagreement rate is not yet a clean model comparison. Not fixed
   this session -- flagged for the owner to prioritize (see chat).

No `src/` file other than `casemap_pipeline.py` (the regex) and
`important_lines.py` (the batching) changed. `real_petition/` content not
committed to the repo -- personal document, processed in `temp/` only.

## 2026-09-10 (35) — Viewer: document tree for the new important-line nodes, paragraph provenance in the evidence card

UI-side follow-up to entry (34). Re-ran `scripts/poc_run.py --important-lines`
against the viewer's existing 5-document sample bundle (`temp/2026-09-10-ui-poc/
sample_bundle/`) — 26 real nodes (15 `IMPORTANT_LINE`, up from 11 total before).
Added: a collapsible "Document tree" section (one `<details>` per document,
real rows sorted by page then paragraph then char offset — every extracted
detail in one place, not just the cross-document timeline); a gold node/badge
treatment for `extractive_embedding`/`extractive_deterministic` confidence,
distinct from the existing resolved/role-unstable/block tiers; the evidence
card now shows the source document name and paragraph number (new fields,
alongside the page/section/char-offset it already had) — the specific ask was
"when clicking it should show ... document name page number paragraph number
from where its coming." Clicking a tree row shows a small inline preview
without losing place, and still updates the full evidence card + timeline
highlighting via the same `selectNode()` path already in use. Stat-bar
breakdown fixed to count the new confidence tiers (was silently omitting 15 of
26 nodes from its own summary). Caveat text updated to name F-11 and the
important-lines flag honestly. Republished to the existing Artifact URL — same
link, no new one. One real bug hit and fixed during this work, not shipped:
an earlier `re.sub`-based script edit used a *string* replacement, which
Python's `re` module silently backslash-unescapes (`\n`/`\t` in the JSON
became literal control characters, breaking the page's JS with a syntax
error) — fixed by using a function replacement instead, which `re.sub` never
processes for escapes.

## 2026-09-10 (34) — `important_lines.py` shipped: extractive important-line nodes, real bugs found and fixed at real-corpus scale (F-11)

Owner gave the dated go-ahead F-11 needed ("ok lets do this and complete backend
end to end") to move the extractive-important-lines POC into `src/`. New module
`src/important_lines.py`: `split_sentences()` (abbreviation- and short-fragment-
aware, span-based so every kept sentence is byte-verbatim by construction, never
reconstructed), `rank_sentences()` (Qwen3-Embedding centrality if
`sentence-transformers` is installed, deterministic fact-density scoring
otherwise — same optional-dependency degrade contract as
`make_similarity_fn()`), `extract_important_lines()` (per-paragraph, keeps the
top sentence(s), threads a running paragraph counter across a document's
sections). Wired into `scripts/poc_run.py` behind an opt-in `--important-lines`
flag (off by default). One-line `casemap_pipeline.to_react_flow()` change: an
event can now carry an explicit `label`, so each `IMPORTANT_LINE` node shows its
own real text instead of a generic type-title.

Real bugs found and fixed by actually running this against all 22 testdata
documents, not just the single validation paragraph: `"Rs."` and name-initial
abbreviations (`"Y.V."`) were being treated as sentence boundaries, and even
after fixing those, bare paragraph numbers / uncaught abbreviations were still
kept as standalone fake "sentences" — **18 of 85 nodes (21%) in the first real
run were fragments.** Fixed with a general minimum-sentence-length merge pass.
Re-run after the fix: 52 real `IMPORTANT_LINE` nodes, 0 fragments. Also caught
in review before shipping: an earlier version reconstructed merged sentences by
joining stripped text with a literal space, which silently stops being verbatim
the moment the real separator is a newline/tab — fixed by working with
`(start, end)` spans into the source text throughout. 11 new tests
(`tests/test_important_lines.py`), full suite still green (38+11 passing).
Also fixed the long-standing cosmetic Windows console crash in `poc_run.py`'s
final print (`✓` → `[ok]`, same fix pattern as entry (31)'s installer). Full
detail: `FINDINGS.md` F-11. Real output:
`temp/2026-09-10-important-lines-e2e/`.

## 2026-09-10 (33) — 5-way "important lines, no rewrite" summarization POC (F-11)

Owner wants long sections (e.g. a 50-page Grounds section) reduced to important
lines that become graph nodes, explicitly **not** a generative rewrite. Tested 5
approaches head-to-head on the same real paragraph, CPU-only:
Qwen3-Embedding-based extractive centrality ranking (no generation), flan-t5-small,
t5-small, `sshleifer/distilbart-cnn-6-6`, `nsi319/legal-pegasus`. Winner: the
Qwen-embedding extractive ranking — 100% verbatim (it only selects real sentences,
never generates), fast, and each kept sentence already carries a real char offset
matching `build_evidence_card()`'s existing `sources[]` shape, so it can become a
node the same way today's event nodes do. Both tiny generative models were actively
bad: flan-t5-small collapsed to one garbage word, t5-small hallucinated a real date
wrong. Full table and scripts: `FINDINGS.md` F-11,
`temp/2026-09-10-docling-qwen-poc/`. Evaluation only — no `src/` change, no default
adopted, same dated-owner-decision gate as F-10 (HANDOFF §9).

## 2026-09-10 (32) — Real Docling + Qwen3-Embedding POC (F-10); fact-checked an external AYN/InLegalBERT/OpenNyAI summarization proposal

Owner asked for a real POC of Docling and Qwen3-Embedding rather than relying on the
small F-4 test or T3's still-open status. Built `temp/2026-09-10-docling-qwen-poc/`
(fresh `venv_docling_qwen`, `docling==2.126.0` + `sentence-transformers`, isolated per
`requirements-docling.txt`'s own warning). Ran `detect_structure_layered()` against 4
real `real_pdfs/` (2 digital, 2 scanned) — all 4 returned `docling_layout`/high with
correct real headings, RapidOCR handling the scanned ones internally. Ran
`make_similarity_fn("Qwen/Qwen3-Embedding-0.6B")` against real same-matter vs unrelated
`testdata/` pairs — Qwen showed a wider same-matter/unrelated score spread (~0.41) than
the current default MiniLM (~0.24). Found and logged a real bug:
`make_similarity_fn()`'s `_EMBED`/`_EMBED_CACHE` globals aren't keyed by `model_name`,
so switching models mid-process silently reuses stale cached embeddings. Full detail:
`FINDINGS.md` F-10.

Separately, fact-checked an external proposal (pasted by the owner) recommending a
hierarchical extractive-summary architecture using Paramanu-AYN (a small Indian legal
generative model), InLegalBERT, and OpenNyAI's extractive summarizer. Verified against
primary sources (HF model cards, the arXiv paper, OpenNyAI's own docs): confirmed
InLegalBERT is encoder-only (not a summarizer), confirmed AYN-88M's non-commercial
license and lack of human legal-summarization evaluation, and corrected one number —
the arXiv paper (2403.13681v3) reports an **88M**-parameter model, not 97M. Flagged the
proposal's implicit assumption that "OpenNyAI already gives us" extractive
summarization: that component ships inside the same `opennyai` PyPI package whose
`Rhetorical_Role` component is the one already confirmed blocked on Windows by the
Rust/`tokenizers` compile wall (F-6) — it is very likely blocked by the same wall, not
a free win. No `src/` change; no scope widened (`SCOPE.md`'s no-generative-LLM-in-core
boundary is unchanged, per HANDOFF §9).

## 2026-09-10 (31) — project `.venv` NER default, `case_symbols.py`, F-7 cue fixes

Owner ordered three pipeline items (UI stays on the Artifact side of HANDOFF §0).

1. **NER default-wiring** (`docs/requirements/2026-09-10-ner-project-default/`):
   project-root `.venv` (Python 3.11) + `requirements.txt` + existing
   `scripts/install_en_legal_ner_sm.py` + `en_core_web_sm`. Default
   `load_opennyai_ner()` succeeds in `.venv` (`legal_ner_sm` 3.2.0) without
   `--allow-degraded`. Not installed into system Python. Installer print used
   `✓` which breaks Windows cp1252 — now `[ok]`. README documents `.venv` as
   the default interpreter.

2. **`src/case_symbols.py`** (`docs/requirements/2026-09-10-case-symbol-table/`):
   reconstructed stage [4] API (`normalize_name` / `normalize_amount` /
   `amount_from_words`, `SymbolTable.go_to_definition` /
   `find_all_references`). No HEART tier-2 act-name inheritance.
   `opennyai_bridge.extract_parties_ml` imports `normalize_name` for real.
   testdata 09/21/22: genuine names share keys across documents.
   `casemap_pipeline._canonical_key` delegates to `normalize_name`.

3. **F-7 cue fixes** (`src/rhetorical_roles.py`): dropped `"in the case of"`;
   PRECEDENT does not carry forward; longer cues use `rapidfuzz.partial_ratio`.
   testdata 01/03/21. Heuristic only — not the blocked OpenNyAI classifier.

Tests: `tests/test_case_symbols.py`, `tests/test_rhetorical_roles.py` (16
passed in `.venv` with related files). Structure T3 (Qwen) still not started.

## 2026-09-10 (30) — real_pdfs/ corpus built and validated against the real pipeline; missing since governance init

Closes an item every session's `HANDOFF.md`/`STATUS.md` has flagged as missing since
2026-09-09: `real_pdfs/`, referenced throughout `CaseMap_AGENT_HANDOFF.md` ("6 real
PDFs, 2 genuinely rasterised with zero text layer") but never present in this working
directory. Owner asked for it directly to support Cursor's Tier-1-proof work.

Built from the same 22 real, already-vetted `testdata/` documents (no new sourcing) —
15 rendered to digital PDFs with a real font-size/bold hierarchy, 7 rasterized and
degraded (±1.4° rotation, Gaussian blur, salt-and-pepper noise) into image-only PDFs
with a **programmatically verified zero-character text layer** (not assumed), same
method validated in F-4. ~1/3 scanned ratio matches what the original corpus
documented. Script: `temp/2026-09-10-real-pdfs-build/build_real_pdfs.py`.

**Validated for real, not just built:** ran `scripts/poc_run.py real_pdfs --ocr
tesseract` (the mandatory model, not `--allow-degraded`) end to end. Installed
`pytesseract`/`pymupdf`/`opencv-python-headless`/`pillow` into `venv_ner` to make this
possible. Result: 37 total pages, 25 digital + **12 genuinely OCR'd (32% of pages)**
— the corpus actually exercises the OCR ladder, not just claims to. 39 event nodes,
76 edges across all 22 documents. Structure tier came back `legacy_fallback_internal`
for all — expected, Docling lives in the separate `venv_docling`, not `venv_ner`; not
a defect in the corpus. Raw run output kept at
`temp/2026-09-10-real-pdfs-build/validation-run/` (`poc_report.md`, `poc_graph.json`).
`real_pdfs/README.md` documents composition and provenance. `HANDOFF.md` §6's
"still not found" list updated to drop `real_pdfs/`. No `src/` file changed.

## 2026-09-10 (29) — Viewer visual design pass (no data/logic change)

Owner asked for a design polish on the published viewer, not new data — prayers/
issues stay flagged as not-yet-available (F-6/F-7), unchanged this entry. Added: a
confidence-breakdown stat bar in the masthead (resolved/role-unstable/block share,
at a glance before reading any card); left-accent color bars on case cards keyed to
their real party confidence tier, not decorative; hover lift/shadow on case cards;
alternating lane bands in the event-graph SVG for scannability; larger node-hover
target with a visible selected-state; a shadow on the evidence-card panel for depth
consistency with the case cards. Same data, same `GRAPH`/`CASE_DATA` JSON, same
honest "what's not here yet" section — purely a visual/typographic pass. Republished
to the existing Artifact URL. No `src/` file changed.

## 2026-09-10 (28) — party-ladder caption furniture (F-9) + structure T4 JSON

Owner ordered the `extract_parties_layered()` header bug first (confidently
wrong parties), then structure T4, T3 last/skip.

New folder `docs/requirements/2026-09-10-party-ladder-header-furniture/`. Did
**not** skip the cause-title region (that F-8 NER skip would drop real names).
`document_profile.py` now treats indiankanoon `Author:`/`Bench:`/`Source:` lines
and `CITATION:`/`CITATOR INFO` headings as non-parties; versus-block walks stop
there; furniture-only tiers fall through; hybrid ML lists get the same filter.
testdata 01/09 and all 22 files: zero furniture names; Dilip Kumar Sharma /
Singhania / Bank of Baroda still present. Tests:
`tests/test_party_ladder_header_furniture.py`. Logged FINDINGS F-9 (fixed).

T4: `poc_report.md` already printed structure tier (CHANGELOG 24).
`poc_graph.json` now includes `documents[]` with `structure_tier` /
`structure_confidence` / `structure_reason` via `structure_docs_for_graph()`.
T3 (Qwen `sentence_transformers`) not started — evaluation only, does not ship.

## 2026-09-10 (27) — HANDOFF.md full sweep + explicit UI boundary for Cursor

Owner asked for a complete handoff refresh (it was stale relative to F-5 through F-8
and 4 requirement folders it never mentioned — `ephemeral-client-results`,
`entity-extraction-header-noise`, `residual-false-edges`, `wire-opennyai-ner`,
`rhetorical-role-cues`) and an explicit instruction that Cursor should not build any
UI, since that work is now happening directly as Claude-published Artifacts (§0,
entries 25-26).

Rewrote `HANDOFF.md` in full: new §0 states the UI boundary first, before anything
else, with the concrete reason (Artifacts already cover the visualization need) and
what stays in scope (pipeline/`src/` work, same as always). §1's requirement-folder
table brought current for all 7 folders including which ones are done, which are
blocked, which were superseded by a follow-up folder (`entity-extraction-header-noise`
by `residual-false-edges`). All 8 findings summarized with their real outcomes. Added
the `extract_parties_layered()` header-parsing bug found while building the UI
(entry 26) as a real, not-yet-ticketed open item, with a note that it's likely the
same fix shape as the already-fixed `extract_entities()` bug. Updated §9's
owner-reserved list with the UI prohibition, dated. No `src/` file changed.

## 2026-09-10 (26) — Viewer extended with per-case dossiers (parties, sections cited, amounts); honest "not yet available" section added

Owner asked for the viewer to surface far more than the sparse event graph — parties,
issues, sections/laws cited, "full case detail without reading pages." Gathered the
richer data that already exists but wasn't being shown: `document_profile.extract_parties_hybrid()`
(the real mandatory ML+deterministic party path, with its real confidence tiers) and
`casemap_pipeline.extract_deterministic()`'s sections/case-numbers/amounts, for all 5
sample documents (`temp/2026-09-10-ui-poc/gather_full_data.py`, `full_case_data.json`).

Found a bug while gathering this, distinct from the already-fixed `extract_entities()`
noise: `document_profile.extract_parties_layered()` (the pure-deterministic ladder, not
the mandatory hybrid path) produces header-parsing garbage on these documents
("Author: Y.V. Chandrachud" as Petitioner, "CITATION" as Respondent) — not used in the
final page; switched to `extract_parties_hybrid()`, which is real, mostly correct, and
already carries honest confidence tiers (`high` vs `ml_role_unstable`) from Cursor's
fallback-node work. Not filed as a separate finding — flagging here for whoever
touches `extract_parties_layered()` next, since it's a real, unaddressed issue.

Added a "Case files" grid above the event timeline: one card per document with name/
court/date, party list with real confidence badge, sections/provisions cited, amounts
mentioned, case number — clicking a card jumps to that document's lane below. Added a
persistent "What's not here yet" section on the page itself (not just chat) answering
the owner's question directly: Issues/Arguments/Court's-reasoning are blocked on F-6/
F-7 (not implemented); Prayers/relief-sought are a real pipeline capability
(`ANNEXURE_PATTERN`) that's simply inapplicable to judgment-type documents (these 5
aren't petitions); party-list noise is shown as-is with its real confidence badge,
not silently cleaned up. No `src/` file changed — still a viewer, not a pipeline
change.

## 2026-09-10 (25) — Lightweight graph viewer built as an Artifact, not the Tier 3 FastAPI/React build

Owner asked for a UI. `HEART.md` gates Tier 3 (React Flow, FastAPI) behind a proven
Tier 1/2, which isn't there yet — flagged that tension explicitly rather than build
past it silently. Owner chose the lighter path: a standalone HTML/JS viewer
(published as an Artifact, no server, no new `src/` dependency) that loads a real
`poc_graph.json`, not synthetic data.

Ran `scripts/poc_run.py --allow-degraded` for real against a 5-document sample
(`temp/2026-09-10-ui-poc/sample_bundle/`: the 09/21/22 connected bundle + 2 unrelated
controls) — the real mandatory NER model loaded in `venv_ner`, producing genuine
output including Cursor's fallback-node work (`confidence: "ml_role_unstable"`
visible in the data). 11 nodes, 14 edges. Output moved from the project root (where
`poc_run.py` defaults to writing) into `temp/2026-09-10-ui-poc/`, per `AGENTS.md` §9.

Built `temp/2026-09-10-ui-poc/casemap_viewer.html`: one lane per source document,
nodes placed in reading order, cross-document edges as curved connectors, click any
node for an evidence card (type, confidence badge, date, page/char offset, the exact
verbatim source text with the matched span highlighted, and jump-to-connected-node
chips). Confidence badges are real (`resolved`/`ml_role_unstable`), not decorative.
Left the real cross-document noise in the sample untouched — some edges connect the
unrelated control documents to the bundle, reflecting `FINDINGS.md` F-8's
still-open work, not curated to look clean. The page states this directly rather
than hiding it. Published as an Artifact — this is a viewer for existing pipeline
output, not a new pipeline stage; no `src/` file changed.

## 2026-09-10 (24) — structure T2: `layout_structure.py` with three Docling degrade paths

Implemented `src/layout_structure.py` (`detect_structure_layered` +
`LayeredStructureResult`) for
`docs/requirements/2026-09-09-structure-and-embedding-layers/` T2. Success path
reuses `casemap_pipeline._segment_by_headings` with Docling `page_no` as-is
(1-indexed, T1). Missing Docling / convert error / zero headings degrade to
existing `detect_structure` + `segment_document` (tiers
`legacy_fallback_internal` / `_docling_error` / `_no_headings`). Docling is
still not in `requirements.txt` (HANDOFF §9). Tests:
`tests/test_layout_structure.py`. Real pass on the T1 fixture PDF via
`venv_docling`: `tier: docling_layout`, 4 headings
(`temp/2026-09-10-structure-t2/T2_REAL.json`). T3–T4 not started.

## 2026-09-10 (23) — wire-opennyai-ner T1–T3; Docling page_no is 1-indexed (structure T1)

HANDOFF §8 item 2: `en_legal_ner_sm` still cannot live in `requirements.txt`. Added
`docs/requirements/2026-09-10-wire-opennyai-ner/` and
`scripts/install_en_legal_ner_sm.py` (download, rename `any`→`3.2.0`, re-pin
spaCy 3.8.16). `opennyai_bridge.NER_INSTALL_CMD` now points at that script, not
the URL pip rejects. Default `load_opennyai_ner()` (no `--allow-degraded`)
succeeds on `venv_ner` (`legal_ner_sm` 3.2.0). `--allow-degraded` is unchanged.
Did not install the model into the system interpreter (known spaCy/pydantic
conflict).

Same session, structure-and-embedding-layers T1: Docling `item.prov[0].page_no`
matched PyMuPDF/casemap 1-indexed `page_number` on 4/4 headings
(`T1_RESULTS.md`). Fixture is a 2-page generated PDF; no off-by-one fix.
Docling is still not added to the project dependency set (HANDOFF §9).

## 2026-09-10 (22) — fallback-nodes T3–T5: identity keys, confidence JSON, poc_run wiring

T3: `party_result_to_fallback_event()` now puts verbatim `PartyResult.parties`
names through `normalize_entities()` and emits `_canonical_key` ids so ALL-CAPS
vs title-case (testdata 22 vs 09/21) share an identity. Forced scoring test:
doc 22 connects to the bundle; doc 01 control does not.

T4: `to_react_flow` node `data.confidence` and `build_evidence_card` expose
the stamp (`ml_role_unstable` / `block` vs `resolved` for keyword events).

T5: `scripts/poc_run.py` accepts `.txt` as well as PDFs and appends fallback
events from `party_result_to_fallback_event()`. T5 equivalent (real model, not
`--allow-degraded`, because the T2 trigger is ML): fallback nodes on 01/12/16/17
and a 09/21/22 edge. Tests: `test_t3_fallback_edges.py`, T4 in
`test_fallback_event.py`, `test_t5_poc_wiring.py` (9 passed with T1/T2).

## 2026-09-10 (21) — fallback-nodes T2: ML role-instability trigger

`extract_parties_hybrid` now inspects raw OpenNyAI NER mentions (not the
first-mention collapse in `extract_parties_ml`) and stamps
`tier`/`confidence` `ml_role_unstable` when the same normalized name carries more
than one party-side label. `party_result_to_fallback_event()` accepts that stamp
and writes `confidence: "ml_role_unstable"`. Span is the existing cause-title
block, or the F-3 800-char prefix if none. `opennyai_bridge.extract_parties_ml`
no longer hard-imports missing `case_symbols.py` (HANDOFF §6) — casefold
whitespace key if that file is absent.

Acceptance: `testdata/` 01, 12, 16, 17 all produce a fallback event with that
stamp (`tests/test_ml_role_unstable.py`, `en_legal_ner_sm` in `venv_ner`).

## 2026-09-10 (20) — residual 24 false edges: preamble prefix + reporter citations

The leftover 24 false cross-document edges after entry (19) were diagnosed on
the real 22-doc run, not guessed: every edge was `entity_overlap=1.0` from one
of three preamble strings (`THE SUPREME COURT OF INDIA`, `AIR 20xx SUPREME
COURT`, `R. Subhash`). Cause: entry (19) excluded only the versus-block interior,
leaving caption/citations/`Bench:` in generic NER.

`extract_entities()` now skips `[0, title-block-end)` and indiankanoon furniture
lines; reporter-shaped `AIR`+year spans are dropped. New requirement folder
`docs/requirements/2026-09-10-residual-false-edges/` (not a retrofit of the
previous folder). 22-doc re-run: false **24→0**, correct 09/21/22 edges **14→16**.
Tests: `tests/test_extract_entities_header_noise.py` (4 passed).

## 2026-09-10 (19) — extract_entities() header-noise fix (F-8) implemented in src/

HANDOFF §8 item 0: confirmed bug, not a new feature.
`casemap_pipeline.extract_entities()` now excludes the cause-title char range from
`document_profile.extract_cause_title_block()` before generic spaCy NER (FR1),
drops newline-containing NER spans (F-8 category 2/3 formatting), and filters
`GENERIC_ENTITY_TEXT` on PERSON/ORG/GPE in both `extract_entities()` and
`normalize_entities()` (FR2). `None` title-block falls through to full text.

Tests: `tests/test_extract_entities_header_noise.py` against real `testdata/` 09/
21/22 (3 passed, `venv_ner` + `en_core_web_sm`). T4 re-run of the dense fact-node
graph over all 22 documents: false cross-document edges 60→24; correct 09/21/22
bundle edges 10→14. Residual 24 false edges remain — not claimed fully fixed.
Did not overwrite the F-8 baseline `poc_results.json`; summary is
`temp/2026-09-10-header-noise-fix/t4_summary.json`.

## 2026-09-10 (18) — Full 22-document validation of the dense fact-node POC: the 6-doc sample was too optimistic, root-caused into 3 distinct bug categories

Owner asked to validate entry (17)'s approach against all 22 `testdata/` documents,
analyze the results fully, and prepare fix/notes for whoever (Cursor) picks this up
next — not just accept the earlier small-sample result. Re-ran
`temp/2026-09-10-fact-nodes-poc/poc_fact_nodes.py` against all 22 documents: 227 nodes
total (1-21/doc, all real deterministic facts with char-offset provenance). Cross-
document edges: 60 false vs. only 10 correct — much worse than the earlier 6-doc
sample (22 correct/2 noise), which undersampled the real noise surface.

Catalogued every entity shared across 2+ documents (28 total, only 7 genuine — all
inside the real 09/21/22 bundle) and root-caused the other 20 into three distinct
categories rather than treating it as one stoplist problem: (1) generic institutional/
procedural nouns near-universal in Indian legal writing (`Court`, `Justice`, `Versus`,
`Order`, `Adv`, `SLP`, `Anr`, `Union Of India`); (2) malformed multi-line entity
extraction — generic spaCy NER grabbing whole header blocks
(`"THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION..."`) as single entities,
because header/cause-title regions are run through generic prose-oriented NER without
ever consulting the codebase's own existing header-detection logic
(`document_profile.extract_cause_title_block`); (3) truncated fragments
(`"R. Subhash"`, `"PRINCIPAL"`, `"C.A. No"`) from the same formatting confusing
spaCy's tokenizer at line-wrap boundaries. A stoplist only ever chases category (1) —
(2) and (3) need an architectural fix (skip/special-case the header region before
generic NER, using logic that already exists). Updated `FINDINGS.md` F-8 in place
with this addendum, per `AGENTS.md` §5's "dated records are never rewritten, add a
banner" rule — the original 6-doc conclusion is now explicitly marked
non-representative. No `src/` file changed.

## 2026-09-10 (17) — Dense fact-node POC: 67 nodes from existing code, real cross-doc timeline, evidence cards working, and a real bug found in extract_entities()

Owner redirected again: pointed out `casemap_pipeline.py` already has 400+ lines of
deterministic extraction and asked to look there before building anything new, and
clarified the actual goal — multiple documents' details connecting on a timeline,
click a node for a summary. Re-reading `casemap_pipeline.py` found
`build_evidence_card()` (exactly "click for summary") already fully implemented and
never invoked in any POC this session, and that `extract_deterministic()` already
finds far more raw facts than `detect_events()` turns into nodes (it only creates a
node near one of 6 narrow event-keyword phrases).

POC (`temp/2026-09-10-fact-nodes-poc/poc_fact_nodes.py`) added one new function
emitting a node per deterministic fact, reusing `extract_deterministic()`'s real
output — took node count from 7 (F-3's earlier count) to 67 across 6 real documents,
zero new dependencies. Found two real bugs along the way: a POC-wiring mistake
(per-document `normalize_entities()` calls caused coincidental id collisions that
falsely connected two unrelated cases — fixed by calling it once, globally) and a
**real bug in `extract_entities()` itself**, affecting the actual pipeline today: the
generic spaCy NER mislabels `"VERSUS"` (in every judgment's cause title) as `ORG` and
`"Order"` as `PERSON`, making them universal false cross-document connectors. After
both fixes, cross-document edges went from 74 (mostly false) to 24 (22 correct
bundle connections, 2 residual noise not yet diagnosed). The bundle's dated nodes
formed a correct real timeline matching the actual procedural history, and
`build_evidence_card()` produced correct real output — visualized for the owner.
Logged as `FINDINGS.md` F-8. No `src/` file changed — the `extract_entities()` bug is
flagged as a real, independent defect, not fixed in `src/` this entry.

## 2026-09-10 (16) — Deterministic rhetorical-role cue tagging POC'd; not ready for TASKS.md yet

Follow-up to entry (15): owner asked whether the "full tree" breakdown needs a
dedicated LLM, and pointed out `en_legal_ner_sm` (already in use) does name/date
detection — clarified that rhetorical-role classification is a different task (span
labelling vs. sentence classification) so the existing model can't be repurposed, but
also isn't inherently an LLM problem: the blocked `opennyai` classifier (F-6) is a
non-generative sequence classifier, same category as `en_legal_ner_sm`, blocked only
by Windows packaging, not a governance objection. Owner chose the deterministic
keyword-cue path instead — same mechanism `casemap_pipeline.EVENT_KEYWORDS`/
`detect_events()` already uses safely, applied at paragraph granularity.

Added `docs/requirements/2026-09-10-rhetorical-role-cues/` (REQUIREMENTS.md,
DESIGN.md, POC_RESULTS.md) before writing any code, per `AGENTS.md` §6. POC
(`temp/2026-09-10-rhetorical-role-cue-poc/poc_rhetorical_cues.py`) ran against 4 real
documents: one produced a correct role sequence (real evidence the mechanism works),
two surfaced concrete, fixable problems — a too-generic cue phrase ("in the case of")
false-matched ordinary prose and then poisoned every subsequent paragraph via
carry-forward with no re-confirmation step, and exact substring matching missed real
wording variation that the codebase's existing `rapidfuzz`-based fuzzy-matching
pattern (`is_versus_line()`) would likely catch. Logged as `FINDINGS.md` F-7. Not
formalized into `TASKS.md` — two fixes needed and a re-run against real documents
first. No `src/` file changed.

## 2026-09-09 (15) — Rhetorical-role dead end abandoned; existing ANNEXURE_PATTERN heading detector confirmed already covers the requested vocabulary

Owner asked for a "full tree" breakdown of documents (prayers, issues, questions of
law) rather than the sparse `detect_events()` node counts F-3/graph POCs showed.
Researched `opennyai_bridge.py`'s long-dormant `load_rhetorical_role_model()` stub —
found the `opennyai` PyPI package (v0.0.13) now documents a real API for it, updating
the pre-governance handoff's "no confirmed load API" note. Installing it hit a real
wall: an unmaintained transitive dependency (`pytorch-transformers`) needs an old Rust
`tokenizers` crate built from source, which failed even after installing a current
Rust toolchain via winget (crate code predates modern Rust's lifetime-elision rules).
Installed an old pinned toolchain (rustup, 1.50.0) and had a retry in progress when
the owner correctly redirected: this was the wrong problem to solve.

Checked what already exists instead: `casemap_pipeline.ANNEXURE_PATTERN` (line 325)
already matches standalone `PRAYER`/`GROUNDS`/`QUESTIONS OF LAW`/`SYNOPSIS`/
`LIST OF DATES`/`MEMO OF PARTIES`/`INDEX` heading lines — exactly the vocabulary
asked for, no new dependency needed. Tested it against several `testdata/` documents
— zero matches, because `testdata/` is published judgments (indiankanoon), not the
original filed petitions where these headings actually appear as standalone lines.
Real gap identified: test-data shape (need petitions/pleadings), not a missing tool.
Logged as `FINDINGS.md` F-6 (updated in place with this addendum, per `AGENTS.md` §5 —
not a new finding, the investigation's own conclusion changed). No `src/` file
changed. The old-Rust-toolchain background install was left to finish or fail
harmlessly; not relied upon further.

## 2026-09-09 (14) — Fallback-node T1 implemented; ephemeral-processing constraint recorded (no FastAPI)

Started requirement one (`2026-09-09-verbatim-fallback-nodes` T1). Added
`document_profile.party_result_to_fallback_event()`: consumes an existing
`PartyResult` on `tier4b_title_block` / `tier5_none`, returns `None` when there is
no `TitleBlock` (does not invent a span), runs `extract_deterministic()` on the
block text only, and passes harvested CASE_NUMBER/PROVISION rows through
`normalize_entities()` (T3's call, landed with T1). Unit tests in
`tests/test_fallback_event.py` (3 passed) are synthetic contract tests only — not
a real-document proof (`FORBIDDEN.md` §E17 still applies to T5).

Owner also stated the product constraint that multi-document upload must process,
return data to the user's machine, and delete PDFs with nothing kept on the
server. That is a new requirement folder
(`docs/requirements/2026-09-09-ephemeral-client-results/`), not a widening of the
fallback-nodes folder. Recorded as `FINDINGS.md` F-5, `docs/spec/SCOPE.md`
amendment, and `docs/spec/ARCHITECTURE.md` G4. Cookies rejected as the graph
store. FastAPI/React upload **not** implemented this entry: `HEART.md` tier 3
is still blocked, and HANDOFF §9 now lists skip-tier as owner-reserved unless
dated. `git init` still not done (HANDOFF §9). Installed already-listed
`rapidfuzz` into the default interpreter to run T1 tests; not a new dependency.

## 2026-09-09 (13) — Cursor-readiness review: requirements.txt added, AGENTS.md stale reference fixed

Owner asked whether the project is ready to hand to Cursor for implementation. Did a
grounded review, not a vibe check: re-verified every function/class name cited in
both requirements folders' `DESIGN.md` files against the actual `src/` code (all
correct), confirmed the real directory structure matches `AGENTS.md`'s folder map,
and checked for what a coding agent needs to start cold.

Found two real gaps and one doc bug. Asked the owner about git init (still not a git
repo) — owner will do that themselves. Asked about a dependency manifest — owner said
yes. Added `requirements.txt` (core pipeline deps, with the spacy/pydantic/numpy/
thinc/typer/weasel/wasabi chain pinned to the exact versions verified working for
`en_legal_ner_sm` this session via `pip freeze` on the working venv — not guessed —
plus the manual install recipe for the model wheel itself, which cannot go in a
requirements file at all due to its invalid PEP 440 version segment) and
`requirements-docling.txt` (optional, ~1.5GB, for the structure-and-embedding-layers
work only — explicitly flagged as never tested in combination with the main
requirements.txt environment). Fixed `AGENTS.md` §9's folder map, which claimed
`docs/research/existing-approach/` contains a `FINDINGS.csv` register — it doesn't
(verified) — leftover from the initial scaffolding template, now corrected to point
at `FINDINGS.md` at the root, the project's actual register.

## 2026-09-09 (12) — Structure/embedding requirement formalized; HANDOFF.md rewritten for the full session

Owner asked for a detailed requirement plus a proper agent handoff, rather than
leaving F-4's research as the only record. Added
`docs/requirements/2026-09-09-structure-and-embedding-layers/` (REQUIREMENTS.md,
DESIGN.md, POC_RESULTS.md, TASKS.md, TRACKER.md) — grounded in a real integration
point discovered by reading `src/casemap_pipeline.py` directly: `segment_document_layered()`
already has a clean `try: from layout_structure import detect_structure_layered
except ImportError: <fallback>` seam, so a Docling-backed `layout_structure.py`
plugs in with zero other pipeline changes. `DESIGN.md` also surfaces two open
questions the POC didn't answer: whether Docling's `item.prov[0].page_no` actually
matches `casemap_pipeline`'s own page numbering (untested), and whether
`Qwen3-Embedding-0.6B` works via the `sentence_transformers` path
`make_similarity_fn()` actually uses (the POC only tested Ollama's API, a different
code path) — both are now T1/T3 in `TASKS.md`, not silently assumed.

Rewrote `HANDOFF.md` in full — it was last substantially accurate at governance init
and had drifted badly behind entries (5)-(11)'s work. Now reflects: both formalized
requirements and their status, all 4 findings, `testdata/`'s existence and limits,
the three `temp/*-poc/` folders and their working (expensive-to-rebuild) venvs, the
Windows-specific dependency fixes needed for `en_legal_ner_sm`, and an updated
recommended work order pointing at the two ready `TASKS.md` files as the actual next
step, ahead of re-deriving what to do from the pre-governance handoff. No `src/` file
changed.

## 2026-09-09 (11) — Docling re-tested against genuinely scanned/OCR-damaged PDFs; MinerU footprint checked (not lighter)

Closes the gap entry (10) explicitly flagged as open. Asked whether MinerU is
"lighter" than Docling before running it — checked its PyPI dependency metadata
directly rather than assume: both its `pipeline` and `vlm` install extras require
`torch`/`transformers` (`vlm` needs a full vision-language model), so it is not
lighter, and no MinerU conversion was run this entry (still flagged as not yet
tested). Instead, per the owner's choice, closed the OCR gap: rendered 2 of the
existing digital PDFs (docs 09, 21) to raster images via PyMuPDF, degraded them with
real scanner artifacts (±1.2° rotation, Gaussian blur, 0.4% salt-and-pepper noise),
and rebuilt zero-text-layer PDFs (`temp/2026-09-09-layer-additions-poc/make_scanned_pdfs.py`,
verified 0 embedded characters before the run) — forcing Docling's actual OCR engine
(RapidOCR), not PDF font metadata. Structure detection (headings, list items) came
back correct on both documents, at real cost (12-18s/doc vs. 1.6-8s on the text-layer
path) and with real OCR word-boundary damage (dropped spaces, e.g.
"NATIONALCOMPANY LAWAPPELLATE") — the same general class of damage
`FORBIDDEN.md` §E18/BUG-26 already documents for this project's own OCR path,
independently observed here in Docling's. Updated
`docs/research/new-directions/layer-additions-assessment.md` (new Part 4) and
`FINDINGS.md` F-4. No `src/` file changed.

## 2026-09-09 (10) — Docling + Qwen3-Embedding tested together (research only): recovers missing structure detection, drops into the existing similarity seam

Owner asked about six more candidate tools (Docling, MinerU, GLiNER2, NuExtract 2.0,
Qwen3-Embedding, HippoRAG 2) and specifically asked to test the top two picks
(Docling — addressing the missing `layout_structure.py`; Qwen3-Embedding — a drop-in
for `make_similarity_fn`'s MiniLM/BGE-M3 slot) **together**, not separately, to see if
they actually compose. NuExtract 2.0 was flagged and excluded up front — architecturally
generative, same category `FORBIDDEN.md` §C already excludes, same risk F-1 already
demonstrated. HippoRAG 2 excluded for the same complexity reason Graphiti/Neo4j were
already rejected (`CaseMap_AGENT_HANDOFF.md` §9).

`testdata/` is plain text, not PDFs, so 4 documents (the 09/21/22 connected bundle +
an unrelated distractor) were rendered to real PDFs with a genuine font-size/bold
hierarchy (`temp/2026-09-09-layer-additions-poc/make_test_pdfs.py`) — stated
limitation: this tests digital-PDF layout only, not scanned/OCR-damaged input.
Installed `docling` (2.126.0, ~1.5GB, its own layout+OCR models) in a dedicated venv
and `qwen3-embedding:0.6b` via Ollama (639MB — smaller than the generative model
tested in entry (5)). Docling correctly labelled headings/list-items using real font
signals; wired its output through `en_legal_ner_sm` (F-2) for entities and
Qwen3-Embedding for `score_pair`'s semantic term, then ran the real, unmodified
`casemap_pipeline` graph functions (same discipline as entry (7)'s fallback-nodes POC
— no parallel reimplementation). Result: the 3 connected documents all linked
correctly (scores 0.30-0.62), the unrelated document never crossed the edge threshold
despite non-trivial raw semantic similarity. Logged as `FINDINGS.md` F-4, full writeup
`docs/research/new-directions/layer-additions-assessment.md`. Not adopted — two real
gaps flagged before this is more than a POC: no test against genuinely scanned/OCR
input yet, and no head-to-head against MinerU. No `src/` file changed.

## 2026-09-09 (9) — Fallback-node requirement formalized: TASKS.md + TRACKER.md opened, ready for implementation

Closes out entry (7)/(8)'s requirements-and-POC work per `AGENTS.md` §6: added
`docs/requirements/2026-09-09-verbatim-fallback-nodes/TASKS.md` (5 scoped tasks —
`party_result_to_fallback_event()`, the ML role-instability trigger, the mandatory
`normalize_entities()` call the POC found necessary, confidence rendering in
`to_react_flow`/`build_evidence_card`, and wiring into `poc_run.py`) and `TRACKER.md`
(all POC steps marked done, all 5 implementation tasks not started). Nothing under
`src/` implemented yet — this entry only formalizes what's ready to build, per the
owner's explicit request to see the requirement finalized before implementation
starts.

## 2026-09-09 (8) — Fallback-node POC follow-up: connected real bundle added, edge formation tested, normalize_entities() gap found

Owner asked to get connected test documents before deciding how to proceed on entry
(7)'s open edge-formation question, rather than accept "untested" as the final answer.
Added `testdata/21_insolvency_nclat_khursheed_anwar_v_sunil_kumar_gupta_2025-09.txt`
and `testdata/22_insolvency_sc_khursheed_anwar_v_sunil_kumar_gupta_2025-12.txt` —
genuinely part of the same matter as the existing doc 09 (same Corporate Debtor
"Cygnus Splendid Ltd", same RP "Sunil Kumar Gupta"; doc 22 is the Supreme Court appeal
that explicitly cites doc 21's order by date and case number). Re-ran the POC across
all 22 docs: still zero regex-ladder tier 4.5/5 triggers (confirms this wasn't a
sampling artifact of the first 20 — that tier needs OCR-damaged input, which nothing
here has). Ran a follow-up scoring-only test (`temp/2026-09-09-verbatim-fallback-poc/poc_edge_formation_test.py`,
clearly labeled forced/synthetic, not a claim about real trigger timing) that got a
real edge between docs 09 and 21 via shared entity text, correctly did not connect an
unrelated negative-control document, and did not connect doc 22 — because its header
writes the same name in ALL CAPS, an exact-string mismatch. That gap has a known fix
already in the codebase (`casemap_pipeline.normalize_entities()`, the BUG-5/BUG-7
type-scoped fuzzy dedup) that this POC didn't call — now added to `DESIGN.md` as a
stated requirement for real implementation, not left implicit. Updated `FINDINGS.md`
F-3 and `POC_RESULTS.md` with the full picture. No `src/` file changed.

## 2026-09-09 (7) — Fallback-node design + POC: verbatim-block sections stay on the graph, honestly labeled

New design direction from the owner, following F-1/F-2: instead of only ever trying to
resolve a section to a clean structured party/role field, let a low-confidence result
(the existing tier-4.5 "verbatim block", or an unstable mandatory-ML role label) become
a graph node in its own right — carrying whatever entities *were* confidently detected
in that span, honestly labeled as lower-confidence, rather than being dropped or forced
into a possibly-wrong field. Explicitly no search/query interface is being built (owner
decision) — the graph view is the only interface this needs to support.

Added `docs/plan/verbatim-fallback-graph-nodes.md` (the plan), then
`docs/requirements/2026-09-09-verbatim-fallback-nodes/REQUIREMENTS.md` + `DESIGN.md`
before any code, per `AGENTS.md` §6. `DESIGN.md` is grounded in what actually exists in
`src/` today (read directly, not assumed): the tier-4.5 `TitleBlock` fallback already
exists in `document_profile.py`, but nothing consumes it into a graph node —
`case_symbols.py`, the component that normally would, is still not present in this
working directory (`HANDOFF.md` §6).

Ran a POC (`temp/2026-09-09-verbatim-fallback-poc/`) using the real
`extract_parties_layered()` and real `casemap_pipeline` graph functions, unmodified,
against `testdata/`. Honest result, logged as `FINDINGS.md` F-3: the regex ladder never
hit tier 4.5/5 on this clean document set (expected — that tier is for OCR-damaged
input, which `testdata/` doesn't have); the mandatory-ML role-instability trigger fired
4/20 times; the resulting fallback events flowed through the unmodified graph pipeline
with zero special-casing (mechanism validated) but produced 0 edges, because
`testdata/`'s 20 documents are unrelated cases with nothing to link — edge formation
remains genuinely untested pending a real connected document bundle. Full write-up:
`docs/requirements/2026-09-09-verbatim-fallback-nodes/POC_RESULTS.md`. No `src/` file
changed — `TASKS.md`/`TRACKER.md` for real implementation not opened yet, pending the
owner's read of this POC result.

## 2026-09-09 (6) — Mandatory model (en_legal_ner_sm) installed and run against real documents for the first time

Following entry (5)'s generative-LLM test, owner asked for a genuinely legal-trained
model under 100M params. A Hugging Face survey found nothing credible in that space
(AYN still has no public checkpoint; the one small "legal" community upload found has
no downloads/evals and isn't trustworthy) — the only real candidate is `en_legal_ner_sm`
itself, OpenNyAI's own model that `opennyai_bridge.py`/`docs/spec/ARCHITECTURE.md` §2
already require as mandatory. It had never actually been installed and run in any
session (`HANDOFF.md` §8 item 1, `CaseMap_AGENT_HANDOFF.md` §7 item 1) — this entry
does that for the first time.

Installed via a dedicated venv (`temp/2026-09-09-mini-llm-poc/venv_ner/`) after working
around two Windows-specific dependency issues: the model wheel served by HuggingFace
has an invalid PEP 440 version segment that current `pip` rejects (fixed by
downloading and renaming it locally), and the model's own `spacy<3.3.0` pin collides
with a newer spaCy needed to avoid a `pydantic`/Python 3.11 incompatibility in spaCy
3.2.x (fixed by installing the model wheel, then re-upgrading spacy/typer/weasel back
to 3.8.16-compatible versions — it loads with a harmless version-mismatch warning).
Ran it against the same 20 documents from entry (5)'s `testdata/`: ~350x faster than
the generative-LLM run (0.06s/doc vs ~21s/doc), never failed to terminate, and every
output is verbatim-by-construction. Raw role labels (PETITIONER/RESPONDENT/JUDGE/COURT)
have real noise (~3.6% of role-tagged spans on a crude check — role confusion across
repeated mentions, lawyers mislabeled as parties/judges, a statute abbreviation
mislabeled as a court) — this is the first real evidence for why
`docs/spec/ARCHITECTURE.md` already mandates a second deterministic role-refinement
layer on top of this model's output rather than trusting it directly; confirms the
existing architecture, doesn't change it. Full writeup:
`docs/research/new-directions/mini-llm-extraction-assessment.md` Part 2. Logged as
`FINDINGS.md` F-2. No file under `src/` changed — `opennyai_bridge.py` still runs in
`--allow-degraded` mode; wiring this venv/install recipe into the real pipeline
dependency set is separate, larger work, not done here.

## 2026-09-09 (5) — Real-document testdata/ added; small-LLM extraction assessed (research only)

Owner asked for a real-world sanity check before further build effort: (a) at least 20
real legal documents for POC testing, and (b) a look at what a small, cheap, local
generative LLM actually produces on them, before deciding whether that's worth
anything. Both done as research, not core changes — no file under `src/` touched.

Added `testdata/` — 20 real Indian court judgments (Supreme Court, 6 High Courts,
NCLAT, a State Consumer Commission, ITAT), pulled from indiankanoon.org (public-domain
judgment text, `robots.txt`-compliant), spanning criminal, matrimonial, civil/contract,
tax, motor vehicle, land/property, labour, insolvency, constitutional/bail, consumer,
company law, and succession matters. See `testdata/README.md` for provenance.

Ran a one-shot structured-extraction prompt (court/parties/dates/amounts as JSON)
against all 20 documents using `qwen2.5:1.5b` via Ollama (local, CPU, temperature 0) —
a generic small model, not the previously-investigated-and-rejected AYN (still no
public checkpoint found, per `CaseMap_AGENT_HANDOFF.md` §6). Script and raw output live
in `temp/2026-09-09-mini-llm-poc/` (ephemeral, per `AGENTS.md` §9 routing table); the
write-up is `docs/research/new-directions/mini-llm-extraction-assessment.md`; the
one-line conclusion is logged as `FINDINGS.md` F-1. Headline: party names came back
95%+ verbatim with zero fine-tuning, but the model degenerated into a non-terminating
repetition loop on 1 of 20 documents and misread page furniture as a dollar amount on
another — evidence for, not against, `FORBIDDEN.md` §C's no-generative-LLM-in-the-core
rule. This does not change that rule, which stays owner-reserved (`HANDOFF.md` §9).

## 2026-09-09 (4) — poc_run.py split out of src/ into a new scripts/ folder

`poc_run.py` is a CLI proof-of-concept runner, not core pipeline library code and not a
test — it doesn't belong mixed into `src/` alongside `casemap_pipeline.py`,
`document_profile.py`, `opennyai_bridge.py` either (owner feedback: "these were not test
files right? there were poc test files can't we have script folder?"). Moved it to a new
`scripts/poc_run.py`. Since it imports `opennyai_bridge`, `document_profile`, and
`casemap_pipeline` as flat siblings and those stayed in `src/`, added a two-line
`sys.path` bootstrap at the top of the file (right after its existing stdlib imports,
before its local imports) so it still resolves them at `../src` relative to itself — the
same non-invasive pattern as `tests/conftest.py` in entry (3), nothing else in the file
changed. Updated every cross-reference in `AGENTS.md`, `HANDOFF.md`, `STATUS.md`,
`HEART.md`, `THESIS.md`, and `docs/spec/ARCHITECTURE.md`.

## 2026-09-09 (3) — Pipeline source moved out of repo root into src/

`casemap_pipeline.py`, `document_profile.py`, `opennyai_bridge.py`, `poc_run.py` moved
from repo root into `src/` (still flat siblings there, no `__init__.py`/package install
yet) at the owner's request — plain source files should not sit at the governance root
alongside `FORBIDDEN.md`/`AGENTS.md`/etc. Added `tests/conftest.py` to put `src/` on
`sys.path` so `tests/test_opennyai_bridge.py`'s existing flat imports
(`import opennyai_bridge as bridge`, `from document_profile import ...`) keep working
without editing the import lines themselves. Updated `AGENTS.md` §9's folder map and
every other cross-reference in `HANDOFF.md`, `STATUS.md`, `HEART.md`, `THESIS.md`, and
`docs/spec/ARCHITECTURE.md` (the two dated records under
`docs/research/existing-approach/` were left untouched — they are frozen historical
write-ups, not live references, per `AGENTS.md` §5).

## 2026-09-09 (2) — Existing pre-governance files relocated into the governance structure

Moved `CaseMap_AGENT_HANDOFF.md`, `CaseMap_Mandatory_ML_Layer_v7.md`, and
`poc_report.md` from repo root into `docs/research/existing-approach/` (they are dated
records of the existing system — measurements and write-ups of the pre-governance build,
exactly the kind of content that section is for, per `AGENTS.md` §9's routing table).
Moved `test_opennyai_bridge.py` from repo root into a new `tests/` directory. Updated
every cross-reference to these files across `AGENTS.md`, `HANDOFF.md`, `STATUS.md`,
`FINDINGS.md`, `FORBIDDEN.md`, `THESIS.md`, `HEART.md`, `README.md`, and
`docs/spec/{SCOPE,ARCHITECTURE}.md`. No file content changed, only location. (Pipeline
source itself moved out of repo root in a later entry below — see 2026-09-09 (4).)

## 2026-09-09 (1) — Governance scaffolded on top of the existing POC

`FORBIDDEN.md`, `AGENTS.md`, `THESIS.md`, `HEART.md`, `HANDOFF.md`, `STATUS.md`,
`FINDINGS.md`, `README.md`, and `docs/spec/{SCOPE,ARCHITECTURE}.md` created. Regular-
engineering governance pattern used (no two-judge law / global trial counter) — decided
explicitly with the project owner, since the existing "real documents as the only valid
test oracle" + 26-bug-ledger discipline already covers the anti-drift need without a
formal statistical-trial framework. `git init` explicitly deferred at the owner's
request. No pipeline code changed. `FORBIDDEN.md` §E and `THESIS.md`/`HEART.md` were
seeded with real content (not placeholders) from `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md`,
`docs/research/existing-approach/CaseMap_Mandatory_ML_Layer_v7.md`, and `docs/research/existing-approach/poc_report.md`.
