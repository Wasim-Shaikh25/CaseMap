"""T2: ML role-instability trigger — testdata/01, 12, 16, 17 (F-3).

Glue-code check uses a fake spaCy NER (same pattern as test_opennyai_bridge.py).
Acceptance on the four F-3 documents uses en_legal_ner_sm when loadable.
"""

from pathlib import Path

import pytest
import spacy

from document_profile import (
    extract_parties_hybrid,
    party_result_to_fallback_event,
)

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
F3_UNSTABLE = [
    TESTDATA / "01_criminal_sc_dilip_kumar_sharma_v_mp.txt",
    TESTDATA / "12_consumer_stateconsumercommission_prudential_v_kukreja.txt",
    TESTDATA / "16_tax_itat_nalco_v_dcit.txt",
    TESTDATA / "17_succession_sc_ashok_kumar_v_raj_gupta.txt",
]


def strip_header(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("Source:"):
        for i, l in enumerate(lines):
            if l.strip() == "" and i > 0:
                return "\n".join(lines[i + 1:])
    return text


class SequentialFakeNLP:
    """Place each (needle, label) at the next occurrence of needle."""

    def __init__(self, specs: list[tuple[str, str]]):
        self._specs = specs
        self._vocab_nlp = spacy.blank("en")

    def __call__(self, text: str):
        doc = self._vocab_nlp.make_doc(text)
        ents = []
        cursor = 0
        for needle, label in self._specs:
            idx = text.find(needle, cursor)
            if idx == -1:
                idx = text.find(needle)
            if idx == -1:
                continue
            span = doc.char_span(idx, idx + len(needle), label=label,
                                  alignment_mode="expand")
            if span is not None:
                ents.append(span)
            cursor = idx + max(len(needle), 1)
        doc.set_ents(ents)
        return doc


def test_hybrid_stamps_ml_role_unstable_when_same_name_has_two_roles():
    text = (
        "IN THE HIGH COURT OF BOMBAY\n"
        "ALICE SMITH                                      ... Petitioner\n"
        "                    VERSUS\n"
        "BOB JONES                                        ... Respondent\n"
        "JUDGMENT\n"
        "The court later referred again to ALICE SMITH as respondent.\n"
    )
    nlp = SequentialFakeNLP([
        ("ALICE SMITH", "PETITIONER"),
        ("BOB JONES", "RESPONDENT"),
        ("ALICE SMITH", "RESPONDENT"),
    ])
    result = extract_parties_hybrid(text, "syn.txt", nlp=nlp)
    assert result.tier == "ml_role_unstable"
    assert result.confidence == "ml_role_unstable"
    assert result.title_block is not None
    event = party_result_to_fallback_event(
        result, "syn.txt", [(0, len(text), 1)],
    )
    assert event is not None
    assert event["confidence"] == "ml_role_unstable"


def test_f3_docs_01_12_16_17_produce_ml_role_unstable_fallback():
    try:
        nlp = spacy.load("en_legal_ner_sm")
    except Exception as exc:
        pytest.skip(f"en_legal_ner_sm not loadable: {exc}")

    missing = []
    for path in F3_UNSTABLE:
        text = strip_header(path.read_text(encoding="utf-8"))
        result = extract_parties_hybrid(text, path.name, nlp=nlp)
        event = party_result_to_fallback_event(
            result, path.name, [(0, len(text), 1)],
        )
        if result.tier != "ml_role_unstable" or event is None:
            missing.append((path.name, result.tier, event is None))
    assert not missing, (
        "F-3 docs must produce ml_role_unstable fallback events; failed: "
        f"{missing}"
    )
