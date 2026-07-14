# 0M3-G4-ARC Command Console v3

## Correct default root

`C:\Users\BillH\Desktop\NERD\Turning`

## New in v3

- Built-in Settings window
- Change only the Project Root
- Backend, frontend, training, and virtual-environment paths update automatically
- Live derived-path preview
- Health check reruns after settings are saved
- Visible backend and frontend terminals
- Diagnostics report with exact paths

## Install

Extract to:

`C:\Users\BillH\Desktop\NERD\Turning\omega_arc_command_console_v3`

Run:

`Install_Console.bat`

Then use the new desktop shortcut.

## Use

1. Click **HEALTH CHECK**.
2. If a path fails, click **SETTINGS**.
3. Confirm Project Root is:

   `C:\Users\BillH\Desktop\NERD\Turning`

4. Click **SAVE SETTINGS**.
5. Click **START SYSTEM**.
6. Read the visible backend and frontend windows.
7. Click **OPEN UI** when both are online.


## v3.1 terminal launch fix

This release replaces `cmd.exe /k` command construction with PowerShell `Set-Location -LiteralPath` and explicit executable invocation.

It fixes:

`The filename, directory name, or volume label syntax is incorrect.`

You do not need to reinstall the backend, frontend, Node.js, or Python.
