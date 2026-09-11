"""Install OpenNyAI en_legal_ner_sm the way this machine actually needs.

HuggingFace serves en_legal_ner_sm-any-py3-none-any.whl — current pip rejects
that filename (invalid PEP 440 version 'any'). This script downloads it,
renames to 3.2.0, pip-installs it, then re-pins spaCy 3.8.x so Python 3.11 /
pydantic v2 still work.

See docs/research/new-directions/mini-llm-extraction-assessment.md Part 2
and docs/requirements/2026-09-10-wire-opennyai-ner/.

Usage (from the project venv you want the model in):

    python scripts/install_en_legal_ner_sm.py
"""

from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WHL_URL = (
    "https://huggingface.co/opennyaiorg/en_legal_ner_sm/resolve/main/"
    "en_legal_ner_sm-any-py3-none-any.whl"
)
LOCAL_NAME = "en_legal_ner_sm-3.2.0-py3-none-any.whl"
# After the wheel's old pins: restore the combination verified 2026-09-09.
REPIN = [
    "spacy==3.8.16",
    "pydantic>=2.0.0,<3.0.0",
    "thinc==8.3.13",
    "typer==0.27.2",
    "weasel==1.0.0",
    "wasabi==1.1.3",
]


def main() -> int:
    dest_dir = ROOT / "temp" / "wheels"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / LOCAL_NAME
    print(f"[+] downloading wheel to {dest} ...", flush=True)
    urllib.request.urlretrieve(WHL_URL, dest)
    print(f"[+] pip install {dest.name}", flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", str(dest)])
    print("[+] re-pinning spaCy 3.8.x chain ...", flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", *REPIN])
    print("[+] verifying spacy.load('en_legal_ner_sm') ...", flush=True)
    import spacy
    nlp = spacy.load("en_legal_ner_sm")
    print("[ok]", nlp.meta.get("name"), nlp.meta.get("version"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
