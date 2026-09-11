"""Caption furniture must not be parties — testdata/, not synthetic.

See docs/requirements/2026-09-10-party-ladder-header-furniture/.
"""

from pathlib import Path

import pytest

from document_profile import (
    _is_caption_furniture_name,
    extract_parties_hybrid,
    extract_parties_layered,
)

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
DOC_01 = TESTDATA / "01_criminal_sc_dilip_kumar_sharma_v_mp.txt"
DOC_09 = TESTDATA / "09_insolvency_nclat_singhania_v_bank_of_baroda.txt"


def _names(result):
    return [p.name for p in result.parties]


def test_t1_doc01_no_author_or_citation_still_has_litigants():
    text = DOC_01.read_text(encoding="utf-8")
    r = extract_parties_layered(text, DOC_01.name)
    joined = " | ".join(_names(r)).casefold()
    assert "author:" not in joined
    assert "citation" not in joined
    assert "chandrachud" not in joined
    assert "dilip kumar sharma" in joined
    assert "madhya pradesh" in joined


def test_t1_doc09_no_author_judge_still_has_litigants():
    text = DOC_09.read_text(encoding="utf-8")
    r = extract_parties_layered(text, DOC_09.name)
    joined = " | ".join(_names(r)).casefold()
    assert "author:" not in joined
    assert "ashok bhushan" not in joined
    assert "singhania" in joined
    assert "baroda" in joined


def test_t2_hybrid_doc09_drops_author_if_model_loads():
    try:
        import spacy
        nlp = spacy.load("en_legal_ner_sm")
    except Exception as exc:
        pytest.skip(f"en_legal_ner_sm not loadable: {exc}")
    text = DOC_09.read_text(encoding="utf-8")
    r = extract_parties_hybrid(text, DOC_09.name, nlp=nlp)
    joined = " | ".join(_names(r)).casefold()
    assert "author:" not in joined
    assert "ashok bhushan" not in joined


def test_t3_all_testdata_layered_no_furniture_names():
    files = sorted(TESTDATA.glob("*.txt"))
    assert len(files) >= 22
    bad = []
    for path in files:
        r = extract_parties_layered(path.read_text(encoding="utf-8"), path.name)
        for p in r.parties:
            if _is_caption_furniture_name(p.name) or "author:" in p.name.casefold():
                bad.append((path.name, p.name, r.tier, r.confidence))
    assert bad == []
