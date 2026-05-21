import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

from app.db.models import ModelCallLog, UpstreamAccount
from app.db.session import get_session
from app.relay.client import RelayError, run_openai_chat_completion, test_openai_compatible


router = APIRouter()


class UpstreamAccountCreate(BaseModel):
    label: str
    base_url: str = "https://api.openai.com/v1"
    api_key: str
    models: list[str] = Field(default_factory=list)
    provider_type: str = "openai_compatible"
    priority: int = 0


class UpstreamAccountUpdate(BaseModel):
    label: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    models: list[str] | None = None
    status: str | None = None
    priority: int | None = None


class AccountStatusUpdate(BaseModel):
    status: str


class LoginImportRequest(BaseModel):
    provider_type: str
    credential: str
    label: str | None = None
    models: list[str] | None = None


class RelayRunRequest(BaseModel):
    model: str
    messages: list[dict]
    task_id: str | None = None
    task_step_id: str | None = None
    role_id: str | None = None


def mask_secret(value: str) -> str:
    if len(value) <= 10:
        return "********"
    return value[:4] + "..." + value[-4:]


PROVIDER_PRESETS = [
    {
        "id": "openai",
        "label": "OpenAI / GPT",
        "provider_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4.1-mini"],
        "auth_url": "https://platform.openai.com/api-keys",
        "auth_modes": ["api_key", "login_import"],
        "description": "GPT 系列与 OpenAI-compatible 标准入口。",
    },
    {
        "id": "deepseek",
        "label": "DeepSeek",
        "provider_type": "deepseek",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"],
        "auth_url": "https://platform.deepseek.com/api_keys",
        "auth_modes": ["api_key", "login_import"],
        "description": "DeepSeek 官方 OpenAI-compatible API。",
    },
    {
        "id": "qwen_dashscope",
        "label": "Qwen / 阿里云百炼",
        "provider_type": "qwen_dashscope",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-max", "qwen3.6-plus"],
        "auth_url": "https://bailian.console.aliyun.com/",
        "auth_modes": ["api_key", "login_import"],
        "description": "通义千问 / DashScope OpenAI 兼容模式。",
    },
    {
        "id": "glm_bigmodel",
        "label": "GLM / 智谱 BigModel",
        "provider_type": "glm_bigmodel",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4.7", "glm-5.1"],
        "auth_url": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
        "auth_modes": ["api_key", "login_import"],
        "description": "智谱 AI 开放平台 OpenAI 兼容接口。",
    },
    {
        "id": "glm_zai",
        "label": "GLM / Z.AI",
        "provider_type": "glm_zai",
        "base_url": "https://api.z.ai/api/paas/v4",
        "models": ["glm-4.7", "glm-4.6"],
        "auth_url": "https://chat.z.ai/",
        "auth_modes": ["api_key", "login_import"],
        "description": "Z.AI GLM 通用 OpenAI-compatible API。",
    },
    {
        "id": "siliconflow",
        "label": "SiliconFlow / 硅基流动",
        "provider_type": "siliconflow",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen3-Coder"],
        "auth_url": "https://cloud.siliconflow.cn/account/ak",
        "auth_modes": ["api_key", "login_import"],
        "description": "聚合国产与开源模型的 OpenAI-compatible 平台。",
    },
    {
        "id": "custom_openai_compatible",
        "label": "自定义兼容上游",
        "provider_type": "openai_compatible",
        "base_url": "",
        "models": [],
        "auth_url": "",
        "auth_modes": ["api_key"],
        "description": "任意兼容 /chat/completions 的上游服务。",
    },
]


def get_provider_preset(provider_type: str) -> dict | None:
    return next(
        (
            preset
            for preset in PROVIDER_PRESETS
            if preset["id"] == provider_type or preset["provider_type"] == provider_type
        ),
        None,
    )


def account_to_public(account: UpstreamAccount) -> dict:
    return {
        "id": account.id,
        "provider_type": account.provider_type,
        "label": account.label,
        "base_url": account.base_url,
        "api_key_masked": mask_secret(account.api_key),
        "models": json.loads(account.models_json or "[]"),
        "status": account.status,
        "priority": account.priority,
        "total_request_count": account.total_request_count,
        "total_input_tokens": account.total_input_tokens,
        "total_output_tokens": account.total_output_tokens,
        "total_cached_tokens": account.total_cached_tokens,
        "last_error": account.last_error,
        "last_used_at": account.last_used_at,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def select_account(session: Session, model: str) -> UpstreamAccount | None:
    accounts = session.exec(
        select(UpstreamAccount)
        .where(UpstreamAccount.status == "active")
        .order_by(UpstreamAccount.priority.desc(), UpstreamAccount.total_request_count.asc())
    ).all()
    for account in accounts:
        models = json.loads(account.models_json or "[]")
        if not models or model in models:
            return account
    return None


@router.get("/accounts")
def list_accounts(session: Session = Depends(get_session)) -> list[dict]:
    accounts = session.exec(select(UpstreamAccount).order_by(UpstreamAccount.created_at.desc())).all()
    return [account_to_public(account) for account in accounts]


@router.get("/provider-presets")
def provider_presets() -> list[dict]:
    return PROVIDER_PRESETS


@router.post("/accounts")
def create_account(payload: UpstreamAccountCreate, session: Session = Depends(get_session)) -> dict:
    account = UpstreamAccount(
        provider_type=payload.provider_type,
        label=payload.label,
        base_url=payload.base_url,
        api_key=payload.api_key,
        models_json=json.dumps(payload.models, ensure_ascii=False),
        priority=payload.priority,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account_to_public(account)


@router.post("/accounts/import-login")
def import_login_account(payload: LoginImportRequest, session: Session = Depends(get_session)) -> dict:
    preset = get_provider_preset(payload.provider_type)
    if preset is None:
        raise HTTPException(status_code=400, detail="unsupported provider_type")
    credential = payload.credential.strip()
    if not credential:
        raise HTTPException(status_code=400, detail="credential is required")

    account = UpstreamAccount(
        provider_type=preset["provider_type"],
        label=payload.label or f"{preset['label']} 登录导入",
        base_url=preset["base_url"],
        api_key=credential,
        models_json=json.dumps(payload.models if payload.models is not None else preset["models"], ensure_ascii=False),
        priority=10,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account_to_public(account)


@router.put("/accounts/{account_id}")
def update_account(
    account_id: str,
    payload: UpstreamAccountUpdate,
    session: Session = Depends(get_session),
) -> dict:
    account = session.get(UpstreamAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    update = payload.model_dump(exclude_unset=True)
    if "models" in update:
        account.models_json = json.dumps(update.pop("models") or [], ensure_ascii=False)
    for key, value in update.items():
        setattr(account, key, value)
    account.updated_at = datetime.now(timezone.utc)
    session.add(account)
    session.commit()
    session.refresh(account)
    return account_to_public(account)


@router.patch("/accounts/{account_id}/status")
def update_account_status(
    account_id: str,
    payload: AccountStatusUpdate,
    session: Session = Depends(get_session),
) -> dict:
    if payload.status not in {"active", "disabled"}:
        raise HTTPException(status_code=400, detail="status must be active or disabled")
    account = session.get(UpstreamAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    account.status = payload.status
    account.updated_at = datetime.now(timezone.utc)
    session.add(account)
    session.commit()
    session.refresh(account)
    return account_to_public(account)


@router.delete("/accounts/{account_id}")
def delete_account(account_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    account = session.get(UpstreamAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    session.delete(account)
    session.commit()
    return {"status": "deleted", "id": account_id}


@router.post("/accounts/{account_id}/test")
async def test_account(account_id: str, session: Session = Depends(get_session)) -> dict:
    account = session.get(UpstreamAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    try:
        result = await test_openai_compatible(account)
        account.last_error = None
        account.updated_at = datetime.now(timezone.utc)
        session.add(account)
        session.commit()
        return result
    except RelayError as exc:
        account.last_error = str(exc)
        account.updated_at = datetime.now(timezone.utc)
        session.add(account)
        session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/chat/completions")
async def relay_chat_completion(payload: RelayRunRequest, session: Session = Depends(get_session)) -> dict:
    account = select_account(session, payload.model)
    if account is None:
        raise HTTPException(status_code=400, detail="no active upstream account supports this model")

    log = ModelCallLog(
        task_id=payload.task_id,
        task_step_id=payload.task_step_id,
        role_id=payload.role_id,
        upstream_account_id=account.id,
        provider_type=account.provider_type,
        model=payload.model,
        status="running",
        request_summary=json.dumps({"message_count": len(payload.messages)}, ensure_ascii=False),
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    try:
        result = await run_openai_chat_completion(account, payload.model, payload.messages)
        usage = result["usage"]
        input_tokens = usage["input_tokens"]
        cached_tokens = usage["cached_tokens"]
        cache_hit_rate = cached_tokens / input_tokens if input_tokens > 0 else 0

        account.total_request_count += 1
        account.total_input_tokens += input_tokens
        account.total_output_tokens += usage["output_tokens"]
        account.total_cached_tokens += cached_tokens
        account.last_error = None
        account.last_used_at = datetime.now(timezone.utc)
        account.updated_at = datetime.now(timezone.utc)

        log.status = "success"
        log.input_tokens = input_tokens
        log.output_tokens = usage["output_tokens"]
        log.cached_tokens = cached_tokens
        log.reasoning_tokens = usage["reasoning_tokens"]
        log.total_tokens = usage["total_tokens"]
        log.cache_hit_rate = cache_hit_rate
        log.latency_ms = result["latency_ms"]
        log.response_summary = result["text"][:500]

        session.add(account)
        session.add(log)
        session.commit()
        return {
            "account": account_to_public(account),
            "text": result["text"],
            "usage": usage,
            "log_id": log.id,
        }
    except RelayError as exc:
        account.last_error = str(exc)
        account.updated_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.error_code = str(exc.status_code or "upstream_error")
        log.error_message = str(exc)
        session.add(account)
        session.add(log)
        session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/usage/summary")
def usage_summary(session: Session = Depends(get_session)) -> dict:
    logs = session.exec(select(ModelCallLog)).all()
    accounts = session.exec(select(UpstreamAccount)).all()
    total_input = sum(log.input_tokens for log in logs if log.status == "success")
    total_output = sum(log.output_tokens for log in logs if log.status == "success")
    total_cached = sum(log.cached_tokens for log in logs if log.status == "success")
    success_count = sum(1 for log in logs if log.status == "success")
    failed_count = sum(1 for log in logs if log.status == "failed")

    def grouped(field: str) -> list[dict]:
        rows = session.exec(
            select(
                getattr(ModelCallLog, field),
                func.sum(ModelCallLog.input_tokens),
                func.sum(ModelCallLog.output_tokens),
                func.sum(ModelCallLog.cached_tokens),
                func.count(ModelCallLog.id),
            )
            .where(ModelCallLog.status == "success")
            .group_by(getattr(ModelCallLog, field))
        ).all()
        return [
            {
                "key": key or "unknown",
                "input_tokens": int(input_tokens or 0),
                "output_tokens": int(output_tokens or 0),
                "cached_tokens": int(cached_tokens or 0),
                "request_count": int(request_count or 0),
            }
            for key, input_tokens, output_tokens, cached_tokens, request_count in rows
        ]

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cached_tokens": total_cached,
        "cache_hit_rate": total_cached / total_input if total_input > 0 else 0,
        "total_request_count": success_count + failed_count,
        "success_request_count": success_count,
        "failed_request_count": failed_count,
        "total_accounts": len(accounts),
        "active_accounts": sum(1 for account in accounts if account.status == "active"),
        "by_role": grouped("role_id"),
        "by_task": grouped("task_id"),
        "by_model": grouped("model"),
        "by_account": grouped("upstream_account_id"),
    }


@router.get("/logs")
def relay_logs(session: Session = Depends(get_session)) -> list[dict]:
    logs = session.exec(select(ModelCallLog).order_by(ModelCallLog.created_at.desc()).limit(50)).all()
    return [log.model_dump() for log in logs]
