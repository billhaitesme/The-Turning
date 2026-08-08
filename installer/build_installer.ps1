# Builds OMEGA-ARC-Setup-<version>.exe.
# Assembles installer\build\staging (embedded Python + deps, backend, built UIs, launcher),
# then compiles installer\OMEGA-ARC.iss with Inno Setup. ASCII-only for PS 5.1.
param(
    [string]$PythonVersion = "3.12.8"
)
$ErrorActionPreference = 'Stop'

$InstallerDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $InstallerDir
$BuildDir = Join-Path $InstallerDir 'build'
$Staging = Join-Path $BuildDir 'staging'

Write-Host "== OMEGA-ARC installer build =="
Write-Host "repo: $RepoRoot"

# --- clean staging ------------------------------------------------------------
if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

# --- 1) embedded Python + dependencies ---------------------------------------
$PyDir = Join-Path $Staging 'python'
$PyZip = Join-Path $BuildDir "python-$PythonVersion-embed-amd64.zip"
if (-not (Test-Path $PyZip)) {
    Write-Host "[python] downloading embeddable $PythonVersion..."
    Invoke-WebRequest "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip" -OutFile $PyZip
}
Expand-Archive -Path $PyZip -DestinationPath $PyDir -Force

# enable site-packages in the embeddable distribution
$PthFile = Get-ChildItem $PyDir -Filter 'python3*._pth' | Select-Object -First 1
(Get-Content $PthFile.FullName) -replace '^#\s*import site$', 'import site' | Set-Content $PthFile.FullName -Encoding ascii

# bootstrap pip and install backend requirements into the embedded runtime
$GetPip = Join-Path $BuildDir 'get-pip.py'
if (-not (Test-Path $GetPip)) {
    Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile $GetPip
}
$PyExe = Join-Path $PyDir 'python.exe'
& $PyExe $GetPip --no-warn-script-location | Select-Object -Last 1
& $PyExe -m pip install --no-warn-script-location -r (Join-Path $RepoRoot 'backend\requirements.txt') | Select-Object -Last 1

# --- 2) backend: tracked sources + clean data fixtures (no venv/tests/benchmarks)
Push-Location $RepoRoot
$tracked = git ls-files backend | Where-Object {
    $_ -notmatch '^backend/tests/' -and $_ -notmatch '^backend/benchmarks/' -and $_ -notmatch '^backend/docs/'
}
foreach ($f in $tracked) {
    $dst = Join-Path $Staging $f
    New-Item -ItemType Directory -Path (Split-Path $dst) -Force | Out-Null
    Copy-Item (Join-Path $RepoRoot $f) $dst
}
Pop-Location
$BackendDst = Join-Path $Staging 'backend'

# --- 3) built UIs -------------------------------------------------------------
foreach ($pair in @(
    @{ src = 'frontend\dist';           dst = 'frontend' },
    @{ src = 'bridge\bridge-zero\dist'; dst = 'bridge-zero' }
)) {
    $src = Join-Path $RepoRoot $pair.src
    if (-not (Test-Path (Join-Path $src 'index.html'))) { throw ("Missing built UI: " + $pair.src + " - run the Vite builds first.") }
    Copy-Item -Recurse $src (Join-Path $Staging $pair.dst)
}

# --- 4) launcher, env defaults, licenses -------------------------------------
Copy-Item -Recurse (Join-Path $InstallerDir 'app') (Join-Path $Staging 'app')
Copy-Item (Join-Path $RepoRoot '.env.example') (Join-Path $Staging '.env.example')
foreach ($lic in 'LICENSE', 'LICENSE-MIT', 'LICENSE-APACHE') {
    Copy-Item (Join-Path $RepoRoot $lic) (Join-Path $Staging $lic)
}

# --- 5) smoke-test the embedded runtime against the staged backend -----------
Write-Host '[smoke] importing staged backend with embedded python...'
$SmokePy = Join-Path $BuildDir 'smoke.py'
@(
    'import sys, os, tempfile'
    "backend = sys.argv[1]"
    'os.chdir(backend)'
    'sys.path.insert(0, backend)'
    "os.environ.setdefault('TURNING_DB_PATH', os.path.join(tempfile.gettempdir(), 'omega-smoke.db'))"
    'import app'
    "print('backend import OK:', app.app.title)"
) | Set-Content $SmokePy -Encoding ascii
& $PyExe $SmokePy $BackendDst
if ($LASTEXITCODE -ne 0) { throw 'Embedded runtime failed to import the staged backend.' }

# --- 6) compile the installer -------------------------------------------------
$Iscc = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { throw 'Inno Setup 6 (ISCC.exe) not found.' }

& $Iscc (Join-Path $InstallerDir 'OMEGA-ARC.iss') | Select-Object -Last 3
if ($LASTEXITCODE -ne 0) { throw 'ISCC compile failed.' }
$Setup = Get-ChildItem (Join-Path $InstallerDir 'Output') -Filter 'OMEGA-ARC-Setup-*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host ''
Write-Host ("== built: " + $Setup.FullName + "  (" + [math]::Round($Setup.Length/1MB,1) + " MB) ==") -ForegroundColor Green
