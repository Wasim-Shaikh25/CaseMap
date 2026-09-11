"""F-11 — extractive important lines. Real testdata paragraph, no ML required
for the default test path (deterministic fallback) since sentence-transformers
is an optional dependency."""

from pathlib import Path

import pytest

from casemap_pipeline import build_section_text
from important_lines import (
    extract_important_lines, rank_sentences, split_sentences,
)

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def _load(name: str) -> str:
    text = (TESTDATA / name).read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("Source:"):
        for i, l in enumerate(lines):
            if l.strip() == "" and i > 0:
                return "\n".join(lines[i + 1:])
    return text


# The real long paragraph F-11 validated against: lease dates, rent amounts,
# notice dates -- dense enough to exercise both ranking backends honestly.
LONG_PARAGRAPH = (
    "The respondent's mother took the petition mentioned property on lease on "
    "05.02.1982 for non residential purpose to run a book stall. Thereafter, "
    "with the consent of her mother, the respondent became the tenant under "
    "the petitioner on 05.01.1991 for running the said book stall on a "
    "monthly rent of Rs.1,500/-. The respondent paid a sum of Rs.4,500/- "
    "towards advance. Thereafter, another lease deed was executed on "
    "05.06.1994 with a monthly rent of Rs.1,800/-. The respondent committed "
    "willful default in payment of rent from June 1994."
)

SHORT_PARAGRAPH = "The appeal is dismissed with costs."


def _section(text: str) -> dict:
    return {"section_label": "Test Section",
            "pages": [{"page_number": 7, "text": text}]}


def test_abbreviation_rs_does_not_split_mid_sentence():
    """Real bug found via a hybrid Docling+Qwen POC on real_pdfs/02: 'Rs.'
    before an amount was kept as its own fake 'sentence' fragment."""
    text = "The respondent No 2 started to pay Rs. 5,000 per month from March 2019."
    sentences = split_sentences(text)
    assert len(sentences) == 1
    assert sentences[0][0] == text


def test_name_initials_do_not_split_mid_sentence():
    """Real bug found running --important-lines against all 22 testdata
    docs: 'The Judgment of Y.' and a bare 'N.' were kept as fake sentences --
    name initials ('Y.V. Chandrachud') aren't in any fixed abbreviation list."""
    text = "The Judgment of Y.V. Chandrachud, J. was delivered on that date."
    sentences = split_sentences(text)
    assert len(sentences) == 1
    assert sentences[0][0] == text


def test_short_fragments_merge_into_neighbour_not_kept_alone():
    """Real bug found in the same run: bare paragraph numbers ('2.', '14.')
    and short abbreviations ('U.P.', 'I.K.') were kept as standalone
    'important lines' -- 18 of 85 nodes (21%) in that run were fragments
    like this before the merge-short-fragments safety net was added."""
    text = ("2. The appellant, resident of Agra, U.P. filed the petition "
            "before the Sessions Judge on 14. March seeking bail.")
    sentences = split_sentences(text)
    for s, _, _ in sentences:
        assert len(s) >= 20, f"fragment too short to be a real sentence: {s!r}"


def test_merged_sentences_stay_byte_verbatim_even_across_newlines():
    """Guards the actual bug this was almost shipped with: reconstructing
    merged text by joining stripped pieces with a literal ' ' silently stops
    being verbatim the moment the real separator was a newline/tab, which is
    common in PDF-extracted legal text."""
    text = "He relied on Rs.\n5,000 as proof of the transaction that followed."
    sentences = split_sentences(text)
    assert len(sentences) == 1
    s, start, end = sentences[0]
    assert text[start:end] == s
    assert "\n" in s  # the real newline is preserved, not replaced with " "


def test_split_sentences_are_real_verbatim_substrings():
    sentences = split_sentences(LONG_PARAGRAPH)
    assert len(sentences) >= 4
    for text, start, end in sentences:
        assert LONG_PARAGRAPH[start:end] == text


def test_deterministic_fallback_never_needs_ml():
    sentences = [s for s, _, _ in split_sentences(LONG_PARAGRAPH)]
    scores, backend = rank_sentences(sentences, use_embeddings=False)
    assert backend == "deterministic"
    assert len(scores) == len(sentences)
    # the sentence with a real date+amount should outscore a plain narrative one
    date_amount_sentence_idx = next(
        i for i, s in enumerate(sentences) if "05.06.1994" in s and "Rs.1,800" in s)
    plain_sentence_idx = next(
        i for i, s in enumerate(sentences) if "willful default" in s)
    assert scores[date_amount_sentence_idx] > scores[plain_sentence_idx]


def test_extract_important_lines_produces_real_char_offsets():
    section = _section(LONG_PARAGRAPH)
    section_text, offsets = build_section_text(section)
    events, next_para = extract_important_lines(
        section, section_text, offsets, "doc01.pdf",
        start_paragraph_no=1, use_embeddings=False)

    assert events, "a dense paragraph should yield at least one important line"
    for e in events:
        assert e["type"] == "IMPORTANT_LINE"
        assert e["confidence"] == "extractive_deterministic"
        src = e["sources"][0]
        assert src["document"] == "doc01.pdf"
        assert src["page"] == 7
        assert src["paragraph"] == 1
        # the kept line must be a REAL, verbatim substring of the section text
        # -- this is the whole point: never generated, always extracted.
        assert section_text[src["char_start"]:src["char_end"]] == src["text"]
        assert src["text"] in LONG_PARAGRAPH


def test_short_paragraphs_are_skipped_not_forced():
    section = _section(SHORT_PARAGRAPH)
    section_text, offsets = build_section_text(section)
    events, next_para = extract_important_lines(
        section, section_text, offsets, "doc01.pdf",
        start_paragraph_no=1, use_embeddings=False)
    assert events == []
    assert next_para == 2  # paragraph counter still advances


def test_paragraph_numbering_continues_across_sections():
    section = _section(LONG_PARAGRAPH)
    section_text, offsets = build_section_text(section)
    _, next_para = extract_important_lines(
        section, section_text, offsets, "doc01.pdf",
        start_paragraph_no=5, use_embeddings=False)
    assert next_para == 6  # one paragraph in this section -> counter +1


def test_real_doc_no_crash_no_hallucination():
    """Run against a real testdata document end to end (deterministic
    backend, no network/model download needed) -- every kept sentence must
    trace back to real text in the document."""
    raw = _load("15_rentcontrol_madrashc_krishnasamy_v_kannika.txt")
    section = _section(raw)
    section_text, offsets = build_section_text(section)
    events, _ = extract_important_lines(
        section, section_text, offsets,
        "15_rentcontrol_madrashc_krishnasamy_v_kannika.txt",
        use_embeddings=False)
    assert events
    for e in events:
        src = e["sources"][0]
        assert section_text[src["char_start"]:src["char_end"]] == src["text"]
        assert src["page"] is not None
        assert src["paragraph"] >= 1


def test_embedding_backend_when_available():
    """Only meaningful if sentence-transformers is installed; skipped
    otherwise rather than failing a fresh checkout."""
    pytest.importorskip("sentence_transformers")
    sentences = [s for s, _, _ in split_sentences(LONG_PARAGRAPH)]
    scores, backend = rank_sentences(sentences, use_embeddings=True)
    assert backend == "embedding"
    assert len(scores) == len(sentences)
