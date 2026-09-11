"""F-7 cue fixes — real testdata/01 and 03."""

from pathlib import Path

from rhetorical_roles import match_cue, tag_document

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def _load(name: str) -> str:
    text = (TESTDATA / name).read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("Source:"):
        for i, l in enumerate(lines):
            if l.strip() == "" and i > 0:
                return "\n".join(lines[i + 1:])
    return text


def test_generic_in_the_case_of_is_not_precedent():
    assert match_cue(
        "conviction under section 303 in the case of Rohitsingh"
    ) != "PRECEDENT"


def test_doc01_precedent_does_not_poison_all_later_paragraphs():
    tagged = tag_document(_load("01_criminal_sc_dilip_kumar_sharma_v_mp.txt"))
    after_first_cue = [t for t in tagged if t["role"]]
    assert after_first_cue
    roles = {t["role"] for t in tagged if t["confidence"] == "cue_matched"}
    carried_precedent = [
        t for t in tagged
        if t["role"] == "PRECEDENT" and t["confidence"] == "carried_forward"
    ]
    assert not carried_precedent
    assert len(roles) >= 1


def test_doc03_facts_this_case_fuzzy_or_exact():
    text = _load("03_matrimonial_sc_rajnesh_v_neha.txt")
    tagged = tag_document(text)
    facts = [t for t in tagged if t["role"] == "FACTS"]
    assert facts, "expected FACTS from 'facts of this case' wording"
    assert any(t["confidence"] == "cue_matched" for t in facts)


def test_doc21_still_hits_arguments_or_analysis():
    tagged = tag_document(
        _load("21_insolvency_nclat_khursheed_anwar_v_sunil_kumar_gupta_2025-09.txt")
    )
    roles = {t["role"] for t in tagged if t["role"]}
    assert roles & {"ARGUMENTS_PETITIONER", "ARGUMENTS_RESPONDENT", "ANALYSIS"}
