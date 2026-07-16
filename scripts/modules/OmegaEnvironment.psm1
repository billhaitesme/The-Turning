Set-StrictMode -Version Latest

function Write-OmegaInfo {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-OmegaPass {
    param([string]$Message)
    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-OmegaWarning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-OmegaFail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Get-OmegaRepoRoot {
    param([string]$StartPath = $PSScriptRoot)

    $current = Resolve-Path $StartPath
    while ($null -ne $current) {
        $candidate = $current.Path
        if (Test-Path (Join-Path $candidate ".git")) {
            return $candidate
        }

        $parent = Split-Path -Parent $candidate
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $candidate) {
            break
        }
        $current = Resolve-Path $parent
    }

    throw "Could not locate repository root (.git)."
}

function Get-OmegaPaths {
    $repo = Get-OmegaRepoRoot
    return [pscustomobject]@{
        RepoRoot = $repo
        Scripts = Join-Path $repo "scripts"
        Backend = Join-Path $repo "backend"
        Frontend = Join-Path $repo "frontend"
        BackendVenv = Join-Path $repo "backend/.venv"
        BackendPython = Join-Path $repo "backend/.venv/Scripts/python.exe"
        BackendApp = Join-Path $repo "backend/app.py"
        BackendEnv = Join-Path $repo "backend/.env"
        FrontendPackage = Join-Path $repo "frontend/package.json"
        FrontendViteConfigJs = Join-Path $repo "frontend/vite.config.js"
        FrontendViteConfigTs = Join-Path $repo "frontend/vite.config.ts"
        StateDir = Join-Path $repo "scripts/.omega-state"
    }
}

function Ensure-OmegaStateDirectory {
    $paths = Get-OmegaPaths
    if (-not (Test-Path $paths.StateDir)) {
        New-Item -ItemType Directory -Path $paths.StateDir | Out-Null
    }
    return $paths.StateDir
}

function Get-OmegaPidFilePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $stateDir = Ensure-OmegaStateDirectory
    return Join-Path $stateDir ("{0}.pid.json" -f $Name)
}

function Save-OmegaProcessRecord {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [int]$Pid,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    $path = Get-OmegaPidFilePath -Name $Name
    $record = [pscustomobject]@{
        name = $Name
        pid = $Pid
        port = $Port
        command = $Command
        created_at = (Get-Date).ToString("o")
    }
    $record | ConvertTo-Json | Set-Content -Path $path -Encoding UTF8
    return $path
}

function Get-OmegaProcessRecord {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $path = Get-OmegaPidFilePath -Name $Name
    if (-not (Test-Path $path)) {
        return $null
    }

    try {
        return (Get-Content -Path $path -Raw | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

function Remove-OmegaProcessRecord {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $path = Get-OmegaPidFilePath -Name $Name
    if (Test-Path $path) {
        Remove-Item -Path $path -Force
    }
}

function Get-OmegaProcessByPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $connection) {
        return $null
    }

    $proc = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
    [pscustomobject]@{
        Port = $Port
        Pid = $connection.OwningProcess
        ProcessName = if ($proc) { $proc.ProcessName } else { "unknown" }
    }
}

function Test-OmegaCommandExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-OmegaToolVersions {
    $paths = Get-OmegaPaths

    $pythonVersion = "unknown"
    if (Test-Path $paths.BackendPython) {
        $pythonVersion = (& $paths.BackendPython --version 2>&1 | Out-String).Trim()
    }

    $nodeVersion = if (Test-OmegaCommandExists -Name "node") { (& node --version 2>&1 | Out-String).Trim() } else { "missing" }
    $npmVersion = if (Test-OmegaCommandExists -Name "npm") { (& npm --version 2>&1 | Out-String).Trim() } else { "missing" }

    $uvicornVersion = "missing"
    if (Test-Path $paths.BackendPython) {
        $uvicornProbe = & $paths.BackendPython -m uvicorn --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $uvicornVersion = ($uvicornProbe | Out-String).Trim()
        }
    }

    [pscustomobject]@{
        Python = $pythonVersion
        Node = $nodeVersion
        Npm = $npmVersion
        Uvicorn = $uvicornVersion
    }
}

function Test-OmegaBackendOnline {
    param([int]$Port = 8001)

    $urls = @(
        "http://127.0.0.1:$Port/system/status",
        "http://127.0.0.1:$Port/health"
    )

    foreach ($url in $urls) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
        }
    }

    return $false
}

function Test-OmegaFrontendOnline {
    param([int]$Port = 5173)

    try {
        $response = Invoke-WebRequest -Uri ("http://localhost:{0}" -f $Port) -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

Export-ModuleMember -Function @(
    "Write-OmegaInfo",
    "Write-OmegaPass",
    "Write-OmegaWarning",
    "Write-OmegaFail",
    "Get-OmegaRepoRoot",
    "Get-OmegaPaths",
    "Ensure-OmegaStateDirectory",
    "Get-OmegaPidFilePath",
    "Save-OmegaProcessRecord",
    "Get-OmegaProcessRecord",
    "Remove-OmegaProcessRecord",
    "Get-OmegaProcessByPort",
    "Test-OmegaCommandExists",
    "Get-OmegaToolVersions",
    "Test-OmegaBackendOnline",
    "Test-OmegaFrontendOnline"
)
