Set-StrictMode -Version Latest

function Start-OmegaFrontend {
    param(
        [int]$Port = 5173,
        [int]$BackendPort = 8001
    )

    $paths = Get-OmegaPaths

    $owner = Get-OmegaProcessByPort -Port $Port
    $record = Get-OmegaProcessRecord -Name "frontend"
    if ($owner) {
        if ($record -and [int]$record.pid -eq [int]$owner.Pid) {
            Write-OmegaInfo "Frontend already running on port $Port (PID $($owner.Pid))."
            return $record
        }
        throw "Port $Port is in use by PID $($owner.Pid) ($($owner.ProcessName))."
    }

    $command = "Set-Location '$($paths.Frontend)'; `$env:VITE_API_URL='http://127.0.0.1:$BackendPort'; npm run dev -- --host localhost --port $Port"
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $command
    ) -PassThru

    Save-OmegaProcessRecord -Name "frontend" -Pid $proc.Id -Port $Port -Command $command | Out-Null
    Write-OmegaPass "Frontend started (PID $($proc.Id))"

    return (Get-OmegaProcessRecord -Name "frontend")
}

function Stop-OmegaFrontend {
    $record = Get-OmegaProcessRecord -Name "frontend"
    if (-not $record) {
        Write-OmegaWarning "No frontend PID record found."
        return
    }

    $pid = [int]$record.pid
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $pid -Force
        Write-OmegaPass "Stopped frontend process PID $pid"
    }
    else {
        Write-OmegaWarning "Frontend PID $pid is not running."
    }

    Remove-OmegaProcessRecord -Name "frontend"
}

function Get-OmegaFrontendStatus {
    param([int]$Port = 5173)

    $record = Get-OmegaProcessRecord -Name "frontend"
    $owner = Get-OmegaProcessByPort -Port $Port
    $online = Test-OmegaFrontendOnline -Port $Port

    [pscustomobject]@{
        Port = $Port
        Url = "http://localhost:$Port"
        Online = $online
        PortOwner = $owner
        Record = $record
    }
}

Export-ModuleMember -Function @(
    "Start-OmegaFrontend",
    "Stop-OmegaFrontend",
    "Get-OmegaFrontendStatus"
)
