from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.models import CompanyRole
from app.db.session import get_session


router = APIRouter()


DEFAULT_ROLES = [
    {
        "id": "general-manager",
        "title": "总经理",
        "department": "管理层",
        "level": "L1",
        "responsibility": "理解 Boss 目标，制定公司级计划，分配关键岗位并汇总最终交付。",
        "prompt": "你是 AI 公司的总经理。请理解 Boss 的目标，制定清晰、可执行、可验收的公司级计划。",
        "enabled": True,
        "sort_order": 10,
    },
    {
        "id": "deputy-manager",
        "title": "副经理",
        "department": "管理层",
        "level": "L2",
        "responsibility": "拆解任务，协调岗位节奏，发现执行缺口并推动补齐。",
        "prompt": "你是 AI 公司的副经理。请把目标拆成岗位任务，明确协作顺序、风险和检查点。",
        "enabled": True,
        "sort_order": 20,
    },
    {
        "id": "product-manager",
        "title": "产品经理",
        "department": "产品部",
        "level": "L3",
        "responsibility": "整理需求、用户故事、范围边界和验收标准。",
        "prompt": "你是产品经理。请把目标整理成清晰需求、用户故事、功能范围和验收标准。",
        "enabled": True,
        "sort_order": 30,
    },
    {
        "id": "tech-lead",
        "title": "技术负责人",
        "department": "技术部",
        "level": "L3",
        "responsibility": "设计架构、模块边界、技术方案和风险控制。",
        "prompt": "你是技术负责人。请输出架构方案、模块边界、实现步骤、风险点和技术取舍。",
        "enabled": True,
        "sort_order": 40,
    },
    {
        "id": "qa-lead",
        "title": "测试负责人",
        "department": "质量部",
        "level": "L3",
        "responsibility": "制定验证策略、测试清单、异常场景和发布检查。",
        "prompt": "你是测试负责人。请输出测试策略、核心用例、异常场景和发布前检查清单。",
        "enabled": True,
        "sort_order": 50,
    },
]


class RoleUpsert(BaseModel):
    id: str | None = None
    title: str
    department: str
    level: str = "L3"
    responsibility: str
    prompt: str
    enabled: bool = True
    sort_order: int = 0


class RoleEnabledUpdate(BaseModel):
    enabled: bool


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def role_to_public(role: CompanyRole) -> dict:
    return role.model_dump()


def seed_default_roles(session: Session) -> None:
    existing = {role.id for role in session.exec(select(CompanyRole)).all()}
    created = False
    for role_data in DEFAULT_ROLES:
        if role_data["id"] in existing:
            continue
        role = CompanyRole(**role_data)
        session.add(role)
        created = True
    if created:
        session.commit()


def get_role_or_404(session: Session, role_id: str) -> CompanyRole:
    role = session.get(CompanyRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="role not found")
    return role


@router.get("")
def list_roles(session: Session = Depends(get_session)) -> list[dict]:
    seed_default_roles(session)
    roles = session.exec(select(CompanyRole).order_by(CompanyRole.sort_order.asc(), CompanyRole.created_at.asc())).all()
    return [role_to_public(role) for role in roles]


@router.get("/{role_id}")
def get_role(role_id: str, session: Session = Depends(get_session)) -> dict:
    seed_default_roles(session)
    role = get_role_or_404(session, role_id)
    return role_to_public(role)


@router.post("")
def create_role(payload: RoleUpsert, session: Session = Depends(get_session)) -> dict:
    data = payload.model_dump(exclude_none=True)
    role = CompanyRole(**data)
    session.add(role)
    session.commit()
    session.refresh(role)
    return role_to_public(role)


@router.put("/{role_id}")
def update_role(role_id: str, payload: RoleUpsert, session: Session = Depends(get_session)) -> dict:
    role = get_role_or_404(session, role_id)
    if payload.id and payload.id != role_id:
        raise HTTPException(status_code=400, detail="role id cannot be changed")
    role.title = payload.title
    role.department = payload.department
    role.level = payload.level
    role.responsibility = payload.responsibility
    role.prompt = payload.prompt
    role.enabled = payload.enabled
    role.sort_order = payload.sort_order
    role.updated_at = utc_now()
    session.add(role)
    session.commit()
    session.refresh(role)
    return role_to_public(role)


@router.patch("/{role_id}/enabled")
def update_role_enabled(role_id: str, payload: RoleEnabledUpdate, session: Session = Depends(get_session)) -> dict:
    role = get_role_or_404(session, role_id)
    role.enabled = payload.enabled
    role.updated_at = utc_now()
    session.add(role)
    session.commit()
    session.refresh(role)
    return role_to_public(role)


@router.delete("/{role_id}")
def delete_role(role_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    role = get_role_or_404(session, role_id)
    session.delete(role)
    session.commit()
    return {"status": "deleted", "id": role_id}
