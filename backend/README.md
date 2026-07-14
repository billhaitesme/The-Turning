# Backend

Run from this folder after installing dependencies and starting Ollama.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configure

Copy `.env.example` to `.env` and edit as needed.

## Start

```powershell
uvicorn app:app --reload
```

## Notes

- Chat uses Ollama `/api/chat`
- Embeddings use Ollama `/api/embed`
- Web search is optional and uses the `ddgs` package when enabled
