# Plan: fallback nodes stay on the graph, honestly labeled

**Date:** 2026-09-09
**Status:** planned, not yet built. See `docs/requirements/2026-09-09-verbatim-fallback-nodes/`
for the requirements/design this turns into before any code is written.

## The idea, in one paragraph

Right now the party-extraction ladder's last resort (`docs/spec/ARCHITECTURE.md` §1
stage [2], "tier-4.5 verbatim block") exists but the rest of the pipeline treats a
low-confidence result as something to route around, not something to build on. The
refinement: when nothing can be assigned a clean role/field with confidence, don't drop
it or block the graph on it — put the raw section on the graph as a node anyway, with
whatever it *did* confidently detect (dates, statutes, provisions, org names) attached
as best-effort signal, clearly labeled by confidence, and let the event-graph
construction stage (§1 stage [5]) block/score/link it like any other node. The node's
"evidence" is the verbatim text itself, not a synthesized field.

## Why this is in scope, not a rule change

This does not touch `FORBIDDEN.md` §C — nothing here proposes inferring or generating
a field the source doesn't literally contain. It's the opposite: it's choosing to show
an honest, lower-confidence node (the raw span) instead of either (a) forcing a
possibly-wrong structured field, or (b) silently dropping the section because it
couldn't be structured. `THESIS.md` §5 already says a confidently-wrong result is worse
than an honest low-confidence one — this is that principle applied one stage further
downstream, into the graph, not just the extraction ladder.

## Why now

`FINDINGS.md` F-2 (`en_legal_ner_sm` run against 20 real documents) found real,
measurable role-label noise (~3.6% of role-tagged spans wrong or noisy) even from the
mandatory model. Rather than trying to drive that number to zero before anything can
reach the graph, this plan accepts that some sections will never cleanly resolve to a
structured field, and designs the graph to represent that honestly instead of hiding
it.

## What's explicitly out of scope (per owner decision, 2026-09-09)

- **No search/query interface.** The graph view is the only interface being planned;
  nodes do not need to be filterable/queryable by field, which simplifies what
  "structure" a fallback node needs to carry — it needs enough to be a graph node
  (some entities/dates for blocking and scoring), not a fully normalized record.

## Rough shape (to be nailed down in DESIGN.md)

- A node's confidence is visible, not hidden — same instinct as `FORBIDDEN.md` §E15/G1
  (never let a low-confidence result look as certain as a high-confidence one).
- Fallback nodes still participate in stage [5]'s inverted-index blocking, multi-signal
  scoring, and Union-Find clustering — they are not a second-class graph citizen, just
  a node whose "party" field is a text span instead of a normalized name.
- The React Flow / evidence-card output (stage [6], not yet built) should be able to
  render a fallback node the same way it renders any other — evidence card showing the
  verbatim span — so this doesn't need special-casing at the UI layer either.

## Next step

`docs/requirements/2026-09-09-verbatim-fallback-nodes/REQUIREMENTS.md` +
`DESIGN.md`, then a POC against `testdata/` to see what this actually looks like on
real documents before committing to `src/` changes, per the owner's explicit
instruction: POC first, get an honest read of the result, then formalize into
`TASKS.md`/`TRACKER.md` for real implementation.
