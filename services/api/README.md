# AI Company Local API

FastAPI service for local authentication, role/task orchestration, model-provider relay, and SQLite persistence.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --port 8787
```

## Current Endpoints

- `GET /health`
- `POST /auth/login`
- `GET /auth/session`
- `GET /company`
- `GET /roles`
- `GET /tasks`
- `POST /tasks`
- `POST /tasks/{task_id}/run`
