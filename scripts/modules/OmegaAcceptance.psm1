Set-StrictMode -Version Latest

function Get-OmegaAcceptanceFiles {
    $paths = Get-OmegaPaths
    $acceptanceDir = Join-Path $paths.RepoRoot "docs/acceptance"

    if (-not (Test-Path $acceptanceDir)) {
        return @()
    }

    Get-ChildItem -Path $acceptanceDir -Filter "*.md" |
        Where-Object { $_.Name -match "^\d{3}_" } |
        Sort-Object Name
}

function Get-OmegaAcceptanceCount {
    return (Get-OmegaAcceptanceFiles).Count
}

function Invoke-OmegaAcceptance {
    param([string]$Scenario)

    $files = Get-OmegaAcceptanceFiles
    if (-not $Scenario) {
        Write-OmegaInfo "Acceptance Scenarios:"
        foreach ($file in $files) {
            if ($file.BaseName -match "^(\d{3})_(.+)$") {
                $id = $Matches[1]
                $title = ($Matches[2] -replace "_", " ")
                $title = (Get-Culture).TextInfo.ToTitleCase($title)
                Write-Host ("- {0} {1}" -f $id, $title)
            }
            else {
                Write-Host ("- {0}" -f $file.BaseName)
            }
        }
        return
    }

    $id = $Scenario.PadLeft(3, '0')
    $target = $files | Where-Object { $_.BaseName -like "${id}_*" } | Select-Object -First 1

    if ($null -eq $target) {
        Write-OmegaFail "Scenario $id not found in docs/acceptance."
        exit 1
    }

    Write-OmegaInfo "Opening $($target.FullName)"
    Start-Process $target.FullName
}

Export-ModuleMember -Function @(
    "Get-OmegaAcceptanceFiles",
    "Get-OmegaAcceptanceCount",
    "Invoke-OmegaAcceptance"
)
