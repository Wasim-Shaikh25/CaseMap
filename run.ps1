<#
  run.ps1 - one-command setup + launch for CaseMap.

  What this does, in order:
    1. Creates .venv (Python 3.11) if it doesn't exist yet.
    2. Installs the core pipeline deps (requirements.txt) + the web app deps
       (requirements-webapp.txt) into it.
    3. Installs the MANDATORY OpenNyAI legal-NER model (en_legal_ner_sm) if
       it isn't already present - this can't go in requirements.txt (see
       that file's own header) so it needs its own install step.
    4. Downloads spaCy's en_core_web_sm if it isn't already present.
    5. Checks (does not install) for the system Tesseract OCR binary -
       only needed for genuinely SCANNED pdfs; everything else (digital
       PDFs, .docx, .txt) works without it.
    6. Starts the FastAPI backend (server/app.py) on port 8756.

  There is only ONE process to run: server/app.py mounts ui/ as static
  files, so the same server IS the frontend - there is no separate
  frontend dev server to start.

  Note: this script deliberately does NOT set $ErrorActionPreference =
  "Stop". Several tools this script shells out to (spaCy, pip, uvicorn)
  write harmless warnings to stderr; under "Stop" that stderr output is
  treated as a terminating error by PowerShell and would abort the whole
  script on a step that actually succeeded. Instead, exit codes
  ($LASTEXITCODE) are checked explicitly after the steps that matter.

  Usage (from a PowerShell prompt, in the project root):
      .\run.ps1
      .\run.ps1 -Port 9000        # run on a different port
      .\run.ps1 -NoBrowser        # don't auto-open the browser
#>

param(
    [switch]$NoBrowser,
    [int]$Port = 8756
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Venv = Join-Path $Root ".venv"
$Py = Join-Path $Venv "Scripts\python.exe"

function Test-PyImport($code) {
    & $Py -c "import $code" *> $null
    return ($LASTEXITCODE -eq 0)
}

function Invoke-Checked($what) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] $what failed (exit $LASTEXITCODE)." -ForegroundColor Red
        exit 1
    }
}

# --- 1. venv -----------------------------------------------------------
if (-not (Test-Path $Py)) {
    Write-Host "[+] No .venv found - creating one with Python 3.11 ..." -ForegroundColor Cyan
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & py -3.11 -m venv $Venv
    }
    if (-not (Test-Path $Py)) {
        Write-Host "[!] 'py -3.11' unavailable or failed - falling back to 'python' on PATH." -ForegroundColor Yellow
        & python -m venv $Venv
    }
    if (-not (Test-Path $Py)) {
        Write-Host "[!] Could not create a virtual environment. Install Python 3.11 first: https://www.python.org/downloads/" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[ok] .venv already exists." -ForegroundColor Green
}

# --- 2. core + webapp deps ----------------------------------------------
Write-Host "[+] Installing core + web app dependencies (first run can take several minutes) ..." -ForegroundColor Cyan
& $Py -m pip install --upgrade pip -q
& $Py -m pip install -r (Join-Path $Root "requirements.txt") -q
Invoke-Checked "pip install -r requirements.txt"
& $Py -m pip install -r (Join-Path $Root "requirements-webapp.txt") -q
Invoke-Checked "pip install -r requirements-webapp.txt"

# --- 3. mandatory NER model ----------------------------------------------
Write-Host "[+] Checking mandatory OpenNyAI NER model (en_legal_ner_sm) ..." -ForegroundColor Cyan
if (Test-PyImport "spacy; spacy.load('en_legal_ner_sm')") {
    Write-Host "[ok] en_legal_ner_sm already installed." -ForegroundColor Green
} else {
    Write-Host "[+] Not found - installing (see scripts/install_en_legal_ner_sm.py) ..." -ForegroundColor Cyan
    & $Py (Join-Path $Root "scripts\install_en_legal_ner_sm.py")
    Invoke-Checked "en_legal_ner_sm install"
}

# --- 4. en_core_web_sm ---------------------------------------------------
Write-Host "[+] Checking spaCy's en_core_web_sm (entity-extraction fallback) ..." -ForegroundColor Cyan
if (Test-PyImport "spacy; spacy.load('en_core_web_sm')") {
    Write-Host "[ok] en_core_web_sm already installed." -ForegroundColor Green
} else {
    & $Py -m spacy download en_core_web_sm
    Invoke-Checked "spacy download en_core_web_sm"
}

# --- 5. tesseract check (warn only - never auto-installed) --------------
$tesseract = Get-Command tesseract.exe -ErrorAction SilentlyContinue
if ($tesseract) {
    Write-Host "[ok] Tesseract OCR found: $($tesseract.Source)" -ForegroundColor Green
} else {
    Write-Host "[!] Tesseract OCR not found on PATH." -ForegroundColor Yellow
    Write-Host "    Digital PDFs, .docx, and .txt work fully without it." -ForegroundColor Yellow
    Write-Host "    Only genuinely SCANNED pdfs need OCR. If you'll process those, install:" -ForegroundColor Yellow
    Write-Host "    https://github.com/UB-Mannheim/tesseract/wiki  (then re-run this script)" -ForegroundColor Yellow
}

# --- 6. run ---------------------------------------------------------------
Write-Host ""
Write-Host "[+] Starting CaseMap at http://127.0.0.1:$Port (Ctrl+C to stop)." -ForegroundColor Cyan
Write-Host "    server/app.py serves the ui/ frontend too - this is the only process you need." -ForegroundColor Cyan
Write-Host ""

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$Port"
}

& $Py -m uvicorn server.app:app --port $Port
