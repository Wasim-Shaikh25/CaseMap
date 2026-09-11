# Design — HANDOFF §9 petition follow-ups

## Sources (oracle order)

1. `testdata/` + `real_pdfs/` — confirm they are still all judgments (gap).
2. `temp/2026-09-10-real-petition-run/BCI_NOC_WP.txt` — the only long filed
   petition on disk; process in `temp/` only.
3. Official Supreme Court e-filing PDFs (public, government host):
   - WP format: `https://cdnbbsr.s3waas.gov.in/s3ec0490f1f4972d133619a60c30f3559e/uploads/2024/01/2024011726.pdf`
   - SLP Form-style: `.../2024011763.pdf`
   These are court-published specimens, not synthetic tests.

## Protocol

**§9.1** Reuse `compare_models_post_fix.py`'s method (`detect_structure` →
`segment_document` → eligible paragraphs → centrality argmax). Run on the BCI
petition (reconfirm) and on any second petition-shaped file found. If none,
record the gap; do not substitute a judgment (that would be a flattering
proxy — `FORBIDDEN.md` §E17 / `THESIS.md` §5).

**§9.2** Run `extract_parties_layered`, `extract_parties_hybrid`, and
`case_symbols.normalize_name` / `table_from_extractions` on the BCI petition
and on segmented sections. Compare names/sides to the cause-title block
(petitioner vs numbered respondents vs affidavit deponent).

**§9.3** Sweep `ANNEXURE_PATTERN` against: testdata lines, BCI heading lines,
official SC PDF lines, and the HANDOFF-named probes (`A. GROUNDS`,
`(vii) GROUNDS`). Expand the regex only for heading lines that appear as
standalone headings in the official PDFs or the real petition.

**§9.4** Build a digital multi-page PDF in `temp/` from the real petition
text, page-broken at detected headings (real text, synthetic pagination —
stated as such). Run `extract_pages` + `detect_structure` +
`segment_document`. Also put two headings on one physical PDF page to check
in-page offsets survive PyMuPDF round-trip.

## Outputs

Scripts and raw logs: `temp/2026-09-10-petition-followups/`.
Conclusion: `FINDINGS.md`. Tests only for evidenced heading lines / PDF split.
