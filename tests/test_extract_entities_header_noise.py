"""Header-noise fix for extract_entities() — testdata/, not synthetic.

See docs/requirements/2026-09-10-entity-extraction-header-noise/.
Requires en_core_web_sm (same model extract_entities() already loads).
"""

from pathlib import Path

import pytest

from casemap_pipeline import (
    GENERIC_ENTITY_TEXT,
    extract_entities,
    normalize_entities,
)

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
DOC_09 = TESTDATA / "09_insolvency_nclat_singhania_v_bank_of_baroda.txt"
DOC_21 = TESTDATA / "21_insolvency_nclat_khursheed_anwar_v_sunil_kumar_gupta_2025-09.txt"
DOC_22 = TESTDATA / "22_insolvency_sc_khursheed_anwar_v_sunil_kumar_gupta_2025-12.txt"

GENUINE = [
    "Bank of Baroda",
    "The Bank of Baroda",
    "National Company Law Tribunal",
    "Khursheed Anwar",
    "Kumar Gupta",
    "Khursheed Anwar & Anr",
    "Cygnus Splendid Ltd. & Ors",
]


def strip_header(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("Source:"):
        for i, l in enumerate(lines):
            if l.strip() == "" and i > 0:
                return "\n".join(lines[i + 1:])
    return text


def _load(path: Path) -> str:
    return strip_header(path.read_text(encoding="utf-8"))


def _ents(path: Path):
    text = _load(path)
    return extract_entities(text, [(0, len(text), 1)])


@pytest.fixture(scope="module")
def spacy_ok():
    try:
        import spacy
        spacy.load("en_core_web_sm")
    except Exception as exc:
        pytest.skip(f"en_core_web_sm not loadable: {exc}")


def test_t1_no_multiline_header_grab_on_doc09_and_22(spacy_ok):
    """T1: malformed multi-line header entities must not appear."""
    for path in (DOC_09, DOC_22):
        texts = [e["text"] for e in _ents(path)]
        for t in texts:
            assert "CIVIL APPELLATE JURISDICTION" not in t, path.name
            assert "\n" not in t, f"multi-line entity survived in {path.name}: {t!r}"


def test_t2_stoplist_terms_not_emitted(spacy_ok):
    for path in (DOC_09, DOC_21, DOC_22):
        for e in _ents(path):
            key = e["text"].strip().lower()
            assert key not in GENERIC_ENTITY_TEXT, (
                f"{path.name} still emitted stoplist term {e['text']!r} as {e['label']}"
            )


def test_t3_genuine_bundle_names_still_match_when_present(spacy_ok):
    """FR3: names that still appear after T1+T2 must share a canonical id
    across the 09/21/22 bundle. Names that only lived in the skipped header
    are reported (not forced back in)."""
    by_doc = {
        "09": _ents(DOC_09),
        "21": _ents(DOC_21),
        "22": _ents(DOC_22),
    }
    flat = [e for ents in by_doc.values() for e in ents]
    mapping = normalize_entities(flat)

    missing_everywhere = []
    split_ids = []
    for name in GENUINE:
        hits = []
        for doc, ents in by_doc.items():
            for e in ents:
                if e["text"].strip() == name:
                    cid = mapping.get((e["label"], e["text"].strip()))
                    if cid:
                        hits.append((doc, cid))
        if not hits:
            missing_everywhere.append(name)
            continue
        ids = {cid for _, cid in hits}
        if len(ids) > 1:
            split_ids.append((name, hits))

    assert not split_ids, f"genuine names split across ids: {split_ids}"
    # At least the names that F-8 found in body-like prose of this bundle
    # must still be present in some document — Bank of Baroda / NCLT / Cygnus
    # are in 09 body. Header-only strings may be absent; that is recorded,
    # not papered over.
    body_expected = ["Bank of Baroda", "National Company Law Tribunal"]
    for name in body_expected:
        assert name not in missing_everywhere, f"body-expected genuine name gone: {name}"


def test_residual_preamble_connectors_gone(spacy_ok):
    """Leftover 24-edge connectors: forum caption, AIR citations, bench fragment."""
    paths = [
        TESTDATA / "03_matrimonial_sc_rajnesh_v_neha.txt",
        TESTDATA / "05_tax_sc_union_of_india_v_rajeev_bansal.txt",
        TESTDATA / "06_motorvehicle_sc_sanjay_verma_v_haryana_roadways.txt",
        TESTDATA / "17_succession_sc_ashok_kumar_v_raj_gupta.txt",
        TESTDATA / "19_constitution_sc_home_secretary_v_nilofer_nisha.txt",
        DOC_22,
    ]
    forbidden = {
        "the supreme court of india",
        "r. subhash",
    }
    for path in paths:
        for e in _ents(path):
            key = e["text"].strip().lower()
            assert key not in forbidden, f"{path.name}: {e['text']!r}"
            assert "AIR" not in e["text"] or not any(ch.isdigit() for ch in e["text"]), (
                f"{path.name} still emitted reporter-shaped entity {e['text']!r}"
            )
