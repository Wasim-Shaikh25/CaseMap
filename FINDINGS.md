# Findings

> Every finding gets a one-liner, a fix/decision, and a link to full evidence if there is
> one. A finding that exists only in a chat reply, a scratch script, or a temp file is
> **not recorded** — write it here or it did not happen.
>
> This register is **append-only** in spirit: when a finding is fixed, update its status
> in place (fixed findings are useful history, not clutter) but never delete a finding or
> rewrite what it originally said. If a later result supersedes one, add a banner naming
> the successor.

**Open:** 7 · **Fixed:** 12 · **Superseded:** 0

## F-20 — Three more rhetorical-role models actually run for real (two platform fixes worked); all three still unusable on real documents

**Date:** 2026-09-11
**One-liner:** Owner pushed back on F-19's addendum: the `opennyai` blocker
was a platform/toolchain gap, not proof the model itself doesn't work —
"can't we make it work, it's our platform that's lacking." That was the
right instinct and worth honoring with real effort, not a shrug. Three more
models were actually run end-to-end (not just researched): AllenNLP (dead,
confirmed unfixable), Hier_BiLSTM_CRF (platform issue *fixed* via WSL — a
real, working model), and InLegalBERT(i) (loads and runs cleanly). None of
the three produce output worth combining with the existing phrase-matcher
once tested against real judgments.

**AllenNLP (the original OpenNyAI/`rhetorical-role-baseline` dependency):
confirmed dead, not a version-pin fix.** Latest release (2.10.1) hard-pins
`spacy<3.4`, which drags in `preshed<2.1` needing a source build, whose
`setup.py` imports `distutils.msvccompiler` — removed from modern
`setuptools` entirely. Not attempted further: this isn't a version choice,
it's 2021-era tooling calling an API that no longer exists anywhere. AllenNLP
's own PyPI page says "maintenance mode... no longer adding new features or
upgrading dependencies."

**Hier_BiLSTM_CRF (the paper's own best model, F1 0.77): the platform issue
was real, and WSL fixed it.** Its pretrained variant needs Facebook's real
`sent2vec` (C++), whose build passes GCC-only flags (`-std=c++0x`,
`-Wno-cpp`) that MSVC rejects — confirmed this is a Windows-vs-Linux gap,
not a broken library, by building it clean under WSL/Ubuntu (`sudo apt
install python3-venv build-essential python3-dev`, then
`pip install git+https://github.com/epfml/sent2vec` — succeeded with zero
patching). Cloned `Law-AI/semantic-segmentation` (the actual code this
model's architecture comes from), downloaded the real checkpoint
(`L-NLProc/LegalSeg_Hier_BiLSTM-CRF` on HF: `model_state4.tar`,
`word2idx.json`, `tag2idx.json` — its `word2idx.json` confirms this
checkpoint is the NON-pretrained variant, so `sent2vec` wasn't even
ultimately needed for this specific checkpoint, but building it removed
that as a variable). Three more real bugs found and fixed to get inference
running at all:
  1. `argparse`'s `type=bool` treats any non-empty string as `True` — passing
     `--pretrained False` on the command line actually set it `True`.
     Fix: omit the flag (default is already `False`).
  2. `torch.load()`'s `weights_only=True` default (PyTorch 2.6+) rejects the
     2019-era pickled checkpoint. Fix: `weights_only=False` (safe — official
     paper checkpoint from the authors' own HF repo).
  3. Checkpoint was saved from a CUDA device; this machine has none.
     Fix: `map_location=torch.device('cpu')`.
  4. A real bug in `Law-AI/semantic-segmentation`'s own code:
     `Hier_LSTM_CRF_Classifier.__init__` builds its `LSTM_Sentence_Encoder`/
     `LSTM_Emitter` submodules WITHOUT passing `device=self.device` through,
     so they silently default to `'cuda'` regardless of the `--device cpu`
     flag. Patched both constructor calls in `model/Hier_BiLSTM_CRF.py`.

  **Result once it actually ran**: fed two real `testdata/*.txt` judgments,
  once with a quick regex sentence-splitter (naive) and once with this
  project's own abbreviation-aware sentence splitter
  (`important_lines.py`'s `_raw_sentence_spans`/`_ends_with_abbreviation`/
  `_merge_short_spans`, to rule out bad input as the cause). The better
  splitter measurably helped — it correctly caught one real
  `Arguments of Petitioner` the phrase-matcher's fixed cues would have
  missed ("Counsel for the appellants urged that under this order
  Bharatsingh is entitled to challenge...", no match in
  `RHETORICAL_ROLE_CUES`) — but the model still collapsed to **almost
  entirely "Facts" or "None"** across both full documents: zero
  predictions for Issue, Arguments of Respondent, Reasoning, or Decision,
  including on sentences that plainly are Reasoning ("Dilip Kumar's
  conduct cannot be viewed with leniency and the High Court was right in
  confirming the death sentence..." — this or similar sentences were
  tagged `None`, not `Reasoning`). One correct catch in ~50 real sentences
  is not enough signal to build on.

**InLegalBERT(i) (`L-NLProc/LegalSeg_InLegalBERT`, plain `transformers`):
loads cleanly, output looks close to random.** `BertForSequenceClassification.
from_pretrained("law-ai/InLegalBERT", num_labels=7)` +
`load_state_dict(safetensors, strict=True)` — zero missing/unexpected keys,
confirming the architecture guess was exactly right. But real predictions on
the same two documents look incoherent, not just weak: "The High Court
confirmed the conviction and sentence of Dilip Kumar" (plainly Facts) →
`Issue` at 0.85 confidence; "Payment of interim maintenance III." (a
table-of-contents fragment) → `Arguments of Respondent` at 0.55. The HF repo
ships only bare weight tensors, no `config.json`/label-mapping file, so the
7-way label order (`Facts, Issue, Arguments of Petitioner, Arguments of
Respondent, Reasoning, Decision, None`) had to be inferred from the paper's
prose listing of the task's label set `Y` — this result casts real doubt on
whether that inferred order matches their actual training-time integer
encoding, and without their exact `train.csv`/label-encoding code there's no
way to confirm it from outside. Not worth guessing further (5040 possible
orderings).

**Verdict: still not worth integrating, but for a fully verified reason
this time, not an assumption.** Across five real attempts (`opennyai`,
AllenNLP, Hier_BiLSTM_CRF, InLegalBERT(i), and F-19's own embedding
fallback), two were genuine platform/toolchain gaps and one of those (WSL)
was actually fixed — proving the "it's our platform, not the model" instinct
right in that one case. But once each model that could actually run was
tested against real judgments, none produced signal reliable enough to
combine with the existing phrase-matcher (a hybrid only helps if the
fallback beats honest silence; here it would inject confident wrong
answers into cases the matcher currently — correctly — leaves untagged).
`RHETORICAL_ROLE_CUES` stays on the plain phrase/fuzzy matcher.
**Evidence**: `temp/2026-09-11-hier-bilstm-crf-poc/` (WSL venv + patched
`Law-AI/semantic-segmentation` clone + checkpoint, never committed),
`temp/2026-09-11-allennlp-rhetorical-role-poc/` (never committed), direct
inference runs against `testdata/01_criminal_sc_dilip_kumar_sharma_v_mp.txt`
and `testdata/03_matrimonial_sc_rajnesh_v_neha.txt` with full label-by-label
output inspected by hand.

## F-19 — Tried and rejected: embedding-similarity fallback for `RHETORICAL_ROLE_CUES`

**Date:** 2026-09-11
**One-liner:** Same fixed-phrase-list problem as F-16/F-18, attempted the
same fix pattern (reuse an already-loaded small model, no training) for
`rhetorical_roles.py`'s Facts/Issues/Arguments/Precedent/Analysis/Ruling
tagging — and it made role tagging **less** trustworthy, not more. Reverted
before merging; recorded here so the approach isn't tried again without new
information (same honesty standard as the Qwen3-vs-MiniLM decision above).

**What was tried:** `match_cue_embedding()` — encode each of
`RHETORICAL_ROLE_CUES`'s own phrases with `sentence_transformers/
all-MiniLM-L6-v2` (already a mandatory dependency, used elsewhere for
embedding centrality — no new model), average into one anchor vector per
role, and compare a paragraph's embedding to all six via cosine similarity.
Only fire above an absolute threshold AND a margin over the runner-up, to
avoid guessing on ambiguous cases.

**Why it failed:** built `scripts/tune_rhetorical_embedding.py` and ran it
against all 22 real `testdata/*.txt` judgments before wiring this in live —
the same "measure before shipping" discipline used throughout this session.
Result: roughly half of the 26 "embedding_matched" tags it produced were
wrong, and several were clear header/caption noise mistaken for real
content — `"DATE OF JUDGMENT10/10/1975"` → tagged PRECEDENT, `"Source:
https://indiankanoon.org/doc/..."` → tagged ARGUMENTS_PETITIONER,
`"PETITIONER: U.P. State Electricity Board"` (a caption label) → tagged
ARGUMENTS_PETITIONER purely because the word "petitioner" appears. Worse,
some misfires looked plausible enough to pass a casual read: `"Heard the
learned counsel for the parties."` → tagged ARGUMENTS_PETITIONER when it's
much closer to the existing ANALYSIS cue ("having heard"); `"4. Brief facts
which are necessary to dispose of this appeal..."` → tagged
ARGUMENTS_PETITIONER when it's literally FACTS. Short cue phrases are too
weak an anchor for six-way role classification with generic sentence
embeddings — the model latches onto surface word overlap ("petitioner"
appears → ARGUMENTS_PETITIONER) rather than actual argumentative role.

**Disposition:** reverted (`git checkout -- src/rhetorical_roles.py`); the
plain phrase/fuzzy matcher is unchanged and still the only role-tagging
signal. `RHETORICAL_ROLE_CUES` remains a genuinely open item — per
`opennyai_bridge.py:122`'s already-noted seam, this needs an actual trained
classifier (OpenNyAI's own rhetorical-role baseline is the known candidate,
unconfirmed inference entrypoint), not another parse-based generalization.
`scripts/tune_rhetorical_embedding.py` kept as evidence of what was tried
and why it didn't work, same as the Qwen3-vs-MiniLM comparison scripts.

**Addendum, 2026-09-11: the "unconfirmed inference entrypoint" is now
confirmed — and confirmed broken on this machine.** `opennyaiorg/
InRhetoricalRoles` does have a real, documented, pip-installable package
(`pip install opennyai`, `Pipeline(components=['Rhetorical_Role'])`),
resolving `opennyai_bridge.py:122`'s open question about whether a real
entrypoint exists. It does — but it is not a small model (pulls in
`torch`+`transformers`, self-labeled "Development Status :: 2 - Pre-Alpha"
on PyPI) and **requires Python >=3.13**; the version that supports Python
3.11 (`0.0.12`) hard-pins `spacy>=3.2.2,<3.3.0`, directly conflicting with
this project's own mandatory spaCy **3.8.16** pin
(`docs/requirements/2026-09-10-wire-opennyai-ner/`). Owner approved
installing Python 3.13 (via `winget install Python.Python.3.13`, isolated
from the existing Python 3.11/`.venv`) specifically to evaluate this in a
throwaway venv (`temp/2026-09-11-opennyai-rhetorical-role-poc/
venv_opennyai/`, never committed) before deciding whether to upgrade the
whole project.

**Result: hard blocked, not a fixable version pin.** `pip install opennyai`
fails building `spacy-curated-transformers`'s own transitive dependency
chain: it needs `thinc>=9.0`, whose Cython source (`thinc/backends/
numpy_ops.pyx`) does not compile under Python 3.13's toolchain/Cython
version on this machine (`Cython.Compiler.Errors.CompileError`). This is
not a workaround-able "wrong version selected" problem — it's `thinc` 9.0's
own C-extension source failing to build, an upstream compatibility gap,
consistent with `opennyai` 0.0.15 being three weeks past a major rewrite
(Python 3.8→3.13 jump between PyPI releases 0.0.12 and 0.0.13) and still
labeled Pre-Alpha. Confirmed `spacy-curated-transformers` is NOT optional
at runtime — `Pipeline(components=['Rhetorical_Role'])` requires it to load
`en_core_web_trf` for its own internal preprocessing; every other declared
dependency (torch, transformers, spacy-transformers, pytorch-transformers,
etc.) installed and imported cleanly on Python 3.13 in isolation, so this is
narrowly `spacy-curated-transformers`'s fault, not a broader Python-3.13
problem.

**Verdict: do not pursue further right now.** Re-evaluate only if a future
`opennyai`/`spacy-curated-transformers` release fixes this (worth a periodic
check, not active work). `RHETORICAL_ROLE_CUES` stays open on the plain
phrase/fuzzy matcher. Python 3.13 was installed system-wide for this
evaluation (harmless, isolated from the project's Python 3.11 `.venv`) and
left in place in case a retry becomes worthwhile later.

**Continued in F-20**: owner pushed back that the `opennyai` blocker looked
like a platform gap, not a broken model, and asked to actually try fixing
it rather than stop — that push led to AllenNLP, `Hier_BiLSTM_CRF`, and
`InLegalBERT(i)` all being tried for real (two platform fixes genuinely
worked), see F-20 for the full result.

## F-18 — `DENIAL_MARKERS`/`ASSERTION_MARKERS` fixed-phrase polarity missed real denials/assertions; added a dependency-parse signal alongside them

**Date:** 2026-09-11
**One-liner:** Same failure class as F-16, in `_classify_polarity()`
(`casemap_pipeline.py`): `DENIAL_MARKERS`/`ASSERTION_MARKERS` only fire on an
exact phrase ("did not receive", "states that"). "Has not received", "is
denying", "refutes the claim", "counsel contends that" all fell through to
NEUTRAL, which is what drives conflict detection (`build_case_graph`'s
DENIES/ASSERTS matching) — a real denial phrased slightly differently than
the enumerated list simply never became a conflict.

**Fix:** `DENIAL_VERB_LEMMAS`/`ASSERTION_VERB_LEMMAS` (new, small verb-lemma
sets) plus spaCy's own `neg` dependency tag (real syntactic negation,
catches "not"/"never" attached to *any* verb) are checked as a second pass
**after** the original phrase lists, using `en_core_web_sm` — already
mandatory-loaded for entity extraction, no new model. **Additive, not a
replacement**: idiomatic non-verbal phrases ("false and baseless", "wrongly
alleged") have no verb or negation particle to key off, so the original
`DENIAL_MARKERS`/`ASSERTION_MARKERS` phrase lists stay exactly as they were
and are checked first.

**Verified:** direct unit check — "the respondent has not received any
payment" and "the petitioner refutes the claim entirely" (both real phrasing
the old list missed) now correctly return `DENIES`; "counsel contends that
the notice was invalid" now correctly returns `ASSERTS`; existing phrase-list
cases and a neutral control sentence unaffected. Full `pytest`: 62 passed, 1
skipped, no regressions.

**Correction, 2026-09-11 (same day, CHANGELOG 71):** the `neg`-dependency
half of the fix above was tested against a real document immediately after
landing — the owner's own writ petition
(`temp/2026-09-10-real-petition-run/BCI_NOC_WP.txt`, never committed, run
locally only) — and it was wrong. An argumentative legal brief is full of
negation as ordinary reasoning ("does not maintain", "cannot accomplish",
"is not distinguishable") that is not one party denying another's fact.
Blanket "any negated verb = DENIES" mislabeled **20 of 111 events (18%)**
DENIES on that real document, nearly all of them ordinary argument, not
conflicts — DENIES/ASSERTS exists specifically to feed `label_edge()`'s
POTENTIAL_CONFLICT pairing between two events, not to flag every negated
sentence. **Removed** the `neg`-dependency check; kept only the verb-lemma
sets (`DENIAL_VERB_LEMMAS`/`ASSERTION_VERB_LEMMAS`), which still catch real
phrasing the old list missed ("refutes the claim", "counsel contends that")
without the flood. Re-verified on the same real document post-correction:
DENIES dropped from 20 to 1, ASSERTS unchanged at 3. `pytest`: still 62
passed, 1 skipped.

## F-17 — New capability: opt-in provision lookup (`src/provision_lookup.py`), the pipeline's first outbound network call

**Date:** 2026-09-11
**One-liner:** Owner asked to add a free web lookup so a cited provision's
own text shows up next to the citation, explicitly scoped to "only the
provision, not client details." This is a new capability, not a bug fix —
recorded here because it's the first place this pipeline makes any outbound
network call, which is a real change to the privacy posture stated on the
dashboard and in `server/app.py`'s "nothing is persisted" docstring
(persistence is unaffected; **egress** is the new thing).

**What it does:** `provision_lookup.lookup_provision(section_raw, act)`
queries IndianKanoon.org's free, no-login search (the same source the
`testdata/` judgments themselves came from) with the citation string alone
("Section 125 of the Code of Criminal Procedure") and returns the matching
statute's own text snippet + source link — **or `None`**, whenever the
result isn't confidently a bare-statute page (checked via IndianKanoon's own
`docsource` type marker and a section-number match in the result title, not
guessed). One outbound call per **unique** provision per document (in-process
cache), never per citation instance.

**Confirmed default-off:** wired through `casemap_service.process_document(
lookup_provisions=False)` → `server/app.py`'s `/api/process` (`Form(False)`)
→ a checkbox on `ui/index.html`'s upload screen, unchecked by default, with
its own disclosure text next to it. The dashboard's privacy paragraph
(`ui/index.html`) was updated to say so plainly rather than leave the older
"the only thing that ever leaves this device is..." line technically wrong
once this toggle exists.

**Verified end-to-end** against real `testdata/` documents via the running
server (`/api/process` with `lookup_provisions=true`): confident matches
("section 303", "section 302", "section 34" → correct IPC text + source
link) and correct skips on genuinely ambiguous citations ("s. 303" alone,
with no "Section" keyword or Act name nearby — skipped rather than guessed,
by design). Rendered and screenshot-checked in both the per-document report
(`App.downloadReport()`) and the live cross-document **Provisions** tab
(`App.renderProvisions()`), light and dark theme. Full `pytest`: 62 passed,
1 skipped, no regressions — this feature has no test coverage of its own yet
(network-dependent; a mocked-response test is a reasonable follow-up, not
done this pass).

**Addendum, 2026-09-11: test coverage added.** `tests/test_provision_lookup.py`
(8 tests) — a fake `requests.get` (same pattern as
`test_opennyai_bridge.py`'s fake NER model: real parsing/gating logic,
faked network response) covers a confident bare-statute match, a judgment
result correctly skipped (not mistaken for statute text), a
right-docsource-wrong-section-number mismatch correctly skipped, no
results, a non-OK HTTP response, a raised `ConnectionError` (must degrade
to `None`, never crash document processing), and the in-process cache
(one outbound call per unique query, confirmed via a call counter; two
different queries resolve independently). All 8 pass; full suite now 70
passed, 1 skipped.

## F-16 — `EVENT_KEYWORDS` fixed-phrase event detection missed real events; replaced with a dependency-parse (SRL) layer, no new model

**Date:** 2026-09-11
**One-liner:** `casemap_pipeline.detect_events()`'s event detection only ever
fired on an exact multi-word phrase (`EVENT_KEYWORDS` — "paid", "filed on",
"order dated", ~26 phrases across 6 types). A real event phrased any other
way ("Rohitsingh was acquitted...", "the wife left the matrimonial
home...") was structurally invisible to it, not just uncommon.

**Measured, not assumed:** `scripts/poc_srl_events.py` (history in the file's
own docstring — an earlier version compared only against `detect_events()`
in isolation and found a 73% miss rate; that overstated the gap, since
`casemap_service.py` already had two more coverage layers on top of it
(`_events_for_uncovered_dates()`'s `DATED_EVENT` fallback, and
`important_lines.py`'s per-paragraph central-sentence pick). Re-measured
against the FULL real pipeline output, the true gap was **23% of real
event-bearing sentences on actual judgments** (30 event-like sentences
across 3 real testdata documents; 7 were still completely missing — real
facts like "Prabhu was murdered... in May 1972", "Rohitsingh was acquitted
by Madhya Pradesh High Court... in February 1974", "this Court granted
Special Leave... in May 1974").

**Fix:** `casemap_pipeline.detect_events_srl()` (new) reads WHO (nsubj/
nsubjpass), ACTION (root verb lemma), WHAT (dobj/attr/prep-object), and WHEN
(DATE entities) / certainty (MD-tagged modals) directly off `en_core_web_sm`'s
own dependency parse and POS tags — a component already mandatory-loaded by
`extract_entities()` for every document, so this adds **no new model and no
new dependency**. It only fires for a sentence with a real date or modal
that no earlier stage already turned into an event (`covered_spans`, passed
in by the caller in `casemap_service.py`), so it adds coverage without
duplicating existing events. Header/citation furniture is excluded via the
same `_header_exclude_end()` already used for entity extraction (same F-8
failure class: a well-formed parse of "Retrieved: 2026-09-09" is
grammatically valid but meaningless).

**On hardcoding, deliberately:** `EVENT_VERB_LEMMAS` (the new, much smaller
verb-lemma → type map replacing `EVENT_KEYWORDS` for coarse type labeling
only, never for detection) is intentionally not exhaustive. A verb lemma not
in the map does not drop the sentence — it becomes an untyped `FACT` event,
still fully shown with its real WHO/WHAT/WHEN. This is the actual fix for
the original bug class: nothing is silently dropped anymore for not matching
a fixed vocabulary, whether that vocabulary is 6 phrase-types or 50.
`DENIAL_MARKERS`/`ASSERTION_MARKERS` (polarity) and `RHETORICAL_ROLE_CUES`
(Facts/Issues/Ruling role tagging) are the same class of fixed-phrase
hardcoding and were NOT touched this pass — `DENIAL_MARKERS` is a plausible
next candidate (spaCy's `neg` dependency tag covers the same ground without
a phrase list); `RHETORICAL_ROLE_CUES` is a harder, genuinely different
problem (role classification, not fact extraction) and would need an actual
trained classifier, not just more of the parse — see `HANDOFF.md`/
`opennyai_bridge.py:122`'s already-noted unwired rhetorical-role-baseline
seam.

**Verified:** re-ran `scripts/poc_srl_events.py` against all 22
`testdata/*.txt` documents post-integration — 188 event-like sentences
total, 3% ("genuinely new, SRL only") remain, and every one of those
remaining 6 is cause-title/appeal-number boilerplate ("Arising out of
SLP(C) No.11663 of 2019") that the comparison script's own whole-document
scan (no header exclusion) surfaces but the real per-section pipeline
correctly filters — i.e. the real remaining gap is ~0%, not noise the
product will show a user. Full `pytest` suite: 62 passed, 1 skipped, no
regressions.

## F-15 — Consolidated open-items pass: what's genuinely still open vs. what earlier notes only claimed was

**Date:** 2026-09-11
**One-liner:** Owner asked to check on the `en_legal_ner_sm` mandatory-model
status and a flagged `document_profile` bug, then asked for all open items to
be marked down with proper comments. Both checks turned out to already be
resolved; this entry is the resulting sweep of every place in the docs that
called something "open" or "not started," verified directly against current
code rather than trusted at face value.

**Genuinely open (real, unresolved):**

1. ~~**Qwen3-Embedding-0.6B adoption decision.**~~ **Closed, 2026-09-11:
   owner decision is to reject Qwen3-Embedding-0.6B and keep
   all-MiniLM-L6-v2.** Evaluated for real (F-10): Qwen separates same-matter
   document pairs from unrelated ones by roughly double the margin of the
   current default (~0.41 vs. ~0.24 spread, small sample), but F-12 measured
   it at ~112x MiniLM's per-sentence cost on real hardware (32.7s vs 0.29s
   for 50 sentences) with picks that differ from MiniLM's ~40% of the time
   while never being nonsense in spot-checks — a real trade in WHICH valid
   sentence/pair gets surfaced, not a correctness regression MiniLM has and
   Qwen doesn't. Given this pipeline's whole design center (small models,
   CPU-friendly, no heavy weights) the owner's call is to stay on MiniLM;
   `EMBED_MODEL` in `src/casemap_service.py:49` stays
   `"all-MiniLM-L6-v2"`. Not open any further.
2. **Docling is not installed in this project's own `.venv`.** Confirmed
   directly: `import docling` fails there (2026-09-11). It's proven to work
   on real digital + scanned corpora in a *separate* evaluation venv (F-4,
   F-10) but was deliberately never made a `requirements.txt` pin — see that
   file's own header for why (untested combined with the mandatory
   `spacy==3.8.16`/`en_legal_ner_sm` chain). `layout_structure.py` degrades
   to a non-Docling tier without it; this is a known, accepted state, not a
   bug. `run.ps1 -IncludeDocling` (added this session) installs it on
   request.
3. **`important_lines.py` model comparison needs a second real petition.**
   `testdata/`/`real_pdfs/` still have no petition-shaped filing (F-13) — the
   one comparison run exists only against the owner's own BCI petition
   (kept out of the repo entirely, `temp/`-only, never committed).

**Checked and found already resolved (docs said "open," code says otherwise):**

1. **Tier 1's mandatory-NER blocking item** (`STATUS.md`, originally
   2026-09-09) — closed. `en_legal_ner_sm` is installed in this project's own
   `.venv` and wired into `get_ml_nlp()`/`process_document()`
   (`src/casemap_service.py`); every real run this session logged `ml_layer:
   active`. `allow_degraded=True` is a graceful-fallback flag for machines
   without the model, not a sign it's running in practice. See `STATUS.md`'s
   2026-09-11 correction.
2. **`document_profile.extract_parties_layered()` header-furniture bug**
   (`STATUS.md` 2026-09-10, described as "not yet its own requirements
   folder") — already had one the same day:
   `docs/requirements/2026-09-10-party-ladder-header-furniture/` (F-9).
   Verified directly against all 22 `testdata/*.txt` docs plus the ML hybrid
   path with the real model loaded: zero `Author:`/`CITATION`/`CITATOR`
   names leak in as parties.
3. **`docs/requirements/2026-09-09-verbatim-fallback-nodes/`** — its own
   `TRACKER.md` shows T1-T5 all `Done` (2026-09-09/10). An older `STATUS.md`
   line calling it "ready for implementation, neither started" was already
   stale by the time it was written relative to later same-day work; left
   as historical record there (append-only), corrected via a pointer in
   `HANDOFF.md` §7 instead.
4. **`structure-and-embedding-layers` T3** (Qwen via `sentence_transformers`)
   — its own `TRACKER.md` said "Not started"; it was actually run and
   produced the real result in item 1 above. Tracker row corrected in place
   (2026-09-11) since `TRACKER.md` files are living state, not append-only
   history, unlike this register.

**Status:** Open (items 1-3 above are the real remaining work; everything
else in this entry was a documentation correction, not a code change).
**Evidence:** `HANDOFF.md` §7 correction (CHANGELOG 66); `STATUS.md`
2026-09-11 entries; `docs/requirements/2026-09-09-structure-and-embedding-
layers/TRACKER.md`; direct verification commands run this session (`spacy.
load('en_legal_ner_sm')`, `import docling`, `extract_parties_layered()`
against all 22 `testdata/*.txt`).

## F-14 — Full-repo audit: not single-petition (India-specialised); 2 of 4 unused features earned wiring, 2 rejected on evidence; a bare-comma amount bug

**Date:** 2026-09-11
**One-liner:** Deterministic line-by-line audit of all 5787 source lines + the
design-governance docs, then an empirical test of every "unused-but-beneficial"
feature against all 22 `testdata/` docs before wiring anything.

**Petition-generality (the primary question): NOT single-petition.** No specific
party/case-number/date/filename is hardcoded anywhere in `src/` or `server/`.
`document_profile.py` = 7 declarative document profiles + a 5-tier party ladder;
`server/app.py` dispatches PDF/DOCX/TXT and builds a real cross-doc graph. It IS
India-specialised, and that is the honest scope, not a bug: (1) amounts are
Rupee-only (`AMOUNT_PATTERN`, `case_symbols._AMOUNT_NUM` — `$`/`£` never
extracted); (2) the mandatory ML layer is OpenNyAI *Indian* Legal NER; (3)
forum/case-number regexes are Indian; (4) date parsing is DMY-biased. Non-Indian
documents would need work on all four. Several tuning constants
(`EST_CHARS_PER_PAGE=3000`, `_line_bounds` 20–600, `MIN_SENTENCE_CHARS=20`,
`TOP_K_PER_PARAGRAPH=1`, the SaT `2*(ce-cs)+200` guard) were fit to the tested
petitions — reasonable, but the places most likely to behave differently on a
very differently-shaped filing.

**Feature evaluation (measured, then decided — never outcome-selected):**
- **Rhetorical-role labelling — WIRED.** 46 events tagged across 9 of 22 docs;
  distribution FACTS 26 / ARGUMENTS_PETITIONER 12 / ISSUES 4 / ANALYSIS 4.
  Classifier only; verbatim-safe. `_attach_rhetorical_roles` in `server/app.py`.
- **amounts-in-words — WIRED.** `case_symbols.find_word_amounts` (new). Corpus:
  1 real new amount ("rupees one crore", doc 13), 0 false positives.
- **bi-temporal invalidation — REJECTED.** 0 edges invalidated on the connected
  insolvency bundle: structurally needs two edges per node-pair (SUPPORTS +
  POTENTIAL_CONFLICT) the graph never emits; and `persist_edges` → `casemap.db`
  would break the server's no-persistence privacy contract.
- **GLiNER-multi entity extraction — REJECTED.** 218s cold-start, ~6–10× slower
  warm; reintroduces filtered court-name noise (would resurrect the false
  cross-doc edges fixed in CHANGELOG 58); labels don't map to PERSON/ORG/GPE.
  No evidence it links better. spaCy kept as default.

**Bug found + fixed:** `AMOUNT_PATTERN`/`_AMOUNT_NUM` `[\d,]+` matched a bare
comma → "Rs," / "Rs.," surfaced as junk amounts on real docs (04/18/19). Now
`\d[\d,]*` (leading digit required).

**Dead code removed:** `classify_page`'s unused `image_area` (also wrong
geometry); dead `detect_structure`/`segment_document` imports in `poc_run.py`;
`current_role = current_role` no-op; 5 dead CSS rule-sets in `ui/styles.css`.

**Also flagged (owner's call):** `poc_run.py` has drifted far behind the web
pipeline (none of the SaT/uncovered-date/polarity/act-name/entity-gate
improvements exist there); `esc()` in `ui/app.js` doesn't escape `"` though its
output goes into HTML attributes; the drawer highlight no-ops when `s.text` was
boundary-trimmed; three `_trim_*` helpers duplicate one another.

**Update 2026-09-11 (CHANGELOG 63):** two of the four addressed. `esc()` now
escapes `"`/`'`. The poc_run drift is resolved by extracting the pipeline into
`src/casemap_service.py`; `server/app.py` and `poc_run.py` are now thin wrappers
over it (which also collapsed two of the three duplicate `_trim_*` helpers into
one — the JS `smartTruncate` copy remains, intentionally, on the frontend). Still
open: the drawer highlight no-op on boundary-trimmed `s.text`.

**Update 2026-09-11 (CHANGELOG 64):** the last item closed. The drawer's
`<mark>` highlight relied on a literal `String.replace(esc(s.text), ...)`
search inside `s.context` — fragile: silently no-ops whenever `s.text` isn't
an exact substring of `s.context`, and vulnerable to `.replace()`'s
`$`-replacement-pattern syntax. The backend already computes exact offsets
for this (`_attach_context()`'s `context_start`, alongside `char_start`/
`char_end`) but the frontend never read them. New `highlightSpan()` helper
(`ui/app.js`) slices by those offsets, self-verified against the real text
before trusting them, falling back to the old search when they don't line up
(the one real mismatch: `_section_fallback_event`'s `char_end` spans the
whole section while `text` is only its ~400-char boundary-trimmed excerpt).
Verified against real pipeline output (16 event sources, insolvency bundle):
12 now hit the precise offset path, 4 fall back correctly, 0 no-ops. All four
items from this entry's punch list are now resolved.

**Status:** Fixed (audit complete; 2 features wired + tested; 1 bug fixed; docs
synced; dead code removed). Full suite 62 passed / 1 skipped.
**Evidence:** CHANGELOG 62; `tests/test_word_amounts.py`; scratch harnesses
`eval_features.py` / `eval_gliner.py` / `verify_wired.py` (temp, not committed).

## F-13 — HANDOFF §9 petition follow-ups: no second petition in corpus; MiniLM/Qwen still 28/47; official SC form headings missed; petition cause-title parties noisy; multi-page PDF split works

**Date:** 2026-09-10
**One-liner:** Ran the four owner-approved F-12 follow-ups against `testdata/`/`real_pdfs/`, the real filed petition (temp only), and two official Supreme Court e-filing PDFs.

**§9.1 second MiniLM/Qwen document:** `testdata/` and `real_pdfs/` are still all published judgments. The only `ANNEXURE_PATTERN` hits in that corpus are a lone `INDEX` line in `03_matrimonial_sc_rajnesh_v_neha`. No second filed petition exists on disk. Re-ran the F-12 protocol on the same BCI petition: **28/47 (59.6%) same top pick** — identical to F-12. Disagreements remain two real sentences, not garbage. MiniLM default unchanged (needs a dated owner decision).

**§9.2 parties / symbols:** Layered cause-title extraction on the real petition was wrong in three evidenced ways: address/email lines and `PAPER BOOK` treated as parties; respondent 3 `UNIVERSITY GRANTS COMMISSION` dropped because `FORUM_RE` matched bare `commission`; hybrid NER listed `INDEX`/`SYNOPSIS`/`VERSUS`/case citations as parties (F-9 family). `normalize_name` correctly collapses `BAR COUNCIL OF INDIA` / `the Bar Council of India`. After the fix, layered output on the real petition is `[NAME OF PETITIONER]` (redacted placeholder) + BCI/UOI/UGC as respondents; one leftover `BAR COUNCIL OF INDIA & ORS` from later caption text remains. Hybrid is still `ml_role_unstable` (BCI tagged both sides — F-2) and still emits some first-listing/heading fragments; section-label and citation names are gone.

**§9.3 heading variants:** Lettered/parenthetical probes (`A. GROUNDS`, `(vii) GROUNDS`) do **not** appear in testdata, the real petition, or the official forms — pattern left unmatched. Official SC WP/SLP specimen headings that **are** real and were missed: `6. GROUNDS FOR INTERIM RELIEF :`, `7. MAIN PRAYER :`, `8. INTERIM RELIEF :`, `Question(s) of Law`. Those now match. Instructional prose in the same PDFs ("Leave to appeal is sought for on the following grounds.") still correctly does not match.

**§9.4 multi-page PDF:** Digital PDF from the real petition, one heading per page (10 pages) and two headings on the last page (AFFIDAVIT+VAKALATNAMA, offsets 0 and 959): `extract_pages` + `detect_structure` + `_segment_by_headings` recovered all 10 section labels. Pagination is synthetic; body text is the real filing. Not an OCR/scanned-petition test.

**Status:** Partial. Headings (official forms) + layered cause-title + PDF in-page split: fixed and tested. Second-petition MiniLM comparison: blocked on corpus. Hybrid ML list: improved, not clean. Lettered prefixes: not expanded (no real hit).
**Evidence:** `temp/2026-09-10-petition-followups/`, `docs/requirements/2026-09-10-petition-followups/`.

## F-12 — Real filed petition exposed 3 real bugs: `ANNEXURE_PATTERN` missed all numbered headings, `_segment_by_headings()` couldn't split a single-page `.txt` at all, Qwen is ~112x slower than MiniLM on this CPU

**Date:** 2026-09-10
**One-liner:** Owner supplied a real, personal Supreme Court writ petition (a
filed petition, not a published judgment — the first of its kind this project
has ever tested) and asked to run the pipeline against it. Every prior test
document (`testdata/`, `real_pdfs/`) was a published judgment; none had a real
Prayer/Grounds section, so this gap had never been exercised for real before.

**Bug 1 — `ANNEXURE_PATTERN` only matched a bare heading word.** Real
petitions number these sections (`VII. GROUNDS`, `XI. INTERIM PRAYER`,
`XII. FINAL PRAYER`) — the pattern matched none of them. Fixed: optional
roman-numeral/numeric prefix, PRAYER qualifiers (INTERIM/FINAL/ADDITIONAL),
`LIST OF DATES AND EVENTS` variant. `testdata/`'s one existing match (`INDEX`)
unchanged. 5 tests, `tests/test_annexure_pattern_numbered_headings.py`.

**Bug 2 — deeper, structural: `_segment_by_headings()` only created a section
boundary per PAGE, never within one.** A `.txt` input loads its entire filing
as a single page, so even after Bug 1 was fixed, all 10 real headings on this
petition's one "page" collapsed into a single section (labeled after
whichever heading happened to be first — every `important_lines` node showed
section `[INDEX]`, regardless of whether it actually came from GROUNDS or
PRAYER). Fixed by giving each detected heading a character offset
(`detect_structure()`) and having `_segment_by_headings()` slice a page's text
into one sub-page per heading when a page has more than one (same
`page_number`, correct provenance preserved) — real PDF documents (Docling
headings, one per physical page, no offset key) are unaffected; verified
directly: `VII. GROUNDS` is now its own 15,805-char section, cleanly separate
from `XI. INTERIM PRAYER` (987 chars) and the rest. 3 tests,
`tests/test_multi_heading_single_page_segmentation.py`.

**Bug 3 — speed, real numbers not estimates.** The petition (293 eligible
`important_lines` sentences, before the segmentation fix) took 1131s end to
end. Diagnosed directly: Qwen3-Embedding-0.6B encodes 50 short sentences in
32.7s on this CPU vs all-MiniLM-L6-v2's 0.29s — a ~112x gap, roughly tracking
the 27x parameter-count difference (600M vs 22M). `important_lines.py`'s
embedding calls were already batched per-section this session (2.26x real
measured speedup, 771s vs 1745s on a 17-paragraph test) — real, but nowhere
near enough alone. **Tested whether MiniLM can safely replace Qwen as the
default: it cannot, not yet** — MiniLM picked a different top sentence than
Qwen in 4 of 6 real eligible paragraphs before the Bug-2 fix, likely
confounded by those paragraphs being abnormally large blended blobs (Bug 2's
fault, not necessarily the model's). Re-testing model agreement on the
now-correctly-segmented sections is the natural next step, not done this
session — owner explicitly chose to fix Bug 2 first (the correctness issue)
over either speed workaround.

**Status:** Fixed/Implemented. Bugs 1 and 2 fixed and tested. Bug 3 (speed):
owner's dated decision (CHANGELOG (38)) — re-tested Qwen vs MiniLM agreement
on the fixed segmentation (28/47, 60% same top pick; spot-checked
disagreements as consistently real/substantive either way, not a correctness
regression) and switched `important_lines.py`'s default to MiniLM given the
measured 112x speed gap. Real re-confirmation: same petition, 1131s → 16.5s,
same output shape. Multiprocessing-across-documents not attempted (not
needed once per-document runtime dropped this far). `real_petition/` content
not committed to the repo (personal document); processed only in
`temp/2026-09-10-real-petition-run/`.

## F-11 — Extractive (embedding-centrality) "important lines" beats every generative summarizer tested, on accuracy and on zero-new-dependency simplicity

**Date:** 2026-09-10
**One-liner:** Owner asked to test "important lines, not rewritten paragraphs" for
long sections (e.g. a 50-page Grounds section) — the idea being that a long
paragraph's key facts should become graph nodes without any generative rewriting.
Tested 5 approaches head-to-head against the same real 303-word paragraph
(`testdata/15_rentcontrol_madrashc_krishnasamy_v_kannika.txt`'s longest paragraph —
real lease dates, rent amounts, notice dates), CPU-only, in
`temp/2026-09-10-docling-qwen-poc/poc_important_lines.py` +
`poc_more_models.py`/`poc_pegasus_only.py`:

| method | size | time (CPU, incl. load) | verbatim% | accuracy |
|---|---|---|---|---|
| **Qwen3-Embedding centrality ranking (extractive, no generation)** | 0.6B embed-only | ~35s | 100% (real sentences, by construction) | perfect — every date/amount exact, real char offsets preserved |
| flan-t5-small (prompted "extract, don't rewrite") | 80M | ~3s | trivial 100% | **garbage** — collapsed to a single word, `'Court'` |
| t5-small (`"summarize: "` prefix, its native task format) | 60M | ~200s | 0% (full paraphrase) | **wrong** — hallucinated `05.01.1982` for a real date of `05.02.1982` |
| sshleifer/distilbart-cnn-6-6 (abstractive) | 230M | ~67s | 33% | accurate, no errors observed, real compression |
| nsi319/legal-pegasus (abstractive, US-SEC-litigation-tuned) | 568M | ~174-258s | 80% | accurate, mostly copies real sentences, slowest by far |

**The extractive approach — sentence-split a section, embed each sentence with
Qwen3-Embedding (Apache-2.0), rank by average similarity to every other sentence in
the section (TextRank-lite centrality), keep the top-K in original order — won on
every axis that matters here:** zero hallucination (it never generates text, only
selects real sentences), fast enough, and each kept sentence already carries a real
char offset back into the source, so it drops directly into the same
`sources: [{"document","page","char_start","char_end","text"}]` shape
`build_evidence_card()` already produces (`casemap_pipeline.py:936`) — meaning each
kept line can become a graph node the same way today's event nodes do, no new node
schema needed.

**Both tiny generative models were actively bad, not just mediocre** — this is useful
negative evidence against reaching for a small instruction-tuned or `"summarize:"`-
prefix model at this size for legal text: flan-t5-small produced a degenerate
one-word output, t5-small silently changed a real date. For legal use, a wrong date
is worse than no summary at all.

**Addendum 2026-09-10 (later):** owner asked whether a faster *and* accurate
generative option exists. Tested 3 more on the same paragraph, checking each output
sentence-by-sentence against the source (not just the verbatim% metric, which can't
catch a fluent-sounding but wrong claim):

| method | time | real accuracy issue found |
|---|---|---|
| legal-pegasus, greedy decoding (`num_beams=1`, faster) | 18.8s | **worse, not just faster** — wrote "The petitions were dismissed on 25.01.1999," but the source says the petitions were *allowed* on 14.11.1997 and it was the *appeals against them* that were dismissed on 25.01.1999. Greedy decoding introduced a real procedural-outcome error beam search (F-11's original legal-pegasus run) did not make. |
| distilbart-cnn-12-6 (306M, larger sibling of the 6-6 tested above) | 112.0s | same June-to-December-1994 default-period conflation as the 6-6 variant; slower, not more accurate. |
| Falconsai/text_summarization (60M, t5-small actually fine-tuned for summarization) | 139.8s | same June-to-December-1994 conflation again; also truncated mid-word. |

**The same distortion — merging "default started June 1994" with a separate later
sentence "arrears paid June to December 1994" into one false claim about the default
period — now appears independently across 3 differently-trained abstractive models**
(distilbart-6-6, distilbart-12-6, Falconsai/text_summarization). That is a strong
signal the paragraph itself contains an easy trap for any generic sentence-fusion
behavior, not a one-model quirk — reinforcing that abstractive rewriting is the wrong
tool class here regardless of which specific model is chosen. No generative
candidate tested (5 models, 2 configurations) was both faster than, and as accurate
as, the Qwen extractive approach; the fastest one (greedy pegasus) was the least
accurate of all.

**Status:** Fixed/Implemented (2026-09-10, later) — owner gave the dated go-ahead
("ok lets do this and complete backend end to end") and it's shipped:
`src/important_lines.py` + wired into `scripts/poc_run.py` behind an opt-in
`--important-lines` flag (off by default, same "optional heavy dependency"
contract as `make_similarity_fn()` — degrades to a no-ML deterministic-density
scorer if `sentence-transformers` isn't installed, backend name recorded on every
node so a run can be audited for which one actually ran). Real ranking backend
is the F-11-validated Qwen3-Embedding centrality method; a hybrid Docling+Qwen POC
(`temp/2026-09-10-docling-qwen-poc/poc_hybrid_lexrank.py`) additionally confirmed
proper LexRank (power-iteration centrality, not just mean-similarity) picks the
*same* top sentence as the simpler method on 2 real documents — no reason to prefer
the heavier algorithm.

**3 more real bugs found and fixed while wiring this against the actual 22-document
corpus** (not just the single test paragraph): (1) `"Rs."` before an amount was
treated as a sentence boundary, keeping fragments like `'...started to pay Rs.'`;
(2) name initials (`"Y.V. Chandrachud"`, judge suffix `"J."`) split mid-name for the
same reason; (3) even after both fixes, bare paragraph numbers / uncaught
abbreviations (`'2.'`, `'U.P.'`, `'I.K.'`) still got kept as standalone fake
"sentences" — **18 of 85 kept nodes (21%) in the first full 22-document run were
fragments like this.** Fixed with a general `MIN_SENTENCE_CHARS` merge-forward pass
(`important_lines.py`'s `_merge_short_spans`) rather than trying to enumerate every
abbreviation — re-run after the fix: 0 of 52 nodes were short fragments. A related
near-miss caught in review before shipping: merging split pieces back together by
rejoining stripped text with a literal `" "` would have silently stopped being
verbatim the moment a real separator was a newline/tab (common in PDF-extracted
text) — fixed by working with (start, end) spans into the original text throughout,
never reconstructing strings, so every kept sentence is a byte-verbatim slice by
construction, not just by convention. 11 tests, `tests/test_important_lines.py`,
all against real `testdata/` content. Node schema: `IMPORTANT_LINE` events use the
exact same shape `detect_events()` already produces (flows through
`to_react_flow()`/`build_evidence_card()` unchanged), with one addition —
`sources[0].paragraph`, a running paragraph counter threaded across a document's
sections — plus a one-line `to_react_flow()` change so an event can carry an
explicit `label` (previously every non-amount event showed the same generic
`"Key Fact"`-style title; now each `IMPORTANT_LINE` node shows its own real text).
Real end-to-end run (`poc_run.py testdata --important-lines`): 52 IMPORTANT_LINE
nodes across 22 real documents, 0 fragments, every node carrying real
document/page/paragraph provenance. Output:
`temp/2026-09-10-important-lines-e2e/`.

## F-10 — Docling proven on the real corpus (digital + OCR'd scans); Qwen3-Embedding separates same-matter docs better than MiniLM in a small test; `make_similarity_fn()` has a real model-switch cache bug

**Date:** 2026-09-10
**One-liner:** Owner asked for a real POC of Docling and Qwen3-Embedding "how they
can produce results," since T3 (Qwen) was never run and Docling had only ever been
exercised on a small F-4 test, not the full real corpus. Ran both for real in a fresh
`temp/2026-09-10-docling-qwen-poc/venv_docling_qwen` (docling==2.126.0 +
sentence-transformers, never combined with `requirements.txt`'s spaCy chain, per
`requirements-docling.txt`'s own warning).

**Docling — real result, not a claim:** ran `detect_structure_layered()` against 4
real `real_pdfs/` documents (2 digital, 2 genuinely scanned/degraded). All 4 returned
`docling_layout` / `high` confidence, with correct real headings extracted — e.g. on
the scanned `21_insolvency_nclat_khursheed_anwar_...pdf`: `'NATIONAL COMPANY LAW
APPELLATE TRIBUNAL'`, `'IN THE MATTER OF:'`, `'ORDER'`, plus the real case title (with
one OCR-typical missing-space artifact: "AnwarAnd"). Docling's bundled RapidOCR
handled the scanned PDFs itself, no separate OCR step needed. This is the first time
Docling has been run against this project's genuinely-scanned real documents, not just
a small F-4 test set.

**Qwen3-Embedding-0.6B — loads and runs via `sentence_transformers`, T3's open
question is now answered:** using `casemap_pipeline.make_similarity_fn("Qwen/Qwen3-
Embedding-0.6B")` against real `testdata/` excerpts (21 vs 22 = genuine same-matter
NCLAT-order-then-SC-appeal pair; 21 vs 03, 09 vs 05 = unrelated pairs):

| model | same-matter (21 vs 22) | unrelated (21 vs 03) | unrelated (09 vs 05) | spread |
|---|---|---|---|---|
| all-MiniLM-L6-v2 (current default) | 0.8656 | 0.6234 | 0.6189 | ~0.24 |
| Qwen/Qwen3-Embedding-0.6B | 0.8177 | 0.4048 | 0.4985 | ~0.41 |

Qwen separates same-matter from unrelated pairs by a wider margin in this small test —
a real, if small-sample, signal in favor of the upgrade path `make_similarity_fn()`'s
own docstring already names. Still evaluation-only; no default changed (HANDOFF §9
requires a dated owner decision before that).

**Real bug found while running this, fixed 2026-09-10 (CHANGELOG entry 40):**
`make_similarity_fn()`'s module-level `_EMBED` and `_EMBED_CACHE` globals in
`src/casemap_pipeline.py` were not keyed by `model_name`. Calling it with two
different model names inside the same process silently reused the first
model's loaded weights and cached embeddings for the second — confirmed by a
second "Qwen" run returning bit-identical scores to MiniLM in 0.0s (no load,
all cache hits). Not a problem for the pipeline's actual usage (one model per
process today), but would have silently corrupted results the moment two
`make_similarity_fn()` calls with different `model_name` coexisted in one
process (e.g. an A/B eval script). Fixed: `_EMBED_MODELS: dict[str, model]`
and `_EMBED_CACHE: dict[(model_name, text), embedding]`, both keyed by
`model_name`. 1 new test, `tests/test_similarity_fn_model_cache_key.py`.

**Status:** Fixed (cache-key bug). Qwen T3 evaluation still has a real result
(above) but adopting it as the pipeline's default similarity model still
needs a dated owner decision per `HANDOFF.md` §10 — that part remains open.

## F-9 — `extract_parties_layered()` treated indiankanoon caption furniture as parties

**Date:** 2026-09-10
**One-liner:** The regex party ladder listed `"Author: Y.V. Chandrachud"` as
Petitioner and `"CITATION"` as Respondent on real `testdata/` (CHANGELOG 26).
Same family as F-8 (metadata fed to an extractor meant for names) but **not**
the same fix: skipping `extract_cause_title_block` would drop real litigants.
**Decision:** Implemented — furniture/section-label guards + fall-through if a
tier's only hits were furniture; hybrid ML output filtered the same way.
**Status:** Fixed (2026-09-10). Evidence: `tests/test_party_ladder_header_furniture.py`
(22-doc sweep), `docs/requirements/2026-09-10-party-ladder-header-furniture/`.

## F-8 — Dense fact-node coverage achievable with zero new dependencies; found a real bug in extract_entities() that affects the pipeline today

**Date:** 2026-09-10
**One-liner:** Owner clarified the actual goal (multiple documents, multiple details,
connected on a timeline, click a node for a summary) — closer to
`casemap_pipeline.py`'s existing design than F-7's rhetorical-role path. Found
`build_evidence_card()` (the "click for summary" feature) and dense
`extract_deterministic()` output already exist and were unused. A POC emitting a node
per deterministic fact (not just `detect_events()`'s narrow keyword hits) took node
count from 7 to 67 across 6 real documents — using only already-existing extraction
functions. Along the way found two real bugs: (1) a POC-wiring mistake — calling
`normalize_entities()` per-document instead of once globally caused coincidental ID
collisions that falsely connected two completely unrelated cases (fixed in the POC);
(2) **a real bug in the already-existing `extract_entities()`**, not a POC artifact —
generic spaCy NER (`en_core_web_sm`) mislabels `"VERSUS"` (present in every Indian
judgment's cause title) as `ORG` and `"Order"` as `PERSON`, making them universal
false cross-document connectors. This affects the real pipeline today, not just this
POC. After both fixes, cross-document edges dropped from 74 (mostly false) to 24 (22
correct, 2 residual noise not yet diagnosed). The 3-document bundle's dated nodes
formed a correct real timeline (2023→2025→2025, matching the actual procedural
history), and `build_evidence_card()` produced real, correct click-for-summary output.
**Decision:** Not adopted — POC only, but more promising than F-7 (zero new
classification logic needed, just found and fixed real bugs). The `extract_entities()`
generic-NER bug should be tracked as a real defect independent of whether this
dense-node direction is formalized — it affects any real multi-document run today.
**Full evidence:** `temp/2026-09-10-fact-nodes-poc/POC_NOTES.md` (script + raw output
in the same folder).
**Addendum (same day, full 22-document validation) — the 6-document sample was too
small to reveal the real scope:** re-ran against all 22 `testdata/` documents.
227 nodes total (1-21/doc). Cross-document edges: **60 false vs. only 10 correct** —
far worse than the earlier 6-doc read (22 correct/2 noise). Catalogued every entity
shared across 2+ documents (28 total) — only 7 are genuine (all within the real
09/21/22 bundle); the other 20 fall into three distinct root causes, not one:
(1) **generic institutional/procedural nouns** near-universal in Indian legal writing
(`Court`, `High Court`, `Justice`, `Versus`, `Order`, `Notice`, `Adv`, `SLP`, `Anr`,
`Union Of India` — the last because it's the near-universal respondent name in
government cases, not because of any real connection); (2) **malformed multi-line
entity extraction** — generic spaCy NER sometimes grabs an entire header block
(`"THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION\nCIVIL APPEAL"`) as one
entity, because header/cause-title regions aren't ordinary prose and the codebase's
existing header-region logic (`document_profile.extract_cause_title_block`) is never
consulted before running generic NER over that text; (3) **truncated fragments**
(`"Appellant(s"`, `"R. Subhash"`, `"PRINCIPAL"`, `"C.A. No"`) likely from the same
formatting confusing spaCy's tokenizer at line-wrap boundaries. A hand-maintained
stoplist (what this POC used) only ever chases category (1) — categories (2) and (3)
need an architectural fix: skip or specially handle the header/party-block region
(already identifiable via existing code) before running generic entity extraction on
it. **Do not read the original 6-doc result as representative — the 22-doc run is the
honest baseline.**
**Fix applied (2026-09-10, first pass):** header-noise T1–T4 — skip versus-block
interior + stoplist + newline spans. False **60→24**, correct bundle **10→14**.
**Fix applied (2026-09-10, second pass):** the leftover 24 were all preamble
connectors (`THE SUPREME COURT OF INDIA`, `AIR 20xx SUPREME COURT`, `R. Subhash`).
NER now skips `[0, cause-title-end)` plus furniture lines; reporter citations are
dropped. 22-doc re-run: **false 24→0**, correct bundle **14→16**. Evidence:
`temp/2026-09-10-header-noise-fix/t4_after_preamble.json`,
`docs/requirements/2026-09-10-residual-false-edges/`.
**Status (2026-09-10):** the `extract_entities()` preamble/header defect is closed
on the 22-doc protocol (false 0). The dense fact-node *product* path is still
not adopted.

## F-7 — Deterministic rhetorical-role cue tagging: works when cues match, breaks two concrete ways when they don't

**Date:** 2026-09-10
**One-liner:** POC for `docs/requirements/2026-09-10-rhetorical-role-cues/` (a
zero-dependency, `detect_events()`-style keyword-cue alternative to the blocked
`opennyai` classifier from F-6) ran against 4 real documents. One (doc 21) produced a
correct role sequence (Arguments→Analysis) — real evidence the mechanism works. Two
failures found: (1) a too-generic cue phrase ("in the case of," meant to catch
precedent citations, also matches ordinary prose like "in the case of Rohitsingh")
caused a false-positive match that then poisoned every subsequent paragraph via the
carry-forward logic, since there is no re-confirmation step; (2) exact substring
matching missed real wording variation ("facts of this case" vs. the cue table's
"facts of the case") — the same class of problem `is_versus_line()`'s rapidfuzz
fallback already solves elsewhere in this codebase, not yet applied here.
**Decision:** Two fixes applied 2026-09-10 then re-checked on real `testdata/`:
(1) removed `"in the case of"`; PRECEDENT no longer carries forward;
(2) longer cues use `rapidfuzz.partial_ratio` (same class as `is_versus_line()`),
plus an explicit `"facts of this case"` cue. Landed in `src/rhetorical_roles.py`.
Heuristic confidence only (`cue_matched` / `carried_forward` / `untagged`).
**Status:** Implemented (not a trained-model replacement). Tests:
`tests/test_rhetorical_roles.py`.
**Full evidence:** `docs/requirements/2026-09-10-rhetorical-role-cues/POC_RESULTS.md`
(script + raw output in `temp/2026-09-10-rhetorical-role-cue-poc/`).

## F-6 — opennyai's Rhetorical_Role component has a real API now, but is not installable on this Windows/Python 3.11 machine

**Date:** 2026-09-09
**One-liner:** Owner asked for a "full tree" breakdown of a document (prayers, issues,
facts, arguments, law, ruling) — this maps to OpenNyAI's rhetorical-role classifier
(13 sentence-level roles: Facts, Issues, Arguments, Precedent Analysis, Ratio,
Ruling, etc.), which `opennyai_bridge.py`'s `load_rhetorical_role_model()` stub has
always raised on, citing "no confirmed simple load API." Research this session found
that's now outdated: the `opennyai` PyPI package (v0.0.13) documents a real
`Pipeline(components=['Rhetorical_Role'])` API. Installing it fails on this machine —
it pulls in `pytorch-transformers` (unmaintained since ~2019), which needs an old Rust
`tokenizers` crate built from source. Installed a full Rust toolchain via winget to
unblock this; it still fails, because the old crate's code doesn't compile against a
modern Rust compiler (lifetime-elision rules tightened since the crate was written).
**Decision:** Abandoned mid-fix, not because the Rust wall was unfixable (an old
pinned toolchain, ~1.50.0, was actually installed and a retry was in progress) but
because the owner correctly pointed out this was solving the wrong problem: the
project already has a working heading detector with the exact right vocabulary — see
the addendum below — and pursuing a heavy, unmaintained ML dependency chain for
document-tree structure wasn't necessary.
**Addendum (same session, immediately after):** Tested the *existing*
`ANNEXURE_PATTERN` regex in `casemap_pipeline.py` (line 325) — it already matches
standalone `PRAYER`, `GROUNDS`, `QUESTIONS OF LAW`, `SYNOPSIS`, `LIST OF DATES`,
`MEMO OF PARTIES`, `INDEX` heading lines, exactly the "full tree" vocabulary asked
for. Ran it against several `testdata/` documents — zero headings matched, **not
because the tool is broken**: `testdata/` is entirely published court *judgments*
(from indiankanoon), which narrate these things in prose, never the original *filed
petitions* parties submit, which is where standalone `PRAYER`/`GROUNDS` heading lines
actually appear. The real gap is test-data shape (petitions/pleadings, not judgments),
not a missing tool — likely exactly what the still-absent `real_docs`/`real_pdfs`
corpus (flagged since governance init, `HANDOFF.md` §6) was originally for.
**Full evidence:** this session's install logs, `temp/2026-09-09-rhetorical-role-poc/`
(abandoned, no working venv); the `ANNEXURE_PATTERN` re-test used the working
`temp/2026-09-09-mini-llm-poc/venv_ner/` inline, no new files saved.



## F-5 — Owner: no server retention of uploads; results live on the client

**Date:** 2026-09-09
**One-liner:** Owner instructed that multi-document upload is processed, the
processed payload is returned to the user's system for local viewing/storage, and
PDFs are deleted afterward — the server must not keep case data after the run.
**Decision:** Recorded as a new requirement folder (not a widening of the
verbatim-fallback-nodes work). FastAPI/UI implementation is **not** started this
session (`HEART.md` tier 3 still blocked on proven tier 1). Cookies are rejected as
the graph store (too small); IndexedDB or a JSON download is the design. Citable as
`docs/spec/ARCHITECTURE.md` G4 and `docs/spec/SCOPE.md` amendment 2026-09-09.
**Full evidence:** `docs/requirements/2026-09-09-ephemeral-client-results/`.

## F-4 — Docling + Qwen3-Embedding compose correctly through the real graph pipeline (small test, digital PDFs only)

**Date:** 2026-09-09
**One-liner:** Tested Docling (structure detection, addressing the missing
`layout_structure.py`) and `qwen3-embedding:0.6b` (semantic similarity, dropped into
`casemap_pipeline.score_pair`'s existing `similarity_fn` seam) together, not in
isolation, against 4 documents (the 09/21/22 connected bundle + an unrelated
distractor), rendered to real PDFs with a genuine font hierarchy. Result: the 3
connected documents all linked to each other (scores 0.30-0.62), the unrelated
document never crossed the edge threshold despite moderate raw semantic similarity —
`score_pair`'s existing entity+semantic weighting correctly prevented a false
connection. Docling's layout labelling (`section_header`/`text`/`list_item`) was
correct on all 4 documents; cost was 90.8s first-run (model download) then 1.6-8.3s
per document after.
**Decision:** Not adopted — POC only. Real value demonstrated for recovering missing
structure-detection capability and for a semantic-similarity upgrade. Follow-up
(same day): Docling was re-tested against 2 genuinely rasterized-and-degraded PDFs
(real rotation/blur/noise, zero embedded text layer, forcing actual OCR) — structure
detection (headings, list items) survived correctly, at real cost (12-18s/doc vs.
1.6-8s on the text-layer path) and with real OCR word-boundary damage (dropped
spaces) that any consumer of this output needs OCR-tolerant matching for, same as the
project's existing `is_versus_line()` discipline. MinerU's dependency footprint was
checked (not actually lighter than Docling — its `pipeline`/`vlm` extras both need
`torch`/`transformers`, `vlm` needs a full VLM) but no conversion run was done, so no
head-to-head result exists yet.
**Full evidence:** `docs/research/new-directions/layer-additions-assessment.md`
**Status (2026-09-10):** structure T2 implemented as optional
`src/layout_structure.py` (degrades without Docling). Still **not** a permanent
`requirements.txt` pin (HANDOFF §9). Qwen ST-path (T3) not yet run.
(scripts + raw output in `temp/2026-09-09-layer-additions-poc/`).

## F-3 — Fallback-node POC: mechanism + edge formation both validated, conditional on entity normalization; regex-ladder trigger still unexercised

**Date:** 2026-09-09
**One-liner:** POC for `docs/requirements/2026-09-09-verbatim-fallback-nodes/` ran the
real `extract_parties_layered()` against 22 `testdata/` docs (20 originals + a
genuinely connected 3-document insolvency bundle: docs 09/21/22, same Corporate
Debtor and RP, doc 22 explicitly cites doc 21's order by date and case number). Zero
of the 22 landed on the regex ladder's tier 4.5/5 fallback (clean input — that tier is
for OCR damage, which nothing here has); 4/22 needed a fallback node under the
mandatory-ML role-instability trigger (F-2). Those events, in the real `events[i]`
shape, flowed through `casemap_pipeline`'s unmodified graph functions with zero
special-casing. A follow-up forced test (fallback-shaped nodes built from the 3
connected documents regardless of trigger, to isolate the scoring question) got a real
edge between docs 09 and 21 via a shared name, and correctly did **not** connect an
unrelated negative-control document — but did **not** connect doc 22, because its
header writes the same name in ALL CAPS, an exact-string mismatch that
`casemap_pipeline.normalize_entities()` (already in the codebase, BUG-5/7 fix) exists
to solve and this POC didn't call.
**Decision:** Mechanism and edge-formation are both validated, conditionally: real
implementation must call `normalize_entities()` on fallback-node entities before
scoring — now a stated requirement in `DESIGN.md`, not an afterthought. The
regex-ladder half of the trigger condition (tier 4.5/5) remains unexercised by any
document currently available — needs OCR-damaged input or `real_pdfs/` (still absent,
`HANDOFF.md` §6) before that half is called proven too.
**Full evidence:** `docs/requirements/2026-09-09-verbatim-fallback-nodes/POC_RESULTS.md`
(scripts + raw output in `temp/2026-09-09-verbatim-fallback-poc/`).

## F-2 — Mandatory model (`en_legal_ner_sm`) installed and run against real documents for the first time; confirms why Layer 2 role-refinement is mandatory

**Date:** 2026-09-09
**One-liner:** `en_legal_ner_sm` (OpenNyAI's mandatory NER model) was installed and run
against the same 20 real documents — first time ever in this project's history (see
`HANDOFF.md` §8 item 1). It ran ~350x faster than the small generative LLM tested as
F-1 (0.06s/doc vs ~21s/doc), never failed to terminate, and its output is
verbatim-by-construction (char-offset spans, invention structurally impossible). But
its raw PETITIONER/RESPONDENT/JUDGE/COURT labels have real noise — role confusion on
repeated mentions of the same person, lawyers mislabeled as parties or judges, statute
abbreviations mislabeled as courts (~3.6% of role-tagged spans on a crude check).
**Decision:** Not a fix, not an open bug — this is the first real evidence for *why*
`docs/spec/ARCHITECTURE.md` §1 stage [2] already mandates a second, deterministic
role-refinement layer on top of this model's raw output rather than trusting it
directly. Confirms the existing two-layer design; does not change it.
**Full evidence:** `docs/research/new-directions/mini-llm-extraction-assessment.md`
Part 2 (script, raw output, and a working install recipe/venv in
`temp/2026-09-09-mini-llm-poc/`).

## F-1 — Small generative LLM: no hallucinated-fact failures found, but a non-termination failure mode does

**Date:** 2026-09-09
**One-liner:** A zero-shot small local LLM (Qwen2.5 1.5B) run against 20 real Indian
judgments for party/date/amount extraction kept party names 95%+ verbatim and never
produced a confidently-wrong short answer — but on 1 of 20 documents it entered a
degenerate repetition loop and never terminated with valid output, and on 1 of 20 it
misread page furniture (`$~5`, a routine cause-list marker) as a dollar amount.
**Decision:** Not a fix — this is evidence for the standing `FORBIDDEN.md` §C /
`THESIS.md` no-generative-LLM-in-the-core rule, not a proposal to change it. The
non-termination failure mode is new information worth keeping: it is a structural risk
a deterministic fallback ladder cannot exhibit, and would need to weigh into any future
owner-reserved decision to reconsider generative models near this pipeline.
**Full evidence:** `docs/research/new-directions/mini-llm-extraction-assessment.md`
(script + raw output in `temp/2026-09-09-mini-llm-poc/`).

---

The pre-governance project already has its own complete 26-bug ledger and open-gaps list — see
`docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §4 (bug ledger, all fixed and verified) and §7 (9 open gaps,
ordered by value, not yet transcribed here). Transcribing the top open gap (installing
and verifying the real OpenNyAI model) into this register as the first entry is a good
next task under this governance system.
