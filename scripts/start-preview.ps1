$ErrorActionPreference = 'Stop'

# The Codex command host can expose both `Path` and `PATH` in its environment
# block. Windows treats those names as equivalent, while Start-Process rejects
# the duplicate keys. Normalize them before creating detached child processes.
$savedPath = $env:Path
Remove-Item Env:PATH -ErrorAction SilentlyContinue
$env:Path = $savedPath

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend\dist'
$logRoot = Join-Path $projectRoot '.runtime-logs'
$pythonExe = Join-Path $backendRoot '.venv\Scripts\python.exe'
$ollamaExe = 'C:\Users\BillH\AppData\Local\Programs\Ollama\ollama.exe'
$ollamaAppExe = 'C:\Users\BillH\AppData\Local\Programs\Ollama\ollama app.exe'
$backendLauncher = Join-Path $PSScriptRoot 'launch_backend.py'

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

function Get-ListenerProcess([int]$Port) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        return Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    }
    return $null
}

function Wait-ForEndpoint([string]$Service, [string]$Uri, [int]$TimeoutSeconds = 60) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-Host "[ready] $Service - $Uri"
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    } while ([DateTime]::UtcNow -lt $deadline)

    throw "$Service did not become ready at $Uri within $TimeoutSeconds seconds. Logs: $logRoot"
}

$started = @()

if (-not (Get-ListenerProcess 11434)) {
    # A stale Ollama tray/server process can remain alive while its API port is
    # closed. Stop only the known Ollama executables before starting a fresh
    # server; never disturb a healthy listener.
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -in @($ollamaExe, $ollamaAppExe) } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 750

    $process = Start-Process -FilePath $ollamaExe -ArgumentList @('serve') -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logRoot 'ollama.stdout.log') `
        -RedirectStandardError (Join-Path $logRoot 'ollama.stderr.log')
    $started += [PSCustomObject]@{ Service = 'ollama'; PID = $process.Id }
}

if (-not (Get-ListenerProcess 8001)) {
    $process = Start-Process -FilePath $pythonExe -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru `
        -ArgumentList @('-u', $backendLauncher) `
        -RedirectStandardOutput (Join-Path $logRoot 'backend.stdout.log') `
        -RedirectStandardError (Join-Path $logRoot 'backend.stderr.log')
    $started += [PSCustomObject]@{ Service = 'backend'; PID = $process.Id }
}

if (-not (Get-ListenerProcess 5173)) {
    $process = Start-Process -FilePath $pythonExe -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru `
        -ArgumentList @('-u', '-m', 'http.server', '5173', '--bind', '127.0.0.1') `
        -RedirectStandardOutput (Join-Path $logRoot 'frontend.stdout.log') `
        -RedirectStandardError (Join-Path $logRoot 'frontend.stderr.log')
    $started += [PSCustomObject]@{ Service = 'frontend'; PID = $process.Id }
}

$started | Format-Table -AutoSize

Wait-ForEndpoint 'Ollama' 'http://127.0.0.1:11434/api/tags'
Wait-ForEndpoint 'OMEGA-ARC backend' 'http://127.0.0.1:8001/'
Wait-ForEndpoint 'OMEGA-ARC UI' 'http://127.0.0.1:5173/'

Write-Host "Runtime logs: $logRoot"
