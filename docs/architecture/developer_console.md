# Developer Console

## Purpose

The OMEGA-ARC Developer Console is the primary local development entry point for Epoch V.
It centralizes environment checks, startup and shutdown, diagnostics, testing, acceptance navigation, and repository inspection.

Design goals:

- Keep runtime behavior unchanged.
- Avoid backend API changes.
- Avoid frontend behavior changes.
- Manage only developer tooling workflows.

## Commands

Run commands from the repository root:

```powershell
.\scripts\omega.ps1 launch
.\scripts\omega.ps1 stop
.\scripts\omega.ps1 restart
.\scripts\omega.ps1 status
.\scripts\omega.ps1 doctor
.\scripts\omega.ps1 test
.\scripts\omega.ps1 acceptance
.\scripts\omega.ps1 acceptance 004
.\scripts\omega.ps1 docs
.\scripts\omega.ps1 git
.\scripts\omega.ps1 clean
```

### launch

Performs full startup orchestration:

- Locates repository root.
- Validates required project paths.
- Validates `backend/.venv`, Python, Node, npm, and uvicorn.
- Checks ports `8001` and `5173`.
- Reports port owners when occupied and never kills unknown processes.
- Starts backend and waits for `/system/status` or `/health`.
- Starts frontend.
- Opens browser and prints a launch summary.

### stop

Stops only processes that were started by the developer console.
It relies on PID records in `scripts/.omega-state` and does not kill unrelated Python or Node processes.

### restart

Runs `stop` followed by `launch`.

### status

Prints repository and runtime development status:

- repository path
- branch
- commit
- dirty/clean
- latest tag
- backend and frontend online states
- backend and frontend URLs
- Python, Node, and uvicorn versions
- venv path
- backend test count
- acceptance scenario count

### doctor

Runs diagnostics and marks each check as:

- PASS (green)
- WARNING (yellow)
- FAIL (red)

Checks include:

- Python
- Node
- npm
- uvicorn
- `backend/.venv`
- `frontend/node_modules`
- `backend/app.py`
- `frontend/package.json`
- `backend/.env`
- frontend Vite config
- port conflicts

### test

Runs backend tests via unittest discovery and reports:

- tests run
- failures
- duration
- summary

### acceptance

Without an argument, lists acceptance scenarios.
With an ID argument (for example `004`), opens the matching acceptance file.

### docs

Opens:

- `SYSTEM_OVERVIEW.md`
- `VERSION_HISTORY.md`
- `docs/decisions`
- `docs/acceptance`
- `docs/architecture`

### git

Prints:

- current branch
- current commit
- latest tag
- git status
- ahead/behind

### clean

Offers to remove development cache artifacts only:

- `__pycache__`
- `.pyc`
- `.pytest_cache`
- node cache directories (for example `.cache`, `.vite` under `frontend/node_modules`)

Never removes:

- virtual environments
- `node_modules`
- `.git`

## Examples

```powershell
# Full local start
.\scripts\omega.ps1 launch

# Health and dependency diagnostics
.\scripts\omega.ps1 doctor

# Open acceptance scenario 007
.\scripts\omega.ps1 acceptance 007

# Run backend tests
.\scripts\omega.ps1 test
```

## Future Roadmap

Reserved command hooks are present for:

- benchmark
- profile
- release
- package
- deploy
- backup
- restore
- vision-test
- reasoning-report
- acceptance-runner

These hooks intentionally print a placeholder warning until implemented.
