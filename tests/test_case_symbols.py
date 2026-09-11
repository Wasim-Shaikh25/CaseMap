"""Case Symbol Table — testdata 09/21/22, not synthetic-only."""

from pathlib import Path

from case_symbols import (
    SymbolSite,
    SymbolTable,
    amount_from_words,
    normalize_amount,
    normalize_name,
    table_from_extractions,
)
from casemap_pipeline import extract_deterministic, extract_entities

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
DOC_09 = TESTDATA / "09_insolvency_nclat_singhania_v_bank_of_baroda.txt"
DOC_21 = TESTDATA / "21_insolvency_nclat_khursheed_anwar_v_sunil_kumar_gupta_2025-09.txt"
DOC_22 = TESTDATA / "22_insolvency_sc_khursheed_anwar_v_sunil_kumar_gupta_2025-12.txt"


def test_normalize_name_collapses_legal_suffix():
    assert normalize_name("Cygnus Splendid Ltd.") == normalize_name(
        "Cygnus Splendid Limited")


def test_normalize_amount_and_words():
    assert normalize_amount("Rs.1,20,00,000") == 12_000_000
    assert normalize_amount("Rs. 9 lakh") == 900_000
    assert amount_from_words("Rupees One Crore Twenty Lakh") == 12_000_000


def test_go_to_definition_is_first_site():
    t = SymbolTable()
    t.add(SymbolSite("a.txt", "Bank of Baroda", "ORG", (0, 14), 1))
    t.add(SymbolSite("b.txt", "The Bank of Baroda", "ORG", (10, 28), 1))
    key = [k for k in t.keys() if "baroda" in k][0]
    d = t.go_to_definition(key)
    assert d is not None and d.document_id == "a.txt"
    refs = t.find_all_references(key)
    assert {s.document_id for s in refs} == {"a.txt", "b.txt"}


def test_t3_bundle_shared_name_across_docs():
    import pytest
    try:
        import spacy
        spacy.load("en_core_web_sm")
    except Exception as exc:
        pytest.skip(f"en_core_web_sm not loadable: {exc}")

    merged = SymbolTable()
    for path in (DOC_09, DOC_21, DOC_22):
        text = path.read_text(encoding="utf-8")
        offsets = [(0, len(text), 1)]
        det = extract_deterministic(text, offsets)
        ents = extract_entities(text, offsets)
        merged.merge_from(table_from_extractions(path.name, det, ents))

    multi = [
        k for k in merged.keys()
        if len({s.document_id for s in merged.find_all_references(k)}) >= 2
    ]
    blob = " ".join(multi).casefold()
    assert any(n in blob for n in ("baroda", "khursheed", "cygnus", "gupta")), (
        f"no genuine bundle key across 2+ docs; keys={multi[:20]}"
    )
