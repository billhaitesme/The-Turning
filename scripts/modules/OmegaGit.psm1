Set-StrictMode -Version Latest

function Get-OmegaGitInfo {
    $paths = Get-OmegaPaths
    $repo = $paths.RepoRoot

    $branch = (git -C $repo rev-parse --abbrev-ref HEAD 2>$null | Out-String).Trim()
    if (-not $branch) { $branch = "unknown" }

    $commit = (git -C $repo rev-parse --short HEAD 2>$null | Out-String).Trim()
    if (-not $commit) { $commit = "unknown" }

    $latestTag = (git -C $repo describe --tags --abbrev=0 2>$null | Out-String).Trim()
    if (-not $latestTag) { $latestTag = "none" }

    $statusShort = (git -C $repo status --porcelain 2>$null | Out-String).Trim()
    $dirty = -not [string]::IsNullOrWhiteSpace($statusShort)

    $ahead = 0
    $behind = 0
    $upstream = ""
    try {
        $upstream = (& git -C $repo rev-parse --abbrev-ref --symbolic-full-name "@{upstream}" 2>$null | Out-String).Trim()
    }
    catch {
        $upstream = ""
    }

    if ($upstream) {
        $aheadBehind = (& git -C $repo rev-list --left-right --count "$upstream...HEAD" 2>$null | Out-String).Trim()
        if ($aheadBehind -match "^(\d+)\s+(\d+)$") {
            $behind = [int]$Matches[1]
            $ahead = [int]$Matches[2]
        }
    }

    [pscustomobject]@{
        Branch = $branch
        Commit = $commit
        LatestTag = $latestTag
        IsDirty = $dirty
        Status = if ($dirty) { "Dirty" } else { "Clean" }
        Ahead = $ahead
        Behind = $behind
        StatusShort = $statusShort
    }
}

function Show-OmegaGitStatus {
    $info = Get-OmegaGitInfo

    Write-OmegaInfo "Current Branch: $($info.Branch)"
    Write-OmegaInfo "Current Commit: $($info.Commit)"
    Write-OmegaInfo "Latest Tag: $($info.LatestTag)"
    Write-OmegaInfo "Git Status: $($info.Status)"
    Write-OmegaInfo "Ahead/Behind: +$($info.Ahead) / -$($info.Behind)"

    if ($info.StatusShort) {
        Write-Host ""
        Write-Host $info.StatusShort
    }
}

Export-ModuleMember -Function @(
    "Get-OmegaGitInfo",
    "Show-OmegaGitStatus"
)
