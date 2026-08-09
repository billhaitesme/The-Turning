# OMEGA-ARC installed-app launcher.
# Layout (install root = parent of this script's directory):
#   python\          embedded CPython with backend dependencies preinstalled
#   backend\         Core Runtime source + clean data fixtures
#   frontend\        built Command Deck (static)
#   bridge-zero\     built desktop Bridge Zero (static)
#   .env             created from .env.example on first run
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root 'python\python.exe'
$BackendRoot = Join-Path $Root 'backend'
$FrontendRoot = Join-Path $Root 'frontend'
$LogRoot = Join-Path $Root 'logs'
New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

Write-Host ''
Write-Host '  OMEGA-ARC — local runtime launcher' -ForegroundColor Cyan
Write-Host "  Install root: $Root"
Write-Host ''

# --- .env bootstrap -----------------------------------------------------------
$EnvFile = Join-Path $Root '.env'
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Root '.env.example') $EnvFile
    Write-Host '[setup] Created .env from defaults.'
}

# --- Ollama -------------------------------------------------------------------
function Find-Ollama {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'),
        'C:\Program Files\Ollama\ollama.exe'
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$Ollama = Find-Ollama
if (-not $Ollama) {
    Write-Host '[error] Ollama was not found. Install it from https://ollama.com/download and run this launcher again.' -ForegroundColor Red
    Read-Host 'Press Enter to exit'
    exit 1
}

function Test-Port([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

if (-not (Test-Port 11434)) {
    Write-Host '[start] Ollama model server...'
    Start-Process -FilePath $Ollama -ArgumentList @('serve') -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogRoot 'ollama.out.log') `
        -RedirectStandardError (Join-Path $LogRoot 'ollama.err.log')
}

# --- first-run model check ----------------------------------------------------
function Get-EnvValue([string]$Name, [string]$Fallback) {
    $line = Select-String -Path $EnvFile -Pattern "^$Name=" | Select-Object -First 1
    if ($line) { return ($line.Line -split '=', 2)[1].Trim() }
    return $Fallback
}

$ChatModel = Get-EnvValue 'ACTIVE_CHAT_MODEL' 'huihui_ai/gemma-4-abliterated:12b'
$EmbedModel = Get-EnvValue 'OLLAMA_EMBED_MODEL' 'embeddinggemma'

$deadline = (Get-Date).AddSeconds(60)
while (-not (Test-Port 11434)) {
    if ((Get-Date) -gt $deadline) { Write-Host '[error] Ollama did not start.' -ForegroundColor Red; exit 1 }
    Start-Sleep -Milliseconds 500
}

$installed = (& $Ollama list 2>$null) -join "`n"
$missing = @()
foreach ($m in @($ChatModel, $EmbedModel)) {
    $short = ($m -split ':')[0]
    if ($installed -notmatch [regex]::Escape($short)) { $missing += $m }
}
if ($missing.Count -gt 0) {
    Write-Host ''
    Write-Host '[first run] The following models are required and will be downloaded now:' -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "    $_" }
    Write-Host '  The chat model is ~8 GB and the embedder ~0.6 GB. This is a one-time download.'
    $answer = Read-Host 'Download now? [Y/n]'
    if ($answer -and $answer.ToLower().StartsWith('n')) {
        Write-Host 'Cannot run without the models. Exiting.'
        exit 1
    }
    foreach ($m in $missing) { & $Ollama pull $m }
}

# --- backend ------------------------------------------------------------------
if (-not (Test-Port 8001)) {
    Write-Host '[start] OMEGA-ARC Core Runtime (port 8001)...'
    $backendCmd = @(
        '-u', '-c',
        "import os, sys; os.chdir(r'$BackendRoot'); sys.path.insert(0, r'$BackendRoot'); " +
        "from dotenv import load_dotenv; load_dotenv(r'$EnvFile', override=True); " +
        "import uvicorn; uvicorn.run('app:app', host=os.environ.get('OMEGA_BIND_HOST', '127.0.0.1'), " +
        "port=int(os.environ.get('OMEGA_BACKEND_PORT', '8001')), loop='asyncio', http='h11', lifespan='on', log_level='info')"
    )
    Start-Process -FilePath $Python -ArgumentList $backendCmd -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogRoot 'backend.out.log') `
        -RedirectStandardError (Join-Path $LogRoot 'backend.err.log')
}

# --- frontend (Command Deck, static) -----------------------------------------
if (-not (Test-Port 5173)) {
    Write-Host '[start] Command Deck UI (port 5173)...'
    Start-Process -FilePath $Python -ArgumentList @('-u', '-m', 'http.server', '5173', '--bind', '127.0.0.1', '--directory', $FrontendRoot) -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogRoot 'frontend.out.log') `
        -RedirectStandardError (Join-Path $LogRoot 'frontend.err.log')
}

# --- readiness + browser ------------------------------------------------------
function Wait-Ready([string]$Name, [string]$Uri, [int]$TimeoutSec = 90) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 3
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { Write-Host "[ready] $Name"; return $true }
        } catch { Start-Sleep -Milliseconds 700 }
    }
    Write-Host "[warn] $Name did not answer at $Uri (logs: $LogRoot)" -ForegroundColor Yellow
    return $false
}

$null = Wait-Ready 'Ollama' 'http://127.0.0.1:11434/api/tags'
$null = Wait-Ready 'Core Runtime' 'http://127.0.0.1:8001/'
$null = Wait-Ready 'Command Deck' 'http://127.0.0.1:5173/'

Write-Host ''
Write-Host '  OMEGA-ARC is up.' -ForegroundColor Green
Write-Host '  UI:      http://127.0.0.1:5173/'
Write-Host '  Backend: http://127.0.0.1:8001/'
Write-Host "  Logs:    $LogRoot"
Start-Process 'http://127.0.0.1:5173/'
