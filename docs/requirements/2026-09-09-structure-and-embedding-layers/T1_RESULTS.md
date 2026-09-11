# T1 results: Docling `page_no` vs PyMuPDF/casemap `page_number`

**Date:** 2026-09-10
**Script:** `temp/2026-09-10-docling-page-no/verify_page_no.py`
**PDF:** `temp/2026-09-09-layer-additions-poc/pdfs/09_insolvency_nclat_singhania_v_bank_of_baroda.pdf`
(2 pages — the generated testdata PDFs in that folder are short)

## Result

`item.prov[0].page_no` is **1-indexed** and matched `pages[i]["page_number"]`
(PyMuPDF `i+1`, same convention `casemap_pipeline.extract_pages` uses) for
**4/4** `section_header` items. Zero disagreements. Zero unmatched heading texts.

No off-by-one correction is required for FR2.

## Honest limit

All four headings in this fixture sit on **page 1**. That is enough to reject
0-based Docling pages (those would have been `page_no=0`). It is **not** a
deep check of page 2+ on a long judgment. T2 should still pass heading text
through `_segment_by_headings` using `page_no` as-is (1-indexed). Re-check if
a longer real PDF is added.

Raw JSON: `temp/2026-09-10-docling-page-no/t1_compare.json`
