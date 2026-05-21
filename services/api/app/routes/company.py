from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class CompanyUpdate(BaseModel):
    name: str
    description: str = ""


@router.get("")
def get_company() -> dict[str, str]:
    return {
        "id": "default-company",
        "name": "AI Company",
        "description": "A local multi-agent company workspace.",
    }


@router.put("")
def update_company(payload: CompanyUpdate) -> dict[str, str]:
    return {
        "id": "default-company",
        "name": payload.name,
        "description": payload.description,
    }
