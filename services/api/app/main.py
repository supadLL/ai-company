from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlmodel import Session

from app.db.session import create_db_and_tables
from app.db.session import engine
from app.routes import auth, company, relay, roles, tasks
from app.routes import workspaces


app = FastAPI(title="AI Company Local API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(company.router, prefix="/company", tags=["company"])
app.include_router(roles.router, prefix="/roles", tags=["roles"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
app.include_router(relay.router, prefix="/relay", tags=["relay"])


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        roles.seed_default_roles(session)
        workspaces.ensure_seed_data(session)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
