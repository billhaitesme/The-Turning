# OMEGA-ARC school day - Windows Task Scheduler entry point.
# Fires daily at 09:00 (see Register-SchoolDayTask.ps1); studies until 14:00, then reflects.
# All real logic is in scripts/school_day.py; this wrapper only pins paths and captures output.
$ErrorActionPreference = 'Continue'
$repo   = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo 'backend\.venv\Scripts\python.exe'
$script = Join-Path $PSScriptRoot 'school_day.py'
$logDir = Join-Path $repo '.runtime-logs\school'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stamp  = Get-Date -Format 'yyyy-MM-dd'
$out    = Join-Path $logDir "$stamp.task.log"

"[$(Get-Date -Format 'HH:mm:ss')] task fired; python=$python" | Out-File -FilePath $out -Append -Encoding utf8
Set-Location $repo
& $python $script --until 14:00 --start-stack @args *>> $out
"[$(Get-Date -Format 'HH:mm:ss')] task exit code $LASTEXITCODE" | Out-File -FilePath $out -Append -Encoding utf8
exit $LASTEXITCODE
