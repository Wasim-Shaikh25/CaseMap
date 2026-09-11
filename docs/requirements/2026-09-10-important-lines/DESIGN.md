# Design — `src/important_lines.py`

## Shape

`extract_important_lines(section, section_text, offsets, document_id,
start_paragraph_no, use_embeddings=True) -> (events, next_paragraph_no)`

Called once per section, same call site and same inputs `detect_events()`
already receives in `scripts/poc_run.py`'s per-section loop. Returns a list of
event dicts in the exact shape `detect_events()` produces (`type`,
`document_id`, `section_label`, `section_text`, `linked_entities/date/amount`,
`polarity`, `confidence`, `sources: [...]`) plus two additions: a `label` key
(so `to_react_flow()` can show real text instead of a generic type-title —
required a 1-line change there) and `sources[0].paragraph` (the running
paragraph counter). Because the shape matches, these events append directly
into `poc_run.py`'s existing `all_events` list — no second graph-building path.

## Sentence splitting (`split_sentences`)

Works on `(start, end)` spans into the real paragraph text throughout, never
on reconstructed strings — the reason: an earlier version joined split pieces
back together with a literal `" "` when merging abbreviation fragments, which
is only correct if the original separator actually was a single space. Real
PDF-extracted legal text frequently isn't (tabs, newlines, multiple spaces),
so that version would have silently produced sentences that were *not* real
substrings of the source — undermining the entire point of the feature
(verbatim, char-offset-backed provenance). Caught in review before shipping;
regression test: `test_merged_sentences_stay_byte_verbatim_even_across_newlines`.

Two merge passes over the raw regex-split spans, both span-based:
1. **Abbreviation merge** — a fixed list (`Rs`, `No`, `Sec`, `Mr`, etc.) plus a
   general single-capital-letter rule (`_TRAILING_INITIAL_RE`) for name
   initials, which can't be enumerated ("Y.V. Chandrachud").
2. **Short-fragment merge** (`_merge_short_spans`, `MIN_SENTENCE_CHARS=20`) —
   catches whatever the abbreviation list didn't (bare paragraph numbers,
   uncaught abbreviations like "U.P.", OCR debris) by folding any span under
   the threshold into its neighbour until it clears it.

Both were added after running the feature against the real 22-document corpus
and finding 21% of kept nodes were fragments — see `FINDINGS.md` F-11 for the
full before/after.

## Ranking (`rank_sentences`)

- `use_embeddings=True` (default): Qwen3-Embedding-0.6B via
  `sentence_transformers`, mean-similarity centrality (F-11's validated
  winner; a hybrid Docling+Qwen POC additionally confirmed proper LexRank
  power-iteration centrality picks the same top sentence on real documents,
  so the simpler/cheaper method was kept).
- Falls back to `_rank_deterministic` (counts deterministic-fact regex hits —
  reusing `casemap_pipeline`'s existing `AMOUNT_PATTERN`/`DATE_CANDIDATE_PATTERN`/
  etc.) if `sentence_transformers` isn't importable. Never raises.
- The backend actually used is recorded on every node
  (`confidence: "extractive_embedding"` or `"extractive_deterministic"`), so a
  run can be audited for which path really executed rather than assumed.

## Wiring

`scripts/poc_run.py`: one new import, one new CLI flag (`--important-lines`,
default off), a running `doc_paragraph_no` counter reset per document and
threaded across that document's sections, four lines calling
`extract_important_lines()` and extending `all_events` — same pattern
`detect_events()` already follows in that loop.

## Tests

`tests/test_important_lines.py`, 11 tests, all against real `testdata/`
content (no synthetic-only tests, per `FORBIDDEN.md` §E17) plus the specific
abbreviation/initial/short-fragment/verbatim-offset bugs found while
validating against the real corpus. One test (`test_embedding_backend_when_available`)
is skipped, not failed, on a checkout without `sentence-transformers`.
