"""
poc_run.py — CaseMap CLI / batch runner (thin wrapper over casemap_service).

Runs the ONE shared pipeline (src/casemap_service.py — the exact same code
path the web app uses) over a folder of PDFs/Word/.txt files and writes a
Markdown proof report + a machine-readable poc_graph.json. No UI, no server.

This used to reimplement the per-document pipeline inline, which drifted
badly behind server/app.py (it silently ran an older, weaker pipeline while
claiming to prove "the pipeline"). It now calls casemap_service.process_document
/ build_case_graph — so what this report proves is exactly what the app does.

Two things live ONLY here, not in the product, on purpose:
  * the Markdown proof report + poc_graph.json (batch/verification artifacts),
  * the bi-temporal edge experiment (TemporalEdge/apply_invalidation) and its
    SQLite persistence — deliberately kept out of the server, whose privacy
    contract is "persist nothing" (see FINDINGS.md F-14 on why it isn't wired
    into the product: it fires on ~0 real edges and would need per-document
    filing dates the product doesn't track).

Usage:
    python poc_run.py ./sample_bundle/                  # auto-detect scans
    python poc_run.py ./sample_bundle/ --ocr paddle     # force a specific engine
    python poc_run.py ./sample_bundle/ --lang eng+hin   # mixed-script documents
    python poc_run.py ./sample_bundle/ --force-ocr      # OCR every page
"""

import argparse
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import opennyai_bridge as bridge
import casemap_service as service
from casemap_pipeline import TemporalEdge, apply_invalidation, persist_edges


def run_poc(folder, out_md="poc_report.md", out_json="poc_graph.json",
            ocr_engine="paddle", ocr_lang="eng", force_ocr=False,
            embed_model="all-MiniLM-L6-v2", allow_degraded=False, ner_size="sm"):
    t0 = time.time()
    exts = (".pdf", ".docx", ".doc", ".txt")
    inputs = sorted(os.path.join(folder, f) for f in os.listdir(folder)
                    if f.lower().endswith(exts))
    if not inputs:
        print(f"No PDF/Word/.txt files found in {folder}")
        return

    # --- MANDATORY: load the ML party layer once, eagerly, before any file
    # is processed. By default this RAISES if the model is missing -- the
    # POC is meant to prove the real pipeline, not a regex-only stand-in.
    # Pass allow_degraded=True (--allow-degraded) only for local development
    # before the model is installed. The handle is injected into every
    # process_document() call (loaded once, not per document).
    print(f"[+] loading OpenNyAI legal NER ('{ner_size}') -- MANDATORY layer ...",
          flush=True)
    ml_nlp = bridge.load_opennyai_ner(ner_size, allow_degraded=allow_degraded)
    print("[+] ML party layer loaded." if ml_nlp is not None
          else "[!] Running in DEGRADED mode -- see warning above.", flush=True)

    L = ["# CaseMap POC Report", "",
         f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
         f"OCR engine: `{ocr_engine}` · lang: `{ocr_lang}` · "
         f"embeddings: `{embed_model}`",
         "Pipeline: `casemap_service` (the same code path the web app runs).", "",
         "## 1. Input", "",
         f"{len(inputs)} document(s): " + ", ".join(os.path.basename(p) for p in inputs), ""]

    all_events = []
    doc_results = []
    page_kind_counter = Counter()
    doc_summaries = []

    # ---- Per-document: the shared pipeline, once per file --------------------
    for doc_path in inputs:
        name = os.path.basename(doc_path)
        print(f"[+] processing {name} ...", flush=True)
        t_doc = time.time()

        doc = service.process_document(doc_path, name, ml_nlp, ocr_engine=ocr_engine,
                                       ocr_lang=ocr_lang, force_ocr=force_ocr)
        evs = doc.pop("events")
        all_events.extend(evs)
        page_kind_counter.update(doc.get("page_kinds") or {})
        doc_summaries.append({
            "name": name, "pages": doc["pages"],
            "tier": doc["structure_tier"], "confidence": doc["structure_confidence"],
            "reason": doc["structure_reason"], "sections": doc["sections"],
            "events": len(evs), "secs": round(time.time() - t_doc, 1),
            "parties": doc["parties"], "party_tier": doc["party_tier"],
            "party_confidence": doc["party_confidence"],
        })
        doc_results.append(doc)

    # ---- OCR report -------------------------------------------------------
    total_pages = sum(page_kind_counter.values())
    L += ["## 2. OCR / Ingestion", "",
          f"- Total pages: **{total_pages}**",
          f"- Digital text layer: **{page_kind_counter['digital']}**",
          f"- Scanned (OCR'd): **{page_kind_counter['scanned']}**",
          f"- Hybrid (partial text + OCR): **{page_kind_counter['hybrid']}**", ""]
    if total_pages:
        ocr_pct = 100 * (page_kind_counter['scanned'] + page_kind_counter['hybrid']) / total_pages
        L.append(f"- **{ocr_pct:.0f}%** of pages required OCR.")
        if ocr_pct > 60:
            L.append("- > Scan-heavy corpus. OCR quality is the dominant "
                     "accuracy factor here — review the extracted samples below "
                     "before trusting downstream entity/date output.")
    L.append("")

    L += ["## 3. Per-Document Structure", "",
          "| Document | Pages | Tier | Confidence | Sections | Events | Time |",
          "|---|---|---|---|---|---|---|"]
    for d in doc_summaries:
        L.append(f"| {d['name']} | {d['pages']} | **{d['tier']}** | "
                 f"{d['confidence']} | {d['sections']} | {d['events']} | {d['secs']}s |")
    L.append("")
    L.append("Tier detail:")
    for d in doc_summaries:
        L.append(f"- `{d['name']}` — {d['reason']}")
    L.append("")

    # ---- MANDATORY ML + deterministic party layer report ------------------
    L += ["## 3b. Parties (mandatory ML + deterministic layer)", "",
          f"ML layer status this run: **{'active' if ml_nlp is not None else 'DEGRADED'}**", ""]
    if ml_nlp is None:
        L.append("> Running without the OpenNyAI model. Every result below "
                 "came from the regex-only ladder, stamped `DEGRADED_*`. "
                 "Install the model and re-run before trusting this section.")
        L.append("")
    L += ["| Document | Tier | Confidence | Parties |",
          "|---|---|---|---|"]
    for d in doc_summaries:
        names = ", ".join(f"{p['name'][:28]} ({p['role']})" for p in d["parties"][:3]) or "—"
        L.append(f"| {d['name']} | `{d['party_tier']}` | {d['party_confidence']} | {names} |")
    L.append("")

    # ---- Events + provenance check ---------------------------------------
    missing_page = [e for e in all_events if e["sources"][0]["page"] is None]
    L += ["## 4. Extracted Events", "",
          f"Total: **{len(all_events)}**",
          f"Provenance check: **{len(all_events) - len(missing_page)}/{len(all_events)}** "
          f"have an exact source page." + (
              "" if not missing_page else
              f" ⚠️ {len(missing_page)} missing — investigate before demo."), ""]

    for i, e in enumerate(all_events[:60]):
        s = e["sources"][0]
        amt = e["linked_amount"]["raw"] if e["linked_amount"] else ""
        dt = e["linked_date"]["iso"] if e["linked_date"] else ""
        L.append(f"- `evt_{i}` **{e['type']}** ({e['polarity']}) {amt} {dt} — "
                 f"{s['document']} **p.{s['page']}** [{s['section']}]")
    if len(all_events) > 60:
        L.append(f"- _... and {len(all_events) - 60} more_")
    L.append("")

    if not all_events:
        L.append("> No events detected. Check OCR output quality first.")
        _write(out_md, L)
        return

    # ---- Stage 6: graph (shared build_case_graph, with scoring details) ----
    n = len(all_events)
    naive = n * (n - 1) // 2
    print(f"[+] building case graph over {n} events ...", flush=True)
    graph, details = service.build_case_graph(
        doc_results, all_events, embed_model, return_details=True)
    kept, scores, edge_labels = details["kept"], details["scores"], details["edge_labels"]

    L += ["## 5. Graph Construction Efficiency", "",
          f"- Events (n): **{n}**",
          f"- Naive pairwise comparisons (n²/2): **{naive}**",
          f"- Candidate pairs after blocking: **{details['candidate_count']}**"]
    if naive:
        L.append(f"- Reduction: **{100 * (1 - details['candidate_count'] / naive):.1f}%**")
    L.append("")

    # ---- Bi-temporal invalidation (poc-only experiment) ------------------
    temporal_edges = []
    for (a, b) in sorted(kept):
        e1 = all_events[a]
        temporal_edges.append(TemporalEdge(
            edge_id=f"e_{a}_{b}", edge_type=edge_labels[(a, b)],
            source=f"evt_{a}", target=f"evt_{b}",
            valid_at=e1["linked_date"]["iso"] if e1["linked_date"] else None,
            recorded_at=e1["linked_date"]["iso"] if e1["linked_date"] else None,
            score=scores[(a, b)]["score"], breakdown=scores[(a, b)]["breakdown"]))
    temporal_edges = apply_invalidation(temporal_edges)

    conflicts = [(a, b) for (a, b) in kept
                 if edge_labels[(a, b)] == "POTENTIAL_CONFLICT"]
    cross_doc = [(a, b) for (a, b) in kept
                 if all_events[a]["document_id"] != all_events[b]["document_id"]]

    L += ["## 6. Connections", "",
          f"- Edges kept (top-K sparsified): **{len(kept)}**",
          f"- **Cross-document** links: **{len(cross_doc)}**  "
          f"← the ones that matter for the demo",
          f"- Potential conflicts flagged: **{len(conflicts)}**", ""]

    L += ["### Cross-document connections", ""]
    for (a, b) in cross_doc[:30]:
        br = scores[(a, b)]["breakdown"]
        e1, e2 = all_events[a], all_events[b]
        L.append(
            f"- `evt_{a}` ({e1['document_id']} p.{e1['sources'][0]['page']}) "
            f"**{edge_labels[(a, b)]}** "
            f"`evt_{b}` ({e2['document_id']} p.{e2['sources'][0]['page']}) — "
            f"score={scores[(a, b)]['score']:.2f} "
            f"[entity={br['entity_overlap']}, temporal={br['temporal_proximity']}, "
            f"semantic={br['semantic_similarity']}]")
    if not cross_doc:
        L.append("- _None found. Lower `min_score` or check entity normalization._")
    L.append("")

    invalidated = [e for e in temporal_edges if e.invalidated_by]
    if invalidated:
        L += ["### Superseded edges (bi-temporal invalidation)", ""]
        for e in invalidated[:10]:
            L.append(f"- `{e.edge_id}` ({e.edge_type}) superseded by "
                     f"`{e.invalidated_by}` on {e.invalidated_at}")
        L.append("")

    if conflicts:
        L += ["### Potential conflicts (review flags — NOT conclusions)", ""]
        for (a, b) in conflicts[:10]:
            e1, e2 = all_events[a], all_events[b]
            L.append(f"- **{e1['type']}**: {e1['document_id']} p.{e1['sources'][0]['page']} "
                     f"({e1['polarity']}) ⟷ {e2['document_id']} "
                     f"p.{e2['sources'][0]['page']} ({e2['polarity']})")
            L.append(f"  - A: _{e1['sources'][0]['text'][:150]}_")
            L.append(f"  - B: _{e2['sources'][0]['text'][:150]}_")
        L.append("")

    # ---- Outputs ----------------------------------------------------------
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    persist_edges(temporal_edges)

    L += ["## 7. Verdict", "",
          f"- Runtime: **{round(time.time() - t0, 1)}s**",
          f"- Graph JSON written to `{out_json}` "
          f"({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)",
          "- Temporal edges persisted to `casemap.db` (SQLite, poc-only)", "",
          "**Ready for UI work if:** every event above shows a plausible page "
          "number, at least one cross-document link is legitimate on inspection, "
          "and the flagged conflicts are real discrepancies rather than noise.", ""]

    _write(out_md, L)


def _write(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n[ok] Report written to {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default="./sample_bundle")
    ap.add_argument("--ocr", default="paddle",
                    choices=["tesseract", "paddle", "surya"])
    ap.add_argument("--lang", default="eng")
    ap.add_argument("--force-ocr", action="store_true")
    ap.add_argument("--embed", default="all-MiniLM-L6-v2")
    ap.add_argument("--ner-size", default="sm", choices=["sm", "trf"],
                    help="OpenNyAI legal NER model size (mandatory layer)")
    ap.add_argument("--allow-degraded", action="store_true",
                    help="Run without the mandatory ML model (development "
                         "only -- output is explicitly stamped DEGRADED)")
    # NOTE: --important-lines and --gliner were removed when this became a thin
    # wrapper over casemap_service. Important-line extraction is now ALWAYS on
    # (it's part of the one shared pipeline), and GLiNER entity extraction was
    # rejected for the pipeline (slower, reintroduces court-name noise — see
    # FINDINGS.md F-14), so spaCy is the entity extractor everywhere.
    a = ap.parse_args()
    run_poc(a.folder, ocr_engine=a.ocr, ocr_lang=a.lang,
            force_ocr=a.force_ocr, embed_model=a.embed,
            allow_degraded=a.allow_degraded, ner_size=a.ner_size)
