from pathlib import Path
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SITE_PACKAGES = BACKEND_ROOT / ".venv" / "Lib" / "site-packages"

sys.path.append(str(SITE_PACKAGES))
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

# Load .env BEFORE reading bind configuration below. Otherwise uvicorn.run reads
# OMEGA_BIND_HOST/OMEGA_BACKEND_PORT from the process environment before importing
# the app (which is where load_dotenv normally runs), so a LAN validation profile
# placed in .env would be silently ignored and the server would stay on loopback.
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=True)
except ModuleNotFoundError:
    pass

import uvicorn


uvicorn.run(
    "app:app",
    host=os.environ.get("OMEGA_BIND_HOST", "127.0.0.1"),
    port=int(os.environ.get("OMEGA_BACKEND_PORT", "8001")),
    loop="asyncio",
    http="h11",
    lifespan="on",
    log_level="info",
)
