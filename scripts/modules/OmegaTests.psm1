Set-StrictMode -Version Latest

function Get-OmegaBackendTestCount {
    $paths = Get-OmegaPaths
    $testDir = Join-Path $paths.Backend "tests"

    if (-not (Test-Path $testDir)) {
        return 0
    }

    $matches = Get-ChildItem -Path $testDir -Recurse -Filter "test_*.py" |
        Select-String -Pattern "^\s*def\s+test_" -CaseSensitive

    return @($matches).Count
}

function Invoke-OmegaTests {
    $paths = Get-OmegaPaths

    if (-not (Test-Path $paths.BackendPython)) {
        Write-OmegaFail "Python environment not found: $($paths.BackendPython)"
        exit 1
    }

    Write-OmegaInfo "Running backend test suite..."
    Push-Location $paths.Backend
    try {
        $start = Get-Date
        $stdoutPath = Join-Path ([System.IO.Path]::GetTempPath()) ("omega-tests-stdout-{0}.log" -f ([guid]::NewGuid().ToString("N")))
        $stderrPath = Join-Path ([System.IO.Path]::GetTempPath()) ("omega-tests-stderr-{0}.log" -f ([guid]::NewGuid().ToString("N")))

        try {
            $proc = Start-Process -FilePath $paths.BackendPython -ArgumentList @(
                "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"
            ) -PassThru -Wait -NoNewWindow -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

            $stdout = if (Test-Path $stdoutPath) { Get-Content -Path $stdoutPath -Raw } else { "" }
            $stderr = if (Test-Path $stderrPath) { Get-Content -Path $stderrPath -Raw } else { "" }
            $text = ($stdout + [Environment]::NewLine + $stderr).Trim()
            $output = if ($text) { $text } else { "" }
            $exitCode = $proc.ExitCode
        }
        finally {
            if (Test-Path $stdoutPath) { Remove-Item -Path $stdoutPath -Force -ErrorAction SilentlyContinue }
            if (Test-Path $stderrPath) { Remove-Item -Path $stderrPath -Force -ErrorAction SilentlyContinue }
        }

        $duration = [math]::Round(((Get-Date) - $start).TotalSeconds, 2)

        $text = ("$output" | Out-String)
        $ran = "unknown"
        $failures = 0

        if ($text -match "Ran\s+(\d+)\s+tests?") {
            $ran = $Matches[1]
        }

        if ($text -match "FAILED\s*\(([^\)]+)\)") {
            $details = $Matches[1]
            if ($details -match "failures=(\d+)") {
                $failures += [int]$Matches[1]
            }
            if ($details -match "errors=(\d+)") {
                $failures += [int]$Matches[1]
            }
        }

        Write-Host $text
        Write-Host ""
        Write-OmegaInfo "Tests: $ran"
        if ($exitCode -eq 0) {
            Write-OmegaPass "Failures: 0"
            Write-OmegaPass "Summary: PASS"
        }
        else {
            Write-OmegaFail "Failures: $failures"
            Write-OmegaFail "Summary: FAIL"
        }
        Write-OmegaInfo "Duration: ${duration}s"

        if ($exitCode -ne 0) {
            exit $exitCode
        }
    }
    finally {
        Pop-Location
    }
}

Export-ModuleMember -Function @(
    "Get-OmegaBackendTestCount",
    "Invoke-OmegaTests"
)
