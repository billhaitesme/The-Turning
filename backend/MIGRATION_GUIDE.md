# Migration Guide

1. Create a branch:

```powershell
git checkout -b refactor/epoch1-foundation
```

2. Back up:

```powershell
.\scripts\backup.ps1
```

3. Copy this patch into the repository without replacing `backend/app.py`.

4. Run tests:

```powershell
$env:PYTHONPATH = "$PWD\backend"
python -m unittest discover -s backend\tests
```

5. Integrate the first route into `backend/app.py`:

```python
from routes.system import router as system_router
app.include_router(system_router)
```

6. Restart and open:

`http://127.0.0.1:8000/system/config`

7. Commit:

```powershell
git add .
git commit -m "refactor: establish modular backend foundation"
```
