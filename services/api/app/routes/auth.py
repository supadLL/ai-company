from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, str]:
    # MVP placeholder: replace with local password hash verification.
    return {"status": "ok", "session": "local-dev-session"}


@router.post("/logout")
def logout() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/session")
def session() -> dict[str, bool]:
    return {"authenticated": True}
