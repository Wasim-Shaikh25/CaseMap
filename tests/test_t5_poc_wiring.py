"""T5: poc_run-equivalent wiring — fallback events on F-3 docs."""

from pathlib import Path

import pytest
import spacy

from document_profile import extract_parties_hybrid, party_result_to_fallback_event
from casemap_pipeline import (
    build_inverted_index,
    detect_events,
    extract_deterministic,
    extract_entities,
    generate_candidate_pairs,
    normalize_entities,
    score_pair,
    sparsify_and_cluster,
    to_react_flow,
)

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
F3 = [
    "01_criminal_sc_dilip_kumar_sharma_v_mp.txt",
    "12_consumer_stateconsumercommission_prudential_v_kukreja.txt",
    "16_tax_itat_nalco_v_dcit.txt",
    "17_succession_sc_ashok_kumar_v_raj_gupta.txt",
]
BUNDLE = [
    "09_insolvency_nclat_singhania_v_bank_of_baroda.txt",
    "21_insolvency_nclat_khursheed_anwar_v_sunil_kumar_gupta_2025-09.txt",
    "22_insolvency_sc_khursheed_anwar_v_sunil_kumar_gupta_2025-12.txt",
]


def strip_header(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("Source:"):
        for i, l in enumerate(lines):
            if l.strip() == "" and i > 0:
                return "\n".join(lines[i + 1:])
    return text


def _doc_events(nlp, fname: str):
    text = strip_header((TESTDATA / fname).read_text(encoding="utf-8"))
    offsets = [(0, len(text), 1)]
    section = {"section_label": "Document",
               "pages": [{"page_number": 1, "text": text}], "detected": False}
    det = extract_deterministic(text, offsets)
    ents = extract_entities(text, offsets)
    ent_map = normalize_entities(ents)
    evs = detect_events(section, text, offsets, det, ent_map, ents, fname)
    pr = extract_parties_hybrid(text, fname, nlp=nlp)
    fb = party_result_to_fallback_event(pr, fname, offsets)
    if fb is not None:
        evs.append(fb)
    return evs, pr, fb


def test_t5_fallback_nodes_and_bundle_edge():
    try:
        nlp = spacy.load("en_legal_ner_sm")
    except Exception as exc:
        pytest.skip(f"en_legal_ner_sm not loadable: {exc}")

    all_events = []
    fallback_docs = set()
    for fname in F3 + BUNDLE:
        evs, pr, fb = _doc_events(nlp, fname)
        all_events.extend(evs)
        if fb is not None:
            fallback_docs.add(fname)
            assert fb["confidence"] in ("ml_role_unstable", "block", "degraded")

    for f in F3:
        assert f in fallback_docs, f"T5: no fallback node for {f}"

    graph = to_react_flow(all_events, set(), {})
    fb_conf = {n["data"]["confidence"] for n in graph["nodes"]
               if n["type"] == "fallback_party_block"}
    assert "ml_role_unstable" in fb_conf

    index = build_inverted_index(all_events)
    candidates = generate_candidate_pairs(index)
    scores = {
        p: score_pair(all_events[p[0]], all_events[p[1]], index, len(all_events),
                      lambda e1, e2: 0.0)
        for p in candidates
    }
    kept, _ = sparsify_and_cluster(all_events, candidates, scores, min_score=0.15)
    pairs = {
        tuple(sorted((all_events[a]["document_id"], all_events[b]["document_id"])))
        for (a, b) in kept
        if all_events[a]["document_id"] != all_events[b]["document_id"]
    }
    bset = set(BUNDLE)
    bundle_edges = [p for p in pairs if set(p) <= bset]
    assert bundle_edges, f"T5: no 09/21/22 edge; pairs={pairs}"
