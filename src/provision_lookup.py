"""provision_lookup.py -- OPTIONAL, opt-in only: fetches what a cited
provision actually says from a free public source (IndianKanoon.org's bare
statute text, no login or API key required) so a reader can see it without
leaving the app.

Privacy: ONE outbound HTTP call per UNIQUE provision citation per
document-processing run (in-process cache below), and the query is the
citation string alone ("Section 125 of the Code of Criminal Procedure") --
never any document content, page text, or party names. Only runs when the
caller opts in (casemap_service.process_document(lookup_provisions=True));
off by default, disclosed in the UI wherever the toggle lives.

Skips (returns None) whenever the match isn't clearly a bare-statute result
-- the same verbatim-only stance as the rest of this pipeline: a wrong
statute link is worse than none. Never raises: a network failure, timeout,
or an IndianKanoon page-layout change all degrade to "not found" and the
document result is otherwise unaffected.
"""

from __future__ import annotations

import html
import re

import requests

SEARCH_URL = "https://indiankanoon.org/search/"
TIMEOUT_S = 6

_CACHE: dict[str, dict | None] = {}

# One search-result <article> block, non-greedy across the intervening
# <div class="hlbottom"> wrapper -- confirmed against a real response
# (see scripts/poc_provision_lookup.py) rather than guessed from memory of
# the site's markup.
_RESULT_RE = re.compile(
    r'<article class="result".*?<h4 class="result_title">.*?'
    r'<a href="(?P<href>/doc/\d+/)">(?P<title>.*?)</a>.*?'
    r'<div class="headline">(?P<headline>.*?)</div>.*?'
    r'<span class="docsource">(?P<docsource>.*?)</span>',
    re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(raw: str) -> str:
    return html.unescape(_TAG_RE.sub("", raw)).strip()


def reset_cache() -> None:
    """Test-only: clear the cached lookups between test cases."""
    _CACHE.clear()


def lookup_provision(section_raw: str, act: str | None) -> dict | None:
    """One provision -> {"title", "snippet", "source_url"}, or None if no
    confident bare-statute match was found. `section_raw` is exactly what
    the deterministic SECTION_PATTERN regex matched in the document (e.g.
    "Section 125"); `act` is whatever _find_act_name() found nearby in the
    document, if anything -- both already computed by the caller, never
    re-derived here.
    """
    query = f"{section_raw} {act}".strip() if act else section_raw.strip()
    if query in _CACHE:
        return _CACHE[query]

    result = None
    try:
        resp = requests.get(
            SEARCH_URL, params={"formInput": query},
            headers={"User-Agent": "Mozilla/5.0 (CaseMap provision lookup; "
                                    "single verbatim-citation query, no document content)"},
            timeout=TIMEOUT_S)
        if resp.ok:
            m = _RESULT_RE.search(resp.text)
            if m:
                docsource = _clean(m.group("docsource"))
                title = _clean(m.group("title"))
                sec_num_match = re.search(r"\d+[A-Z]{0,2}", section_raw)
                sec_num = sec_num_match.group() if sec_num_match else None
                # Confidence gate: IndianKanoon labels a bare-statute result's
                # docsource "<something> - Section" -- a judgment or any
                # other document type never carries that suffix. Also
                # require the same section number to appear in the result
                # title, so "Section 125" never silently matches a
                # different section the query happened to also surface.
                if (sec_num and docsource.endswith("- Section")
                        and re.search(rf"\b{re.escape(sec_num)}\b", title)):
                    result = {
                        "title": title,
                        "snippet": _clean(m.group("headline")),
                        "source_url": "https://indiankanoon.org" + m.group("href"),
                    }
    except requests.RequestException:
        result = None

    _CACHE[query] = result
    return result
