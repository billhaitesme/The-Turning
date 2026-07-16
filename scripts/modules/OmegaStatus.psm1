Set-StrictMode -Version Latest

function Test-OmegaRequiredStructure {
    $paths = Get-OmegaPaths
    $checks = @(
        @{ Name = "backend/"; Path = $paths.Backend; Required = $true },
        @{ Name = "frontend/"; Path = $paths.Frontend; Required = $true },
        @{ Name = "scripts/"; Path = $paths.Scripts; Required = $true },
        @{ Name = "backend/.venv"; Path = $paths.BackendVenv; Required = $true },
        @{ Name = "backend/app.py"; Path = $paths.BackendApp; Required = $true },
        @{ Name = "frontend/package.json"; Path = $paths.FrontendPackage; Required = $true }
    )

    foreach ($check in $checks) {
        if (Test-Path $check.Path) {
            Write-OmegaPass "$($check.Name) found"
        }
        elseif ($check.Required) {
            Write-OmegaFail "$($check.Name) missing"
            return $false
        }
    }

    return $true
}

function Test-OmegaToolchain {
    $paths = Get-OmegaPaths
    $ok = $true

    if (Test-Path $paths.BackendPython) {
        Write-OmegaPass "Python venv executable found"
    }
    else {
        Write-OmegaFail "Python venv executable missing at $($paths.BackendPython)"
        $ok = $false
    }

    if (Test-OmegaCommandExists -Name "node") {
        Write-OmegaPass "Node available"
    }
    else {
        Write-OmegaFail "Node is not installed or unavailable in PATH"
        $ok = $false
    }

    if (Test-OmegaCommandExists -Name "npm") {
        Write-OmegaPass "npm available"
    }
    else {
        Write-OmegaFail "npm is not installed or unavailable in PATH"
        $ok = $false
    }

    if (Test-Path $paths.BackendPython) {
        & $paths.BackendPython -m uvicorn --version 1>$null 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-OmegaPass "uvicorn available in backend venv"
        }
        else {
            Write-OmegaFail "uvicorn missing in backend venv"
            $ok = $false
        }
    }

    return $ok
}

function Test-OmegaPortConflicts {
    param(
        [int]$BackendPort = 8001,
        [int]$FrontendPort = 5173
    )

    $ok = $true
    foreach ($port in @($BackendPort, $FrontendPort)) {
        $owner = Get-OmegaProcessByPort -Port $port
        if ($owner) {
            Write-OmegaWarning "Port $port is occupied by PID $($owner.Pid) ($($owner.ProcessName))."
            $ok = $false
        }
        else {
            Write-OmegaPass "Port $port is available"
        }
    }

    return $ok
}

function Invoke-OmegaLaunch {
    $paths = Get-OmegaPaths

    Write-Host ""
    Write-OmegaInfo "OMEGA-ARC developer launch starting..."

    if (-not (Test-OmegaRequiredStructure)) {
        throw "Required repository structure is incomplete."
    }

    if (-not (Test-OmegaToolchain)) {
        throw "Toolchain checks failed."
    }

    $backendStatus = Get-OmegaBackendStatus -Port 8001
    if ($backendStatus.PortOwner -and (-not ($backendStatus.Record -and [int]$backendStatus.Record.pid -eq [int]$backendStatus.PortOwner.Pid))) {
        throw "Port 8001 is occupied by PID $($backendStatus.PortOwner.Pid) ($($backendStatus.PortOwner.ProcessName))."
    }

    $frontendStatus = Get-OmegaFrontendStatus -Port 5173
    if ($frontendStatus.PortOwner -and (-not ($frontendStatus.Record -and [int]$frontendStatus.Record.pid -eq [int]$frontendStatus.PortOwner.Pid))) {
        throw "Port 5173 is occupied by PID $($frontendStatus.PortOwner.Pid) ($($frontendStatus.PortOwner.ProcessName))."
    }

    Start-OmegaBackend -Port 8001 | Out-Null
    if (Wait-OmegaBackendReady -Port 8001 -TimeoutSeconds 45) {
        Write-OmegaPass "Backend health endpoint responded"
    }
    else {
        Write-OmegaWarning "Backend did not respond within timeout window"
    }

    Start-OmegaFrontend -Port 5173 -BackendPort 8001 | Out-Null

    Start-Process "http://localhost:5173"

    $git = Get-OmegaGitInfo
    $backend = Get-OmegaBackendStatus -Port 8001
    $frontend = Get-OmegaFrontendStatus -Port 5173
    $testCount = Get-OmegaBackendTestCount
    $acceptanceCount = Get-OmegaAcceptanceCount

    Write-Host ""
    Write-Host "-------------------------------------"
    Write-Host "OMEGA-ARC"
    Write-Host ""
    Write-Host "Branch:"
    Write-Host $git.Branch
    Write-Host ""
    Write-Host "Commit:"
    Write-Host $git.Commit
    Write-Host ""
    Write-Host "Latest Tag:"
    Write-Host $git.LatestTag
    Write-Host ""
    Write-Host "Backend:"
    if ($backend.Online) { Write-Host "ONLINE" -ForegroundColor Green } else { Write-Host "OFFLINE" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Frontend:"
    if ($frontend.Online) { Write-Host "ONLINE" -ForegroundColor Green } else { Write-Host "OFFLINE" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Backend URL:"
    Write-Host $backend.Url
    Write-Host ""
    Write-Host "Frontend URL:"
    Write-Host $frontend.Url
    Write-Host ""
    Write-Host "Backend Tests:"
    Write-Host "$testCount Passing"
    Write-Host ""
    Write-Host "Acceptance Scenarios:"
    Write-Host $acceptanceCount
    Write-Host "-------------------------------------"
}

function Stop-OmegaStack {
    Write-OmegaInfo "Stopping OMEGA-ARC processes tracked by PID files..."
    Stop-OmegaFrontend
    Stop-OmegaBackend
}

function Restart-OmegaStack {
    Stop-OmegaStack
    Invoke-OmegaLaunch
}

function Show-OmegaStatus {
    $paths = Get-OmegaPaths
    $git = Get-OmegaGitInfo
    $tools = Get-OmegaToolVersions
    $backend = Get-OmegaBackendStatus -Port 8001
    $frontend = Get-OmegaFrontendStatus -Port 5173
    $testCount = Get-OmegaBackendTestCount
    $acceptanceCount = Get-OmegaAcceptanceCount

    Write-Host ""
    Write-Host "OMEGA-ARC Status"
    Write-Host "-------------------------------------"
    Write-Host "Repository: $($paths.RepoRoot)"
    Write-Host "Branch: $($git.Branch)"
    Write-Host "Commit: $($git.Commit)"
    Write-Host "Dirty/Clean: $($git.Status)"
    Write-Host "Latest Tag: $($git.LatestTag)"
    Write-Host "Backend Online: $($backend.Online)"
    Write-Host "Frontend Online: $($frontend.Online)"
    Write-Host "Backend URL: $($backend.Url)"
    Write-Host "Frontend URL: $($frontend.Url)"
    Write-Host "Python Version: $($tools.Python)"
    Write-Host "Node Version: $($tools.Node)"
    Write-Host "Uvicorn Version: $($tools.Uvicorn)"
    Write-Host "Venv Location: $($paths.BackendVenv)"
    Write-Host "Test Count: $testCount"
    Write-Host "Acceptance Count: $acceptanceCount"
    Write-Host "-------------------------------------"
}

function Invoke-OmegaDoctor {
    $paths = Get-OmegaPaths
    $checks = @()

    $checks += [pscustomobject]@{ Name = "Python"; Status = if (Test-Path $paths.BackendPython) { "PASS" } else { "FAIL" }; Detail = $paths.BackendPython }
    $checks += [pscustomobject]@{ Name = "Node"; Status = if (Test-OmegaCommandExists -Name "node") { "PASS" } else { "FAIL" }; Detail = "node in PATH" }
    $checks += [pscustomobject]@{ Name = "npm"; Status = if (Test-OmegaCommandExists -Name "npm") { "PASS" } else { "FAIL" }; Detail = "npm in PATH" }

    $uvicornStatus = "FAIL"
    if (Test-Path $paths.BackendPython) {
        & $paths.BackendPython -m uvicorn --version 1>$null 2>$null
        if ($LASTEXITCODE -eq 0) {
            $uvicornStatus = "PASS"
        }
    }
    $checks += [pscustomobject]@{ Name = "uvicorn"; Status = $uvicornStatus; Detail = "backend venv" }

    $checks += [pscustomobject]@{ Name = "backend/.venv"; Status = if (Test-Path $paths.BackendVenv) { "PASS" } else { "FAIL" }; Detail = $paths.BackendVenv }
    $checks += [pscustomobject]@{ Name = "frontend/node_modules"; Status = if (Test-Path (Join-Path $paths.Frontend "node_modules")) { "PASS" } else { "WARNING" }; Detail = "Install with npm install if missing" }
    $checks += [pscustomobject]@{ Name = "backend/app.py"; Status = if (Test-Path $paths.BackendApp) { "PASS" } else { "FAIL" }; Detail = $paths.BackendApp }
    $checks += [pscustomobject]@{ Name = "frontend/package.json"; Status = if (Test-Path $paths.FrontendPackage) { "PASS" } else { "FAIL" }; Detail = $paths.FrontendPackage }
    $checks += [pscustomobject]@{ Name = "backend/.env"; Status = if (Test-Path $paths.BackendEnv) { "PASS" } else { "WARNING" }; Detail = "Optional but recommended for local configuration" }

    $viteExists = (Test-Path $paths.FrontendViteConfigJs) -or (Test-Path $paths.FrontendViteConfigTs)
    $checks += [pscustomobject]@{ Name = "frontend vite config"; Status = if ($viteExists) { "PASS" } else { "FAIL" }; Detail = "vite.config.js or vite.config.ts" }

    $port8001 = Get-OmegaProcessByPort -Port 8001
    $port5173 = Get-OmegaProcessByPort -Port 5173
    $checks += [pscustomobject]@{ Name = "Port 8001"; Status = if ($port8001) { "WARNING" } else { "PASS" }; Detail = if ($port8001) { "occupied by PID $($port8001.Pid) ($($port8001.ProcessName))" } else { "available" } }
    $checks += [pscustomobject]@{ Name = "Port 5173"; Status = if ($port5173) { "WARNING" } else { "PASS" }; Detail = if ($port5173) { "occupied by PID $($port5173.Pid) ($($port5173.ProcessName))" } else { "available" } }

    Write-Host ""
    Write-Host "OMEGA-ARC Doctor"
    Write-Host "-------------------------------------"
    foreach ($check in $checks) {
        switch ($check.Status) {
            "PASS" { Write-Host "PASS    $($check.Name): $($check.Detail)" -ForegroundColor Green }
            "WARNING" { Write-Host "WARNING $($check.Name): $($check.Detail)" -ForegroundColor Yellow }
            default { Write-Host "FAIL    $($check.Name): $($check.Detail)" -ForegroundColor Red }
        }
    }
    Write-Host "-------------------------------------"

    if (@($checks | Where-Object Status -eq "FAIL").Count -gt 0) {
        exit 1
    }
}

function Open-OmegaDocs {
    $paths = Get-OmegaPaths
    $targets = @(
        (Join-Path $paths.RepoRoot "SYSTEM_OVERVIEW.md"),
        (Join-Path $paths.RepoRoot "VERSION_HISTORY.md"),
        (Join-Path $paths.RepoRoot "docs/decisions"),
        (Join-Path $paths.RepoRoot "docs/acceptance"),
        (Join-Path $paths.RepoRoot "docs/architecture")
    )

    foreach ($target in $targets) {
        if (Test-Path $target) {
            Start-Process $target
            Write-OmegaInfo "Opened $target"
        }
        else {
            Write-OmegaWarning "Missing documentation target: $target"
        }
    }
}

function Invoke-OmegaClean {
    $paths = Get-OmegaPaths

    $targets = @()
    $targets += Get-ChildItem -Path $paths.RepoRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
    $targets += Get-ChildItem -Path $paths.RepoRoot -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue

    $pytestCache = Join-Path $paths.Backend ".pytest_cache"
    if (Test-Path $pytestCache) {
        $targets += Get-Item $pytestCache
    }

    $nodeCaches = @(
        (Join-Path $paths.Frontend "node_modules/.cache"),
        (Join-Path $paths.Frontend "node_modules/.vite")
    )
    foreach ($cache in $nodeCaches) {
        if (Test-Path $cache) {
            $targets += Get-Item $cache
        }
    }

    if ($targets.Count -eq 0) {
        Write-OmegaInfo "Nothing to clean."
        return
    }

    Write-OmegaInfo "The following cache artifacts can be removed:"
    foreach ($target in $targets) {
        Write-Host "- $($target.FullName)"
    }

    $confirmation = Read-Host "Proceed with deletion? (y/N)"
    if ($confirmation -notin @("y", "Y", "yes", "YES")) {
        Write-OmegaWarning "Clean canceled."
        return
    }

    foreach ($target in $targets) {
        Remove-Item -Path $target.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }

    Write-OmegaPass "Clean operation completed."
}

function Show-OmegaPlan {
    $paths = Get-OmegaPaths
    $goalsPath = Join-Path $paths.Backend "data/goals.json"
    $plansPath = Join-Path $paths.Backend "data/plans.json"

    $activeGoals = @()
    $activePlan = $null

    if (Test-Path $goalsPath) {
        try {
            $store = Get-Content -Path $goalsPath -Raw | ConvertFrom-Json
            foreach ($goal in @($store.goals)) {
                if ($null -eq $goal) {
                    continue
                }
                $status = ("$($goal.status)").ToLowerInvariant()
                if ([string]::IsNullOrWhiteSpace($status) -or $status -eq "active" -or $status -eq "in_progress") {
                    $activeGoals += ("$($goal.title)")
                }
            }
        }
        catch {
            Write-OmegaWarning "Could not parse goals store at $goalsPath"
        }
    }

    if (Test-Path $plansPath) {
        try {
            $planStore = Get-Content -Path $plansPath -Raw | ConvertFrom-Json
            $candidates = @($planStore.plans | Where-Object {
                $status = ("$($_.status)").ToLowerInvariant()
                $status -eq "active" -or $status -eq "blocked" -or $status -eq "validated"
            })
            if ($candidates.Count -gt 0) {
                $activePlan = $candidates | Sort-Object -Property updated_at -Descending | Select-Object -First 1
            }
        }
        catch {
            Write-OmegaWarning "Could not parse plan store at $plansPath"
        }
    }

    Write-Host ""
    Write-Host "Current Goals"
    if ($activeGoals.Count -gt 0) {
        foreach ($goal in $activeGoals) {
            Write-Host "- $goal"
        }
    }
    else {
        Write-Host "- None"
    }

    Write-Host ""
    Write-Host "Current Plans"
    if ($null -ne $activePlan) {
        Write-Host "- ID: $($activePlan.id)"
        Write-Host "  Goal: $($activePlan.title)"
        Write-Host "  Status: $($activePlan.status)"

        $nextStep = @($activePlan.steps | Where-Object { "$_" -and ($_.status -eq "active" -or $_.status -eq "ready" -or $_.status -eq "pending") } | Sort-Object -Property order | Select-Object -First 1)
        if ($nextStep.Count -gt 0) {
            Write-Host "  Next Step: $($nextStep[0].title)"
        }
    }
    else {
        Write-Host "- None"
    }

    Write-Host ""
    Write-Host "Current Blockers"
    if ($null -ne $activePlan) {
        $blocked = @($activePlan.steps | Where-Object { "$_" -and $_.status -eq "blocked" })
        if ($blocked.Count -gt 0) {
            foreach ($step in $blocked) {
                Write-Host "- $($step.title)"
            }
        }
        else {
            Write-Host "- None"
        }
    }
    else {
        Write-Host "- None"
    }

    Write-Host ""
    Write-OmegaInfo "No execution performed. Planning output is proposal-only."
}

function Show-OmegaPlans {
    $paths = Get-OmegaPaths
    $plansPath = Join-Path $paths.Backend "data/plans.json"

    Write-Host ""
    Write-Host "Plans"
    Write-Host "-------------------------------------"

    if (-not (Test-Path $plansPath)) {
        Write-Host "No plans store found."
        return
    }

    try {
        $planStore = Get-Content -Path $plansPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-OmegaWarning "Could not parse plan store at $plansPath"
        return
    }

    $plans = @($planStore.plans)
    if ($plans.Count -eq 0) {
        Write-Host "No plans recorded."
        return
    }

    foreach ($plan in $plans) {
        $nextStep = @($plan.steps | Where-Object { "$_" -and ($_.status -eq "active" -or $_.status -eq "ready" -or $_.status -eq "pending") } | Sort-Object -Property order | Select-Object -First 1)
        $blockers = @($plan.steps | Where-Object { "$_" -and $_.status -eq "blocked" })

        Write-Host "ID: $($plan.id)"
        Write-Host "Goal: $($plan.title)"
        Write-Host "Status: $($plan.status)"
        Write-Host "Next Step: $(if ($nextStep.Count -gt 0) { $nextStep[0].title } else { 'None' })"
        Write-Host "Blockers: $(if ($blockers.Count -gt 0) { ($blockers | ForEach-Object { $_.title }) -join '; ' } else { 'None' })"
        Write-Host ""
    }
}

function Show-OmegaDecisions {
    $paths = Get-OmegaPaths
    $decisionsPath = Join-Path $paths.Backend "data/decisions.json"

    Write-Host ""
    Write-Host "Decisions"
    Write-Host "-------------------------------------"

    if (-not (Test-Path $decisionsPath)) {
        Write-Host "No decisions store found."
        return
    }

    try {
        $decisionStore = Get-Content -Path $decisionsPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-OmegaWarning "Could not parse decision store at $decisionsPath"
        return
    }

    $decisions = @($decisionStore.decisions | Where-Object { "$_" -and $_.status -eq "active" })
    if ($decisions.Count -eq 0) {
        Write-Host "No active decisions recorded."
        return
    }

    foreach ($decision in $decisions) {
        Write-Host "- $($decision.title): $($decision.reason)"
    }
}

function Show-OmegaDeliberation {
    $paths = Get-OmegaPaths
    $deliberationPath = Join-Path $paths.Backend "data/deliberations.json"
    $approvalPath = Join-Path $paths.Backend "data/approvals.json"

    Write-Host ""
    Write-Host "Deliberation"
    Write-Host "-------------------------------------"

    if (-not (Test-Path $deliberationPath)) {
        Write-Host "No deliberation records found."
        return
    }

    try {
        $store = Get-Content -Path $deliberationPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-OmegaWarning "Could not parse deliberation store at $deliberationPath"
        return
    }

    $records = @($store.records)
    if ($records.Count -eq 0) {
        Write-Host "No deliberation records found."
        return
    }

    $latest = $records | Sort-Object -Property updated_at -Descending | Select-Object -First 1
    $recommended = $latest.recommendation.plan_id
    Write-Host "Current recommendation: $(if ($recommended) { $recommended } else { 'none' })"

    if (Test-Path $approvalPath) {
        try {
            $approvalStore = Get-Content -Path $approvalPath -Raw | ConvertFrom-Json
            $latestApproval = @($approvalStore.approvals | Sort-Object -Property updated_at -Descending | Select-Object -First 1)
            if ($latestApproval.Count -gt 0) {
                Write-Host "Approval state: $($latestApproval[0].status)"
            }
            else {
                Write-Host "Approval state: none"
            }
        }
        catch {
            Write-OmegaWarning "Could not parse approval store at $approvalPath"
        }
    }
}

function Show-OmegaRisks {
    $paths = Get-OmegaPaths
    $deliberationPath = Join-Path $paths.Backend "data/deliberations.json"

    Write-Host ""
    Write-Host "Active Risks"
    Write-Host "-------------------------------------"

    if (-not (Test-Path $deliberationPath)) {
        Write-Host "No deliberation records found."
        return
    }

    try {
        $store = Get-Content -Path $deliberationPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-OmegaWarning "Could not parse deliberation store at $deliberationPath"
        return
    }

    $latest = @($store.records | Sort-Object -Property updated_at -Descending | Select-Object -First 1)
    if ($latest.Count -eq 0) {
        Write-Host "No deliberation records found."
        return
    }

    $risks = @($latest[0].deliberation.risk_assessments)
    if ($risks.Count -eq 0) {
        Write-Host "No active risks."
        return
    }

    foreach ($entry in $risks) {
        Write-Host "Plan: $($entry.plan_id) (overall: $($entry.overall_risk))"
        foreach ($risk in @($entry.risks)) {
            Write-Host "- $($risk.risk) [probability=$($risk.probability), impact=$($risk.impact)]"
        }
        Write-Host ""
    }
}

function Show-OmegaAssumptions {
    $paths = Get-OmegaPaths
    $assumptionPath = Join-Path $paths.Backend "data/assumptions.json"

    Write-Host ""
    Write-Host "Assumptions"
    Write-Host "-------------------------------------"

    if (-not (Test-Path $assumptionPath)) {
        Write-Host "No assumptions store found."
        return
    }

    try {
        $store = Get-Content -Path $assumptionPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-OmegaWarning "Could not parse assumptions store at $assumptionPath"
        return
    }

    $items = @($store.assumptions)
    if ($items.Count -eq 0) {
        Write-Host "No assumptions recorded."
        return
    }

    foreach ($item in $items) {
        Write-Host "- $($item.statement)"
        Write-Host "  Status: $($item.status)"
        Write-Host "  Confidence: $($item.confidence)"
    }
}

function Show-OmegaCompare {
    $paths = Get-OmegaPaths
    $deliberationPath = Join-Path $paths.Backend "data/deliberations.json"

    Write-Host ""
    Write-Host "Plan Comparison"
    Write-Host "-------------------------------------"

    if (-not (Test-Path $deliberationPath)) {
        Write-Host "No deliberation records found."
        return
    }

    try {
        $store = Get-Content -Path $deliberationPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-OmegaWarning "Could not parse deliberation store at $deliberationPath"
        return
    }

    $latest = @($store.records | Sort-Object -Property updated_at -Descending | Select-Object -First 1)
    if ($latest.Count -eq 0) {
        Write-Host "No deliberation records found."
        return
    }

    $comparison = @($latest[0].deliberation.comparison.comparison)
    if ($comparison.Count -eq 0) {
        Write-Host "No comparison data recorded."
        return
    }

    foreach ($item in $comparison) {
        Write-Host "Plan: $($item.title)"
        $criteria = $item.criteria
        Write-Host "- Installation: $($criteria.installation_state)"
        Write-Host "- Dependencies: $($criteria.dependency_count)"
        Write-Host "- Evidence Completeness: $($criteria.evidence_completeness)"
        Write-Host "- Complexity: $($criteria.implementation_complexity)"
        Write-Host "- Estimated Risk: $($criteria.estimated_risk)"
        Write-Host "- Confidence: $($criteria.confidence)"
        Write-Host ""
    }
}

function Get-OmegaToolApiBase {
    $backend = Get-OmegaBackendStatus -Port 8001
    return $backend.Url
}

function Show-OmegaTools {
    $apiBase = Get-OmegaToolApiBase
    Write-Host ""
    Write-Host "Registered Tools"
    Write-Host "-------------------------------------"

    try {
        $response = Invoke-RestMethod -Method Get -Uri "$apiBase/system/tools"
    }
    catch {
        Write-OmegaWarning "Could not query tool registry from backend."
        return
    }

    Write-Host "Framework Enabled: $($response.enabled)"
    Write-Host "Execution Enabled: $($response.execution_enabled)"
    Write-Host "Dry-Run Enabled: $($response.dry_run_enabled)"
    Write-Host "Critical Tools Enabled: $($response.critical_tools_enabled)"
    Write-Host "Approval TTL: $($response.approval_ttl_seconds) seconds"
    Write-Host ""

    foreach ($tool in @($response.tools)) {
        Write-Host "Name: $($tool.name)"
        Write-Host "- Category: $($tool.category)"
        Write-Host "- Risk: $($tool.risk_level)"
        Write-Host "- Approval Required: $($tool.requires_approval)"
        Write-Host "- Dry-Run Support: $($tool.supports_dry_run)"
        Write-Host "- Enabled: $($tool.enabled)"
        Write-Host ""
    }
}

function Show-OmegaToolStatus {
    $apiBase = Get-OmegaToolApiBase
    Write-Host ""
    Write-Host "Tool Framework Status"
    Write-Host "-------------------------------------"

    try {
        $response = Invoke-RestMethod -Method Get -Uri "$apiBase/system/tools"
    }
    catch {
        Write-OmegaWarning "Could not query tool framework status from backend."
        return
    }

    Write-Host "Framework Enabled: $($response.enabled)"
    Write-Host "Execution Enabled: $($response.execution_enabled)"
    Write-Host "Dry-Run Enabled: $($response.dry_run_enabled)"
    Write-Host "Critical Tools Enabled: $($response.critical_tools_enabled)"
    Write-Host "Registered Tools: $(@($response.tools).Count)"
    Write-Host "Approval TTL Seconds: $($response.approval_ttl_seconds)"
}

function Show-OmegaFutureHook {
    param([Parameter(Mandatory = $true)][string]$Name)
    Write-OmegaWarning "Future hook '$Name' is reserved but not yet implemented."
}

function Show-OmegaCommandHelp {
    Write-Host "OMEGA-ARC Developer Console (Epoch VII)"
    Write-Host "Usage: .\scripts\omega.ps1 <command> [argument]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  launch"
    Write-Host "  stop"
    Write-Host "  restart"
    Write-Host "  status"
    Write-Host "  doctor"
    Write-Host "  test"
    Write-Host "  acceptance [id]"
    Write-Host "  docs"
    Write-Host "  git"
    Write-Host "  clean"
    Write-Host "  plan"
    Write-Host "  plans"
    Write-Host "  decisions"
    Write-Host "  deliberation"
    Write-Host "  risks"
    Write-Host "  assumptions"
    Write-Host "  compare"
    Write-Host "  tools"
    Write-Host "  tool-status"
}

Export-ModuleMember -Function @(
    "Invoke-OmegaLaunch",
    "Stop-OmegaStack",
    "Restart-OmegaStack",
    "Show-OmegaStatus",
    "Invoke-OmegaDoctor",
    "Open-OmegaDocs",
    "Invoke-OmegaClean",
    "Show-OmegaPlan",
    "Show-OmegaPlans",
    "Show-OmegaDecisions",
    "Show-OmegaDeliberation",
    "Show-OmegaRisks",
    "Show-OmegaAssumptions",
    "Show-OmegaCompare",
    "Show-OmegaTools",
    "Show-OmegaToolStatus",
    "Show-OmegaFutureHook",
    "Show-OmegaCommandHelp"
)
