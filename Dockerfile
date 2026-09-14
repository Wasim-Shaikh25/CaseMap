# CaseMap backend image — server/app.py + ui/, with the full ML pipeline
# (opennyai en_legal_ner_sm, SaT boundary judge, GLiNER party judge, MiniLM
# embedder) baked in. Built for an always-on host with real RAM (a VPS) —
# see CHANGELOG.md entry 80 for why Render's free tier can't run this.
#
# Pin matches requirements.txt's own verified combination (see its header):
# spaCy 3.8.16 chain on Python 3.11. Do not bump the base image's Python
# minor version without re-reading that file first.
FROM python:3.11.9-slim-bookworm

# System deps:
#   tesseract-ocr   — OCR for scanned PDFs. The one thing Render's
#                      Python-only build environment could never give us.
#   libglib2.0-0    — opencv-python-headless still dlopens this on import
#                      even with no X11 (ImportError: libgthread-2.0.so.0
#                      without it).
#   build-essential — a few of the older opennyai-chain transitive deps
#                      (pulled in by en_legal_ner_sm's own pins) have no
#                      manylinux wheel for every combination and fall back
#                      to a source build. Kept in the final image for
#                      simplicity/reliability over shaving image size with
#                      a multi-stage build.
#   curl            — Coolify's default container healthcheck runs curl
#                      against health_check_path from inside the
#                      container; the base slim image has neither curl
#                      nor wget, which fails every deploy before this.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libglib2.0-0 \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first (own layer, cached across source-only changes).
#
# torch is pulled in transitively by sentence-transformers/gliner with no
# version pin of our own, so plain pip grabs the default CUDA build --
# torch itself plus every nvidia_cu*/cudnn/nccl wheel behind it, multiple
# GB of GPU libraries a VPS with no GPU will never touch. Installing the
# CPU-only wheel from PyTorch's own index FIRST means later installs see
# "torch" already satisfied and skip the CUDA variant entirely.
COPY requirements.txt requirements-webapp.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-webapp.txt

# en_legal_ner_sm can't go in requirements.txt at all (HuggingFace serves a
# wheel filename pip rejects outright) — see that file's own header and
# scripts/install_en_legal_ner_sm.py's docstring for the full story.
COPY scripts/install_en_legal_ner_sm.py scripts/install_en_legal_ner_sm.py
RUN python scripts/install_en_legal_ner_sm.py && \
    python -m spacy download en_core_web_sm && \
    rm -rf /app/temp

# Application source last (own layer — this is what actually changes most
# often; keeps the expensive dependency layers above cached on rebuild).
COPY VERSION ./
COPY src/ src/
COPY server/ server/
COPY ui/ ui/

ENV PORT=8756 \
    WARM_MODELS_ON_START=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/casemap/.cache/huggingface

EXPOSE 8756

# SaT (boundary judge) and GLiNER (party judge) are pulled from Hugging Face
# at first *runtime* load, not baked into the image at build time the way
# en_legal_ner_sm/en_core_web_sm are (spaCy models install as regular pip
# packages; these two don't). Without a volume at HF_HOME, every fresh
# container -- every redeploy, every crash-restart -- re-downloads both from
# scratch. docker-compose.yml mounts a named volume here; pre-creating the
# directory with the right ownership below is what lets Docker initialize
# that volume as writable by the non-root user instead of root.
RUN useradd -m -u 10001 casemap && \
    mkdir -p "$HF_HOME" && \
    chown -R casemap:casemap /app /home/casemap
USER casemap

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import os,sys,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT','8756') + '/api/health', timeout=5)" || exit 1

CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${PORT}"]
