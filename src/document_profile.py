"""
document_profile.py — declarative document-type detection + party extraction.

Design principle: a court cause title is STRUCTURALLY invariant even though its
wording is not. Across every Indian court, jurisdiction and language it is:

    IN THE HIGH COURT OF JUDICATURE AT BOMBAY     <- forum line
    W.P. (C) No. 1234 of 2024                     <- case number
    ABC Pvt Ltd                 ...Petitioner     <- party block A
                  VERSUS                          <- SEPARATOR (the anchor)
    XYZ Ltd                     ...Respondent     <- party block B

The anchor is not a keyword list. It is the separator token splitting two name
blocks. Everything above is the first party, everything below is the second.
That holds for writs, plaints, appeals, arbitration petitions and criminal
matters alike.

Adding a new document type is a dict entry in PROFILES, not new code.
No LLM. Stdlib + rapidfuzz only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Separator anchors — including OCR manglings and Indic forms
# ---------------------------------------------------------------------------

_VERSUS_FORMS = [
    r"v\s*/\s*s", r"vs?\.?", r"versus", r"verses",
    r"vers[tu]s", r"ver[sz]us", r"\bv\b",          # OCR: VERSTJS, VERZUS
    r"बनाम", r"विरुद्ध", r"विरूद्ध",                    # Hindi/Marathi
    r"எதிர்", r"వర్సెస్",                              # Tamil, Telugu
]
VERSUS_RE = re.compile(
    r"^\s*[-–—\s]*(?:" + "|".join(_VERSUS_FORMS) + r")[\s.:\-–—]*$", re.I)

_OCR_MAP = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B", "|": "I", "@": "A"})


def is_versus_line(line: str) -> bool:
    """OCR-tolerant separator test.

    'VERSTJS' is a real Tesseract output for VERSUS (U->TJ is a classic
    two-character split). A fixed regex list can never enumerate these, so
    fall back to fuzzy comparison on the alphabetic core of the line.
    """
    s = (line or "").strip()
    if not s or len(s) > 24:
        return False
    if VERSUS_RE.match(s):
        return True
    core = re.sub(r"[^A-Za-z\u0900-\u0DFF]", "", s.translate(_OCR_MAP)).lower()
    if not (2 <= len(core) <= 12):
        return False
    if core in ("v", "vs", "versus", "बनाम", "विरुद्ध"):
        return True
    try:
        from rapidfuzz import fuzz
        return max(fuzz.ratio(core, "versus"), fuzz.ratio(core, "verses")) >= 70
    except ImportError:
        return False

# Role suffix markers: "...Petitioner", "— Appellant", "/Plaintiff"
ROLE_MARKER_RE = re.compile(
    r"[\.\u2026\-–—/:]{1,4}\s*(petitioner|respondent|plaintiff|defendant|"
    r"appellant|applicant|claimant|complainant|accused|opposite\s+part(?:y|ies)|"
    r"deponent|obligor|obligee|financial\s+creditor|operational\s+creditor|"
    r"corporate\s+debtor|corporate\s+applicant|decree\s+holder|judgment\s+debtor|"
    r"याचिकाकर्ता|प्रतिवादी|प्रत्यर्थी|वादी|अपीलकर्ता|अभियुक्त)s?", re.I)

# Devanagari role words also appear WITHOUT a leading dot separator
_INDIC_ROLE_RE = re.compile(
    r"(याचिकाकर्ता|प्रतिवादी|प्रत्यर्थी|वादी|अपीलकर्ता|अभियुक्त)\s*$")
_INDIC_ROLE_EN = {"याचिकाकर्ता": "Petitioner", "प्रतिवादी": "Respondent",
                  "प्रत्यर्थी": "Respondent", "वादी": "Plaintiff",
                  "अपीलकर्ता": "Appellant", "अभियुक्त": "Accused"}

# Case-number prefix -> (moving party role, opposing party role)
CASE_TYPE_ROLES = {
    "wp": ("Petitioner", "Respondent"), "w.p": ("Petitioner", "Respondent"),
    "slp": ("Petitioner", "Respondent"), "cwp": ("Petitioner", "Respondent"),
    "crlmc": ("Petitioner", "Respondent"), "oa": ("Applicant", "Respondent"),
    "cs": ("Plaintiff", "Defendant"), "os": ("Plaintiff", "Defendant"),
    "comap": ("Appellant", "Respondent"), "ca": ("Appellant", "Respondent"),
    "fa": ("Appellant", "Respondent"), "sa": ("Appellant", "Respondent"),
    "crla": ("Appellant", "Respondent"), "crl.a": ("Appellant", "Respondent"),
    "omp": ("Claimant", "Respondent"), "arbp": ("Claimant", "Respondent"),
    "cp": ("Petitioner", "Respondent"), "ibc": ("Applicant", "Respondent"),
    "ma": ("Applicant", "Respondent"), "ia": ("Applicant", "Respondent"),
    # spelled-out forms
    "commercialsuit": ("Plaintiff", "Defendant"),
    "civilsuit": ("Plaintiff", "Defendant"),
    "suit": ("Plaintiff", "Defendant"),
    "civilappeal": ("Appellant", "Respondent"),
    "criminalappeal": ("Appellant", "Respondent"),
    "appeal": ("Appellant", "Respondent"),
    "writpetition": ("Petitioner", "Respondent"),
    "specialleavepetition": ("Petitioner", "Respondent"),
    "companypetition": ("Petitioner", "Respondent"),
    "arbitrationpetition": ("Claimant", "Respondent"),
    "executionpetition": ("Decree Holder", "Judgment Debtor"),
    "originalapplication": ("Applicant", "Respondent"),
    "petition": ("Petitioner", "Respondent"),
}

CASE_NUMBER_RE = re.compile(
    r"\b([A-Z][A-Za-z.]{0,8}(?:\.[A-Z])?\.?\s*(?:\([A-Za-z]{1,3}\))?)\s*"
    r"No\.?\s*(\d+)\s*(?:of|/)\s*(\d{4})\b", re.I)

# Spelled-out case types: "COMMERCIAL SUIT NO. 442 OF 2024", "CIVIL APPEAL NO..."
CASE_TYPE_WORDS_RE = re.compile(
    r"\b((?:commercial\s+suit|civil\s+suit|civil\s+appeal|criminal\s+appeal|"
    r"writ\s+petition|special\s+leave\s+petition|company\s+petition|"
    r"arbitration\s+petition|execution\s+petition|original\s+application|"
    r"suit|appeal|petition))\s*(?:Nos?\.?)?\s*([\d\-–]*)\s*(?:of|/)\s*(\d{4})\b", re.I)

# Any line that is essentially a case-number heading (incl. ranges and blanks):
# "CIVIL APPEAL NOS. 5023-5024 OF 2024", "CIVIL APPEAL NO. OF 2024"
CASE_HEADING_RE = re.compile(
    r"^\s*(?:[A-Z][A-Za-z.()\s]{0,40})?(?:suit|appeal|petition|application|"
    r"slp|w\.?p\.?|c\.?a\.?|o\.?a\.?|crl)[A-Za-z.()\s]{0,12}"
    r"\s*Nos?\.?\s*[\d\-–,\s]*\s*(?:of|/)\s*\d{4}\s*$", re.I)

# Registry short forms with no "No.": "BAIL APPLN. 4102/2024", "CRL.M.C. 998/2023",
# "O.M.P. (COMM) 45/2024", "CP (IB) No. 2205/MB/2019"
CASE_SHORTFORM_RE = re.compile(
    r"^\s*(?:bail\s+appln?|crl\.?\s*m\.?\s*c|crl\.?\s*a|w\.?\s*p|o\.?\s*m\.?\s*p|"
    r"c\.?\s*p|c\.?\s*a|o\.?\s*a|i\.?\s*a|m\.?\s*a|s\.?\s*l\.?\s*p|arb)"
    r"[A-Za-z.()\s]{0,18}\s*(?:No\.?)?\s*\d+\s*/\s*[A-Za-z0-9/]+\s*$", re.I)


@dataclass
class Party:
    name: str
    role: str
    role_confidence: str          # 'explicit' | 'case_type' | 'positional'
    side: str                     # 'A' | 'B'
    ordinal: Optional[int]        # 1st respondent, 2nd respondent...
    line_no: int

FORUM_RE = re.compile(
    r"\b(?:in\s+the\s+)?(supreme\s+court|high\s+court|district\s+court|"
    r"family\s+court|sessions\s+court|tribunal|arbitral\s+tribunal|"
    r"nclt|nclat|drt|consumer\s+forum|magistrate)|"
    r"\b(?:this\s+(?:hon'?ble\s+)?commission|hon'?ble\s+commission)\b|"
    r"(?:उच्च\s*न्यायालय|सर्वोच्च\s*न्यायालय|न्यायालय|अधिकरण)", re.I)

# Indic case-number line: "याचिका संख्या 445/2024"
INDIC_CASE_NO_RE = re.compile(
    r"(?:याचिका|वाद|अपील|मुकदमा)\s*(?:संख्या|सं\.?|क्रमांक)\s*\d+", re.I)


# ---------------------------------------------------------------------------
# Profile registry — declarative, extend by adding a dict
# ---------------------------------------------------------------------------

@dataclass
class Profile:
    id: str
    roles: tuple[str, str]
    role_source: Optional[str]
    detectors: list = field(default_factory=list)


def _has(rx, weight=1.0):
    return lambda text: weight if rx.search(text) else 0.0


PROFILES: list[Profile] = [
    Profile(
        id="court_filing", roles=("Petitioner", "Respondent"),
        role_source="cause_title",
        detectors=[
            _has(CASE_NUMBER_RE, 3.0),
            _has(FORUM_RE, 3.0),
            lambda t: 3.0 if any(is_versus_line(l)
                                 for l in t.splitlines()[:80]) else 0.0,
            _has(ROLE_MARKER_RE, 2.0),
        ]),
    Profile(
        id="affidavit", roles=("Deponent", "—"), role_source="deponent_clause",
        detectors=[
            _has(re.compile(r"\bI,\s+[A-Z]", ), 2.0),
            _has(re.compile(r"\bdo\s+hereby\s+(?:solemnly\s+)?"
                            r"(?:affirm|state|declare)", re.I), 3.0),
            _has(re.compile(r"\bverification\b", re.I), 1.0),
            _has(re.compile(r"\bdeponent\b", re.I), 2.0),
        ]),
    Profile(
        id="contract", roles=("First Party", "Second Party"),
        role_source="recital",
        detectors=[
            _has(re.compile(r"\bthis\s+agreement\s+is\s+made", re.I), 3.0),
            _has(re.compile(r"\bbetween\b.{0,200}\band\b", re.I | re.S), 1.0),
            _has(re.compile(r"\bwhereas\b", re.I), 2.0),
            _has(re.compile(r"\bwitnesseth\b|\bnow\s+therefore\b", re.I), 2.0),
            _has(re.compile(r"\bin\s+witness\s+whereof\b", re.I), 2.0),
        ]),
    Profile(
        id="legal_notice", roles=("Sender", "Recipient"), role_source="letterhead",
        detectors=[
            _has(re.compile(r"\blegal\s+notice\b", re.I), 3.0),
            _has(re.compile(r"\bunder\s+instructions\s+from\s+my\s+client", re.I), 3.0),
            _has(re.compile(r"\bmy\s+client\b", re.I), 1.0),
            _has(re.compile(r"\bwithin\s+\d+\s+days\b", re.I), 1.0),
        ]),
    Profile(
        id="correspondence", roles=("Sender", "Recipient"), role_source="letterhead",
        detectors=[
            _has(re.compile(r"^\s*(?:from|to)\s*:", re.I | re.M), 2.0),
            _has(re.compile(r"^\s*sub(?:ject)?\s*:", re.I | re.M), 2.0),
            _has(re.compile(r"^\s*ref(?:erence)?\s*(?:no\.?)?\s*:", re.I | re.M), 1.5),
            _has(re.compile(r"\b(?:dear\s+(?:sir|madam)|yours\s+(?:faithfully|"
                            r"sincerely|truly))\b", re.I), 2.0),
        ]),
    Profile(
        id="financial", roles=("Account Holder", "Counterparty"),
        role_source="statement_header",
        detectors=[
            _has(re.compile(r"\b(?:a/?c|account)\s*(?:no\.?|number)", re.I), 3.0),
            _has(re.compile(r"\bIFSC\b|\bMICR\b|\bUTR\b", re.I), 3.0),
            _has(re.compile(r"\b(?:debit|credit)\b.{0,40}\b(?:balance)\b", re.I | re.S), 2.0),
            _has(re.compile(r"\b(?:invoice|tax\s+invoice|GSTIN)\b", re.I), 2.0),
        ]),
    Profile(
        id="court_order", roles=("Petitioner", "Respondent"), role_source="cause_title",
        detectors=[
            _has(re.compile(r"\b(?:it\s+is\s+ordered|hereby\s+ordered|"
                            r"the\s+court\s+directs)\b", re.I), 3.0),
            _has(re.compile(r"\bcoram\b|\bbefore\s+(?:hon|the\s+hon)", re.I), 3.0),
            _has(re.compile(r"\b(?:oral\s+)?(?:order|judgment)\b", re.I), 1.0),
            _has(re.compile(r"\blist\s+(?:on|after)\b", re.I), 1.0),
        ]),
    Profile(id="generic", roles=("Party A", "Party B"), role_source=None, detectors=[]),
]


def detect_profile(text: str, filename: str = "") -> tuple[Profile, float, dict]:
    """Score every profile; highest wins. 'generic' always matches at 0.0."""
    head = text[:8000]  # cause titles / letterheads live at the top
    scores: dict[str, float] = {}
    for p in PROFILES:
        s = sum(d(head) for d in p.detectors)
        # filename is a weak but free signal
        fn = filename.lower()
        if p.id.split("_")[0] in fn or p.id.replace("_", "") in fn.replace("_", ""):
            s += 1.0
        scores[p.id] = s
    best = max(PROFILES, key=lambda p: scores[p.id])
    if scores[best.id] <= 0:
        best = PROFILES[-1]
    return best, scores[best.id], scores


# ---------------------------------------------------------------------------
# Cause-title party extraction (the VERSUS anchor)
# ---------------------------------------------------------------------------

_NOISE_LINE_RE = re.compile(
    r"^\s*(?:in\s+the\s|before\s|coram|dated|filed|through\s+its|advocate|"
    r"memo\s+of\s+parties|index|synopsis|list\s+of\s+dates)", re.I)
_NUMBERED_PARTY_RE = re.compile(r"^\s*(\d+)\s*[\.\)]\s*(.+)$")

# A line that is ONLY a role marker. Real petitions right-align these on their
# own line, separate from the party name — the single most common layout.
STANDALONE_ROLE_RE = re.compile(
    r"^\s*[\.\u2026\-–—/:\s]*(petitioner|respondent|plaintiff|defendant|"
    r"appellant|applicant|claimant|complainant|accused|opposite\s+part(?:y|ies)|financial\s+creditor|operational\s+creditor|corporate\s+debtor|decree\s+holder|judgment\s+debtor)"
    r"s?(?:\s*no\.?\s*\d+)?\s*[\.\s]*$", re.I)

# indiankanoon caption furniture (same family as casemap_pipeline._FURNITURE_LINE_RE).
# `Author:` not `^author\b` — that would drop "Authorised Officer" as a party.
_CAPTION_FURNITURE_RE = re.compile(
    r"^(equivalent citations\b|author\s*:|bench\s*:|reportable\b|source:)", re.I)
_CAPTION_SECTION_RE = re.compile(
    r"^(citation|citator info|date of judgment|act)\s*:?\s*$", re.I)

# A PDF page-break line landing mid-block is a layout artifact, not a
# boundary -- unlike _CAPTION_FURNITURE_RE (below), it must NOT close/reset
# whatever party entry is currently being built. Found on a real NGT appeal
# (2026-09-11, F-22/F-23): a "Page 2 of 43" line lands in the MIDDLE of a
# 3-line address ("Khashewadi, Tiroda," / [page break] / "Tal. Sawantwadi,").
# Treating it as furniture (which resets cur=None) orphaned everything after
# it, turning real address continuations into fake new parties again.
_PAGE_BREAK_RE = re.compile(r"^page\s+\d+\s+of\s+\d+\s*$", re.I)


def _is_caption_furniture_line(s: str) -> bool:
    t = (s or "").strip()
    return bool(t) and bool(_CAPTION_FURNITURE_RE.match(t))


def _is_caption_section_label(s: str) -> bool:
    t = (s or "").strip()
    return bool(t) and bool(_CAPTION_SECTION_RE.match(t))


# Whole-name hits that are petition/paper-book furniture, not litigants.
# Found on a real filed writ (2026-09-10): hybrid NER labelled INDEX, SYNOPSIS,
# LIST OF DATES, VERSUS, first-listing field labels, and case citations as parties.
_PETITION_FURNITURE_NAMES = {
    "citation", "citator info", "author", "bench",
    "equivalent citations", "reportable",
    "index", "synopsis", "list of dates", "list of dates and events",
    "paper book", "versus", "vakalatnama", "affidavit",
    "nature of matter", "land acquisition", "special category",
    "memo of parties", "written statement", "proforma for first listing",
}
_CASE_CITE_AS_NAME_RE = re.compile(
    r"\bv\.?\s+.+\(\s*\d{4}\s*\)", re.I)


def _is_caption_furniture_name(name: str) -> bool:
    n = (name or "").strip()
    if not n:
        return False
    if _is_caption_furniture_line(n) or _is_caption_section_label(n):
        return True
    folded = n.casefold().strip(" .:-")
    if folded in _PETITION_FURNITURE_NAMES:
        return True
    if re.search(r"e-?mail\s*:|mobile\s*:", n, re.I):
        return True
    if re.match(r"indian citizen,?\s+residing", n, re.I):
        return True
    if _CASE_CITE_AS_NAME_RE.search(n):
        return True
    return False


def _filter_caption_furniture_parties(parties: list[Party]) -> list[Party]:
    return [p for p in parties if not _is_caption_furniture_name(p.name)]


# Where the cause title STOPS and the pleading body begins.
BODY_START_RE = re.compile(
    r"^\s*(?:memo\s+of\s+parties|plaint\b|petition\s+under|application\s+under|"
    r"written\s+statement|affidavit|synopsis|list\s+of\s+dates|index|"
    r"paper\s*book|counsel\s+for\s+petitioner|advocate-on-record|"
    r"to,?\s*$|may\s+it\s+please|most\s+respectfully|the\s+humble\s+petition|"
    r"\d+\s*[\.\)]\s*That\b|That\s+the\b|"
    # Spaced-letter headings are ubiquitous in Indian judgments: "J U D G M E N T"
    r"(?:[JO])\s*[UR]\s*[DA]\s*[GE]\s*(?:M\s*E\s*N\s*T|R)\s*$|"
    r"judgment\s*$|order\s*$|coram\b|"
    # "WITH" connects multiple appeals in one judgment — a hard boundary
    r"with\s*$|and\s*$)", re.I)


def _is_body_paragraph(s: str) -> bool:
    """Distinguish a numbered BODY paragraph from a numbered PARTY entry.

    Both look like "1. Something". The difference is sentence-hood:
      body  -> "1. That the Plaintiff paid Rs. 1,20,00,000 on 18.03.2024"
      party -> "1. Meridian Constructions Pvt. Ltd."
    Party entries are short, verbless, and often carry a role marker.
    Getting this wrong silently drops every defendant in a numbered list.
    """
    t = (s or "").strip()
    m = re.match(r"^\s*\d+\s*[\.\)]\s+(.+)$", t)
    if not m:
        return False
    rest = m.group(1)
    if ROLE_MARKER_RE.search(rest):
        return False                      # "...Defendant No.1" -> a party
    if re.match(r"^(?:That\b|Leave\s+granted|The\s+\w+\s+"
                r"(?:is|are|was|were|has|have|shall|may)\b)", rest, re.I):
        return True
    if len(rest) > 90:
        return True                       # long = prose
    # A finite verb early in the line suggests prose
    return bool(re.search(r"\b(?:filed|paid|issued|held|arise|arises|submitted|"
                          r"dismissed|granted|directed|passed)\b", rest, re.I))

# Judge signature / authoring line: "VIKRAM NATH, J." or "J.B. PARDIWALA, J. :-"
JUDGE_LINE_RE = re.compile(r"^\s*[A-Z][A-Za-z.\s]{2,40},\s*J\.?\s*[:\-]*\s*$")

# Where the cause title STARTS (walking up from VERSUS).
TITLE_TOP_RE = re.compile(
    r"^\s*(?:in\s+the\s|before\s+the\s|.*\bjurisdiction\s*$|.*\bbench\s*$)", re.I)

# Continuation lines that describe a party rather than naming a new one.
_DESC_LINE_RE = re.compile(
    r"^\s*(?:a\s+(?:company|firm|society|partnership)|having\s+its|"
    r"registered\s+office|through\s+its|represented\s+by|r/?o\b|resident\s+of|"
    r"aged\s+about|s/?o\b|d/?o\b|w/?o\b|branch\b|office\s+at|"
    r"indian\s+citizen|e-?mail\s*:|mobile\s*:|"
    r"in\s+the\s+matter\s+of|section\s+\d+|read\s+with|\()", re.I)

# High Court cause lists put counsel between the party name and the separator:
#     VEDPAL SINGH TANWAR            .....Petitioner
#     Through: Mr. Vikas Pahwa, Sr. Advocate with
#     Mr. Sumer Singh Boparai, Mr. Sirhaan Seth, Advocates.
# Without this the whole counsel team becomes "parties".
ADVOCATE_START_RE = re.compile(r"^\s*(?:through\s*:|counsel\s+for|"
                               r"appearance\s*:|for\s+the\s+(?:petitioner|respondent))", re.I)
ADVOCATE_LINE_RE = re.compile(
    r"\b(?:advocates?|sr\.?\s*adv|senior\s+advocate|standing\s+counsel|"
    r"amicus\s+curiae|asg\b|a\.?s\.?g\.?|public\s+prosecutor|panel\s+counsel)\b", re.I)

# Delhi HC listing markers: "$~", "*", "%", "+" at line start
LISTING_MARKER_RE = re.compile(r"^\s*[$~*%+#]+\s*")

# Registry metadata lines
REGISTRY_LINE_RE = re.compile(
    r"^\s*(?:judgment|order)\s+(?:reserved|pronounced|delivered|dated)\s+on\b|"
    r"^\s*(?:date\s+of\s+(?:hearing|judgment|order))\b|^\s*reserved\s+on\b", re.I)

# Address continuation: has a PIN code or a street-type token. "taluk(a)"/
# "tehsil"/"village" added 2026-09-11 (real NGT appeal, F-22) -- unlike
# "district" (a real office title too: "District Collector", "District
# Judge" are genuine parties, so it's deliberately NOT here), these three
# are address-only Indian revenue-administration terms with no plausible
# party-name reading.
ADDRESS_LINE_RE = re.compile(
    r"\b\d{6}\b|\btal\.|\b(?:road|street|marg|nagar|chambers|centre|center|"
    r"bhavan|tower|complex|colony|sector|block|floor|opp\.?|near|taluka?|"
    r"tehsil|village)\b", re.I)

# A line that is prose, not a name.
_SENTENCE_RE = re.compile(r"^\s*(?:\d+\s*[\.\)]\s*)?(?:that\b|the\s+\w+\s+(?:is|are|has|have|was|were)\b)", re.I)


_INWORD_DIGIT_RE = re.compile(r"[A-Za-z][0-9][A-Za-z]|[0-9][A-Za-z]{2,}|[A-Za-z]{2,}[0-9](?![0-9])")


def _ocr_probe(s: str) -> str:
    """OCR-normalise ONLY tokens that contain letters.

    A blanket str.translate corrupts genuine numbers — '2024' becomes '2O24'
    and the year no longer matches, so a case heading slips through as a party.
    Applying the map per token leaves pure-numeric tokens untouched.
    """
    out = []
    for tok in re.split(r"(\s+)", s or ""):
        out.append(tok.translate(_OCR_MAP) if re.search(r"[A-Za-z]", tok) else tok)
    return "".join(out)


def _ocr_mangled_ratio(name: str) -> float:
    """Fraction of alphabetic tokens that contain an embedded digit.

    'REP0RTA8LE', '1N', '5UPREME' are OCR damage, not names. A digit INSIDE a
    word is the signal — 'Sector 15 Society' is a legitimate name and has the
    digit as its own token.
    """
    toks = [t for t in re.split(r"\s+", (name or "").strip()) if t]
    if not toks:
        return 0.0
    bad = sum(1 for t in toks if _INWORD_DIGIT_RE.search(t))
    return bad / len(toks)


def _looks_like_party_name(name: str) -> bool:
    """Reject body prose, headings and boilerplate masquerading as names."""
    n = name.strip()
    # OCR-damaged text must not become a party at any confidence. Test both the
    # raw string and its OCR-normalised form, so '1N THE 5UPREME C0URT' is
    # caught by FORUM_RE below even though the raw string would not match.
    if _ocr_mangled_ratio(n) >= 0.34:
        return False
    if _is_caption_furniture_name(n):
        return False
    probe = _ocr_probe(n)
    if FORUM_RE.search(probe) or CASE_HEADING_RE.match(probe):
        return False
    if re.match(r"^\s*(?:reportable|non[\s\-]?reportable|in\s+the\b)", probe, re.I):
        return False
    if len(n) < 3 or len(n) > 90:
        return False
    if _SENTENCE_RE.match(n) or BODY_START_RE.match(n) or _is_body_paragraph(n):
        return False
    if FORUM_RE.search(n) or CASE_NUMBER_RE.search(n) or INDIC_CASE_NO_RE.search(n):
        return False
    if re.search(r"\bjurisdiction\b|\bbench\b", n, re.I):
        return False
    if JUDGE_LINE_RE.match(n):
        return False
    if (CASE_HEADING_RE.match(n) or CASE_SHORTFORM_RE.match(n)
            or CASE_TYPE_WORDS_RE.search(n)):
        return False
    # A line stating a money figure is body text, not a party
    if re.search(r"(?:Rs\.?|₹|INR)\s?[\d,]", n, re.I):
        return False
    if re.match(r"^\s*\(?(?:arising|rupees|with|versus|and)\b", n, re.I):
        return False
    if not re.search(r"[A-Za-z\u0900-\u0DFF]{3}", n):
        return False
    # Prose has many lowercase function words; names rarely do
    if len(n.split()) > 6 and len(re.findall(r"\b(?:the|of|and|for|with|under|to|in)\b",
                                             n, re.I)) >= 3:
        return False
    return True


def _clean_party_name(raw: str) -> tuple[str, Optional[str], Optional[int]]:
    """Strip role markers and ordinals: '2. XYZ Ltd  ...Respondent No.2'."""
    role = None
    # OCR-normalize before role matching: '...Pet1t1oner' must still match
    probe = raw.translate(_OCR_MAP) if any(c in raw for c in "015 8|") else raw
    m = ROLE_MARKER_RE.search(probe) or ROLE_MARKER_RE.search(raw)
    if m:
        tok = m.group(1)
        role = _INDIC_ROLE_EN.get(tok, tok.title().replace("  ", " "))
        raw = raw[:m.start()]
    elif im := _INDIC_ROLE_RE.search(raw):
        role = _INDIC_ROLE_EN.get(im.group(1), im.group(1))
        raw = raw[:im.start()]
    ordinal = None
    om = _NUMBERED_PARTY_RE.match(raw)
    if om:
        ordinal = int(om.group(1))
        raw = om.group(2)
    raw = re.sub(r"\bNo\.?\s*\d+\s*$", "", raw, flags=re.I)
    raw = re.sub(r"[\.\u2026\-–—_]{2,}", " ", raw)
    raw = re.sub(r"\s{2,}", " ", raw).strip(" \t.,;:-–—…")
    return raw, role, ordinal


def _block_bounds_above(lines: list[str], anchor: int, max_span: int = 20) -> int:
    """Walk up from VERSUS to the top of the cause title."""
    start = anchor
    blanks = 0
    for i in range(anchor - 1, max(-1, anchor - max_span), -1):
        s = lines[i].strip()
        if not s:
            blanks += 1
            if blanks >= 3 and start < anchor:
                break
            continue
        blanks = 0
        if _PAGE_BREAK_RE.match(s):
            continue
        if _is_caption_furniture_line(s) or _is_caption_section_label(s):
            break
        if (TITLE_TOP_RE.match(s) or CASE_NUMBER_RE.search(s)
                or FORUM_RE.search(s) or INDIC_CASE_NO_RE.search(s)
                or CASE_HEADING_RE.match(s) or _BETWEEN_RE.match(s)):
            break
        start = i
    return start


def _block_bounds_below(lines: list[str], anchor: int, max_span: int = 24) -> int:
    """Walk down from VERSUS to where the pleading body starts."""
    end = anchor
    blanks = 0
    for i in range(anchor + 1, min(len(lines), anchor + max_span)):
        s = lines[i].strip()
        if not s:
            blanks += 1
            if blanks >= 3 and end > anchor:
                break
            continue
        blanks = 0
        if _PAGE_BREAK_RE.match(s):
            continue
        if (_is_caption_section_label(s) or _is_caption_furniture_line(s)
                or BODY_START_RE.match(s) or _is_body_paragraph(s)):
            break
        end = i
    return end


def _group_entries(lines: list[str], lo: int, hi: int) -> list[dict]:
    """Group a party block into entries.

    An entry = one party. A new entry starts on a numbered line or after a
    blank; description lines ('a company incorporated...', 'having its
    registered office...') attach to the current entry rather than becoming
    new parties. A standalone role-marker line applies to the current entry.
    """
    entries: list[dict] = []
    cur: Optional[dict] = None
    in_advocate_block = False
    for i in range(lo, hi + 1):
        raw = lines[i] if 0 <= i < len(lines) else ""
        s = LISTING_MARKER_RE.sub("", raw).strip()
        if not s:
            cur = None            # blank line closes the current entry
            in_advocate_block = False
            continue
        if _PAGE_BREAK_RE.match(s):
            continue              # layout artifact -- cur stays open
        if _is_caption_furniture_line(s) or _is_caption_section_label(s):
            cur = None
            continue
        if ADVOCATE_START_RE.match(s):
            in_advocate_block = True
            continue
        if in_advocate_block:
            # stay in the block until a role marker or a blank line ends it
            if ROLE_MARKER_RE.search(s) or STANDALONE_ROLE_RE.match(s):
                in_advocate_block = False
            else:
                continue
        if ADVOCATE_LINE_RE.search(s) or REGISTRY_LINE_RE.match(s):
            continue
        if (re.search(r"\b(?:Rules|Code|Act|Regulations),?\s*\d{4}\b", s)
                and not ROLE_MARKER_RE.search(s)):
            if cur:
                cur["desc"].append(s)
            continue
        if ADDRESS_LINE_RE.search(s) and not ROLE_MARKER_RE.search(s):
            if cur:
                cur["desc"].append(s)
            continue
        if STANDALONE_ROLE_RE.match(s):
            m = STANDALONE_ROLE_RE.match(s)
            role = m.group(1).title()
            om = re.search(r"no\.?\s*(\d+)", s, re.I)
            target = cur or (entries[-1] if entries else None)
            if target:
                target["role"] = role
                if om and target.get("ordinal") is None:
                    target["ordinal"] = int(om.group(1))
            continue
        if _DESC_LINE_RE.match(s) or _NOISE_LINE_RE.match(s):
            if cur:
                cur["desc"].append(s)
            continue
        if cur is not None and cur.get("ordinal") is not None and not _NUMBERED_PARTY_RE.match(s):
            # Inside a NUMBERED multi-line party entry -- e.g. a tribunal
            # "BETWEEN: 1. Name,\n  Address line,\n  Address line,\n\n2. Name,
            # ..." block. Found on a real filed NGT appeal (2026-09-11,
            # F-22/F-23): every line above this one only attaches to `cur`
            # if it POSITIVELY matches a known continuation pattern (address,
            # description, noise, ...) -- anything that doesn't gets the
            # OPPOSITE default, "does this look like a name?", which quietly
            # waves through plain address fragments with no dedicated regex
            # ("Grampanchayat Tiroda", "Khashewadi, Tiroda", "Sindhunagri,
            # Oras") as brand-new fake parties. Once we know we're inside a
            # numbered entry specifically, flip the default: a line is a
            # continuation of THIS entry unless it's itself a new numbered
            # one. Gated on `ordinal is not None` so the far more common
            # unnumbered 2-party VERSUS caption (name / VERSUS / name, no
            # numbering at all) is completely unaffected -- there `cur`
            # never carries an ordinal, so this branch never fires and the
            # existing name-detection default still applies.
            cur["desc"].append(s)
            continue
        name, role, ordinal = _clean_party_name(s)
        if not _looks_like_party_name(name):
            continue
        cur = {"name": name, "role": role, "ordinal": ordinal,
               "desc": [], "line_no": i}
        entries.append(cur)
    return entries


def extract_parties(text: str, profile: Profile) -> tuple[list[Party], dict]:
    """Split the cause title at the VERSUS anchor and assign roles.

    Role cascade, most trustworthy first:
      1. explicit  — a role marker, inline OR on its own right-aligned line
      2. case_type — inferred from the case-number prefix (W.P. -> Petitioner)
      3. positional— first block is the moving party (true by convention)
    """
    meta: dict[str, Any] = {"anchor_line": None, "role_source": None}
    lines = text.splitlines()[:160]

    # A single judgment often decides SEVERAL connected appeals, each with its
    # own cause title joined by "WITH". Collect every separator, not just one.
    anchors = [i for i, l in enumerate(lines) if is_versus_line(l)]
    between_idx = None
    if not anchors:
        # Tribunal captions (NGT, some NCLAT/consumer fora orders) don't use
        # VERSUS at all: "BETWEEN: <party block> ....Appellants. AND <party
        # block> ....Respondents." Found on a real filed NGT appeal
        # (2026-09-11) that returned zero parties despite a clean, real
        # multi-party caption -- the cause title WAS there, just not anchored
        # on a word this ladder recognized. Gated on BETWEEN actually being
        # present so a document's ordinary prose "AND" is never mistaken for
        # a caption separator.
        between_idx = next((i for i, l in enumerate(lines[:80])
                            if _BETWEEN_RE.match(l)), None)
        if between_idx is not None:
            and_idx = next((i for i in range(between_idx + 1, min(len(lines), between_idx + 60))
                            if _AND_SEP_RE.match(lines[i])), None)
            if and_idx is not None:
                anchors = [and_idx]
            else:
                between_idx = None
    if not anchors:
        return [], meta
    anchor = anchors[0]
    meta["anchor_line"] = anchor
    meta["all_anchors"] = anchors

    roles = profile.roles
    head = "\n".join(text.splitlines()[:15])
    cm = CASE_NUMBER_RE.search(head) or CASE_TYPE_WORDS_RE.search(head)
    if cm:
        key = re.sub(r"[^a-z.\s]", "", cm.group(1).lower()).strip(". ")
        for k, v in CASE_TYPE_ROLES.items():
            kk = k.replace(".", "")
            if key.replace(".", "").replace(" ", "").startswith(kk):
                roles = v
                meta["case_type"] = cm.group(0).strip()
                break
        else:
            meta["case_type"] = cm.group(0).strip()

    out: list[Party] = []
    seen: set[str] = set()

    for idx, anc in enumerate(anchors):
        prev_anc = anchors[idx - 1] if idx else -1
        next_anc = anchors[idx + 1] if idx + 1 < len(anchors) else len(lines)

        if idx == 0 and between_idx is not None:
            # We already know exactly where this block starts -- skip the
            # generic upward walk entirely. It exists to FIND the top of a
            # VERSUS cause title, an unknown boundary; here the boundary is
            # already known (right after "BETWEEN:"). Reusing it anyway was
            # the actual bug on the real NGT appeal above: a run of blank
            # lines inside a real 3-party numbered address block (a PDF
            # layout artifact, not a caption boundary) tripped the walk's
            # "3 blank lines = left the caption" heuristic and truncated the
            # block to 2 lines, silently dropping all 3 real Appellants.
            lo_a = max(between_idx + 1, prev_anc + 1)
        else:
            lo_a = max(_block_bounds_above(lines, anc), prev_anc + 1)
        hi_b = min(_block_bounds_below(lines, anc), next_anc - 1)
        if idx == 0:
            meta["block_above"] = (lo_a, anc - 1)
            meta["block_below"] = (anc + 1, hi_b)

        for side, (lo, hi), default_role in (("A", (lo_a, anc - 1), roles[0]),
                                             ("B", (anc + 1, hi_b), roles[1])):
            for e in _group_entries(lines, lo, hi):
                key = e["name"].lower().strip()
                if key in seen:
                    continue
                seen.add(key)
                conf = ("explicit" if e["role"]
                        else ("case_type" if meta.get("case_type") else "positional"))
                out.append(Party(e["name"], e["role"] or default_role, conf, side,
                                 e["ordinal"], e["line_no"]))

    meta["role_source"] = out[0].role_confidence if out else None
    return _filter_caption_furniture_parties(out), meta


# ---------------------------------------------------------------------------
# Non-cause-title extractors — contracts, notices, affidavits
# ---------------------------------------------------------------------------

_BETWEEN_RE = re.compile(r"^\s*between\s*:?\s*$", re.I)
_AND_SEP_RE = re.compile(r"^\s*and\s*:?\s*$", re.I)
_HEREINAFTER_RE = re.compile(
    r"\(\s*(?:herein\s*after|hereinafter)\s+(?:referred\s+to\s+as\s+|called\s+)?"
    r"[\"'“”‘’]?(?:the\s+)?(?P<label>[A-Za-z][A-Za-z\s]{2,30}?)[\"'“”‘’]?\s*\)", re.I)


def extract_parties_recital(text: str, profile: Profile) -> tuple[list[Party], dict]:
    """Contracts: BETWEEN <party A> AND <party B>, with roles from the
    'hereinafter called the Employer/Contractor' label when present."""
    meta: dict[str, Any] = {"anchor_line": None, "role_source": "recital"}
    lines = text.splitlines()[:200]
    b_idx = next((i for i, l in enumerate(lines) if _BETWEEN_RE.match(l)), None)
    if b_idx is None:
        return [], meta
    a_idx = next((i for i in range(b_idx + 1, min(len(lines), b_idx + 30))
                  if _AND_SEP_RE.match(lines[i])), None)
    if a_idx is None:
        return [], meta
    meta["anchor_line"] = a_idx

    out: list[Party] = []
    for side, (lo, hi), default in (("A", (b_idx + 1, a_idx - 1), profile.roles[0]),
                                    ("B", (a_idx + 1, min(len(lines), a_idx + 12)),
                                     profile.roles[1])):
        block = "\n".join(lines[lo:hi + 1])
        label = None
        if hm := _HEREINAFTER_RE.search(block):
            label = hm.group("label").strip().title()
        for e in _group_entries(lines, lo, hi):
            name = _HEREINAFTER_RE.sub("", e["name"]).strip(" ,;")
            if not _looks_like_party_name(name):
                continue
            out.append(Party(name, label or default,
                             "explicit" if label else "positional",
                             side, e["ordinal"], e["line_no"]))
            break  # first named entity per side is the party
    return out, meta


_MY_CLIENT_RE = re.compile(
    r"(?:under\s+instructions\s+from|on\s+behalf\s+of|instructed\s+by)\s+"
    r"(?:my|our)\s+client[s]?,?\s+(?P<name>[A-Z][^,\n.]{3,70})", re.I)
_TO_BLOCK_RE = re.compile(r"^\s*to\s*[,:]?\s*$", re.I)
_FROM_BLOCK_RE = re.compile(r"^\s*from\s*[,:]\s*(?P<name>.+)$", re.I)


def extract_parties_letterhead(text: str, profile: Profile) -> tuple[list[Party], dict]:
    """Notices and correspondence: sender from the 'my client' clause or a
    From: header; recipient from the To: block."""
    meta: dict[str, Any] = {"anchor_line": None, "role_source": "letterhead"}
    lines = text.splitlines()[:120]
    out: list[Party] = []

    if m := _MY_CLIENT_RE.search(text[:4000]):
        nm = m.group("name").strip(" ,.")
        if _looks_like_party_name(nm):
            out.append(Party(nm, "Sender", "explicit", "A", None, 0))
    if not out:
        for i, l in enumerate(lines):
            if fm := _FROM_BLOCK_RE.match(l):
                nm = fm.group("name").strip(" ,.")
                if _looks_like_party_name(nm):
                    out.append(Party(nm, "Sender", "explicit", "A", None, i))
                break

    for i, l in enumerate(lines):
        if _TO_BLOCK_RE.match(l):
            meta["anchor_line"] = i
            for j in range(i + 1, min(len(lines), i + 6)):
                s = lines[j].strip()
                if not s:
                    continue
                if re.match(r"^\s*sub(?:ject)?\s*:", s, re.I):
                    break
                nm, _, _ = _clean_party_name(s)
                if _looks_like_party_name(nm):
                    out.append(Party(nm, "Recipient", "explicit", "B", None, j))
                    break
            break
    return out, meta


_DEPONENT_RE = re.compile(
    r"\bI,\s*(?P<name>[A-Z][A-Za-z.\s]{2,60}?)\s*,\s*"
    r"(?:s/?o|d/?o|w/?o|aged|r/?o|do\s+hereby|residing)", re.I)


def extract_parties_deponent(text: str, profile: Profile) -> tuple[list[Party], dict]:
    """Standalone affidavits: 'I, <name>, S/o ..., do hereby solemnly affirm'."""
    meta: dict[str, Any] = {"anchor_line": None, "role_source": "deponent_clause"}
    if m := _DEPONENT_RE.search(text[:6000]):
        nm = m.group("name").strip(" ,.")
        if _looks_like_party_name(nm):
            return [Party(nm, "Deponent", "explicit", "A", None, 0)], meta
    return [], meta


_EXTRACTORS = {
    "cause_title": extract_parties,
    "recital": extract_parties_recital,
    "letterhead": extract_parties_letterhead,
    "deponent_clause": extract_parties_deponent,
}


def extract_parties_auto(text: str, profile: Profile) -> tuple[list[Party], dict]:
    """Dispatch to the right extractor for the document type, then fall back.

    A cause title is tried for every document regardless of profile, because
    affidavits, orders and even annexures are frequently prefixed with one.
    """
    fn = _EXTRACTORS.get(profile.role_source or "")
    parties, meta = (fn(text, profile) if fn else ([], {"role_source": None}))
    if not parties and profile.role_source != "cause_title":
        parties, meta2 = extract_parties(text, profile)
        if parties:
            meta = {**meta2, "role_source": "cause_title_fallback"}
    if not parties and profile.role_source != "deponent_clause":
        parties, meta3 = extract_parties_deponent(text, profile)
        if parties:
            meta = {**meta3, "role_source": "deponent_fallback"}
    return parties, meta


# ---------------------------------------------------------------------------
# FALLBACK LADDER — mirrors layout_structure.detect_structure_layered()
# ---------------------------------------------------------------------------

# "Gurmeet Singh @ Sheru Versus State NCT of Delhi" — both parties on ONE line.
# Extremely common when an order refers to another case, and in short orders
# where the registry prints the cause title inline rather than stacked.
INLINE_VERSUS_RE = re.compile(
    r"(?P<a>[A-Z][^\n\"']{2,70}?)\s+"
    r"(?:versus|vs\.?|v/s|v\.)\s+"
    r"(?P<b>[A-Z][^\n\"']{2,70}?)"
    r"(?=\s*(?:[\"'\)]|$|,\s|\sis\b|\stitled\b|\sarising\b))", re.I)


def extract_parties_inline(text: str, profile: Profile) -> tuple[list[Party], dict]:
    """Tier 4: both parties on a single line."""
    meta: dict[str, Any] = {"anchor_line": None, "role_source": "inline_versus"}
    for i, line in enumerate(text.splitlines()[:200]):
        s = LISTING_MARKER_RE.sub("", line).strip()
        if len(s) < 8 or len(s) > 200:
            continue
        m = INLINE_VERSUS_RE.search(s)
        if not m:
            continue
        a = re.sub(r"^.*?\btitled\b\s*", "", m.group("a")).strip(" \"'“”,.")
        b = m.group("b").strip(" \"'“”,.")
        if _looks_like_party_name(a) and _looks_like_party_name(b):
            meta["anchor_line"] = i
            return ([Party(a, profile.roles[0], "positional", "A", None, i),
                     Party(b, profile.roles[1], "positional", "B", None, i)], meta)
    return [], meta


# ---------------------------------------------------------------------------
# TIER 4.5 — CAUSE-TITLE BLOCK (show the region, don't guess the names)
# ---------------------------------------------------------------------------

@dataclass
class TitleBlock:
    """The cause-title region as raw text, with provenance. No parsed names."""
    text: str
    line_start: int
    line_end: int
    anchor_line: Optional[int]
    reason: str


def extract_cause_title_block(text: str) -> Optional[TitleBlock]:
    """Locate the cause-title REGION without parsing party names out of it.

    When name-level extraction fails — OCR damage, an unknown court's layout,
    a format we have never seen — the block itself is still locatable, because
    finding it needs only a separator line or a forum/case-number heading, not
    a correct reading of every name.

    Showing the block verbatim is strictly better than showing nothing: the
    lawyer reads the parties off the original text in one glance, and the
    system has asserted nothing it cannot support.
    """
    lines = text.splitlines()[:160]
    if not lines:
        return None

    anchors = [i for i, l in enumerate(lines) if is_versus_line(l)]
    if anchors:
        anc = anchors[0]
        lo = _block_bounds_above(lines, anc)
        hi = _block_bounds_below(lines, anc)
        # widen slightly so the forum and case number come along for context
        lo = max(0, lo - 3)
        block = "\n".join(lines[lo:hi + 1]).strip()
        if block:
            return TitleBlock(block, lo, hi, anc,
                              "separator found; names not parsed")

    # No separator survived. Fall back to the heading region: forum line or
    # case number, plus the lines that follow it.
    for i, l in enumerate(lines[:20]):
        s = _ocr_probe(LISTING_MARKER_RE.sub("", l).strip())
        # A heading line stands alone: short, and not a sentence fragment.
        # Without this, "…the High Court of Judicature at Bombay regarding the
        # maintainability of…" in body prose matches FORUM_RE and the block
        # fallback returns paragraphs instead of a cause title.
        if len(s) > 80 or _is_body_paragraph(s) or _SENTENCE_RE.match(s):
            continue
        # A real heading is terse or capitalised. "CR No. 806 of 2019 registered
        # with Pimpri Police Station for the offences…" carries a case number
        # but is plainly body prose.
        terse = s.isupper() or len(s.split()) <= 8
        if terse and (CASE_NUMBER_RE.search(s) or CASE_HEADING_RE.match(s)
                      or CASE_SHORTFORM_RE.match(s)):
            pass
        elif FORUM_RE.search(s) and TITLE_TOP_RE.match(s):
            pass
        else:
            continue
        if True:
            lo, hi = i, min(len(lines) - 1, i + 14)
            block = "\n".join(lines[lo:hi + 1]).strip()
            if block:
                return TitleBlock(block, lo, hi, None,
                                  "forum/case-number heading; no separator found")
    return None


@dataclass
class PartyResult:
    parties: list[Party]
    tier: str
    tier_reason: str
    confidence: str
    meta: dict = field(default_factory=dict)
    title_block: Optional[TitleBlock] = None   # tier 4.5 payload


def extract_parties_layered(text: str, filename: str = "") -> PartyResult:
    """Five-tier party extraction. Never raises, never hard-fails.

        TIER 1  profile-specific extractor (cause title / recital / letterhead / deponent)
        TIER 2  cause-title fallback — tried for EVERY document type
        TIER 3  deponent-clause fallback
        TIER 4  inline "A Versus B" on one line
        TIER 5  no parties — returns an empty list with a stated reason

    Tier 5 is a real outcome, not a failure: many documents in a bundle
    (invoices, bank statements, photographs) genuinely have no parties, and
    the rest of the pipeline must keep working on them. The caller gets an
    explicit tier and confidence rather than a silent empty list.
    """
    profile, score, all_scores = detect_profile(text, filename)
    meta_base = {"profile": profile.id, "profile_score": score}

    if not (text or "").strip():
        return PartyResult([], "tier5_none", "empty document", "none", meta_base)

    # TIER 1
    fn = _EXTRACTORS.get(profile.role_source or "")
    if fn:
        parties, meta = fn(text, profile)
        parties = _filter_caption_furniture_parties(parties)
        if parties:
            conf = ("high" if any(p.role_confidence == "explicit" for p in parties)
                    else "medium")
            return PartyResult(parties, f"tier1_{profile.role_source}",
                               f"{profile.id} profile, {len(parties)} parties",
                               conf, {**meta_base, **meta})

    # TIER 2
    if profile.role_source != "cause_title":
        parties, meta = extract_parties(text, profile)
        parties = _filter_caption_furniture_parties(parties)
        if parties:
            return PartyResult(parties, "tier2_cause_title",
                               "cause title found despite non-filing profile",
                               "medium", {**meta_base, **meta})

    # TIER 3
    if profile.role_source != "deponent_clause":
        parties, meta = extract_parties_deponent(text, profile)
        parties = _filter_caption_furniture_parties(parties)
        if parties:
            return PartyResult(parties, "tier3_deponent",
                               "deponent clause", "medium", {**meta_base, **meta})

    # TIER 4
    parties, meta = extract_parties_inline(text, profile)
    parties = _filter_caption_furniture_parties(parties)
    if parties:
        return PartyResult(parties, "tier4_inline_versus",
                           "parties on a single line; roles are positional",
                           "low", {**meta_base, **meta})

    # TIER 4.5 — show the cause-title region verbatim rather than guessing
    block = extract_cause_title_block(text)
    if block:
        return PartyResult([], "tier4b_title_block",
                           f"cause-title region located ({block.reason}); "
                           f"shown verbatim for the reader to identify parties",
                           "block", meta_base, title_block=block)

    # TIER 5
    return PartyResult([], "tier5_none",
                       "no cause title, recital, letterhead or inline separator "
                       "found — document may genuinely have no parties",
                       "none", meta_base)


# ---------------------------------------------------------------------------
# MANDATORY HYBRID EXTRACTION — ML layer + deterministic layer, always combined
# ---------------------------------------------------------------------------
#
# This replaces the earlier "tier 0, optional, falls back to regex" idea.
# Both layers below are REQUIRED and their outputs are MERGED, not chosen
# between:
#
#   Layer 1 (mandatory) — OpenNyAI ML NER finds party NAMES and a rough
#       PETITIONER/RESPONDENT-style side. It generalises across court
#       registries this codebase has never seen tested.
#   Layer 2 (mandatory) — the deterministic case-type mapping already built
#       (CASE_TYPE_ROLES) refines that generic side into the PRECISE role a
#       lawyer expects on screen: Plaintiff/Defendant for a suit,
#       Financial Creditor/Corporate Debtor for an insolvency petition, etc.
#       The ML model's label set is coarser than this — it does not know
#       what a commercial suit is — so this layer is not optional even when
#       Layer 1 succeeds.
#
# extract_parties_layered() (the regex-only 5-tier ladder) is NOT deleted.
# It remains as (a) the genuine last resort for documents with no parties
# findable by either layer, and (b) the explicit degraded-mode path when the
# ML model cannot be loaded at all.


def _refine_roles_by_case_type(parties: list[Party], text: str,
                                profile: Profile) -> list[Party]:
    """Turn the ML model's generic PETITIONER/RESPONDENT into the precise
    role for THIS document type. Always run on ML output — never skipped."""
    head = "\n".join(text.splitlines()[:15])
    cm = CASE_NUMBER_RE.search(head) or CASE_TYPE_WORDS_RE.search(head)
    if not cm:
        return parties

    key = re.sub(r"[^a-z.\s]", "", cm.group(1).lower()).strip(". ")
    roles = None
    for k, v in CASE_TYPE_ROLES.items():
        kk = k.replace(".", "")
        if key.replace(".", "").replace(" ", "").startswith(kk):
            roles = v
            break
    if not roles:
        return parties

    return [Party(p.name, roles[0] if p.side == "A" else roles[1],
                  "ml_ner+case_type", p.side, p.ordinal, p.line_no)
            for p in parties]


def _ml_role_unstable_names(text: str, nlp) -> list[str]:
    """Same normalized name tagged with more than one party-side ML label.

    Inspects raw NER mentions, not extract_parties_ml's first-mention
    collapse — that collapse is why instability is invisible on Party lists.
    """
    from collections import defaultdict
    from opennyai_bridge import PARTY_LABELS_TO_SIDE, run_ner

    by_name: dict[str, set[str]] = defaultdict(set)
    for e in run_ner(nlp, text[:20000]):
        if e.label not in PARTY_LABELS_TO_SIDE:
            continue
        key = re.sub(r"\s+", " ", e.text or "").strip().casefold()
        if key:
            by_name[key].add(e.label)
    return sorted(name for name, labels in by_name.items() if len(labels) > 1)


def _prefix_title_block(text: str, max_chars: int = 800) -> Optional[TitleBlock]:
    """Verbatim prefix when ML roles are unstable but no cause-title region
    was located. Same 800-char span the F-3 POC used — not invented text."""
    span = (text or "").strip()[:max_chars].strip()
    if not span:
        return None
    nlines = max(0, span.count("\n"))
    return TitleBlock(span, 0, nlines, None, "ml role-unstable; document prefix")


_UNSET = object()  # distinguishes "caller didn't pass nlp" from "caller
                    # already resolved it and it's genuinely None/unavailable"


def extract_parties_hybrid(text: str, filename: str = "", *,
                           nlp=_UNSET, allow_degraded: bool = False) -> PartyResult:
    """MANDATORY two-layer party extraction. Both layers run; results merge.

    `nlp`:
      - omitted entirely -> this function loads the model itself via
        opennyai_bridge.load_opennyai_ner(), which RAISES by default if the
        model is missing (allow_degraded=True to instead return None).
      - a model object -> used directly (dependency injection for testing).
      - explicit nlp=None -> treated as "caller already resolved this to
        unavailable" and used as-is WITHOUT re-attempting a load. This
        matters for batch callers (e.g. poc_run.py processing many
        documents): load once, pass the result to every call, and a failed
        load should not re-trigger a load attempt (and its warning banner)
        once per document.
    """
    from opennyai_bridge import ModelNotAvailableError, extract_parties_ml

    if nlp is _UNSET:
        from opennyai_bridge import load_opennyai_ner
        nlp = load_opennyai_ner("sm", allow_degraded=allow_degraded)
        # nlp is None here ONLY if allow_degraded=True and loading failed —
        # load_opennyai_ner already raised otherwise.

    profile, score, _ = detect_profile(text, filename)
    meta_base = {"profile": profile.id, "profile_score": score,
                 "ml_layer": "active" if nlp is not None else "degraded"}

    if nlp is not None:
        ml_parties, ml_meta = extract_parties_ml(text, nlp)
        if ml_parties:
            refined = _filter_caption_furniture_parties(
                _refine_roles_by_case_type(ml_parties, text, profile))
            if not refined:
                pass  # furniture-only ML hits — fall through to the ladder
            else:
                role_refined = sum(1 for a, b in zip(ml_parties, refined)
                                   if a.role != b.role)
                unstable = _ml_role_unstable_names(text, nlp)
                if unstable:
                    block = extract_cause_title_block(text) or _prefix_title_block(text)
                    return PartyResult(
                        refined, "ml_role_unstable",
                        "same normalized name tagged with more than one ML role "
                        f"in this document: {unstable}",
                        "ml_role_unstable",
                        {**meta_base, **ml_meta, "role_unstable_names": unstable},
                        title_block=block)
                return PartyResult(
                    refined, "mandatory_ml_plus_case_type",
                    f"{len(refined)} parties from ML NER; {role_refined} role(s) "
                    f"refined by deterministic case-type mapping",
                    "high", {**meta_base, **ml_meta})

    # Either the ML layer is degraded, or it ran and found nothing (some
    # documents — orders with no cause title recap, annexure fragments —
    # genuinely have no ML-findable parties). Fall through to the
    # deterministic ladder, which still runs its own full 5-tier attempt.
    result = extract_parties_layered(text, filename)
    result.meta = {**meta_base, **result.meta,
                   "ml_layer_used": nlp is not None,
                   "note": ("ML layer active but found nothing; deterministic "
                            "ladder used" if nlp is not None else
                            "ML layer degraded; deterministic ladder used")}
    if nlp is None:
        result.tier = f"DEGRADED_{result.tier}"
    return result


# ---------------------------------------------------------------------------
# Fallback graph node — consume an existing low-confidence PartyResult
# ---------------------------------------------------------------------------
#
# Does not change extraction. When the ladder already landed on tier 4.5
# (verbatim cause-title block) or tier 5 with no located region, this turns
# a TitleBlock into an events[i]-shaped dict for the existing graph path.
# See docs/requirements/2026-09-09-verbatim-fallback-nodes/.


def party_result_to_fallback_event(
    result: PartyResult,
    document_id: str,
    offsets: list,
) -> Optional[dict]:
    """Build one fallback event from a low-confidence PartyResult, or None.

    Returns None when there is no located text region (tier 5 with no
    TitleBlock, empty block, or any non-fallback tier). Never invents a
    span. Deterministic extraction runs on ``title_block.text`` only.
    """
    if result.tier not in ("tier4b_title_block", "tier5_none", "ml_role_unstable"):
        return None
    block = result.title_block
    if block is None:
        return None
    span = (block.text or "").strip()
    if not span:
        return None

    # Lazy import: casemap_pipeline does not import this module today; keep
    # the seam one-way so a future reverse import cannot cycle at load time.
    from casemap_pipeline import (
        extract_deterministic,
        normalize_entities,
        offset_to_page,
        _canonical_key,
    )

    det = extract_deterministic(span, offsets)

    entity_dicts: list[dict] = []
    for item in det.get("case_numbers") or []:
        entity_dicts.append({
            "text": item["raw"],
            "label": "CASE_NUMBER",
            "span": item["span"],
        })
    for item in det.get("sections") or []:
        entity_dicts.append({
            "text": item["raw"],
            "label": "PROVISION",
            "span": item["span"],
        })
    # Verbatim party names already extracted — identity for linking, not a
    # guessed role. T3: ALL-CAPS vs title-case must share a canonical key.
    for p in result.parties or []:
        if (p.name or "").strip():
            entity_dicts.append({
                "text": p.name.strip(),
                "label": "PERSON",
                "span": (0, 0),
            })
    # Type-scoped fuzzy merge within this span, then emit canonical keys so
    # a later document's same name (different casing) shares an id without
    # a global ent_NNNN counter (T3 / BUG-5).
    entity_map = normalize_entities(entity_dicts)
    linked_ids = sorted({
        _canonical_key(name) for (_etype, name) in entity_map
        if _canonical_key(name)
    })

    page = offset_to_page(0, offsets) if offsets else None
    if result.tier == "ml_role_unstable":
        confidence = "ml_role_unstable"
    elif result.confidence in ("block", "degraded"):
        confidence = result.confidence
    else:
        confidence = "block" if result.tier == "tier4b_title_block" else "degraded"

    return {
        "type": "fallback_party_block",
        "document_id": document_id,
        "section_label": "cause_title_block",
        "section_text": span,
        "linked_entities": linked_ids,
        "linked_date": det["dates"][0] if det.get("dates") else None,
        "linked_amount": det["amounts"][0] if det.get("amounts") else None,
        "polarity": "NEUTRAL",
        "confidence": confidence,
        "sources": [{
            "document": document_id,
            "page": page,
            "char_start": 0,
            "char_end": len(span),
            "text": span[:300],
            "section": "cause_title_block",
        }],
    }
