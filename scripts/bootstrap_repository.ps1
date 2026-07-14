param(
    [string]$RepositoryRoot = "C:\Users\BillH\Desktop\NERD\Turning\omega-arc"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $RepositoryRoot | Out-Null

$Folders = @(
    "backend","frontend","training","console",
    "docs","docs\decisions","docs\letters-to-future-stewards","scripts"
)

foreach ($Folder in $Folders) {
    New-Item -ItemType Directory -Force -Path (Join-Path $RepositoryRoot $Folder) | Out-Null
}

Set-Location $RepositoryRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not available on PATH."
}

if (-not (Test-Path ".git")) {
    git init
}

Write-Host "Repository initialized at $RepositoryRoot"
