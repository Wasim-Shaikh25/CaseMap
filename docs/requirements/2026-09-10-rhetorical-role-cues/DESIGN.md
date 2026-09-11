# Design: deterministic rhetorical-role tagging

**Date:** 2026-09-10
**Requirements:** `REQUIREMENTS.md` in this folder.

## What's reused vs. genuinely new

**Reused pattern (not reused code):** `casemap_pipeline.EVENT_KEYWORDS` +
`detect_events()`'s phrase-matching mechanism is the direct model for FR2's cue table
— same idea (a dict of category → phrase list, scanned against text), applied at
paragraph granularity instead of per-keyword-hit granularity.

**Genuinely new, not found elsewhere in `src/`:** a paragraph splitter. Neither
`casemap_pipeline.py` nor `document_profile.py` has a "paragraph" concept today —
`detect_structure`'s `TOC_DOTTED`/`TOC_COLUMNAR`/`ANNEXURE_PATTERN` work on single
lines, and `detect_events`'s `WINDOW` is a fixed 400-char radius around a keyword hit,
not a paragraph boundary. This design adds one, explicitly new:

```python
NUMBERED_PARA_RE = re.compile(r"^\s*\d{1,3}\.\s+\S")  # "1. Leave granted." etc.

def split_paragraphs(text: str) -> list[tuple[str, int, int]]:
    """Returns (paragraph_text, char_start, char_end). Splits on numbered-paragraph
    markers (the dominant convention in Indian judgments — see any testdata/ file)
    with a blank-line-block fallback for unnumbered prose."""
```

Real Indian judgments (every `testdata/` file) are numbered-paragraph prose
("1. Leave granted. 2. This appeal arises out of..."), so a numbered-paragraph
splitter is the right first cut — not a generic sentence tokenizer, which would
fragment role assignment far too finely for a coarse heuristic to work well against.

## The cue table (FR2)

```python
RHETORICAL_ROLE_CUES = {
    "FACTS": ["the facts of the case", "brief facts are", "briefly stated",
              "facts leading to", "facts giving rise to"],
    "ISSUES": ["question for consideration", "issue that arises", "issues involved",
               "the question is whether", "point for determination"],
    "ARGUMENTS_PETITIONER": ["learned counsel for the petitioner", "learned counsel
              for the appellant", "it is submitted by the petitioner",
              "it is contended by the appellant"],
    "ARGUMENTS_RESPONDENT": ["learned counsel for the respondent",
              "it is submitted by the respondent", "on behalf of the respondent"],
    "PRECEDENT": ["relied upon the judgment", "in the case of", "reported in",
                  "this court held in"],
    "ANALYSIS": ["we have considered", "having heard", "we are of the view",
                 "in our opinion", "having perused"],
    "RULING": ["in view of the above", "for the reasons stated", "it is ordered",
               "the appeal is", "the petition is", "we dismiss", "we allow"],
}
```

Note: this is a *starting* table sized for the POC, not a claimed-final list — real
judgments will surface cue phrases this table misses; the POC's job is to find that
out, not to pretend completeness in advance.

## Carry-forward logic (FR3)

```python
def tag_paragraphs(paragraphs) -> list[dict]:
    current_role, tagged = None, []
    for text, start, end in paragraphs:
        role = match_cue(text)  # first matching category, or None
        confidence = "cue_matched" if role else "carried_forward"
        if role is None:
            role = current_role  # stays None until the first cue fires
        current_role = role or current_role
        tagged.append({"role": role, "text": text, "char_start": start,
                       "char_end": end, "confidence": confidence})
    return tagged
```

Paragraphs before the first matched cue get `role=None` — never guessed (FR4/FR5) —
rather than defaulting to a plausible-looking but unearned label like `"FACTS"`.

## What the POC needs to show before this is worth writing into `src/`

- Does the paragraph splitter actually produce sensible paragraphs on real
  `testdata/` documents (numbered-paragraph convention holds)?
- Does the cue table fire often enough to be useful, or does most of a real document
  end up `carried_forward`/`None`?
- Does the resulting role sequence look plausible to a human skim (Facts → Issues →
  Arguments → Analysis → Ruling in roughly that order), or does it thrash between
  roles implausibly?

This is exactly the kind of thing that must be checked against real documents, not
assumed from the design alone — same discipline as every other POC this session.
