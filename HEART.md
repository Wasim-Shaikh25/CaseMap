# CaseMap — The Heart

> What *we* want — not a universal theory of the problem, only what matters to this
> project. Read this before `THESIS.md`'s detail. If a design choice doesn't serve
> something on this page, it doesn't belong.

---

## 1. What we want (one sentence)

> A source-grounded, LLM-free-in-the-core visual case-file map for legal document
> bundles — every extracted fact traces to a verbatim source span with page/char
> provenance, and nothing is invented.

---

## 2. The build tiers (ordered — nothing skipped)

> **Amended 2026-09-11 (CHANGELOG 62):** the tier *descriptions* below have drifted.
> Tier 3's "React Flow UI ... and a FastAPI backend ... Not started" is no longer true:
> a FastAPI backend (`server/app.py`) + a plain-JS frontend (`ui/`) are built and in
> daily use (owner reversed the no-UI rule, CHANGELOG 42). Several Tier-2 items are also
> now partly built inside the web pipeline (act-name proximity extraction for bare
> section citations; amount figures-vs-words via `case_symbols.find_word_amounts`,
> wired CHANGELOG 62). The *ordering principle* below still stands and Tier 1's blocking
> claim (real-model accuracy verified, not `--allow-degraded`) is still the open bar —
> the UI/backend were built ahead of that by explicit owner decision, not because the
> claim was proven. Section kept below unedited.

The discipline that keeps this simple: **each tier is built only after the previous
tier's core claim is proven** — never optimise *how* something is done (a later tier)
before *whether it should be done at all* (the earlier tier) is proven.

**Tier 1 — core (in progress, not yet fully proven):** the extraction/graph pipeline
itself — OCR ladder, structure detection, mandatory two-layer party extraction
(OpenNyAI NER + deterministic role refinement), deterministic entity/date/amount/
provision extraction, the case symbol table, and efficient event-graph construction
with bi-temporal SQLite edges. Proven so far only in `--allow-degraded` mode (regex
ladder, no real OpenNyAI weights loaded) and against `real_docs/`/`real_pdfs/`. **Not
yet proven:** end-to-end accuracy with the real mandatory model installed — see
`HANDOFF.md` §8, item 1. This is the single blocking item for calling tier 1 done.

**Tier 2 — enhancement on a PROVEN tier 1** (build only after tier 1 is proven; variants
here must beat the tier-1 baseline, not just look plausible): act-name inheritance for
bare section citations; OCR-tolerant role-marker matching; amount figures-vs-words
cross-check; `& Ors.`/`& Anr.` expansion; same-party-different-roles-across-documents
support; confirming the rhetorical-role model's real inference API before building on
it. (Full list: `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §7.)

**Tier 3 — scale / portfolio / multi-X** (needs a proven tier 2 and/or a larger surface
area): the React Flow UI, the PDF.js click-to-source viewer, and a FastAPI backend
wiring the CLI pipeline (`scripts/poc_run.py`) into a real service. Not started; `scripts/poc_run.py`
already writes `poc_graph.json` in the right shape for this, so this is normal frontend
work once tier 1/2 are stable, not a research problem.

**Explicitly not built here:** any generative LLM in the core extraction/graph loop
(mirrors `docs/spec/SCOPE.md`); a hosted multi-tenant SaaS product (this is currently a
disciplined MVP/hackathon-scoped build, per the original CaseGraph→CaseMap narrowing —
see `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §1); a general-purpose legal-drafting or citation-checking
tool.

---

## 3. How we will do it

1. Selection-only extraction: every fact is a verbatim span with a validated char offset
   against the source, never a generated token. Deterministic ladders first, OpenNyAI's
   extraction/labelling NER as the one exception (mandatory, not generative).
2. Every fallback ladder (OCR, structure, parties) has 4-5 tiers, each earned by a real
   real-document failure, and every ladder terminates honestly rather than crashing or
   guessing confidently — see the 26-bug ledger in `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §4.
3. Honesty discipline: real documents are the only valid test oracle (`THESIS.md` §5); a
   confidently-wrong result is treated as the worst possible failure, worse than a crash;
   negative/"no result" outcomes are recorded, not hidden.
4. **Keep everything** — successes and failures — as a record, not just a running
   codebase state. The bug ledger, the dry-run results, and this governance system's
   `FINDINGS.md` are all part of that record.

---

## 4. The conviction (kept honest)

Indian courts are moving toward penalizing unverified AI-generated legal content (the
July 2026 Supreme Court ruling on unverified AI citations as advocate misconduct is the
concrete trigger). A tool that visually maps a case bundle *without* inventing anything —
every node clickable back to its exact source page — is both defensible under that
scrutiny and genuinely useful for disputes/arbitration teams managing large document
bundles. That belief motivated the build; it is not evidence on its own — only
`THESIS.md` §5's standard (real documents, honest confidence, no flattering proxy)
decides what's actually true about whether this works.
