"""Deterministic rhetorical-role cues (F-7 fixes).

Not a trained classifier. Confidence is always heuristic (`cue_matched` /
`carried_forward` / `untagged`). PRECEDENT does not carry forward — a citation
is a sentence, not a section (F-7 poison). Generic cue `in the case of` is
removed. Longer cues use rapidfuzz partial_ratio (same class as
`is_versus_line()`).
"""

from __future__ import annotations

import re
from typing import Optional

NUMBERED_PARA_RE = re.compile(r"^\s*\d{1,3}\.\s+\S")

RHETORICAL_ROLE_CUES = {
    "FACTS": [
        "the facts of the case", "brief facts are", "briefly stated",
        "facts leading to", "facts giving rise to", "the facts relevant",
        "facts of this case",
    ],
    "ISSUES": [
        "question for consideration", "issue that arises", "issues involved",
        "the question is whether", "point for determination", "main issue",
    ],
    "ARGUMENTS_PETITIONER": [
        "learned counsel for the petitioner",
        "learned counsel for the appellant",
        "it is submitted by the petitioner",
        "it is contended by the appellant",
        "counsel for the appellant submits",
        "counsel for the petitioner",
    ],
    "ARGUMENTS_RESPONDENT": [
        "learned counsel for the respondent",
        "it is submitted by the respondent",
        "on behalf of the respondent",
        "counsel for the respondent",
    ],
    "PRECEDENT": [
        "relied upon the judgment",
        "reported in",
        "this court held in",
        "cited the decision",
    ],
    "ANALYSIS": [
        "we have considered", "having heard", "we are of the view",
        "in our opinion", "having perused", "we have heard", "we have examined",
    ],
    "RULING": [
        "in view of the above", "for the reasons stated", "it is ordered",
        "the appeal is dismissed", "the appeal is allowed",
        "the petition is dismissed", "the petition is allowed",
        "we dismiss", "we allow",
    ],
}

# Roles that are contiguous blocks in judgments. PRECEDENT is not.
_CARRY_ROLES = {
    "FACTS", "ISSUES", "ARGUMENTS_PETITIONER", "ARGUMENTS_RESPONDENT",
    "ANALYSIS", "RULING",
}

_FUZZ_MIN_CUE = 16
_FUZZ_THRESHOLD = 88


def split_paragraphs(text: str) -> list[tuple[str, int, int]]:
    lines = text.splitlines(keepends=True)
    paras, cur, cur_start, offset = [], "", 0, 0
    for line in lines:
        if NUMBERED_PARA_RE.match(line) and cur.strip():
            paras.append((cur, cur_start, offset))
            cur, cur_start = "", offset
        cur += line
        offset += len(line)
    if cur.strip():
        paras.append((cur, cur_start, offset))
    if len(paras) <= 1:
        paras = []
        offset = 0
        for block in re.split(r"\n\s*\n", text):
            if not block.strip():
                offset += len(block)
                continue
            start = text.find(block, offset)
            if start < 0:
                start = offset
            paras.append((block, start, start + len(block)))
            offset = start + len(block)
    return paras


def match_cue(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    if not lowered.strip():
        return None
    try:
        from rapidfuzz import fuzz
    except ImportError:
        fuzz = None
    for role, cues in RHETORICAL_ROLE_CUES.items():
        for cue in cues:
            if cue in lowered:
                return role
            if fuzz is not None and len(cue) >= _FUZZ_MIN_CUE:
                if fuzz.partial_ratio(cue, lowered) >= _FUZZ_THRESHOLD:
                    return role
    return None


def tag_paragraphs(paragraphs) -> list[dict]:
    current_role, tagged = None, []
    for text, start, end in paragraphs:
        matched = match_cue(text)
        if matched:
            role, confidence = matched, "cue_matched"
        elif current_role:
            role, confidence = current_role, "carried_forward"
        else:
            role, confidence = None, "untagged"
        if matched in _CARRY_ROLES:
            current_role = matched
        # PRECEDENT deliberately does NOT become current_role — a citation is a
        # sentence, not a section, so it must not lock the rest of the judgment
        # (F-7 poison). current_role is left untouched.
        tagged.append({
            "role": role,
            "confidence": confidence,
            "char_start": start,
            "char_end": end,
            "text": text,
        })
    return tagged


def tag_document(text: str) -> list[dict]:
    return tag_paragraphs(split_paragraphs(text or ""))
