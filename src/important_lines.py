"""important_lines.py — extractive "important lines" per paragraph (F-11).

Owner's explicit direction (2026-09-10, logged CHANGELOG (34)): long sections
(e.g. a 50-page Grounds section) should surface their important lines as graph
nodes WITHOUT generative rewriting. F-11 tested 5 generative models (60M-568M)
against this exact task and every one distorted at least one real fact at least
once — a hallucinated date, a fused claim two source sentences never made, a
reversed procedural outcome. This module only ever SELECTS a real sentence; it
never generates one, so it cannot repeat those failures.

Two ranking backends:
  - embedding centrality (all-MiniLM-L6-v2 via sentence_transformers, default
    since 2026-09-10, F-12) — for each sentence in a paragraph, rank by its
    average similarity to every other sentence in that paragraph
    (TextRank-lite), keep the most central one(s). Optional dependency,
    lazy-imported. F-11 validated Qwen3-Embedding-0.6B for this; F-12 measured
    Qwen at ~112x MiniLM's per-sentence cost on real hardware (32.7s vs 0.29s
    for 50 sentences) and found MiniLM's picks differ from Qwen's on real
    petition paragraphs (28/47, 60% same) but are consistently real,
    substantive sentences in spot-checks, never nonsense — a real trade in
    WHICH valid sentence gets surfaced, not a correctness regression. Owner's
    call: default to the 112x-faster model. EMBED_MODEL_NAME below is the one
    knob if that trade needs revisiting.
  - deterministic density fallback (no ML, no download) when sentence_transformers
    isn't installed — same "degrade, never crash" philosophy as
    casemap_pipeline.make_similarity_fn(). Scores each sentence by how many
    deterministic facts (date/amount/section/case-number) it contains.

Output events use the exact same shape casemap_pipeline.detect_events() emits,
so they flow through to_react_flow()/build_evidence_card() unchanged — an
IMPORTANT_LINE event is a KEY_FACT-flavoured event, not a new pipeline stage.
"""

from __future__ import annotations

import re

from rhetorical_roles import split_paragraphs

SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

# Indian-legal abbreviations that end in "." but are NOT sentence boundaries
# -- "Rs." before an amount is the common real-world trap (a hybrid Docling+
# Qwen POC on a real document caught this: 'The respondent No 2 started to
# pay Rs.' was kept as a "complete sentence", a fragment, not a real one).
_ABBREVIATIONS = {
    "rs", "no", "nos", "s", "ss", "sec", "secs", "art", "arts", "mr", "mrs",
    "dr", "smt", "shri", "vs", "v", "ors", "anr", "crl", "slp", "addl", "dy",
    "govt", "ltd", "co", "hon", "para", "paras", "regd", "adv", "sd", "w.e.f",
    "i.e", "e.g", "etc", "u/s", "u/a",
}
_TRAILING_ABBREV_RE = re.compile(
    r"\b(" + "|".join(_ABBREVIATIONS) + r")\.$", re.I)
# A single capital letter before a period is almost always a name initial
# ("Y.V. Chandrachud", "the Judgment of Y.") or a judge/justice suffix ("J."),
# never a real sentence end -- can't be enumerated like the list above.
_TRAILING_INITIAL_RE = re.compile(r"\b[A-Za-z]\.$")

# Below this, a "sentence" is almost certainly a boundary-detection artifact
# (a bare paragraph number "2.", an uncaught abbreviation "U.P.", a stray
# initial "N.") rather than a real standalone clause -- found by running the
# real end-to-end pipeline (`--important-lines`) against all 22 testdata
# documents: 18 of 85 kept nodes (21%) were fragments like this before this
# safety net was added.
MIN_SENTENCE_CHARS = 20

# Below this many sentences, a paragraph is already short enough to read as-is
# -- extracting "the important line" out of a 1-2 sentence paragraph adds
# nothing and would just duplicate it as a second node.
MIN_SENTENCES_PER_PARAGRAPH = 3
TOP_K_PER_PARAGRAPH = 1

# Default since 2026-09-10 (F-12): ~112x faster than Qwen3-Embedding-0.6B on
# real hardware (32.7s vs 0.29s per 50 sentences), picks a different sentence
# ~40% of the time on real petition paragraphs but always a real, substantive
# one in spot-checks -- owner's call, speed over the marginal Qwen-specific
# pick. Swap this one constant to revisit that trade.
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_IL_EMBED = None

# Reuse the same deterministic-fact patterns the pipeline already trusts
# (casemap_pipeline.py) for the no-ML fallback scorer, instead of redefining
# them here.
from casemap_pipeline import (  # noqa: E402
    AMOUNT_PATTERN, CASE_NUMBER_PATTERN, SECTION_PATTERN, DATE_CANDIDATE_PATTERN,
    offset_to_page,
)

_FACT_PATTERNS = [AMOUNT_PATTERN, CASE_NUMBER_PATTERN, SECTION_PATTERN, DATE_CANDIDATE_PATTERN]


def _ends_with_abbreviation(text: str) -> bool:
    stripped = text.strip()
    return bool(_TRAILING_ABBREV_RE.search(stripped) or _TRAILING_INITIAL_RE.search(stripped))


def _raw_sentence_spans(paragraph: str) -> list[tuple[int, int]]:
    """(start, end) spans over the REAL paragraph, from SENT_RE's split
    points. Spans, not reconstructed strings -- joining stripped pieces back
    together with a literal space would silently stop being verbatim the
    moment the original separator was a newline, tab, or multiple spaces
    (real legal-PDF text almost always has some of that)."""
    spans, cursor = [], 0
    for m in SENT_RE.finditer(paragraph):
        spans.append((cursor, m.start()))
        cursor = m.end()
    spans.append((cursor, len(paragraph)))
    return [(s, e) for s, e in spans if paragraph[s:e].strip()]


def _merge_short_spans(paragraph: str, spans: list[tuple[int, int]],
                       min_chars: int) -> list[tuple[int, int]]:
    """Keep extending a span forward until it clears min_chars -- catches a
    bare paragraph number, an uncaught abbreviation, or OCR debris without
    needing an exhaustive dictionary. Still a pure slice of `paragraph`, so
    still verbatim by construction."""
    out: list[tuple[int, int]] = []
    buf_start = None
    buf_end = None
    for start, end in spans:
        if buf_start is None:
            buf_start = start
        buf_end = end
        if (buf_end - buf_start) >= min_chars:
            out.append((buf_start, buf_end))
            buf_start = None
    if buf_start is not None:
        if out:
            out[-1] = (out[-1][0], buf_end)
        else:
            out.append((buf_start, buf_end))
    return out


def split_sentences(paragraph: str) -> list[tuple[str, int, int]]:
    """Real sentences with char offsets INTO the paragraph they came from.
    Every returned (text, start, end) satisfies paragraph[start:end] == text
    -- never reconstructed, always a real slice.

    Splits on [.!?] before a capital/digit, but a raw split alone would break
    "Rs." (amount marker), "No." (numbering), name initials ("Y.V.") and
    similar mid-sentence -- these get merged back into the following span
    instead of standing alone as fake "sentences" (see MIN_SENTENCE_CHARS).
    """
    raw_spans = _raw_sentence_spans(paragraph)

    merged: list[tuple[int, int]] = []
    for start, end in raw_spans:
        if merged and _ends_with_abbreviation(paragraph[merged[-1][0]:merged[-1][1]]):
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    merged = _merge_short_spans(paragraph, merged, MIN_SENTENCE_CHARS)

    out: list[tuple[str, int, int]] = []
    for start, end in merged:
        text = paragraph[start:end]
        stripped = text.strip()
        if not stripped:
            continue
        lead = len(text) - len(text.lstrip())
        real_start = start + lead
        real_end = real_start + len(stripped)
        out.append((stripped, real_start, real_end))
    return out


def _rank_deterministic(sentences: list[str]) -> list[float]:
    """No-ML fallback: score = count of deterministic-fact hits, longer
    sentences among ties lose (a fact-dense short sentence beats a long one
    padded with boilerplate)."""
    scores = []
    for s in sentences:
        hits = sum(len(p.findall(s)) for p in _FACT_PATTERNS)
        scores.append(hits - 0.001 * len(s))
    return scores


def _embed_sentences(sentences: list[str]):
    """One batched embedding call. Returns None (never raises) if the
    optional dependency isn't installed, so the caller can fall back to the
    deterministic scorer -- same degrade contract as make_similarity_fn().

    Speed matters here specifically because this used to be called once PER
    PARAGRAPH (see extract_important_lines): a 40-paragraph section meant 40
    small `.encode()` calls, each paying its own Python/model call overhead.
    Callers now batch every eligible sentence in a section into one call and
    slice the resulting matrix per paragraph -- same ranking math, a single
    model invocation instead of one per paragraph.
    """
    global _IL_EMBED
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    if _IL_EMBED is None:
        _IL_EMBED = SentenceTransformer(EMBED_MODEL_NAME)
    return _IL_EMBED.encode(sentences, normalize_embeddings=True)


def _centrality_scores(embs) -> list[float]:
    """Mean-similarity centrality (F-11's validated ranking) from an
    already-computed embedding matrix -- no model call here."""
    import numpy as np
    sim = embs @ embs.T
    np.fill_diagonal(sim, 0.0)
    return sim.mean(axis=1).tolist()


def rank_sentences(sentences: list[str], use_embeddings: bool = True) -> tuple[list[float], str]:
    """Ranks ONE paragraph's sentences. Convenience/test entry point -- for
    a whole document, extract_important_lines() batches all paragraphs'
    embedding calls into one instead of calling this per paragraph."""
    if use_embeddings:
        embs = _embed_sentences(sentences)
        if embs is not None:
            return _centrality_scores(embs), "embedding"
    return _rank_deterministic(sentences), "deterministic"


def extract_important_lines(section: dict, section_text: str, offsets: list,
                            document_id: str, start_paragraph_no: int = 1,
                            use_embeddings: bool = True,
                            min_sentences: int = MIN_SENTENCES_PER_PARAGRAPH,
                            top_k: int = TOP_K_PER_PARAGRAPH) -> tuple[list[dict], int]:
    """Walks section_text's real paragraphs in reading order, keeps the most
    central sentence(s) of each paragraph long enough to be worth compressing.

    Returns (events, next_paragraph_no) -- paragraph numbering is a running
    counter the caller threads across sections so it counts up through the
    whole document, matching what a reader would call "paragraph 12" in the
    original filing, not "paragraph 3 of section 4".
    """
    events: list[dict] = []

    # Pass 1: split every paragraph, decide eligibility, but don't rank yet --
    # this lets embedding-backed ranking batch ALL of this section's sentences
    # into one model call below, instead of one call per eligible paragraph.
    eligible: list[tuple[int, str, int, list[tuple[str, int, int]]]] = []
    paragraph_no = start_paragraph_no
    for para_text, para_start, para_end in split_paragraphs(section_text):
        sentences = split_sentences(para_text)
        if len(sentences) >= min_sentences:
            eligible.append((paragraph_no, para_text, para_start, sentences))
        paragraph_no += 1
    next_paragraph_no = paragraph_no

    if not eligible:
        return events, next_paragraph_no

    backend = "deterministic"
    embs_all = None
    if use_embeddings:
        flat_sentences = [s for _, _, _, sents in eligible for s, _, _ in sents]
        embs_all = _embed_sentences(flat_sentences)
        if embs_all is not None:
            backend = "embedding"

    cursor = 0
    for paragraph_no, para_text, para_start, sentences in eligible:
        n = len(sentences)
        if backend == "embedding":
            scores = _centrality_scores(embs_all[cursor:cursor + n])
        else:
            scores = _rank_deterministic([s for s, _, _ in sentences])
        cursor += n

        ranked = sorted(range(n), key=lambda i: -scores[i])[:top_k]
        for i in sorted(ranked):
            sent_text, sent_start, sent_end = sentences[i]
            abs_start = para_start + sent_start
            abs_end = para_start + sent_end
            page = offset_to_page(abs_start, offsets)
            # display-only: collapse internal tabs/newlines from the source
            # PDF's own layout so the node label reads as one clean line --
            # "text"/"sources[0].text" below stay byte-verbatim, unaffected.
            display = re.sub(r"\s+", " ", sent_text).strip()

            events.append({
                "type": "IMPORTANT_LINE",
                "document_id": document_id,
                "section_label": section["section_label"],
                "section_text": sent_text,
                "label": display[:100] + ("..." if len(display) > 100 else ""),
                "linked_entities": [],
                "linked_date": None,
                "linked_amount": None,
                "polarity": "NEUTRAL",
                "confidence": f"extractive_{backend}",
                "sources": [{
                    "document": document_id,
                    "page": page,
                    "char_start": abs_start,
                    "char_end": abs_end,
                    "text": sent_text,
                    "section": section["section_label"],
                    "paragraph": paragraph_no,
                }],
            })

    return events, next_paragraph_no
