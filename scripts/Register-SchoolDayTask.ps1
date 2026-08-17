# Register (or refresh) the daily OMEGA-ARC school-day task: 09:00 local, every day.
# The operator sets the cadence here (ADR 0025: cadence is operator-set, never chosen by the
# runtime). Re-run to update; -Unregister removes it.
#   powershell -ExecutionPolicy Bypass -File scripts\Register-SchoolDayTask.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Register-SchoolDayTask.ps1 -At 09:00
#   powershell -ExecutionPolicy Bypass -File scripts\Register-SchoolDayTask.ps1 -Unregister
param(
    [string]$At = '09:00',
    [switch]$Unregister
)
$ErrorActionPreference = 'Stop'
$taskName = 'OMEGA-ARC School Day'
$wrapper  = Join-Path $PSScriptRoot 'school_day.ps1'

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "removed task '$taskName'"
    exit 0
}

$action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$wrapper`"" `
    -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$trigger = New-ScheduledTaskTrigger -Daily -At $At
# WakeToRun: wake from sleep for school. No StartWhenAvailable on purpose - a missed 09:00 must
# NOT fire later in the day on top of whatever the operator is doing with the GPU.
$settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Description 'OMEGA-ARC daily learning window: study 09:00-14:00, then reflect. Runs scripts/school_day.py.' `
    -Force | Out-Null

$task = Get-ScheduledTask -TaskName $taskName
$info = $task | Get-ScheduledTaskInfo
Write-Host "registered '$taskName' - daily at $At, next run: $($info.NextRunTime)"
