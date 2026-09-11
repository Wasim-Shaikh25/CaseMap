"""provision_lookup.py -- OPTIONAL, opt-in only: fetches the EXACT verbatim
text of a cited provision from India Code (via eCourtsIndia's free, no-key
JSON mirror, https://indiacode.ecourtsindia.com) so a reader can see the
actual section without leaving the app.

Why this source, not a search engine (2026-09-11, F-24, replacing the
IndianKanoon-search version from F-17): India Code is the Government of
India's own statute repository; the section endpoint returns the ACT'S OWN
TEXT, not a judgment that happens to quote or cite it. The earlier version
searched court judgments on IndianKanoon and inferred the statute text was
probably right from a confidence gate on the search result's metadata --
this one gets the text directly from the primary source, verbatim, with no
inference step. "It does not paraphrase a provision and present it as the
provision" is the source's own stated design (its /llms.txt) -- exactly this
pipeline's own verbatim-only stance (THESIS.md), from an independent source
that committed to it first.

ONE HTTP call per unique provision, not two: resolving "UGC Act" (or a
truncated match like "Corruption Act, 1988" for "The Prevention of
Corruption Act, 1988") to its API slug runs against a LOCAL, bundled index
of every Central Act's title (src/indiacode_acts.json, 836 rows, fetched
ONCE by scripts/build_indiacode_acts_index.py -- never at request time) via
rapidfuzz, already a project dependency. Only the section-text fetch itself
touches the network. A citation whose act can't be confidently resolved
locally, or isn't in the 836-Act Central index at all (a State Act, or an
Act passed after the index was last rebuilt), is a known, accepted
exception: it skips rather than guesses or falls back to a second network
call.

Privacy: unchanged from F-17 -- one outbound call per UNIQUE provision
citation per document-processing run (in-process cache below), and the
query is the citation string alone -- never document content. Opt-in only
(casemap_service.process_document(lookup_provisions=True)), disclosed in
the UI wherever the toggle lives.

Skips (returns None) whenever the act can't be confidently matched, or the
section endpoint 404s -- a wrong statute link is worse than none. Never
raises: a network failure, timeout, or missing local index all degrade to
"not found" and the document result is otherwise unaffected.
"""

from __future__ import annotations

import json
import os
import re

import requests
from rapidfuzz import fuzz, process

API_BASE = "https://indiacode.ecourtsindia.com/api/v1"
TIMEOUT_S = 6
# rapidfuzz token_set_ratio, 0-100. Chosen high: a wrong-Act match here would
# hand a reader the WRONG law under the citation they searched for, worse
# than the honest "not found" a lower score would produce instead.
MATCH_THRESHOLD = 90

_CACHE: dict[str, dict | None] = {}
_ACTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "indiacode_acts.json")
_ACTS_INDEX: list[dict] | None = None

_SEC_NUM_RE = re.compile(r"\d+[A-Za-z]{0,2}")
_YEAR_RE = re.compile(r"\b(1[7-9]\d{2}|20\d{2})\b")
_LEADING_THE_RE = re.compile(r"^\s*the\s+", re.I)


def _load_acts_index() -> list[dict]:
    global _ACTS_INDEX
    if _ACTS_INDEX is None:
        with open(_ACTS_PATH, encoding="utf-8") as f:
            _ACTS_INDEX = json.load(f)
    return _ACTS_INDEX


def _best_match(query: str, candidates: list[dict]) -> tuple[dict, float] | None:
    if not candidates:
        return None
    best = process.extractOne(
        query, [a["short_title"] for a in candidates], scorer=fuzz.token_set_ratio)
    if not best or best[1] < MATCH_THRESHOLD:
        return None
    return candidates[best[2]], best[1]


def _resolve_act_slug(act: str) -> str | None:
    """Fuzzy-match `act` against the LOCAL bundled index -- no network call.
    A year found in `act` (most citations from _find_act_name() carry one,
    e.g. "Prevention of Corruption Act, 1988") narrows the candidate pool
    first, since Act names repeat across different years far more than
    within one; the year-filtered pool is tried first when that narrowing
    found anything.

    The year in a citation is the year most people cite (usually
    enactment), which is not always the index's `act_year` field (which can
    be a commencement/in-force year instead) -- e.g. the Code of Criminal
    Procedure is universally cited as "..., 1973" but this index's
    `act_year` for it is 1974, the year it came into force. So the
    year-filtered pool is a precision optimization, not a guarantee: if it
    fails to clear the confidence threshold, retry against the FULL index
    before giving up, rather than trusting a possibly-wrong year field to
    exclude the right Act. Returns the act's `id` (the slug the section
    endpoint needs), or None if nothing matches confidently enough."""
    if not act:
        return None
    acts = _load_acts_index()
    query = _LEADING_THE_RE.sub("", act).strip().rstrip(".")
    year_m = _YEAR_RE.search(query)
    if year_m:
        year_filtered = [a for a in acts if a.get("act_year") == int(year_m.group(1))]
        match = _best_match(query, year_filtered)
        if match:
            return match[0]["id"]
    match = _best_match(query, acts)
    return match[0]["id"] if match else None


def reset_cache() -> None:
    """Test-only: clear the cached lookups between test cases."""
    _CACHE.clear()


def lookup_provision(section_raw: str, act: str | None) -> dict | None:
    """One provision -> {"title", "text", "source_url", "in_force"}, or None
    if the Act couldn't be confidently resolved locally or the section
    wasn't found. `section_raw` is exactly what the deterministic
    SECTION_PATTERN regex matched in the document (e.g. "Section 125");
    `act` is whatever _find_act_name() found nearby in the document, if
    anything -- both already computed by the caller, never re-derived here.
    No Act name at all means no lookup at all: this is a citation-to-statute
    tool, not a section-number guesser.
    """
    query = f"{section_raw} {act}".strip() if act else section_raw.strip()
    if query in _CACHE:
        return _CACHE[query]

    result = None
    sec_m = _SEC_NUM_RE.search(section_raw or "")
    slug = _resolve_act_slug(act) if act else None
    if sec_m and slug:
        try:
            resp = requests.get(
                f"{API_BASE}/{slug}/section/{sec_m.group()}",
                headers={"User-Agent": "Mozilla/5.0 (CaseMap provision lookup; "
                                        "single verbatim-citation query, no document content)"},
                timeout=TIMEOUT_S)
            if resp.ok:
                data = resp.json()
                sec = data.get("section") or {}
                text = sec.get("text")
                act_meta = data.get("act") or {}
                if text:
                    result = {
                        "title": f"Section {sec.get('number')} — {act_meta.get('short_title')}",
                        "text": text,
                        "source_url": data.get("url"),
                        "in_force": act_meta.get("in_force"),
                    }
        except (requests.RequestException, ValueError):
            result = None

    _CACHE[query] = result
    return result
