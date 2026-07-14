param(
    [string]$SourceRoot = "C:\Users\BillH\Desktop\NERD\Turning",
    [string]$RepositoryRoot = "C:\Users\BillH\Desktop\NERD\Turning\omega-arc"
)

$ErrorActionPreference = "Stop"

$Mappings = @(
    @{ Source = "omega_arc_ollama\backend"; Destination = "backend" },
    @{ Source = "omega_arc_ollama\frontend"; Destination = "frontend" },
    @{ Source = "training"; Destination = "training" },
    @{ Source = "omega_arc_command_console_v3_1"; Destination = "console" }
)

foreach ($Mapping in $Mappings) {
    $Source = Join-Path $SourceRoot $Mapping.Source
    $Destination = Join-Path $RepositoryRoot $Mapping.Destination

    if (-not (Test-Path $Source)) {
        Write-Warning "Missing source: $Source"
        continue
    }

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null

    & robocopy $Source $Destination /E /R:1 /W:1 `
        /XD .venv node_modules __pycache__ .cache models checkpoints `
        /XF .env *.db *.sqlite *.sqlite3 *.gguf *.safetensors *.bin *.pt *.pth

    if ($LASTEXITCODE -ge 8) {
        throw "Copy failed for $Source with Robocopy exit code $LASTEXITCODE"
    }
}

Write-Host "Source copy complete. Review with: git status"
