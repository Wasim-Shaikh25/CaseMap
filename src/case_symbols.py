"""case_symbols.py — Case Symbol Table (ARCHITECTURE stage [4]).

Definition sites, aliases, go_to_definition / find_all_references,
cross-document merge by canonical key. Verbatim spans only.

Tier 2 (HEART): act-name inheritance and figures-vs-words *cross-check* are
intentionally not implemented here — only the keying functions they would use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

_LEGAL_SUFFIXES = re.compile(
    r"\b(pvt|private|ltd|limited|llp|inc|incorporated|corp|corporation|co|company"
    r"|&|and|sons|enterprises|industries)\b\.?", re.I)

_AMOUNT_NUM = re.compile(
    r"(?:Rs\.?|₹|INR)\s?(\d[\d,]*(?:\.\d+)?)(?:\s?(lakh|lakhs|crore|crores))?",
    re.I)

_WORD_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_WORD_SCALES = {
    "hundred": 100,
    "thousand": 1_000,
    "lakh": 100_000, "lakhs": 100_000,
    "crore": 10_000_000, "crores": 10_000_000,
}

_SECTION_IN_SPAN = re.compile(
    r"\b(?:section|sec\.?|s\.)\s?(?P<sec>\d+[A-Z]{0,2})\b", re.I)
_ACT_IN_SPAN = re.compile(
    r"\b(?:the\s+)?(?P<act>[A-Z][A-Za-z.\s]{2,60}?Act(?:,\s*\d{4})?)", re.I)


def normalize_name(name: str) -> str:
    """Canonical person/org key. Same suffix-stripping idea as
    casemap_pipeline._canonical_key (BUG-5/7)."""
    n = _LEGAL_SUFFIXES.sub(" ", name.lower())
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    tokens = [t for t in n.split() if len(t) > 1]
    out = " ".join(tokens).strip()
    if out.startswith("the "):
        out = out[4:]
    return out


def normalize_amount(raw: str) -> Optional[int]:
    """Integer rupees from a figure span, or None if unparseable."""
    m = _AMOUNT_NUM.search(raw or "")
    if not m:
        return None
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (m.group(2) or "").lower()
    if unit.startswith("lakh"):
        n *= 100_000
    elif unit.startswith("crore"):
        n *= 10_000_000
    return int(round(n))


def amount_from_words(text: str) -> Optional[int]:
    """Indian numbering words → integer rupees. None if nothing parseable."""
    t = re.sub(r"[^a-z\s]", " ", (text or "").lower())
    t = re.sub(r"\b(?:rupees?|rs|inr|only|and)\b", " ", t)
    tokens = [w for w in t.split() if w in _WORD_UNITS or w in _WORD_SCALES]
    if not tokens:
        return None
    total = 0
    current = 0
    saw = False
    for w in tokens:
        if w in _WORD_UNITS:
            current += _WORD_UNITS[w]
            saw = True
        elif w in _WORD_SCALES:
            scale = _WORD_SCALES[w]
            if current == 0:
                current = 1
            if scale == 100:
                current *= 100
            else:
                total += current * scale
                current = 0
            saw = True
    total += current
    return int(total) if saw and total else None


# Amount written in words, anchored by a currency marker and ending in a
# scale word: "Rs. Fifty Lakhs Only", "rupees one crore", "INR Ten Thousand".
# Anchoring on Rs/rupees/INR AND requiring a scale word (hundred/thousand/
# lakh/crore) is what keeps this from firing on ordinary prose that happens
# to contain number words. The figure regex (casemap_pipeline.AMOUNT_PATTERN)
# only matches DIGITS, so amounts a document spells out in words are silently
# dropped today — common in contracts, notices, decrees and prayer clauses.
_WORD_AMOUNT_RE = re.compile(
    r"(?:Rs\.?|rupees?|INR)\s+"
    r"((?:[A-Za-z]+[\s,\-]+){1,12}?(?:hundred|thousand|lakhs?|crores?))"
    r"(?:\s+only)?", re.I)


def find_word_amounts(text: str, min_value: int = 100) -> list[dict]:
    """Locate amounts written in words. Returns [{"raw", "span", "value"}]
    for each phrase that parses to at least `min_value` rupees. Pure
    detection over `text`; the caller attaches page/offset provenance.

    Deliberately conservative: only phrases that parse cleanly via
    amount_from_words() to a real figure survive, so a stray "hundred years"
    (no currency anchor) or an unparseable run never becomes a fake amount.
    """
    out: list[dict] = []
    for m in _WORD_AMOUNT_RE.finditer(text or ""):
        value = amount_from_words(m.group(0))
        if value is None or value < min_value:
            continue
        out.append({"raw": m.group(0).strip(), "span": m.span(), "value": value})
    return out


def provision_key(raw: str) -> Optional[str]:
    """section token, plus act only if present in the same span (no inheritance)."""
    sm = _SECTION_IN_SPAN.search(raw or "")
    if not sm:
        return None
    sec = sm.group("sec").upper()
    am = _ACT_IN_SPAN.search(raw or "")
    if am:
        act = re.sub(r"\s+", " ", am.group("act")).strip().casefold()
        return f"{act}::{sec}"
    return f"section::{sec}"


@dataclass
class SymbolSite:
    document_id: str
    text: str
    kind: str
    span: tuple[int, int]
    page: Optional[int] = None


@dataclass
class Symbol:
    key: str
    kind: str
    sites: list[SymbolSite] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

    @property
    def definition(self) -> Optional[SymbolSite]:
        return self.sites[0] if self.sites else None


class SymbolTable:
    def __init__(self) -> None:
        self._by_key: dict[str, Symbol] = {}

    def add(self, site: SymbolSite) -> Optional[str]:
        key = _key_for(site)
        if not key:
            return None
        sym = self._by_key.get(key)
        if sym is None:
            self._by_key[key] = Symbol(key=key, kind=site.kind, sites=[site],
                                       aliases=[site.text])
        else:
            if site.kind != sym.kind:
                return None  # BUG-5: never merge across types
            sym.sites.append(site)
            if site.text not in sym.aliases:
                sym.aliases.append(site.text)
        return key

    def go_to_definition(self, key: str) -> Optional[SymbolSite]:
        sym = self._by_key.get(key)
        return None if sym is None else sym.definition

    def find_all_references(self, key: str) -> list[SymbolSite]:
        sym = self._by_key.get(key)
        return [] if sym is None else list(sym.sites)

    def merge_from(self, other: "SymbolTable") -> None:
        for site in (s for sym in other._by_key.values() for s in sym.sites):
            self.add(site)

    def keys(self) -> list[str]:
        return list(self._by_key)

    def get(self, key: str) -> Optional[Symbol]:
        return self._by_key.get(key)


def _key_for(site: SymbolSite) -> Optional[str]:
    kind = site.kind
    if kind in ("PERSON", "ORG", "GPE"):
        n = normalize_name(site.text)
        return f"{kind}:{n}" if n else None
    if kind == "AMOUNT":
        n = normalize_amount(site.text)
        if n is None:
            n = amount_from_words(site.text)
        return f"AMOUNT:{n}" if n is not None else None
    if kind == "PROVISION":
        k = provision_key(site.text)
        return f"PROVISION:{k}" if k else None
    if kind == "CASE_NUMBER":
        k = re.sub(r"\s+", " ", (site.text or "").casefold()).strip()
        return f"CASE_NUMBER:{k}" if k else None
    n = normalize_name(site.text)
    return f"{kind}:{n}" if n else None


def table_from_extractions(
    document_id: str,
    det: dict,
    entities: list[dict],
) -> SymbolTable:
    """Fill a table from existing extract_deterministic / extract_entities rows."""
    tbl = SymbolTable()
    for row in det.get("amounts") or []:
        tbl.add(SymbolSite(document_id, row["raw"], "AMOUNT",
                           tuple(row["span"]), row.get("page")))
    for row in det.get("sections") or []:
        tbl.add(SymbolSite(document_id, row["raw"], "PROVISION",
                           tuple(row["span"]), row.get("page")))
    for row in det.get("case_numbers") or []:
        tbl.add(SymbolSite(document_id, row["raw"], "CASE_NUMBER",
                           tuple(row["span"]), row.get("page")))
    for e in entities or []:
        span = e.get("span") or (0, 0)
        tbl.add(SymbolSite(document_id, e["text"], e.get("label") or "PERSON",
                           (span[0], span[1]), e.get("page")))
    return tbl
