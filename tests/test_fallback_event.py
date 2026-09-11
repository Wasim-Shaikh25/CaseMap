"""T1 unit tests for party_result_to_fallback_event().

Synthetic PartyResult objects only — these prove the function's contract
(None vs event shape), not extraction accuracy. Real-document acceptance
for this requirement is T5 against testdata/, not this file.
"""

from document_profile import PartyResult, TitleBlock, party_result_to_fallback_event


def _offsets(text: str, page: int = 1):
    return [(0, len(text), page)]


def test_tier5_without_block_returns_none():
    result = PartyResult(
        [], "tier5_none", "no parties found", "none",
        title_block=None,
    )
    assert party_result_to_fallback_event(result, "doc_syn_none", []) is None


def test_tier4b_block_returns_event_with_verbatim_span_and_block_confidence():
    span = (
        "IN THE HIGH COURT OF JUDICATURE AT BOMBAY\n"
        "W.P. (C) No. 1234 of 2024\n"
        "Notice dated 12 January 2024 for Rs. 50,000\n"
        "Section 138 mentioned in the heading region"
    )
    result = PartyResult(
        [], "tier4b_title_block",
        "cause-title region located; shown verbatim",
        "block",
        title_block=TitleBlock(
            span, 0, 3, None, "synthetic unit-test block",
        ),
    )
    event = party_result_to_fallback_event(
        result, "doc_syn_block", _offsets(span, page=2),
    )
    assert event is not None
    assert event["type"] == "fallback_party_block"
    assert event["document_id"] == "doc_syn_block"
    assert event["section_text"] == span
    assert event["section_text"] == result.title_block.text.strip()
    assert event["polarity"] == "NEUTRAL"
    assert event["confidence"] == "block"
    assert event["linked_date"] is not None
    assert event["linked_date"]["iso"] == "2024-01-12"
    assert event["linked_amount"] is not None
    assert "50,000" in event["linked_amount"]["raw"]
    assert event["linked_entities"]  # CASE_NUMBER and/or PROVISION ids
    assert event["sources"][0]["document"] == "doc_syn_block"
    assert event["sources"][0]["page"] == 2
    assert event["sources"][0]["text"] == span[:300]


def test_clean_tier_does_not_become_a_fallback_node():
    result = PartyResult(
        [], "tier1_cause_title", "resolved", "high",
        title_block=TitleBlock("should not be used", 0, 0, None, "unused"),
    )
    assert party_result_to_fallback_event(result, "doc_syn_clean", []) is None


def test_ml_role_unstable_stamp_on_event():
    span = "IN THE SUPREME COURT\nW.P. (C) No. 1 of 2024\nALICE versus ALICE"
    result = PartyResult(
        [], "ml_role_unstable",
        "same name tagged with more than one ML role",
        "ml_role_unstable",
        title_block=TitleBlock(span, 0, 2, None, "test"),
    )
    event = party_result_to_fallback_event(result, "doc_unstable", _offsets(span))
    assert event is not None
    assert event["confidence"] == "ml_role_unstable"
    assert event["type"] == "fallback_party_block"


def test_t4_to_react_flow_surfaces_fallback_confidence():
    from casemap_pipeline import to_react_flow, build_evidence_card

    clean = {
        "type": "ORDER", "document_id": "a", "section_label": "s",
        "section_text": "x", "linked_entities": [], "linked_date": None,
        "linked_amount": None, "polarity": "NEUTRAL",
        "sources": [{"document": "a", "page": 1, "char_start": 0,
                     "char_end": 1, "text": "x", "section": "s"}],
    }
    span = "IN THE COURT\nW.P. (C) No. 1 of 2024"
    fb = party_result_to_fallback_event(
        PartyResult([], "ml_role_unstable", "u", "ml_role_unstable",
                    title_block=TitleBlock(span, 0, 1, None, "t")),
        "b", _offsets(span),
    )
    graph = to_react_flow([clean, fb], set(), {})
    confs = {n["id"]: n["data"]["confidence"] for n in graph["nodes"]}
    assert confs["evt_0"] == "resolved"
    assert confs["evt_1"] == "ml_role_unstable"
    card = build_evidence_card(fb)
    assert card["confidence"] == "ml_role_unstable"
