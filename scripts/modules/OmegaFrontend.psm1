Set-StrictMode -Version Latest

function Start-OmegaBridge {
    param(
        [int]$Port = 5173,
        [int]$BackendPort = 8001
    )

    $paths = Get-OmegaPaths

    $owner = Get-OmegaProcessByPort -Port $Port
    $record = Get-OmegaProcessRecord -Name "bridge"
    if ($owner) {
        if ($record -and [int]$record.pid -eq [int]$owner.Pid) {
            Write-OmegaInfo "Bridge Zero already running on port $Port (PID $($owner.Pid))."
            return $record
        }
        throw "Port $Port is in use by PID $($owner.Pid) ($($owner.ProcessName))."
    }

    if (-not (Test-Path $paths.BridgePackage)) {
        throw "Bridge Zero package not found at $($paths.BridgePackage)."
    }

    $command = "Set-Location '$($paths.BridgeZero)'; `$env:VITE_API_BASE='http://127.0.0.1:$BackendPort'; npm run dev -- --host 127.0.0.1 --port $Port"
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $command
    ) -PassThru

    Save-OmegaProcessRecord -Name "bridge" -Pid $proc.Id -Port $Port -Command $command | Out-Null
    Write-OmegaPass "Bridge Zero started (PID $($proc.Id))"

    return (Get-OmegaProcessRecord -Name "bridge")
}

function Stop-OmegaBridge {
    $record = Get-OmegaProcessRecord -Name "bridge"
    if (-not $record) {
        Write-OmegaWarning "No bridge PID record found."
        return
    }

    $pid = [int]$record.pid
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $pid -Force
        Write-OmegaPass "Stopped bridge process PID $pid"
    }
    else {
        Write-OmegaWarning "Bridge PID $pid is not running."
    }

    Remove-OmegaProcessRecord -Name "bridge"
}

function Get-OmegaBridgeStatus {
    param([int]$Port = 5173)

    $record = Get-OmegaProcessRecord -Name "bridge"
    $owner = Get-OmegaProcessByPort -Port $Port
    $online = Test-OmegaFrontendOnline -Port $Port

    [pscustomobject]@{
        Port = $Port
        Url = "http://127.0.0.1:$Port"
        Online = $online
        PortOwner = $owner
        Record = $record
    }
}

function Start-OmegaFrontend {
    param(
        [int]$Port = 5173,
        [int]$BackendPort = 8001
    )

    Start-OmegaBridge -Port $Port -BackendPort $BackendPort
}

function Stop-OmegaFrontend {
    Stop-OmegaBridge
}

function Get-OmegaFrontendStatus {
    param([int]$Port = 5173)

    Get-OmegaBridgeStatus -Port $Port
}

Export-ModuleMember -Function @(
    "Start-OmegaBridge",
    "Stop-OmegaBridge",
    "Get-OmegaBridgeStatus",
    "Start-OmegaFrontend",
    "Stop-OmegaFrontend",
    "Get-OmegaFrontendStatus"
)
