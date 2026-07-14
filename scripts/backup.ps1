param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$BackupRoot = "C:\Users\BillH\Desktop\NERD\Turning\backups"
)

$ErrorActionPreference = "Stop"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Destination = Join-Path $BackupRoot "omega-arc_$Timestamp"
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null

& robocopy $RepositoryRoot $Destination /E /R:1 /W:1 `
    /XD .git .venv node_modules .cache models checkpoints backups `
    /XF .env *.gguf *.safetensors *.bin *.pt *.pth *.sqlite *.sqlite3 *.db

if ($LASTEXITCODE -ge 8) {
    throw "Backup failed with Robocopy exit code $LASTEXITCODE"
}

Write-Host "Backup complete: $Destination"
