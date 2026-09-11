# CaseMap POC Report

Generated: 2026-09-09 10:28:35
OCR engine: `tesseract` · lang: `eng` · embeddings: `all-MiniLM-L6-v2`

## 1. Input

6 document(s): t1_jaggo_bookmarked.pdf, t2_delhibail_headings.pdf, t3_jain_flat.pdf, t4_nclt_separators.pdf, t5_crim_scanned.pdf, t6_jet_scanned_headings.pdf

## 2. OCR / Ingestion

- Total pages: **9**
- Digital text layer: **5**
- Scanned (OCR'd): **4**
- Hybrid (partial text + OCR): **0**

- **44%** of pages required OCR.

## 3. Per-Document Structure

| Document | Pages | Tier | Confidence | Sections | Events | Time |
|---|---|---|---|---|---|---|
| t1_jaggo_bookmarked.pdf | 2 | **tier1_bookmarks** | high | 2 | 2 | 0.9s |
| t2_delhibail_headings.pdf | 1 | **tier5_per_page** | none | 1 | 0 | 0.1s |
| t3_jain_flat.pdf | 1 | **tier5_per_page** | none | 1 | 4 | 0.1s |
| t4_nclt_separators.pdf | 3 | **tier2_layout_signals** | medium | 2 | 0 | 13.5s |
| t5_crim_scanned.pdf | 1 | **tier2_layout_signals** | medium | 2 | 0 | 8.2s |
| t6_jet_scanned_headings.pdf | 1 | **tier5_per_page** | none | 1 | 5 | 10.8s |

Tier detail:
- `t1_jaggo_bookmarked.pdf` — 16 embedded bookmarks
- `t2_delhibail_headings.pdf` — no structure signals found; using one section per page
- `t3_jain_flat.pdf` — no structure signals found; using one section per page
- `t4_nclt_separators.pdf` — 2 headings from layout scoring (mostly scanned)
- `t5_crim_scanned.pdf` — 2 headings from layout scoring (mostly scanned)
- `t6_jet_scanned_headings.pdf` — no structure signals found; using one section per page

## 3b. Parties (mandatory ML + deterministic layer)

ML layer status this run: **DEGRADED**

> Running without the OpenNyAI model. Every result below came from the regex-only ladder, stamped `DEGRADED_*`. Install the model and re-run before trusting this section.

| Document | Tier | Confidence | Parties |
|---|---|---|---|
| t1_jaggo_bookmarked.pdf | `DEGRADED_tier1_cause_title` | high | JAGGO (Appellant), UNION OF INDIA & ORS (Respondent), ANITA & ORS (Appellant) |
| t2_delhibail_headings.pdf | `DEGRADED_tier1_cause_title` | high | VEDPAL SINGH TANWAR (Petitioner), DIRECTORATE OF ENFORCEMENT (Respondent) |
| t3_jain_flat.pdf | `DEGRADED_tier1_cause_title` | high | PARVIN KUMAR JAIN (Appellant), ANJU JAIN (Respondent) |
| t4_nclt_separators.pdf | `DEGRADED_tier1_cause_title` | high | STATE BANK OF INDIA (Financial Creditor), JET AIRWAYS (INDIA) LIMITED (Corporate Debtor) |
| t5_crim_scanned.pdf | `DEGRADED_tier1_cause_title` | high | SHAILESH KUMAR (Appellant), STATE OF MAHARASHTRA & ANR.  (Respondent) |
| t6_jet_scanned_headings.pdf | `DEGRADED_tier1_cause_title` | high | STATE BANK OF INDIA & ORS (Appellant), THE CONSORTIUM OF MR. MURARI (Respondent), JALAN AND MR. FLORIAN FRITSC (Respondent) |


## 4. Extracted Events

Total: **11**
Provenance check: **11/11** have an exact source page.

- `evt_0` **ORDER** (NEUTRAL)   — t1_jaggo_bookmarked.pdf **p.1** [VIKRAM NATH, J.]
- `evt_1` **TERMINATION** (NEUTRAL)   — t1_jaggo_bookmarked.pdf **p.1** [VIKRAM NATH, J.]
- `evt_2` **ORDER** (NEUTRAL) Rs. 1,00,000  — t3_jain_flat.pdf **p.1** [p.1]
- `evt_3` **ORDER** (NEUTRAL) Rs.18,000  — t3_jain_flat.pdf **p.1** [p.1]
- `evt_4` **ORDER** (NEUTRAL) Rs.4,00,000  — t3_jain_flat.pdf **p.1** [p.1]
- `evt_5` **PAYMENT** (NEUTRAL) Rs.5.10 crore  — t3_jain_flat.pdf **p.1** [p.1]
- `evt_6` **ORDER** (NEUTRAL) Rs. 150 Crore  — t6_jet_scanned_headings.pdf **p.1** [p.1]
- `evt_7` **PAYMENT** (NEUTRAL) Rs. 150 Crore  — t6_jet_scanned_headings.pdf **p.1** [p.1]
- `evt_8` **ORDER** (NEUTRAL) Rs. 150 Crore  — t6_jet_scanned_headings.pdf **p.1** [p.1]
- `evt_9` **ORDER** (NEUTRAL) Rs. 102.5 Crore  — t6_jet_scanned_headings.pdf **p.1** [p.1]
- `evt_10` **PAYMENT** (NEUTRAL) Rs. 150 Crore  — t6_jet_scanned_headings.pdf **p.1** [p.1]

## 5. Graph Construction Efficiency

- Events (n): **11**
- Naive pairwise comparisons (n²/2): **55**
- Candidate pairs after blocking: **48**
- Reduction: **12.7%**

## 6. Connections

- Edges kept (top-K sparsified): **10**
- **Cross-document** links: **5**  ← the ones that matter for the demo
- Potential conflicts flagged: **0**
- Clusters (storylines) with >1 event: **2**

### Cross-document connections

- `evt_5` (t3_jain_flat.pdf p.1) **RELATED_TO** `evt_8` (t6_jet_scanned_headings.pdf p.1) — score=0.35 [entity=1.0, temporal=0.0, semantic=0.0]
- `evt_5` (t3_jain_flat.pdf p.1) **RELATED_TO** `evt_7` (t6_jet_scanned_headings.pdf p.1) — score=0.35 [entity=1.0, temporal=0.0, semantic=0.0]
- `evt_2` (t3_jain_flat.pdf p.1) **RELATED_TO** `evt_6` (t6_jet_scanned_headings.pdf p.1) — score=0.35 [entity=1.0, temporal=0.0, semantic=0.0]
- `evt_4` (t3_jain_flat.pdf p.1) **RELATED_TO** `evt_8` (t6_jet_scanned_headings.pdf p.1) — score=0.35 [entity=1.0, temporal=0.0, semantic=0.0]
- `evt_4` (t3_jain_flat.pdf p.1) **RELATED_TO** `evt_7` (t6_jet_scanned_headings.pdf p.1) — score=0.35 [entity=1.0, temporal=0.0, semantic=0.0]

## 7. Verdict

- Runtime: **34.2s**
- Graph JSON written to `poc_graph.json` (11 nodes, 10 edges)
- Temporal edges persisted to `casemap.db` (SQLite, no server)

**Ready for UI work if:** every event above shows a plausible page number, at least one cross-document link is legitimate on inspection, and the flagged conflicts are real discrepancies rather than noise.
