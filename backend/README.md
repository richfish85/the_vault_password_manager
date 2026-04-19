# TheVault Backend

FastAPI service for authentication, encrypted secret storage, and audit logging.

## Run

```bash
python -m venv .venv
<activate the virtual environment in your shell>
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

The backend expects Postgres and Redis to be available. See the root `README.md` for the full project workflow.
