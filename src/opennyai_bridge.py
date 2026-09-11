"""
opennyai_bridge.py — MANDATORY integration layer for OpenNyAI's Indian Legal NER.

DESIGN: this is not an optional try-then-fall-back layer. The ML NER model is
a REQUIRED processing step, run on every document. Its output is COMBINED
with the deterministic case-type role refinement in document_profile.py —
neither layer is a fallback for the other; both are mandatory and their
results are merged.

WHY MANDATORY: the deterministic ladder in document_profile.py earns each
court one regex at a time (24 bugs fixed across this build, nearly all of
them "new court, new registry convention"). OpenNyAI's en_legal_ner_sm/trf
was trained on 46,545 hand-annotated entities across many Indian courts
(Kalamkar et al., NLLP 2022) and generalises to courts never tested here —
exactly the ceiling regex cannot raise on its own. Making it optional would
mean the demo silently reverts to the regex ceiling whenever the model
isn't installed, which defeats the reason for having it.

WHAT "MANDATORY" MEANS, PRECISELY:
  - load_opennyai_ner() is called eagerly. By default it RAISES
    ModelNotAvailableError if the model cannot load, with the exact install
    command, rather than silently degrading.
  - An explicit allow_degraded=True escape hatch exists for local
    development before the model is installed. It prints a loud warning
    banner, and every downstream artifact is stamped DEGRADED so a
    regex-only run is never mistaken for the real pipeline.

HONESTY ABOUT WHAT WAS TESTED: the real `en_legal_ner_sm` weights have been
loaded and run against `testdata/` (`FINDINGS.md` F-2, 2026-09-09) in
`temp/2026-09-09-mini-llm-poc/venv_ner/`. Glue-code tests in
`tests/test_opennyai_bridge.py` still use fake entity sources injected into
real spaCy Docs. The HuggingFace wheel cannot go in `requirements.txt` —
use `scripts/install_en_legal_ner_sm.py`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Optional


class ModelNotAvailableError(RuntimeError):
    """Raised when a mandatory OpenNyAI model cannot be loaded."""


NER_INSTALL_CMD = {
    "sm": (
        "python scripts/install_en_legal_ner_sm.py\n"
        "    # HuggingFace's en_legal_ner_sm-any-py3-none-any.whl has an invalid\n"
        "    # PEP 440 version; the script renames it to 3.2.0 then re-pins spaCy\n"
        "    # 3.8.16. Direct `pip install <huggingface url>` will fail.\n"
        "    # Recipe: docs/requirements/2026-09-10-wire-opennyai-ner/"
    ),
    "trf": ("pip install https://huggingface.co/opennyaiorg/en_legal_ner_trf/"
            "resolve/main/en_legal_ner_trf-any-py3-none-any.whl"),
}

# Labels transcribed from the model card's documented example output and
# Kalamkar et al. 2022. Verify exact casing against your installed model —
# this list was never checked against loaded weights in this sandbox.
PARTY_LABELS_TO_SIDE = {
    "PETITIONER": "A", "APPELLANT": "A", "PLAINTIFF": "A", "APPLICANT": "A",
    "RESPONDENT": "B", "DEFENDANT": "B",
}
NON_PARTY_PERSON_LABELS = {"JUDGE", "LAWYER", "WITNESS", "OTHER_PERSON"}

_MODEL_CACHE: dict[str, object] = {}


def reset_cache() -> None:
    """Test-only: clear the cached model handle between test cases."""
    _MODEL_CACHE.clear()


def load_opennyai_ner(size: str = "sm", *, allow_degraded: bool = False):
    """Load the OpenNyAI legal NER model. MANDATORY by default.

    Returns the loaded spaCy Language object, or None if allow_degraded=True
    and loading failed. Raises ModelNotAvailableError otherwise.
    """
    if size in _MODEL_CACHE:
        return _MODEL_CACHE[size]

    try:
        import spacy
    except ImportError as e:
        return _fail(size, f"spaCy itself is not installed ({e}).", allow_degraded)

    model_name = f"en_legal_ner_{size}"
    try:
        nlp = spacy.load(model_name)
    except OSError as e:
        return _fail(size, f"model package '{model_name}' not found ({e}).",
                     allow_degraded)

    _MODEL_CACHE[size] = nlp
    return nlp


def _fail(size: str, reason: str, allow_degraded: bool):
    cmd = NER_INSTALL_CMD.get(size, NER_INSTALL_CMD["sm"])
    msg = (f"\nOpenNyAI legal NER model ('{size}') is REQUIRED and could not "
           f"be loaded: {reason}\nInstall it with:\n\n    {cmd}\n")
    if allow_degraded:
        print(f"[DEGRADED MODE]{msg}Continuing WITHOUT the ML layer — "
              f"party/role extraction is regex-only for this run.\n",
              file=sys.stderr)
        return None
    raise ModelNotAvailableError(msg)


# ---------------------------------------------------------------------------
# Rhetorical-role model — same mandatory intent, weaker integration certainty
# ---------------------------------------------------------------------------

class RhetoricalRoleModelNotAvailableError(RuntimeError):
    pass


def load_rhetorical_role_model(*, allow_degraded: bool = False):
    """Load OpenNyAI's rhetorical-role classifier (BUILD corpus baseline,
    Kalamkar et al., LREC 2022 — 'Corpus for Automatic Structuring of Legal
    Documents'). Also mandatory by design.

    HONEST GAP: unlike the NER model, I did not find a confirmed one-line
    `spacy.load(...)` style API for this model in the sources I checked —
    the baseline lives in the Legal-NLP-EkStep/rhetorical-role-baseline
    GitHub repo with its own inference script, not a pip-installable
    package. This function is therefore a clean SEAM, not a working loader:
    it raises with instructions to confirm the repo's actual inference
    entrypoint before wiring it in for real. Treat as mandatory-in-intent,
    not mandatory-in-fact until that entrypoint is confirmed.
    """
    reason = ("no confirmed pip-installable checkpoint; clone "
              "github.com/Legal-NLP-EkStep/rhetorical-role-baseline and "
              "confirm its inference script's entrypoint before wiring "
              "this loader to it")
    if allow_degraded:
        print(f"[DEGRADED MODE] rhetorical-role model unavailable: {reason}\n"
              f"Judgment sections will not be sub-typed as Facts/Arguments/"
              f"Ratio/Ruling this run.\n", file=sys.stderr)
        return None
    raise RhetoricalRoleModelNotAvailableError(
        f"Rhetorical-role model is REQUIRED but not wired: {reason}")


# ---------------------------------------------------------------------------
# Entity extraction — real spaCy API, offset-preserving
# ---------------------------------------------------------------------------

@dataclass
class MLEntity:
    text: str
    label: str
    char_start: int
    char_end: int


def run_ner(nlp, text: str, chunk_size: int = 900_000) -> list[MLEntity]:
    """Run the model over (possibly long) text, preserving absolute offsets
    across chunk boundaries — the same pattern casemap_pipeline.py already
    uses for spaCy's 1M-char limit."""
    out: list[MLEntity] = []
    for start in range(0, len(text), chunk_size):
        chunk = text[start:start + chunk_size]
        doc = nlp(chunk)
        for ent in doc.ents:
            out.append(MLEntity(ent.text, ent.label_,
                                start + ent.start_char, start + ent.end_char))
    return out


def extract_parties_ml(text: str, nlp, *, head_chars: int = 20000) -> tuple[list, dict]:
    """Party NAMES and rough SIDE from the ML model — offsets and precise
    role naming are deliberately NOT this function's job. Role refinement
    (Plaintiff vs Petitioner vs Financial Creditor) is the deterministic
    layer's job, always run afterward on this output, never skipped.
    """
    from document_profile import Party  # local: avoid import cycle
    from case_symbols import normalize_name

    ents = run_ner(nlp, text[:head_chars])
    seen: set[str] = set()
    parties: list[Party] = []
    for e in ents:
        side = PARTY_LABELS_TO_SIDE.get(e.label)
        if side is None:
            continue
        key = normalize_name(e.text)
        if not key or key in seen:
            continue
        seen.add(key)
        parties.append(Party(e.text.strip(), e.label.title(), "ml_ner",
                             side, None, 0))

    meta = {"ner_entity_count": len(ents), "ner_party_count": len(parties),
            "ner_labels_seen": sorted({e.label for e in ents})}
    return parties, meta
