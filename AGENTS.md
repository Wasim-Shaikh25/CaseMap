# Agent Rules

Binding rules for anyone — human or AI — making changes in `CaseMap`. Not
suggestions; follow them in order. This project depends on external code (OpenNyAI
`en_legal_ner_sm`/`trf` pipelines, spaCy, PyMuPDF, PaddleOCR/Surya/Tesseract, rapidfuzz,
dateparser, sentence-transformers) — record any new external dependency taken on in
`CHANGELOG.md` when added.

## 1. Read ALL governance files and the handoff before doing anything

**This is not optional and applies to every session, every agent, every change — however
small.**

**Step 1 — governance (binding rules):**

1. `FORBIDDEN.md` — the mistakes we will never repeat; if a change does any of them it is
   wrong no matter how good it looks
2. `AGENTS.md` (this file) — the rules
3. `THESIS.md` — why this exists, the laws
4. `HEART.md` — what we want, the build tiers
5. `docs/spec/SCOPE.md` — the boundary: what is in scope and what is forever out
6. `docs/spec/ARCHITECTURE.md` — the build spec and its guardrails

**Step 2 — handoff and current state (mandatory, not optional):**

7. `HANDOFF.md` — the single orientation document: current state, every open finding
   with its fix, the ordered work queue, known traps, and decisions reserved for the
   project owner
8. `STATUS.md` — confirm what is actually built before assuming anything
9. `FINDINGS.md` — open findings with a one-liner, fix, and link to full evidence; know
   what is broken/known before adding to it
10. `CHANGELOG.md` — the append-only history; read the last few entries so you do not
    redo or contradict recent work

**Step 3 — reference (read the relevant ones for your task):**

- `README.md` — the project's public front page; keep it true if you change what the
  project does
- `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` — the pre-governance project handoff: architecture, full
  26-bug ledger, real-document dry-run results, open gaps. This is the deepest technical
  context available and is still authoritative for implementation detail; `HANDOFF.md`
  (this governance system's handoff) points back to it rather than repeating it.
- `docs/research/existing-approach/CaseMap_Mandatory_ML_Layer_v7.md` — most current detail on the mandatory OpenNyAI NER
  layer specifically
- `docs/research/existing-approach/poc_report.md` — the most recent POC run's output, useful as a "what does a run
  actually look like" reference
- other files under `docs/spec/` relevant to your task

**Do not write a single line of code, propose a change, run a script, or make any change
until steps 1 and 2 are complete.**

**Self-check before your first change — you must be able to answer these:**

1. What does `FORBIDDEN.md` prohibit that is nearest to what I am about to do?
2. Which open item in `FINDINGS.md`/`HANDOFF.md` does my change touch, and is it
   owner-reserved?
3. If my change touches OCR, structure detection, or party extraction: have I checked the
   26-bug ledger (`docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §4) for a documented reason before assuming
   something is a bug?

If you cannot answer these, you have not finished step 1 or 2. Nothing here is
machine-enforced — the rules bind because you read them, not because a test catches you.

## 2. Scope guard — never widen without an explicit, dated owner decision

No LLM (generative model) may ever generate, paraphrase, or infer party names, dates,
amounts, provisions, events, or graph edges in the extraction/graph core — only select
verbatim spans that validate against source text with char offsets. See `docs/spec/SCOPE.md`.

## 3. The only score is the one stated in THESIS.md — never a flattering proxy

For this project that means: real documents (`real_docs/`, `real_pdfs/`) are the only
valid test oracle, and a confidently-wrong result is always worse than an honest
low-confidence one. Never report a fix as proven on synthetic tests alone — see
`FORBIDDEN.md` §E.

## 4. Build tiers in order — never optimise before the previous tier is proven

See `HEART.md` for the ordered build tiers. Never build tier N+1 for a piece of work
whose tier-N result is not yet proven/shipped. Concretely: do not build the React Flow UI
or PDF.js viewer work ahead of the mandatory ML layer actually being installed and
verified against real weights (see `HANDOFF.md` §8, item 1).

## 5. Changelog, status, and findings discipline

**Every finding must be written down before the session ends:**

1. `FINDINGS.md` (root) — one entry with: one-line description, fix or decision
   required, link to the full evidence if there is one. A finding that exists only in a
   report, temp file, or session note is **not recorded**.

**Changelog and status:** `CHANGELOG.md` is **append-only** — never renumber or
retro-edit an existing entry; if two entries collide on a number, suffix the later one.
Append an entry and update `STATUS.md` as part of the same change.

**Dated records are never rewritten.** Documents under `docs/audit/` and `docs/research/`
are records of what was true when written. When a later result supersedes one, it gets a
banner naming its successor — the original text stands.

## 6. Spec-driven workflow

For each unit of work: `docs/requirements/<YYYY-MM-DD>-<slug>/` with `REQUIREMENTS.md` +
`DESIGN.md` before code, then `TASKS.md` + `TRACKER.md` ticked live. Never retroactively
widen an old requirement folder.

## 7. One git root; ephemeral artifacts in `temp/`

Keep a single git root. One-off dumps/scratch go under `temp/`, never mixed into the
project source. (This project is not yet a git repo as of governance init — see
`HANDOFF.md` §2.)

## 8. Stay standalone

This project depends on external code (OpenNyAI `en_legal_ner_sm`/`trf` pipelines,
spaCy, PyMuPDF, PaddleOCR/Surya/Tesseract, rapidfuzz, dateparser,
sentence-transformers) — record any new external dependency taken on in `CHANGELOG.md`
when added.

## 9. Folder map

```
ROOT
  FORBIDDEN.md AGENTS.md THESIS.md HEART.md   <- governance (step 1)
  HANDOFF.md STATUS.md FINDINGS.md CHANGELOG.md <- current state (step 2)
  README.md                                   <- public front page
  requirements.txt                            <- core pipeline deps; see the file's own
                                                  header for which pins are verified vs
                                                  carried over unverified
  requirements-docling.txt                    <- OPTIONAL, heavy — only for the
                                                  structure-and-embedding-layers work
src/
  casemap_pipeline.py document_profile.py
  opennyai_bridge.py layout_structure.py      <- core pipeline library code (flat
                                                  siblings, no package __init__.py yet;
                                                  layout_structure optionally imports Docling)
scripts/
  poc_run.py                                  <- POC/CLI runner, not library code —
                                                  imports src/ via a sys.path bootstrap
docs/
  spec/                      <- repo specs: SCOPE, ARCHITECTURE
  audit/                     <- audit reports (structure/code audits only)
  research/
    existing-approach/       <- dated pre-governance write-ups: CaseMap_AGENT_HANDOFF.md,
                                 CaseMap_Mandatory_ML_Layer_v7.md, poc_report.md (deep
                                 pre-governance handoff, ML-layer deep-dive, latest POC
                                 run output). No FINDINGS.csv here — this project's
                                 findings register is FINDINGS.md at the root.
    new-directions/          <- assessments of new approaches not yet in the system
  plan/                      <- plans for work not yet done
  requirements/<date>-<slug> <- spec-driven workflow: REQUIREMENTS + DESIGN + TASKS + TRACKER
tests/
  test_opennyai_bridge.py    <- test file
  conftest.py                <- puts src/ on sys.path for the flat intra-module imports
testdata/                    <- 22 real Indian court judgments (plain text) for POC/
                                 extraction testing; see testdata/README.md for
                                 provenance. Not real_docs/real_pdfs (still missing,
                                 see HANDOFF.md §6) but usable today.
temp/                        <- ephemeral: scripts, scratch, one-off dumps (never in source)
```

**Where a result goes, by kind:**

| kind of work | detail lands in | conclusion lands in |
|---|---|---|
| audit of code or structure | `docs/audit/<date>_<NAME>.md` | `FINDINGS.md` |
| measurement of the current system | `docs/research/existing-approach/` | `FINDINGS.md` |
| assessment of new tech / new approach | `docs/research/new-directions/` | `FINDINGS.md` |
| the scripts that produced any of it | `temp/<date>-<slug>/` | — |
| a plan for work not yet done | `docs/plan/` | — |

- **No AI-tool-specific handoffs.** `HANDOFF.md` is the one handoff; do not create a
  parallel per-tool copy that can drift from it.
