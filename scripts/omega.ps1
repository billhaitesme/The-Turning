[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = "status",

    [Parameter(Position = 1)]
    [string]$Argument
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$moduleRoot = Join-Path $PSScriptRoot "modules"
$modules = @(
    "OmegaEnvironment.psm1",
    "OmegaGit.psm1",
    "OmegaAcceptance.psm1",
    "OmegaTests.psm1",
    "OmegaBackend.psm1",
    "OmegaFrontend.psm1",
    "OmegaStatus.psm1"
)

foreach ($module in $modules) {
    Import-Module (Join-Path $moduleRoot $module) -Force -DisableNameChecking
}

$normalized = ("$Command").Trim().ToLowerInvariant()

switch ($normalized) {
    "launch" {
        Invoke-OmegaLaunch
        break
    }
    "stop" {
        Stop-OmegaStack
        break
    }
    "restart" {
        Restart-OmegaStack
        break
    }
    "status" {
        Show-OmegaStatus
        break
    }
    "doctor" {
        Invoke-OmegaDoctor
        break
    }
    "test" {
        Invoke-OmegaTests
        break
    }
    "acceptance" {
        Invoke-OmegaAcceptance -Scenario $Argument
        break
    }
    "docs" {
        Open-OmegaDocs
        break
    }
    "git" {
        Show-OmegaGitStatus
        break
    }
    "clean" {
        Invoke-OmegaClean
        break
    }
    "plan" {
        Show-OmegaPlan
        break
    }
    "plans" {
        Show-OmegaPlans
        break
    }
    "decisions" {
        Show-OmegaDecisions
        break
    }
    "deliberation" {
        Show-OmegaDeliberation
        break
    }
    "risks" {
        Show-OmegaRisks
        break
    }
    "assumptions" {
        Show-OmegaAssumptions
        break
    }
    "compare" {
        Show-OmegaCompare
        break
    }
    "benchmark" {
        Show-OmegaFutureHook -Name "benchmark"
        break
    }
    "profile" {
        Show-OmegaFutureHook -Name "profile"
        break
    }
    "release" {
        Show-OmegaFutureHook -Name "release"
        break
    }
    "package" {
        Show-OmegaFutureHook -Name "package"
        break
    }
    "deploy" {
        Show-OmegaFutureHook -Name "deploy"
        break
    }
    "backup" {
        Show-OmegaFutureHook -Name "backup"
        break
    }
    "restore" {
        Show-OmegaFutureHook -Name "restore"
        break
    }
    "vision-test" {
        Show-OmegaFutureHook -Name "vision-test"
        break
    }
    "reasoning-report" {
        Show-OmegaFutureHook -Name "reasoning-report"
        break
    }
    "acceptance-runner" {
        Show-OmegaFutureHook -Name "acceptance-runner"
        break
    }
    default {
        Show-OmegaCommandHelp
        exit 1
    }
}
