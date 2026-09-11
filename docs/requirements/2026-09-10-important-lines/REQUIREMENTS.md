# Requirements — extractive important lines per paragraph

> **Process note (honesty over tidiness):** this folder was written AFTER
> `src/important_lines.py` was already implemented and tested, not before, as
> `AGENTS.md`/`FORBIDDEN.md` normally require. The owner gave a direct, dated,
> explicit go-ahead in conversation ("ok lets do this and complete backend end
> to end") immediately after F-11's POC (5 generative models tested, all
> rejected) had already answered the open design question — there was no
> remaining design decision a written spec would have caught first. Logged
> here rather than pretending the sequence was different. Future work in this
> area should go through the normal folder-first path.

## Problem

A long section (e.g. a 50-page Grounds section) currently surfaces almost
nothing in the graph: `detect_events()` only fires on a fixed set of keywords
(payment/termination/notice/agreement/order/filing), so a paragraph with no
such keyword produces zero nodes — even if it contains the actual substance of
an argument. The owner asked for every paragraph's important line(s) to become
graph nodes, **explicitly not a generative rewrite** ("we don't want detailed
rewrite things we just want import lines from long paragraph").

## Constraint from F-11

F-11 (`FINDINGS.md`) tested 5 generative summarizers (flan-t5-small, t5-small,
distilbart-cnn-6-6, distilbart-cnn-12-6, Falconsai/text_summarization,
nsi319/legal-pegasus at two decoding settings) against a real paragraph.
**Every one distorted at least one real fact at least once** — a hallucinated
date, two source sentences fused into a claim neither made, a reversed
procedural outcome. None was both faster and more accurate than the extractive
(embedding-centrality) approach. This closes the "which model" question:
generation is ruled out for this feature, not just deprioritized.

## Requirement

For each paragraph in a section long enough to be worth compressing (>=3
sentences), select — never generate — its most representative sentence(s) and
emit it as a graph node carrying:
- the document it came from
- the exact page number
- a paragraph number (a running count through the whole document, matching
  what a reader would call "paragraph 12" of the filing, not "paragraph 3 of
  section 4")
- the real char offset back into the source text
- which ranking backend actually produced it (for auditability)

Must never crash or block a run if the optional embedding dependency
(`sentence-transformers`) isn't installed — degrade to a deterministic,
no-ML scorer instead, same contract as `casemap_pipeline.make_similarity_fn()`.

## Non-goals

- Not a generative rewrite (ruled out by F-11).
- Not a new node schema — must flow through the existing
  `to_react_flow()`/`build_evidence_card()` shape `detect_events()` already
  produces, so the UI/graph consumers don't need a second code path.
- Not adopted as an always-on pipeline default — ships behind an opt-in
  `--important-lines` flag; whether it becomes the default is a separate,
  still-open decision (`HANDOFF.md` §9 pattern).
