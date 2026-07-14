# Quick Start

Recommended repository location:

`C:\Users\BillH\Desktop\NERD\Turning\omega-arc`

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap_repository.ps1
.\scripts\copy_current_project.ps1
git status
git add .
git commit -m "chore: establish OMEGA-ARC repository and continuity foundation"
```

Do not copy `.venv`, `node_modules`, model weights, caches, `.env`, or private databases.
