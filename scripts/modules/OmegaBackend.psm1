Set-StrictMode -Version Latest

function Start-OmegaBackend {
    param([int]$Port = 8001)

    $paths = Get-OmegaPaths

    if (-not (Test-Path $paths.BackendPython)) {
        throw "Python environment not found: $($paths.BackendPython)"
    }

    $owner = Get-OmegaProcessByPort -Port $Port
    $record = Get-OmegaProcessRecord -Name "backend"
    if ($owner) {
        if ($record -and [int]$record.pid -eq [int]$owner.Pid) {
            Write-OmegaInfo "Backend already running on port $Port (PID $($owner.Pid))."
            return $record
        }
        throw "Port $Port is in use by PID $($owner.Pid) ($($owner.ProcessName))."
    }

    $command = "Set-Location '$($paths.Backend)'; `$env:PYTHONPATH='$($paths.Backend)'; & '$($paths.BackendPython)' -m uvicorn app:app --reload --host 127.0.0.1 --port $Port"
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $command
    ) -PassThru

    Save-OmegaProcessRecord -Name "backend" -Pid $proc.Id -Port $Port -Command $command | Out-Null
    Write-OmegaPass "Backend started (PID $($proc.Id))"

    return (Get-OmegaProcessRecord -Name "backend")
}

function Wait-OmegaBackendReady {
    param(
        [int]$Port = 8001,
        [int]$TimeoutSeconds = 40
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-OmegaBackendOnline -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 750
    }

    return $false
}

function Stop-OmegaBackend {
    $record = Get-OmegaProcessRecord -Name "backend"
    if (-not $record) {
        Write-OmegaWarning "No backend PID record found."
        return
    }

    $pid = [int]$record.pid
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $pid -Force
        Write-OmegaPass "Stopped backend process PID $pid"
    }
    else {
        Write-OmegaWarning "Backend PID $pid is not running."
    }

    Remove-OmegaProcessRecord -Name "backend"
}

function Get-OmegaBackendStatus {
    param([int]$Port = 8001)

    $record = Get-OmegaProcessRecord -Name "backend"
    $owner = Get-OmegaProcessByPort -Port $Port
    $online = Test-OmegaBackendOnline -Port $Port

    [pscustomobject]@{
        Port = $Port
        Url = "http://127.0.0.1:$Port"
        Online = $online
        PortOwner = $owner
        Record = $record
    }
}

Export-ModuleMember -Function @(
    "Start-OmegaBackend",
    "Wait-OmegaBackendReady",
    "Stop-OmegaBackend",
    "Get-OmegaBackendStatus"
)
