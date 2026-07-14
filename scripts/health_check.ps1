param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$Items = @(
    @{Name="Git repository"; Path=".git"},
    @{Name="README"; Path="README.md"},
    @{Name="Covenant"; Path="COVENANT.md"},
    @{Name="Constitution"; Path="CONSTITUTION.md"},
    @{Name="Backend"; Path="backend"},
    @{Name="Frontend"; Path="frontend"},
    @{Name="Training"; Path="training"},
    @{Name="Console"; Path="console"}
)

foreach ($Item in $Items) {
    $Full = Join-Path $RepositoryRoot $Item.Path
    $Result = if (Test-Path $Full) { "PASS" } else { "FAIL" }
    Write-Host "$Result`t$($Item.Name)`t$Full"
}
