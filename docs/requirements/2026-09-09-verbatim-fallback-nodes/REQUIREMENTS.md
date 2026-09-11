# Requirements: fallback nodes stay on the graph, honestly labeled

**Date:** 2026-09-09
**Plan:** `docs/plan/verbatim-fallback-graph-nodes.md`
**Read first:** `FORBIDDEN.md`, `AGENTS.md`, `THESIS.md`, `docs/spec/SCOPE.md`,
`docs/spec/ARCHITECTURE.md` — this unit of work does not widen scope or touch the
no-generative-LLM rule; it changes what happens *after* extraction confidence is
already known to be low.

## Problem

Today, when a document section can't be resolved to a clean party/role/date/amount
field with confidence, the pipeline's fallback ladders eventually produce *something*
(regex tier-4.5 "verbatim block", or a `DEGRADED_*` stamp from the ML layer) — but nothing
downstream is designed to treat that "something" as a first-class graph citizen. The
practical effect: low-confidence sections risk being dropped from, or under-represented
on, the final case-map graph, even though a human reading the same section could often
still tell it matters.

`FINDINGS.md` F-2 measured this is not a rare edge case: ~3.6% of role-tagged spans
from the *mandatory* NER model were wrong or noisy across just 20 real documents.

## Goal

When a section's extraction confidence is too low to assign a clean structured field,
put it on the event-graph anyway as a node whose evidence is the verbatim source
span — plus whatever entities/dates/statutes *were* confidently detected inside that
span, attached as best-effort signal — rather than dropping it or forcing a
possibly-wrong field.

## Explicit non-goals (owner decision, 2026-09-09)

- **No search/query interface.** Nodes do not need to be filterable by structured
  field. This is a real scope reduction, not a placeholder — do not build query/filter
  machinery under this requirement.
- **Not a change to extraction confidence rules.** `FORBIDDEN.md` §E15/G1 (never let a
  low-confidence result look certain) is unchanged and still applies to fallback nodes
  — a fallback node must be visibly lower-confidence, not dressed up as equivalent to a
  clean structured node.
- **Not a relaxation of the no-generative-LLM rule.** Nothing here infers or
  synthesizes a field; the fallback content is always a literal source span.

## Functional requirements

1. **FR1 — Fallback node creation.** When party/role extraction for a document section
   falls through to the existing tier-4.5 verbatim-block path (or an equivalent
   low-confidence outcome from the mandatory ML layer), the pipeline must produce a
   graph node for that section instead of discarding it.
2. **FR2 — Honest confidence labeling.** Every fallback node must carry a
   machine-readable confidence/provenance marker distinguishing it from a clean
   structured node, consistent with the `DEGRADED_*` stamping pattern already used
   elsewhere in `document_profile.py`.
3. **FR3 — Best-effort signal attachment.** Any entities, dates, statutes, or amounts
   that *were* confidently detected inside a fallback section's span (by the
   deterministic extractor or the mandatory NER model) must be attached to that node,
   not discarded just because the *party/role* field could not be resolved.
4. **FR4 — Graph participation.** Fallback nodes must go through the same stage [5]
   pipeline as clean nodes — inverted-index blocking, multi-signal scoring, sparsify,
   Union-Find clustering, bi-temporal SQLite edges — not a separate/parallel path.
5. **FR5 — Evidence traceability.** A fallback node's evidence must be the literal
   verbatim span (with page/char provenance, per `THESIS.md`'s core promise) — never a
   summary or paraphrase of it.

## Non-functional requirements

- **NFR1 — No regression to `real_docs`/`real_pdfs` results.** The 17/17 explicit-role
  party-symbol result documented in `CaseMap_AGENT_HANDOFF.md` §5 must not regress;
  this requirement only changes what happens to sections that are *not* already
  cleanly resolved.
- **NFR2 — Terminates, never crashes** (per the standing fallback-ladder rule in
  `docs/spec/ARCHITECTURE.md` §3).

## Acceptance / how this gets validated

Per the owner's instruction: **POC first, against `testdata/`, before any `src/`
change is committed to.** The POC should show, on real documents:
- how many additional nodes this surfaces that today would be dropped/under-represented,
- what a fallback node's evidence card would actually look like,
- whether the confidence marker is visibly distinct enough to satisfy `FORBIDDEN.md`
  §E15/G1 on inspection.

Only after that POC produces an honest (not cherry-picked) result does this requirement
graduate to `TASKS.md`/`TRACKER.md` for real implementation in `src/`.
