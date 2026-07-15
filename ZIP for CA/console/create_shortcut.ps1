$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $Dir "Launch_Console.bat"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Path = Join-Path $Desktop "0M3-G4-ARC Command Console v3.1.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($Path)
$Shortcut.TargetPath = $Target
$Shortcut.WorkingDirectory = $Dir
$Shortcut.Save()
Write-Host "Created $Path"
