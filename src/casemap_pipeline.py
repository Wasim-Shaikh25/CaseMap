"""
casemap_pipeline.py — CaseMap core pipeline (corrected v2)

Fixes applied over the v1 spec code:
  BUG-1  to_react_flow / build_evidence_card crashed on None values (.get on None)
  BUG-2  Provenance pointed at the FIRST page of a section, not the page the fact
         was actually on. This silently broke the product's core promise.
  BUG-3  ocr_fallback() reopened the PDF on every single page (O(pages) file opens)
  BUG-4  get_toc() was copied onto every page record
  BUG-5  Entity normalization merged across types (a PERSON could absorb an ORG)
  BUG-6  events never carried section_text, so the similarity fn had nothing to read
  BUG-7  unused variable / dead code in normalize_entities
  BUG-8  no OCR caching — re-running the POC re-OCR'd everything (minutes per run)

Design change for scanned-heavy corpora:
  OCR is now a FIRST-CLASS stage, not a fallback. See ocr.py section below.

No external services required. No Neo4j. No GPU.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# STAGE 0 — OCR LAYER (first-class, because most legal scans need it)
# ---------------------------------------------------------------------------

OCR_CACHE_DIR = ".casemap_ocr_cache"


def _file_fingerprint(pdf_path: str, page_number: int, dpi: int) -> str:
    """Cache key that changes if the file changes."""
    st = os.stat(pdf_path)
    raw = f"{os.path.abspath(pdf_path)}|{st.st_size}|{st.st_mtime_ns}|{page_number}|{dpi}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _cache_get(key: str) -> Optional[dict]:
    path = os.path.join(OCR_CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _cache_put(key: str, value: dict) -> None:
    os.makedirs(OCR_CACHE_DIR, exist_ok=True)
    with open(os.path.join(OCR_CACHE_DIR, f"{key}.json"), "w", encoding="utf-8") as f:
        json.dump(value, f)


def preprocess_for_ocr(pil_image):
    """Deskew + denoise + adaptive threshold.

    On real court scans (photocopies of photocopies, slight rotation from a
    flatbed feed) this is worth more accuracy than switching OCR engines.
    Falls back to the raw image if OpenCV isn't available.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return pil_image

    import numpy as np
    from PIL import Image

    img = np.array(pil_image.convert("L"))

    # Deskew: estimate dominant text angle from the minimum-area rect of ink pixels
    coords = np.column_stack(np.where(img < 200))
    if coords.size > 0:
        angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 0.3:  # don't rotate for negligible skew
            h, w = img.shape
            m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            img = cv2.warpAffine(img, m, (w, h),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REPLICATE)

    img = cv2.fastNlMeansDenoising(img, h=10)
    img = cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return Image.fromarray(img)


def ocr_page(doc, pdf_path: str, page_number: int, dpi: int = 300,
             engine: str = "tesseract", lang: str = "eng") -> dict:
    """OCR a single page. `doc` is an ALREADY-OPEN fitz document (fixes BUG-3).

    Returns {"text": str, "words": [{"text","x0","y0","x1","y1"}]}.
    Word boxes are what let the UI highlight the exact passage, not just
    jump to the page — keep them even though the MVP may not use them yet.
    """
    key = _file_fingerprint(pdf_path, page_number, dpi) + f"_{engine}_{lang}"
    cached = _cache_get(key)
    if cached is not None:
        return cached  # fixes BUG-8: OCR once, reuse across every POC re-run

    import io

    from PIL import Image

    pix = doc[page_number - 1].get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    img = preprocess_for_ocr(img)

    if engine == "paddle":
        result = _ocr_paddle(img, lang)
    elif engine == "surya":
        result = _ocr_surya(img, lang)
    else:
        result = _ocr_tesseract(img, lang)

    _cache_put(key, result)
    return result


def _words_to_lines_text(words: list[dict], y_tolerance: float = 0.6) -> str:
    """Reconstruct newline-separated TEXT from word boxes, grouped by row.

    BUG FOUND DURING REAL-PDF TESTING: the original version joined every
    word with a single space regardless of position, producing ONE fused
    line per page ("REPORTABLE IN THE SUPREME COURT ... SHAILESH KUMAR ..
    Appellant VERSUS STATE OF MAHARASHTRA .. Respondents JUDGMENT ...").
    Every line-based rule downstream -- is_versus_line(), BODY_START_RE,
    TOC-dot-leader detection, heading regexes -- silently failed on real
    OCR output because there were no lines to test against. Confirmed live:
    a real Supreme Court judgment rendered to an image and OCR'd through
    the old path returned ZERO parties; through this fix it returns both.

    layout_structure.py's lines_from_ocr_words() already does row-grouping
    correctly for its own purposes; this reuses the same logic so the plain
    `text` field callers rely on (document_profile.py, casemap's own
    heading detection) gets real line breaks too, not just the structure
    module's internal Line objects.
    """
    import statistics
    if not words:
        return ""
    heights = [w["y1"] - w["y0"] for w in words if w["y1"] > w["y0"]]
    med_h = statistics.median(heights) if heights else 10.0
    tol = med_h * y_tolerance

    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: ((w["y0"] + w["y1"]) / 2, w["x0"])):
        mid = (w["y0"] + w["y1"]) / 2
        placed = False
        for row in rows:
            rmid = statistics.mean((x["y0"] + x["y1"]) / 2 for x in row)
            if abs(mid - rmid) <= tol:
                row.append(w)
                placed = True
                break
        if not placed:
            rows.append([w])

    lines = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        lines.append(" ".join(str(w["text"]) for w in row))
    return "\n".join(lines)


def _ocr_tesseract(img, lang: str) -> dict:
    """Baseline engine. Zero setup, weakest on degraded scans.
    `lang` accepts Tesseract codes, incl. Indic: 'hin', 'mar', 'tam', 'ben',
    and combinations like 'eng+hin' for mixed-script court documents.
    """
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(img, lang=lang, output_type=Output.DICT)
    words = []
    for i, txt in enumerate(data["text"]):
        if txt and txt.strip() and int(data["conf"][i]) > 0:
            words.append({
                "text": txt,
                "x0": data["left"][i], "y0": data["top"][i],
                "x1": data["left"][i] + data["width"][i],
                "y1": data["top"][i] + data["height"][i],
                "conf": int(data["conf"][i]),
            })
    return {"text": _words_to_lines_text(words), "words": words}


def _ocr_paddle(img, lang: str) -> dict:
    """RECOMMENDED for scanned legal corpora. Markedly better than Tesseract
    on low-contrast photocopies and stamped/annotated pages. CPU-runnable.
    """
    import numpy as np
    from paddleocr import PaddleOCR

    global _PADDLE
    try:
        _PADDLE
    except NameError:
        _PADDLE = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    result = _PADDLE.ocr(np.array(img), cls=True)
    words = []
    for line in (result[0] or []):
        box, (txt, conf) = line[0], line[1]
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        words.append({"text": txt, "x0": min(xs), "y0": min(ys),
                      "x1": max(xs), "y1": max(ys), "conf": float(conf)})
    # Paddle already returns line-level boxes (not word-level), so each
    # "word" here is really a full line -- still safe to run through the
    # same row-grouping reconstruction for a consistent text field.
    return {"text": _words_to_lines_text(words), "words": words}


def _ocr_surya(img, lang: str) -> dict:
    """Best raw accuracy of the three, incl. Indic scripts. Heaviest model
    download; runs on CPU but slowly. Use when Paddle output is too noisy.
    """
    from surya.model.detection.model import load_model as load_det
    from surya.model.recognition.model import load_model as load_rec
    from surya.model.recognition.processor import load_processor
    from surya.ocr import run_ocr

    global _SURYA
    try:
        _SURYA
    except NameError:
        _SURYA = (load_det(), load_rec(), load_processor())
    det_model, rec_model, rec_processor = _SURYA

    preds = run_ocr([img], [[lang]], det_model, None, rec_model, rec_processor)
    words, parts = [], []
    for line in preds[0].text_lines:
        parts.append(line.text)
        words.append({"text": line.text, "x0": line.bbox[0], "y0": line.bbox[1],
                      "x1": line.bbox[2], "y1": line.bbox[3],
                      "conf": float(getattr(line, "confidence", 0.0) or 0.0)})
    return {"text": "\n".join(parts), "words": words}


# ---------------------------------------------------------------------------
# STAGE 1 — PAGE-PRESERVING EXTRACTION
# ---------------------------------------------------------------------------

def classify_page(page, raw_text: str) -> str:
    """Three-way classification, not a binary needs_ocr flag.

    'digital'  — real embedded text, use it
    'scanned'  — no text layer, must OCR
    'hybrid'   — has SOME text but is mostly image (a typed order with a
                 scanned annexure pasted in, very common in court paperbooks).
                 OCR these too and merge, or you lose the scanned half.
    """
    text_len = len(raw_text.strip())
    has_images = len(page.get_images(full=True)) > 0

    if text_len < 20:
        return "scanned"
    if text_len < 200 and has_images:
        return "hybrid"
    return "digital"


def extract_pages(pdf_path: str, ocr_engine: str = "paddle",
                  ocr_lang: str = "eng", force_ocr: bool = False) -> list[dict]:
    """One record per page, with text resolved via OCR where needed."""
    import fitz

    doc = fitz.open(pdf_path)          # opened ONCE (fixes BUG-3)
    toc = doc.get_toc(simple=True)     # fetched ONCE (fixes BUG-4)
    pages = []

    for i, page in enumerate(doc):
        page_number = i + 1
        raw_text = page.get_text("text")
        kind = "scanned" if force_ocr else classify_page(page, raw_text)

        words = []
        if kind == "scanned":
            r = ocr_page(doc, pdf_path, page_number, engine=ocr_engine, lang=ocr_lang)
            text, words = r["text"], r["words"]
        elif kind == "hybrid":
            r = ocr_page(doc, pdf_path, page_number, engine=ocr_engine, lang=ocr_lang)
            text = raw_text + "\n" + r["text"]
            words = r["words"]
        else:
            text = raw_text

        pages.append({
            "document": os.path.basename(pdf_path),
            "document_path": pdf_path,
            "page_number": page_number,
            "text": text,
            "page_kind": kind,
            "words": words,
        })

    doc.close()
    return {"pages": pages, "toc": toc}


# ---------------------------------------------------------------------------
# STAGE 2 — STRUCTURE DETECTION WITH FALLBACK
# ---------------------------------------------------------------------------

ANNEXURE_PATTERN = re.compile(
    r"^\s*(?:(?:[IVXLCDM]{1,7}|\d{1,2})[.)]\s*)?"  # real petitions number these
    r"(ANNEXURE[\s\-–]*[A-Z0-9\-/]+|EXHIBIT\s+[A-Z0-9\-]+|AFFIDAVIT|SYNOPSIS|"
    r"LIST OF DATES(?:\s+AND\s+EVENTS)?|WRITTEN STATEMENT|"
    r"(?:INTERIM\s+|FINAL\s+|ADDITIONAL\s+|MAIN\s+)?PRAYER(?:\s+FOR\s+RELIEF)?|"
    r"GROUNDS(?:\s+FOR\s+INTERIM\s+RELIEF)?|INTERIM\s+RELIEF|"
    r"QUESTIONS?(?:\(S\))? OF LAW|MEMO OF PARTIES|INDEX|VAKALATNAMA)\s*[:.]?\s*$", re.I)

# Two TOC forms: dot-leader, and whitespace-column (common in Indian indexes)
TOC_DOTTED = re.compile(r"^(.{3,90}?)[.·]{3,}\s*(\d{1,4})\s*$")
TOC_COLUMNAR = re.compile(r"^\s*(?:\d{1,2}[.)]\s+)?(.{5,80}?)\s{2,}(\d{1,4})\s*$")


def detect_structure(pages: list[dict], toc: list) -> dict:
    signals = {"has_bookmarks": bool(toc), "toc_pages": [], "headings": []}

    for p in pages:
        text = p["text"]
        lines = text.splitlines()
        toc_hits = sum(1 for l in lines
                       if TOC_DOTTED.match(l) or TOC_COLUMNAR.match(l))
        if toc_hits >= 3:
            signals["toc_pages"].append(p["page_number"])
        cursor = 0
        for raw_line in text.splitlines(keepends=True):
            stripped = raw_line.strip()
            if ANNEXURE_PATTERN.match(stripped):
                # offset lets _segment_by_headings split WITHIN a single page
                # -- needed for .txt input, which loads an entire filing as
                # one "page", so a real petition's GROUNDS/PRAYER/AFFIDAVIT
                # headings all share page_number 1 and would otherwise
                # collapse into a single section (found running the pipeline
                # against a real filed petition, 2026-09-10).
                signals["headings"].append({"page": p["page_number"],
                                            "text": stripped, "offset": cursor})
            cursor += len(raw_line)

    # OCR'd pages produce noisier text, so demand slightly more evidence
    scanned_ratio = sum(1 for p in pages if p["page_kind"] != "digital") / max(len(pages), 1)
    threshold = 4 if scanned_ratio > 0.5 else 3

    score = (3 * signals["has_bookmarks"]
             + 2 * len(signals["toc_pages"])
             + 1 * len(signals["headings"]))
    signals["structure_score"] = score
    signals["scanned_ratio"] = round(scanned_ratio, 2)
    signals["mode"] = "structured" if score >= threshold else "fallback"
    return signals


def segment_document(pages: list[dict], signals: dict) -> list[dict]:
    """Same output shape in both modes, so downstream never branches."""
    if signals["mode"] == "structured" and signals["headings"]:
        return _segment_by_headings(pages, signals["headings"])
    return [{"section_label": f"p.{p['page_number']}", "pages": [p], "detected": False}
            for p in pages]


def segment_document_layered(pdf_path: str, pages: list[dict],
                             toc: list | None = None) -> tuple[list[dict], dict]:
    """Entry point kept stable for callers/tests; `pdf_path` is unused.

    A Docling-backed layout layer (`layout_structure.py`) previously sat in
    front of the text-pattern detector below. Removed 2026-09-11 (FINDINGS.md
    F-21): it was never installed in this project's own .venv (a deliberate,
    never-changed choice, so the Docling path never actually ran in the
    deployed app), its OCR benefit fully duplicates the pipeline's own
    first-class OCR stage (STAGE 0 above), and its one distinct capability --
    generic ML layout-based heading detection -- was only ever measured on
    heading-text correctness, never on any downstream extraction-accuracy
    gain, against a 1.5GB weight the project's own small-model philosophy
    already rejected once for Qwen3-Embedding (F-15/F-19). The (tier,
    confidence, tier_reason, stats) return shape is unchanged so the report
    and tests need no changes.
    """
    signals = detect_structure(pages, toc or [])
    return segment_document(pages, signals), {
        "tier": "legacy_text_patterns", "confidence": "unknown",
        "tier_reason": "text-pattern detector (ANNEXURE_PATTERN/TOC/bookmarks)",
        "stats": signals}


def _segment_by_headings(pages, headings) -> list[dict]:
    """One section boundary per heading, not per page. A PDF's headings
    (no "offset" key) are usually one per physical page already --
    unaffected. A .txt input loads its entire
    filing as a SINGLE page, so a real petition's GROUNDS/PRAYER/AFFIDAVIT
    headings all share page_number 1: without splitting by offset within
    that one page, they'd collapse into a single section labeled after
    whichever heading happened to be first (found running the pipeline
    against a real filed petition, 2026-09-10 -- see FINDINGS.md F-11
    addendum / CHANGELOG (36))."""
    headings_by_page: dict = defaultdict(list)
    for h in headings:
        headings_by_page[h["page"]].append(h)
    for hs in headings_by_page.values():
        hs.sort(key=lambda h: h.get("offset", 0))

    # (page_dict, heading_label_or_None) -- expand a page with N>1 headings
    # into N page-dicts (same page_number, sliced text), each carrying its
    # own heading; a page with 0 or 1 headings passes through unchanged.
    expanded: list[tuple[dict, Optional[str]]] = []
    for p in pages:
        hs = headings_by_page.get(p["page_number"], [])
        if len(hs) <= 1:
            expanded.append((p, hs[0]["text"] if hs else None))
            continue
        text = p["text"]
        offsets = [h.get("offset", 0) for h in hs] + [len(text)]
        for i, h in enumerate(hs):
            chunk = text[offsets[i]:offsets[i + 1]]
            if chunk.strip():
                expanded.append(({**p, "text": chunk}, h["text"]))

    sections, current = [], None
    for p, heading_label in expanded:
        if current is None or heading_label is not None:
            current = {"section_label": heading_label or "Document",
                       "pages": [], "detected": True}
            sections.append(current)
        current["pages"].append(p)
    return sections


# ---------------------------------------------------------------------------
# CRITICAL FIX (BUG-2) — CHARACTER OFFSET -> EXACT PAGE
# ---------------------------------------------------------------------------

def build_section_text(section: dict) -> tuple[str, list[tuple[int, int, int]]]:
    """Concatenate a section's pages while recording which char range came
    from which page. Without this, every fact in a multi-page section reports
    the section's FIRST page as its source — which is wrong, and the whole
    product promise is exact-page traceability.
    """
    parts, offsets, cursor = [], [], 0
    for p in section["pages"]:
        t = p["text"]
        parts.append(t)
        offsets.append((cursor, cursor + len(t), p["page_number"]))
        cursor += len(t) + 1  # +1 for the "\n" inserted by join
    return "\n".join(parts), offsets


def offset_to_page(offset: int, offsets: list[tuple[int, int, int]]) -> Optional[int]:
    for start, end, page_number in offsets:
        if start <= offset < end:
            return page_number
    return offsets[-1][2] if offsets else None


# ---------------------------------------------------------------------------
# STAGE 3 — DETERMINISTIC EXTRACTION (now offset-aware)
# ---------------------------------------------------------------------------

# `\d[\d,]*` (must START with a digit), not `[\d,]+`: the old class accepted a
# bare comma, so "Rs.," and "Rs," (a currency marker with no figure at all, very
# common in real filings: "a sum of Rs. ____") matched as an "amount" of just a
# comma. Surfaced as junk "rs,"/"rs.," entries in the amounts list. A real
# amount always has at least one digit.
AMOUNT_PATTERN = re.compile(
    r"(?:Rs\.?|₹|INR)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:lakh|lakhs|crore|crores))?", re.I)
CASE_NUMBER_PATTERN = re.compile(
    r"\b(?:C\.?S\.?|W\.?P\.?|Crl\.?|C\.?A\.?|SLP|O\.?A\.?)\s?"
    r"(?:\(\w+\)\s?)?No\.?\s?\d+\s?(?:of|[/-])\s?\d{2,4}\b", re.I)
SECTION_PATTERN = re.compile(
    r"\b(?:Section|Sec\.?|S\.)\s?\d+[A-Z]{0,2}\b|\bOrder\s+[IVXL]+\s+Rule\s+\d+\b", re.I)
DATE_CANDIDATE_PATTERN = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?[\s.]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    # DD/MM/YYYY, DD-MM-YYYY, AND DD.MM.YYYY (the numeric-date branch below
    # only accepted "/" and "-" as separators — "." never matched, even
    # though DD.MM.YYYY is the standard numeric-date format in Indian court
    # filings and circulars ("24.09.2024"). Found via a real petition where
    # every single date in the document uses dots and none were extracted.
    # A trailing 4-digit year plus two more digit groups is specific enough
    # that this doesn't start matching ordinary decimal/paragraph numbering
    # like "3.1." or "7A.2." (those never have a 4-digit final group).
    r"[a-z]*[\s.,]+\d{4}\b"
    # Month name FIRST ("December 5, 2025", "Dec 5th 2025") — the branch
    # above only matched DAY-then-month ("5 December 2025"). Found by
    # direct audit, not a real-document report this time: month-first is
    # the standard US legal-filing convention, and this pipeline had zero
    # coverage for it despite already targeting mixed real-world sources.
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s.]+"
    r"\d{1,2}(?:st|nd|rd|th)?[\s.,]+\d{4}\b"
    # ISO 8601 (YYYY-MM-DD) — increasingly common in anything
    # software-generated (court e-filing portals, cause-list exports).
    r"|\b\d{4}-\d{1,2}-\d{1,2}\b"
    r"|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b", re.I)


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")


def extract_deterministic(text: str, offsets: list) -> dict:
    import dateparser
    from datetime import date as _date

    dates = []
    for m in DATE_CANDIDATE_PATTERN.finditer(text):
        raw = m.group()
        if _ISO_DATE_RE.match(raw):
            # ISO 8601 is unambiguous (YYYY-MM-DD) — forcing DATE_ORDER=DMY
            # on it made dateparser swap month/day anyway (verified
            # directly: "2025-12-05" parsed to 2025-05-12, silently wrong).
            # Parse it directly instead of routing through the DMY-biased
            # settings meant for the ambiguous DD/MM/YYYY-style formats.
            try:
                parsed_date = _date.fromisoformat(raw)
            except ValueError:
                parsed_date = None
            if parsed_date:
                dates.append({"raw": raw, "iso": parsed_date.isoformat(),
                              "span": m.span(), "page": offset_to_page(m.start(), offsets)})
            continue
        parsed = dateparser.parse(raw, settings={"DATE_ORDER": "DMY"})
        if parsed:
            dates.append({"raw": raw, "iso": parsed.date().isoformat(),
                          "span": m.span(), "page": offset_to_page(m.start(), offsets)})

    def collect(pattern):
        return [{"raw": m.group(), "span": m.span(),
                 "page": offset_to_page(m.start(), offsets)}
                for m in pattern.finditer(text)]

    return {"dates": dates, "amounts": collect(AMOUNT_PATTERN),
            "case_numbers": collect(CASE_NUMBER_PATTERN),
            "sections": collect(SECTION_PATTERN)}


# ---------------------------------------------------------------------------
# STAGE 4 — ENTITIES + TYPE-AWARE NORMALIZATION
# ---------------------------------------------------------------------------

_NLP = None

# Confirmed generic-NER noise from FINDINGS.md F-8 (22-doc addendum). Exact
# match, case-insensitive, PERSON/ORG/GPE only — not MONEY. A stoplist is
# FR2 only; header-region exclusion (FR1) is the architectural fix for
# multi-line / truncated header grabs. See
# docs/requirements/2026-09-10-entity-extraction-header-noise/.
GENERIC_ENTITY_TEXT = {
    "court", "the court", "high court", "the high court",
    "sessions court", "the sessions court", "supreme court", "the supreme court",
    "the supreme court of india",
    "versus", "order", "notice", "judgment", "appeal",
    "justice", "adv", "slp", "anr", "union of india",
}

# indiankanoon / judgment caption furniture — first 40 lines only
_FURNITURE_LINE_RE = re.compile(
    r"^(equivalent citations|author|bench|reportable|source:)\b", re.I)
# reporter citations mislabeled as ORG (AIR 2014 SUPREME COURT, …)
_REPORTER_CITATION_RE = re.compile(r"\bAIR\s+\d{4}\b|\bAIRONLINE\b", re.I)


def _is_generic_entity(label: str, name: str) -> bool:
    if label not in ("PERSON", "ORG", "GPE"):
        return False
    return (name or "").strip().lower() in GENERIC_ENTITY_TEXT


def _is_reporter_citation(name: str) -> bool:
    return bool(_REPORTER_CITATION_RE.search(name or ""))


def _title_block_char_range(text: str) -> Optional[tuple[int, int]]:
    """Char span of the cause-title region, or None if none found / import fail.

    Uses document_profile.extract_cause_title_block (already in this repo).
    Line indices from that function map onto text.splitlines(keepends=True).
    """
    try:
        from document_profile import extract_cause_title_block
    except ImportError:
        return None
    block = extract_cause_title_block(text)
    if block is None:
        return None
    lines = text.splitlines(keepends=True)
    if not lines or block.line_start >= len(lines):
        return None
    start = sum(len(l) for l in lines[:block.line_start])
    end = sum(len(l) for l in lines[:min(block.line_end + 1, len(lines))])
    if end <= start:
        return None
    return start, end


def _furniture_prefix_end(text: str) -> int:
    """Char offset after the last caption-furniture line in the first 40 lines.

    `Equivalent citations` / `Bench:` sit *above* the versus block, so excluding
    only TitleBlock.line_start–line_end left them in generic NER.
    """
    lines = text.splitlines(keepends=True)
    end = 0
    for i, line in enumerate(lines[:40]):
        if _FURNITURE_LINE_RE.match((line or "").strip()):
            end = sum(len(l) for l in lines[: i + 1])
    return end


def _header_exclude_end(text: str) -> int:
    """First body char: after preamble + cause title, or 0 if neither found."""
    end = _furniture_prefix_end(text)
    rng = _title_block_char_range(text)
    if rng is not None:
        end = max(end, rng[1])
    return end


def _body_segments_excluding_title_block(text: str) -> list[tuple[int, str]]:
    """(original_char_offset, substring) for generic NER.

    Excludes [0, header_end) — preamble through cause title — not only the
    versus-bounded interior. Empty if the whole document is header.
    """
    he = _header_exclude_end(text)
    if he <= 0:
        return [(0, text)]
    if he >= len(text):
        return []
    return [(he, text[he:])]


def extract_entities(text: str, offsets: list, use_gliner: bool = False) -> list[dict]:
    if use_gliner:
        return _extract_entities_gliner(text, offsets)

    global _NLP
    if _NLP is None:
        import spacy
        _NLP = spacy.load("en_core_web_sm")

    keep = {"PERSON", "ORG", "GPE", "MONEY"}
    out = []
    # spaCy has a 1M-char limit; chunk long sections defensively
    for seg_origin, seg_text in _body_segments_excluding_title_block(text):
        for chunk_start in range(0, len(seg_text), 900_000):
            chunk = seg_text[chunk_start:chunk_start + 900_000]
            for ent in _NLP(chunk).ents:
                if ent.label_ not in keep:
                    continue
                if _is_generic_entity(ent.label_, ent.text):
                    continue
                if _is_reporter_citation(ent.text):
                    continue
                # F-8 category (2): generic NER grabbing a line-wrap as one
                # entity. A real PERSON/ORG/GPE name is a single typographic
                # line; a newline in the span is formatting, not a name.
                if "\n" in ent.text:
                    continue
                abs_start = seg_origin + chunk_start + ent.start_char
                abs_end = seg_origin + chunk_start + ent.end_char
                out.append({"text": ent.text.strip(), "label": ent.label_,
                            "span": (abs_start, abs_end),
                            "page": offset_to_page(abs_start, offsets)})
    return out


def _extract_entities_gliner(text: str, offsets: list) -> list[dict]:
    from gliner import GLiNER

    global _GLINER
    try:
        _GLINER
    except NameError:
        _GLINER = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")

    labels = ["person", "organization", "court", "legal provision", "case number"]
    out = []
    for chunk_start in range(0, len(text), 3000):  # GLiNER prefers short windows
        chunk = text[chunk_start:chunk_start + 3000]
        for r in _GLINER.predict_entities(chunk, labels, threshold=0.4):
            abs_start = chunk_start + r["start"]
            out.append({"text": r["text"].strip(),
                        "label": r["label"].upper().replace(" ", "_"),
                        "span": (abs_start, chunk_start + r["end"]),
                        "page": offset_to_page(abs_start, offsets)})
    return out


def _canonical_key(name: str) -> str:
    from case_symbols import normalize_name
    return normalize_name(name)


def normalize_entities(entities: list[dict], threshold: int = 88) -> dict:
    """Type-aware fuzzy dedup (fixes BUG-5 and BUG-7).

    Matching is scoped WITHIN an entity type — a PERSON can never be merged
    into an ORG just because the strings look similar.

    IDs are derived from the canonical name itself (`f"{etype}:{key}"`),
    NOT a call-local sequential counter. This function is called fresh
    once per SECTION across the whole pipeline (poc_run.py and
    server/app.py both do this — not a bug introduced by either, it's how
    this was always called). With a counter, "Bank of Baroda" gets
    "ent_0003" in one section (the 3rd entity encountered there) and
    "ent_0001" in another (the 1st entity there) — same real entity, two
    different IDs, entirely dependent on encounter order within that one
    isolated call. Verified directly: this made build_inverted_index()'s
    entity_overlap scoring connect real-world-UNRELATED documents whose
    entity counters happened to collide (a civil property case and a
    financial cheque-bounce case scored entity_overlap=1.0 with zero real
    shared parties), while giving no guarantee that genuinely shared
    parties connect at all if their encounter order differs. Deriving the
    ID from the name instead makes it a pure function of WHAT the entity
    is, stable across any section, any document, any call, with no shared
    state required. No test asserts the exact "ent_NNNN" string — only
    relational connectivity — so this only makes existing behavior more
    correct, verified via the full suite."""
    from rapidfuzz import fuzz, process

    canonical_by_type: dict[str, dict[str, str]] = defaultdict(dict)
    mapping: dict[tuple[str, str], str] = {}

    for e in entities:
        etype, name = e["label"], e["text"].strip()
        if not name:
            continue
        if _is_generic_entity(etype, name):
            continue
        if _is_reporter_citation(name):
            continue
        if "\n" in name:
            continue
        key = _canonical_key(name)
        if not key:
            continue

        pool = canonical_by_type[etype]
        match = (process.extractOne(key, list(pool.keys()),
                                    scorer=fuzz.token_sort_ratio,
                                    score_cutoff=threshold) if pool else None)
        if match:
            cid = pool[match[0]]
        else:
            cid = f"{etype}:{key}"
            pool[key] = cid
        mapping[(etype, name)] = cid

    return mapping


# ---------------------------------------------------------------------------
# STAGE 5 — EVENT / STATEMENT DETECTION (offset-aware, page-accurate)
# ---------------------------------------------------------------------------

EVENT_KEYWORDS = {
    "PAYMENT": ["paid", "payment of", "transferred", "remitted", "received a sum"],
    "TERMINATION": ["terminated", "termination of", "revoked", "rescinded"],
    "NOTICE": ["legal notice", "hereby notified", "notice dated", "served a notice"],
    "AGREEMENT": ["agreement dated", "entered into", "executed an agreement"],
    "ORDER": ["it is ordered", "the court directs", "order dated", "hereby directed"],
    "FILING": ["filed on", "instituted", "presented before"],
}
DENIAL_MARKERS = ["denies", "denied", "no such", "did not receive", "never received",
                  "false and baseless", "wrongly alleged", "disputed"]
ASSERTION_MARKERS = ["states that", "submits that", "acknowledges", "confirms",
                     "admits", "it is averred"]

# Verb-lemma polarity signal (F-18), UNION'd with the phrase lists above
# rather than replacing them -- same reasoning as EVENT_VERB_LEMMAS:
# DENIAL_MARKERS/ASSERTION_MARKERS only fire on an exact phrase ("did not
# receive") and miss the same claim in any other phrasing ("refutes the
# claim", "counsel contends that"). One VERB LEMMA (from en_core_web_sm's
# own parse, already loaded for entity extraction, no new model) catches
# every inflection a phrase list would have to enumerate one at a time.
#
# Deliberately does NOT also key off raw syntactic negation (spaCy's "neg"
# dependency tag, "not"/"never" attached to ANY verb) -- that was tried
# first and tested against a real writ petition
# (temp/2026-09-10-real-petition-run/BCI_NOC_WP.txt, never committed): an
# argumentative legal brief is full of negation as ordinary reasoning ("does
# not maintain", "cannot accomplish") that is not one party denying
# another's fact. That version mislabeled 20/111 events (18%) DENIES on
# real text, nearly all ordinary argument. DENIES/ASSERTS exists to feed
# label_edge()'s POTENTIAL_CONFLICT pairing, not to flag every negated
# sentence -- verb lemma alone is the more precise signal.
# Idiomatic non-verbal phrases ("false and baseless", "wrongly alleged")
# have no verb to key off, which is exactly why the original phrase lists
# are kept rather than dropped -- this is additive,
# like F-16/F-17, not a replacement.
DENIAL_VERB_LEMMAS = {"deny", "dispute", "refute", "contest", "rebut", "refuse"}
ASSERTION_VERB_LEMMAS = {"state", "submit", "acknowledge", "confirm", "admit",
                         "aver", "contend", "assert", "allege"}

WINDOW = 400  # chars either side of a keyword hit, for local context


def _trim_display_text(text: str, max_len: int) -> str:
    """Cut to at most max_len chars, ending at a real sentence if one
    falls in range, else the last whole word — never mid-word. Used for
    display-only text fields (never the verbatim spans other stages match
    against by exact offset)."""
    if len(text) <= max_len:
        return text
    cut = text.rfind(". ", 0, max_len)
    if cut > max_len * 0.4:
        return text[:cut + 1]
    sp = text.rfind(" ", 0, max_len)
    return text[:sp] if sp > max_len * 0.4 else text[:max_len]


def detect_events(section: dict, section_text: str, offsets: list,
                  det: dict, entity_map: dict, entities: list[dict],
                  document_id: str) -> list[dict]:
    """One event per keyword HIT (not per section), so each event gets the
    page where its evidence actually appears — the BUG-2 fix in practice.
    """
    lowered = section_text.lower()
    events = []

    for event_type, keywords in EVENT_KEYWORDS.items():
        for kw in keywords:
            start = 0
            while True:
                idx = lowered.find(kw, start)
                if idx == -1:
                    break
                start = idx + len(kw)

                page = offset_to_page(idx, offsets)
                lo, hi = max(0, idx - WINDOW), min(len(section_text), idx + WINDOW)
                context = section_text[lo:hi]

                near_dates = [d for d in det["dates"] if lo <= d["span"][0] <= hi]
                near_amounts = [a for a in det["amounts"] if lo <= a["span"][0] <= hi]
                near_entity_ids = sorted({
                    entity_map[(e["label"], e["text"].strip())]
                    for e in entities
                    if lo <= e["span"][0] <= hi
                    and (e["label"], e["text"].strip()) in entity_map
                })

                events.append({
                    "type": event_type,
                    "document_id": document_id,
                    "section_label": section["section_label"],
                    "section_text": context,        # fixes BUG-6
                    "linked_entities": near_entity_ids,
                    "linked_date": near_dates[0] if near_dates else None,
                    "linked_amount": near_amounts[0] if near_amounts else None,
                    "polarity": _classify_polarity(context.lower()),
                    "sources": [{
                        "document": document_id,
                        "page": page,                # EXACT page, not section start
                        "char_start": idx,
                        "char_end": idx + len(kw),
                        # A hard [:300] cut here reads as broken in the UI
                        # once something highlights this text (the drawer
                        # wraps it in <mark> against a wider paragraph
                        # context) — end at a real sentence when one falls
                        # in range, else the last whole word, never mid-word.
                        "text": _trim_display_text(context.strip(), 300),
                        "section": section["section_label"],
                    }],
                })
    return _dedupe_events(events)


# ---------------------------------------------------------------------------
# STAGE 4b -- SRL-style fact extraction: WHO/ACTION/WHAT/WHEN read directly
# off en_core_web_sm's own dependency parse and DATE/MODAL tags, no fixed
# phrase list (FINDINGS.md F-16).
#
# EVENT_KEYWORDS above only fires on an exact multi-word phrase ("filed on",
# "order dated") -- a real event phrased any other way ("Rohitsingh was
# acquitted...", "the wife left the matrimonial home...") is structurally
# invisible to it, not just uncommon. scripts/poc_srl_events_v2.py measured
# this directly against the REAL pipeline (including important_lines.py and
# casemap_service.py's own _events_for_uncovered_dates() fallback, not just
# this module in isolation): 23% of real event-bearing sentences on actual
# judgments were still missing everything above catches.
#
# This still only ever SELECTS and LABELS a real sentence -- it never
# generates one, so it carries the same verbatim guarantee as every other
# stage here (THESIS.md "judge, not generator").
#
# EVENT_VERB_LEMMAS below is deliberately much smaller than EVENT_KEYWORDS
# even though it covers strictly more surface forms: one LEMMA ("pay")
# matches every inflection and spacing variant a multi-word phrase list has
# to enumerate one at a time ("paid", "payment of", "pays", "paying a sum
# to", ...). A verb not in this map is never dropped -- it becomes type
# "FACT" (untyped, but still surfaced with its real WHO/WHAT/WHEN) rather
# than silently vanishing the way an unmatched EVENT_KEYWORDS phrase does.
EVENT_VERB_LEMMAS = {
    "pay": "PAYMENT", "remit": "PAYMENT", "transfer": "PAYMENT", "receive": "PAYMENT",
    "terminate": "TERMINATION", "revoke": "TERMINATION", "rescind": "TERMINATION",
    "cancel": "TERMINATION",
    "notify": "NOTICE", "serve": "NOTICE",
    "execute": "AGREEMENT", "sign": "AGREEMENT", "enter": "AGREEMENT",
    "order": "ORDER", "direct": "ORDER", "hold": "ORDER", "rule": "ORDER",
    "file": "FILING", "institute": "FILING", "present": "FILING",
}

_SRL_SUBJ_DEPS = {"nsubj", "nsubjpass"}
_SRL_OBJ_DEPS = {"dobj", "attr", "oprd", "dative"}


def _srl_root_verb(sent):
    for tok in sent:
        if tok.dep_ == "ROOT" and tok.pos_ in ("VERB", "AUX"):
            return tok
    return sent.root  # fragment/heading with no verbal root -- best effort


def _srl_fields(sent) -> tuple[list[str], str | None, list[str]]:
    root = _srl_root_verb(sent)
    who = [tok.text for tok in root.children if tok.dep_ in _SRL_SUBJ_DEPS]
    what = [tok.text for tok in root.children if tok.dep_ in _SRL_OBJ_DEPS]
    for child in root.children:
        if child.dep_ == "prep":
            what += [gc.text for gc in child.children if gc.dep_ == "pobj"]
    action = root.lemma_ if root.pos_ in ("VERB", "AUX") else None
    return who, action, what


def detect_events_srl(section: dict, section_text: str, offsets: list,
                       covered_spans: list[tuple[int, int]],
                       entity_map: dict, entities: list[dict],
                       document_id: str) -> list[dict]:
    """WHO/ACTION/WHAT/WHEN facts for any sentence with a real DATE entity
    or a modal verb (MD tag: will/would/could/shall/may/should/must) that no
    earlier stage already turned into an event. `covered_spans` is the
    caller's accumulated set of (char_start, char_end) from every earlier
    layer for this section (detect_events()'s keyword hits,
    important_lines.py, casemap_service.py's uncovered-dates fallback) --
    this function only adds what's still missing, never duplicates.

    Header/citation furniture (HEADNOTE blocks, "Equivalent citations",
    cause-title lines) is excluded via _header_exclude_end() -- the same
    function extract_entities() already uses for the same reason: a
    dependency parse over "Retrieved: 2026-09-09" produces a grammatically
    well-formed but meaningless WHO/WHAT, same failure class F-8 documents
    for generic NER on header text.
    """
    global _NLP
    if _NLP is None:
        import spacy
        _NLP = spacy.load("en_core_web_sm")

    header_end = _header_exclude_end(section_text)
    doc = _NLP(section_text[:900_000])
    out = []
    for sent in doc.sents:
        if sent.start_char < header_end:
            continue
        dates = [e for e in sent.ents if e.label_ == "DATE"]
        modals = [t for t in sent if t.tag_ == "MD"]
        if not dates and not modals:
            continue
        s_start, s_end = sent.start_char, sent.end_char
        if any(cs <= s_start and s_end <= ce for cs, ce in covered_spans):
            continue

        who, action, what = _srl_fields(sent)
        if not who and not what:
            continue

        near_entity_ids = sorted({
            entity_map[(e["label"], e["text"].strip())]
            for e in entities
            if s_start <= e["span"][0] <= s_end
            and (e["label"], e["text"].strip()) in entity_map
        })
        text = section_text[s_start:s_end].strip()

        out.append({
            "type": EVENT_VERB_LEMMAS.get(action, "FACT"),
            "document_id": document_id,
            "section_label": section["section_label"],
            "section_text": text,
            "linked_entities": near_entity_ids,
            "linked_date": None,    # attached uniformly by _link_dates_in_place
            "linked_amount": None,
            "polarity": "NEUTRAL",  # reclassified uniformly by the caller
            "confidence": "srl_parse",
            "who": who, "action": action, "what": what,
            "sources": [{
                "document": document_id, "page": offset_to_page(s_start, offsets),
                "char_start": s_start, "char_end": s_end,
                "text": text, "section": section["section_label"],
            }],
        })
    return out


def _dedupe_events(events: list[dict]) -> list[dict]:
    """Several keywords in one paragraph shouldn't become several events."""
    seen, out = set(), []
    for e in sorted(events, key=lambda x: x["sources"][0]["char_start"]):
        key = (e["type"], e["sources"][0]["page"],
               e["sources"][0]["char_start"] // WINDOW)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def _classify_polarity(text_lower: str) -> str:
    if any(m in text_lower for m in DENIAL_MARKERS):
        return "DENIES"
    if any(m in text_lower for m in ASSERTION_MARKERS):
        return "ASSERTS"

    # Phrase list found nothing -- try the verb-lemma signal before falling
    # back to NEUTRAL (F-18). Deliberately verb-lemma ONLY, not also raw
    # syntactic negation (spaCy's "neg" dep tag) -- that was the first
    # version of this fix, and testing it against a real writ petition
    # (temp/2026-09-10-real-petition-run/BCI_NOC_WP.txt, never committed --
    # see FINDINGS.md F-18's correction) showed why: an argumentative legal
    # brief is FULL of negation as ordinary reasoning ("does not maintain",
    # "cannot accomplish", "is not distinguishable") that is not one party
    # denying another's fact -- DENIES/ASSERTS exists specifically to feed
    # label_edge()'s POTENTIAL_CONFLICT pairing, not to flag every negated
    # sentence. Blanket negation-as-DENIES mislabeled 20/111 events (18%) on
    # that real document, nearly all ordinary argument, not conflicts.
    # Verb lemma alone still catches real phrasing the old list missed
    # ("refutes the claim", "has not received" only when phrased with an
    # actual denial verb) without that flood. Original-case text is not
    # available here (every caller already lowercases before calling,
    # matching the phrase-list checks above); lemma matching is stable on
    # lowercased input.
    global _NLP
    if _NLP is None:
        import spacy
        _NLP = spacy.load("en_core_web_sm")
    doc = _NLP(text_lower)
    verb_lemmas = {tok.lemma_ for tok in doc if tok.pos_ in ("VERB", "AUX")}
    if verb_lemmas & DENIAL_VERB_LEMMAS:
        return "DENIES"
    if verb_lemmas & ASSERTION_VERB_LEMMAS:
        return "ASSERTS"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# STAGE 6 — EFFICIENT GRAPH CONSTRUCTION
# ---------------------------------------------------------------------------

def build_inverted_index(events: list[dict]) -> dict:
    index = defaultdict(set)
    for i, e in enumerate(events):
        for ent_id in e["linked_entities"]:
            index[ent_id].add(i)
        if e["linked_date"]:
            index[f"date::{e['linked_date']['iso']}"].add(i)
        if e["linked_amount"]:
            norm = re.sub(r"[^\d]", "", e["linked_amount"]["raw"])
            if norm:
                index[f"amt::{norm}"].add(i)
        index[f"type::{e['type']}"].add(i)
    return index


def entity_idf_weight(entity_id: str, index: dict, total_events: int) -> float:
    df = len(index.get(entity_id, ()))
    return math.log((total_events + 1) / (df + 1)) + 0.1


def generate_candidate_pairs(index: dict, max_bucket_size: int = 40) -> set[tuple]:
    candidates = set()
    for key, event_ids in index.items():
        if len(event_ids) > max_bucket_size:
            continue  # hub key (e.g. "the Court") — not discriminative
        ids = sorted(event_ids)
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                candidates.add((ids[a], ids[b]))
    return candidates


def score_pair(e1: dict, e2: dict, index: dict, total_events: int,
               similarity_fn: Callable[[dict, dict], float]) -> dict:
    shared = set(e1["linked_entities"]) & set(e2["linked_entities"])
    entity_score = sum(entity_idf_weight(s, index, total_events) for s in shared)
    entity_score = min(entity_score / 2.0, 1.0)

    temporal_score = 0.0
    if e1["linked_date"] and e2["linked_date"]:
        d1 = date.fromisoformat(e1["linked_date"]["iso"])
        d2 = date.fromisoformat(e2["linked_date"]["iso"])
        temporal_score = max(0.0, 1 - abs((d1 - d2).days) / 180)

    semantic_score = similarity_fn(e1, e2)
    same_doc_bonus = 0.1 if e1["document_id"] == e2["document_id"] else 0.0

    total = (0.35 * entity_score + 0.20 * temporal_score
             + 0.35 * semantic_score + 0.10 * same_doc_bonus)
    return {"score": total, "breakdown": {
        "entity_overlap": round(entity_score, 3),
        "temporal_proximity": round(temporal_score, 3),
        "semantic_similarity": round(semantic_score, 3),
        "same_document_bonus": same_doc_bonus}}


def sparsify_and_cluster(events, candidate_pairs, scores, top_k=5, min_score=0.35):
    by_node = defaultdict(list)
    for (a, b) in candidate_pairs:
        s = scores[(a, b)]["score"]
        if s >= min_score:
            by_node[a].append((b, s))
            by_node[b].append((a, s))

    kept = set()
    for node, neighbors in by_node.items():
        neighbors.sort(key=lambda x: -x[1])
        for other, _ in neighbors[:top_k]:
            kept.add(tuple(sorted((node, other))))

    parent = list(range(len(events)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in kept:
        union(a, b)

    clusters = defaultdict(list)
    for i in range(len(events)):
        clusters[find(i)].append(i)
    return kept, clusters


def label_edge(e1: dict, e2: dict) -> str:
    p1, p2 = e1["polarity"], e2["polarity"]
    if {p1, p2} == {"ASSERTS", "DENIES"}:
        return "POTENTIAL_CONFLICT"
    if "ASSERTS" in (p1, p2):
        return "SUPPORTS"
    return "RELATED_TO"


# ---------------------------------------------------------------------------
# EMBEDDINGS (real, not the v1 dummy that returned a constant 0.5)
# ---------------------------------------------------------------------------

_EMBED_MODELS: dict[str, object] = {}
_EMBED_CACHE: dict[tuple[str, str], object] = {}


def make_similarity_fn(model_name: str = "all-MiniLM-L6-v2"):
    """BAAI/bge-m3 is the upgrade path; MiniLM is the CPU-cheap default.

    Both the loaded model and the embedding cache are keyed by model_name
    (not just a single shared global) -- found by F-10: the old single
    `_EMBED`/text-only `_EMBED_CACHE` globals meant a second
    make_similarity_fn(model_name=B) call inside the same process silently
    reused model A's already-loaded weights AND A's cached embeddings for any
    text A had already seen, returning wrong scores for B with no error.
    Harmless as long as only one model is ever used per process (the only
    way this pipeline calls it today) but a real bug the moment that stops
    being true (e.g. an A/B evaluation script).
    """
    def fn(e1: dict, e2: dict) -> float:
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return 0.0  # degrade to entity+temporal signal only
        if model_name not in _EMBED_MODELS:
            _EMBED_MODELS[model_name] = SentenceTransformer(model_name)
        model = _EMBED_MODELS[model_name]

        def emb(txt):
            key = (model_name, txt)
            if key not in _EMBED_CACHE:
                _EMBED_CACHE[key] = model.encode(txt, normalize_embeddings=True)
            return _EMBED_CACHE[key]

        return float(np.dot(emb(e1["section_text"]), emb(e2["section_text"])))
    return fn


# ---------------------------------------------------------------------------
# STAGE 7 — OUTPUT (crash bugs fixed)
# ---------------------------------------------------------------------------

def _safe(d: Optional[dict], key: str, default=None):
    """v1 used `x.get('k', {}).get('v')`, which explodes when the value is
    explicitly None rather than absent. This is BUG-1."""
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def to_react_flow(events: list[dict], edges: set[tuple],
                  edge_labels: dict) -> dict:
    nodes = [{
        "id": f"evt_{i}",
        "type": e["type"],
        "data": {
            "label": e.get("label") or _safe(e.get("linked_amount"), "raw") or e["type"].title(),
            "date": _safe(e.get("linked_date"), "iso"),
            "polarity": e["polarity"],
            "confidence": e.get("confidence") or "resolved",
            "sources": e.get("sources", []),
        },
    } for i, e in enumerate(events)]

    graph_edges = [{
        "id": f"e_{a}_{b}",
        "source": f"evt_{a}",
        "target": f"evt_{b}",
        "label": edge_labels.get((a, b), "RELATED_TO"),
    } for (a, b) in edges]

    return {"nodes": nodes, "edges": graph_edges}


def build_evidence_card(event: dict) -> dict:
    return {
        "title": event["type"].title(),
        "value": _safe(event.get("linked_amount"), "raw", ""),
        "date": _safe(event.get("linked_date"), "iso", "unknown"),
        "statement": (f"{event['polarity'].title()} in {event['section_label']}"
                      if event["polarity"] != "NEUTRAL"
                      else f"Mentioned in {event['section_label']}"),
        "sources": event.get("sources", []),
        "confidence": event.get("confidence") or "resolved",
    }


# ---------------------------------------------------------------------------
# BI-TEMPORAL STORE — replaces Graphiti/Neo4j, no external service
# ---------------------------------------------------------------------------

@dataclass
class TemporalEdge:
    """Same invalidation semantics Graphiti gives you, in plain SQLite.

    valid_at     — when the asserted fact happened
    recorded_at  — when the document asserting it was filed
    invalidated_by / invalidated_at — set when a later-filed document
                   contradicts this edge about the same subject
    """
    edge_id: str
    edge_type: str
    source: str
    target: str
    valid_at: Optional[str]
    recorded_at: Optional[str]
    score: float
    invalidated_by: Optional[str] = None
    invalidated_at: Optional[str] = None
    breakdown: dict = field(default_factory=dict)


def apply_invalidation(edges: list[TemporalEdge]) -> list[TemporalEdge]:
    """If two edges concern the same subject and one DENIES what another
    ASSERTS, the later-RECORDED one supersedes the earlier. This is the
    'the later affidavit supersedes the earlier claim' behaviour — with no
    graph database running.
    """
    by_subject = defaultdict(list)
    for e in edges:
        by_subject[tuple(sorted((e.source, e.target)))].append(e)

    for _, group in by_subject.items():
        conflicting = [e for e in group if e.edge_type in ("SUPPORTS", "POTENTIAL_CONFLICT")]
        if len(conflicting) < 2:
            continue
        dated = [e for e in conflicting if e.recorded_at]
        if len(dated) < 2:
            continue
        dated.sort(key=lambda e: e.recorded_at)
        latest = dated[-1]
        for e in dated[:-1]:
            e.invalidated_by = latest.edge_id
            e.invalidated_at = latest.recorded_at
    return edges


def persist_edges(edges: list[TemporalEdge], db_path: str = "casemap.db") -> None:
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS edges (
        edge_id TEXT PRIMARY KEY, edge_type TEXT, source TEXT, target TEXT,
        valid_at TEXT, recorded_at TEXT, score REAL,
        invalidated_by TEXT, invalidated_at TEXT, breakdown TEXT)""")
    conn.executemany(
        "INSERT OR REPLACE INTO edges VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(e.edge_id, e.edge_type, e.source, e.target, e.valid_at, e.recorded_at,
          e.score, e.invalidated_by, e.invalidated_at, json.dumps(e.breakdown))
         for e in edges])
    conn.commit()
    conn.close()
