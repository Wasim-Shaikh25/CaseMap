# real_pdfs/

22 real Indian court judgments as PDFs — the corpus referenced throughout
`docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` ("6 real PDFs, 2 genuinely
rasterised with zero text layer") but missing from this working directory since
governance init (flagged in `HANDOFF.md` §6 every session since). Added 2026-09-10 to
support Tier 1 proof work.

**Source content:** the same 22 real, public-domain Indian court judgments already in
`testdata/` (indiankanoon.org — see `testdata/README.md` for full provenance/licensing
detail). This is a second representation of already-vetted documents, not new sourcing.

**Composition — a genuine mix, not all one kind:**
- **15 digital PDFs** — real font-size/bold hierarchy (title, forum line,
  "JUDGMENT"/"ORDER" markers distinct from body text), a real embedded text layer.
- **7 scanned PDFs** — rendered to raster images, degraded with real scanner
  artifacts (±1.4° rotation, Gaussian blur, 0.3-0.6% salt-and-pepper noise), rebuilt
  as image-only PDFs with a **verified zero-character text layer** (checked
  programmatically before being written here, not assumed) — forces any consumer to
  actually run OCR, not read embedded text. Same method validated in
  `docs/research/new-directions/layer-additions-assessment.md` (F-4) Part 4.

This ~1/3 scanned ratio mirrors what the original corpus documented, not an arbitrary
choice — see `temp/2026-09-10-real-pdfs-build/build_real_pdfs.py` for the exact
selection and generation logic.

**Each source document appears exactly once** (as either its digital or scanned
version, never both) — this is a plausible bundle composition, not an inflated count.

**Scanned documents in this corpus:**
- `01_criminal_sc_dilip_kumar_sharma_v_mp.pdf`
- `04_civil_bombayhc_vidhale_v_malpani.pdf`
- `08_labour_sc_upseb_v_shiv_mohan_singh.pdf`
- `12_consumer_stateconsumercommission_prudential_v_kukreja.pdf`
- `15_rentcontrol_madrashc_krishnasamy_v_kannika.pdf`
- `18_financial_gujarathc_aurovill_v_district_magistrate.pdf`
- `21_insolvency_nclat_khursheed_anwar_v_sunil_kumar_gupta_2025-09.pdf`

All other files are digital PDFs.

**Validated against the real pipeline:** `scripts/poc_run.py real_pdfs --ocr tesseract`
(the mandatory model, not `--allow-degraded`) — see `CHANGELOG.md` for the run result
this corpus was built and confirmed against.
