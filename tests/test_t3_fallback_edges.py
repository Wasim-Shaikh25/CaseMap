"""T3: fallback-node identity linking via normalize_entities / canonical keys.

Forced fallback-shaped nodes from the 09/21/22 bundle (those docs do not
naturally trigger T2 — F-3) using the real party_result_to_fallback_event()
path, including verbatim party names. Doc 22's ALL-CAPS names must connect
to 09/21; the unrelated control must not.
"""

from pathlib import Path

import pytest
import spacy

from document_profile import (
    PartyResult,
    extract_cause_title_block,
    extract_parties_hybrid,
    party_result_to_fallback_event,
    _prefix_title_block,
)
import casemap_pipeline as cp

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
BUNDLE = [
    "09_insolvency_nclat_singhania_v_bank_of_baroda.txt",
    "21_insolvency_nclat_khursheed_anwar_v_sunil_kumar_gupta_2025-09.txt",
    "22_insolvency_sc_khursheed_anwar_v_sunil_kumar_gupta_2025-12.txt",
]
CONTROL = "01_criminal_sc_dilip_kumar_sharma_v_mp.txt"


def strip_header(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("Source:"):
        for i, l in enumerate(lines):
            if l.strip() == "" and i > 0:
                return "\n".join(lines[i + 1:])
    return text


def _forced_fallback(nlp, fname: str):
    text = strip_header((TESTDATA / fname).read_text(encoding="utf-8"))
    pr = extract_parties_hybrid(text, fname, nlp=nlp)
    block = pr.title_block or extract_cause_title_block(text) or _prefix_title_block(text)
    forced = PartyResult(
        pr.parties, "ml_role_unstable",
        "T3 forced scoring path — not a claim the trigger fired",
        "ml_role_unstable",
        dict(pr.meta),
        title_block=block,
    )
    ev = party_result_to_fallback_event(forced, fname, [(0, len(text), 1)])
    assert ev is not None, fname
    return ev


def test_t3_doc22_connects_to_bundle_not_control():
    try:
        nlp = spacy.load("en_legal_ner_sm")
    except Exception as exc:
        pytest.skip(f"en_legal_ner_sm not loadable: {exc}")

    events = [_forced_fallback(nlp, f) for f in BUNDLE + [CONTROL]]
    index = cp.build_inverted_index(events)
    candidates = cp.generate_candidate_pairs(index)
    scores = {
        (a, b): cp.score_pair(events[a], events[b], index, len(events),
                               lambda e1, e2: 0.0)
        for (a, b) in candidates
    }
    kept, _ = cp.sparsify_and_cluster(
        events, candidates, scores, min_score=0.15,
    )
    pairs = {
        tuple(sorted((events[a]["document_id"], events[b]["document_id"])))
        for (a, b) in kept
    }
    bundle_ids = set(BUNDLE)
    assert any(
        "22_insolvency_sc_khursheed_anwar_v_sunil_kumar_gupta_2025-12.txt" in p
        and (p[0] in bundle_ids and p[1] in bundle_ids)
        for p in pairs
    ), f"doc 22 did not connect to 09/21; pairs={pairs}"
    assert not any(CONTROL in p and (p[0] in bundle_ids or p[1] in bundle_ids)
                    for p in pairs), f"control linked to bundle: {pairs}"
