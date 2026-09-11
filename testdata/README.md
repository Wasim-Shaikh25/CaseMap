# testdata/

22 real Indian court judgments, plain text, used for POC/extraction testing. The first
20 were added 2026-09-09 for the mini-LLM extraction assessment
(`docs/research/new-directions/mini-llm-extraction-assessment.md`); two more (21, 22)
were added the same day as a genuinely connected same-matter bundle (with the existing
doc 09) for `docs/requirements/2026-09-09-verbatim-fallback-nodes/`'s edge-formation
test — see that folder's `POC_RESULTS.md`. All available for reuse in future pipeline
testing.

**Source:** indiankanoon.org (public-domain judgment text — judicial proceedings are
exempt from copyright under s.52(1)(q) of the Indian Copyright Act; browsed and saved
individually per its `robots.txt`, which allows general crawling except for a list of
specific takedown-flagged document IDs not used here). Each file's header records the
exact source URL, court, and case type it was pulled for.

**Coverage:** Supreme Court of India, Delhi HC, Bombay HC, Madras HC, Gujarat HC,
Karnataka HC, Kerala HC, NCLAT, a State Consumer Disputes Redressal Commission, and an
ITAT bench — criminal, matrimonial/maintenance, civil/contract, tax, motor vehicle
accident, land & property, industrial/labour, insolvency (IBC), constitutional/bail,
consumer, company law, NDPS bail, rent control, and succession matters.

**Note on length:** most files are excerpts (a few thousand words), not complete
judgments — enough to exercise party/date/amount/citation extraction realistically
without needing full multi-page documents. They are plain text, not scanned PDFs, so
they do not exercise the OCR ladder (`casemap_pipeline.py`'s 3-tier OCR path) — for
that, the project still needs `real_pdfs/` (see `HANDOFF.md` §6, not present in this
working directory).
