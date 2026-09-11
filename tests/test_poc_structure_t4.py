"""T4: structure tier/confidence must reach poc_graph.json's documents[].

After the 2026-09-11 refactor (CHANGELOG 62) the poc-only `structure_docs_for_graph`
helper is gone: poc_graph.json's documents[] now comes straight from
casemap_service.process_document() results (which carry structure_tier/
confidence/reason) via build_case_graph(), the same code the web app uses. This
tests that real contract — the structure fields survive into graph["documents"] —
with all_events empty so no models load.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "casemap_service", ROOT / "src" / "casemap_service.py")
service = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(service)


def test_t4_graph_documents_carry_structure_tier():
    doc_results = [
        {
            "name": "fixture.pdf", "pages": 2, "structure_tier": "docling_layout",
            "structure_confidence": "high", "structure_reason": "docling found 4 headings",
            "sections": 1, "provisions_detail": [],
        },
        {
            "name": "plain.txt", "pages": 1, "structure_tier": "legacy_fallback_internal",
            "structure_confidence": "unknown", "structure_reason": "docling not installed",
            "sections": 1, "provisions_detail": [],
        },
    ]
    # No events -> build_case_graph returns documents + provisions without
    # touching the embedding model.
    graph = service.build_case_graph(doc_results, [])
    docs = graph["documents"]
    assert docs[0]["structure_tier"] == "docling_layout"
    assert docs[0]["structure_confidence"] == "high"
    assert docs[1]["structure_tier"] == "legacy_fallback_internal"
    assert "structure_reason" in docs[1]
    assert graph["nodes"] == [] and graph["edges"] == []
    assert graph["provisions"] == []
