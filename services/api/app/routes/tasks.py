from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.models import CompanyRole, ModelCallLog, Task, TaskStep
from app.db.session import get_session
from app.relay.client import RelayError, run_openai_chat_completion
from app.routes.relay import account_to_public, select_account


router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    objective: str


class TaskStatusUpdate(BaseModel):
    status: str


class RunRoleRequest(BaseModel):
    objective: str
    model: str
    role_title: str | None = None
    role_prompt: str | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def task_to_public(task: Task, steps: list[TaskStep] | None = None) -> dict:
    payload = task.model_dump()
    if steps is not None:
        payload["steps"] = [step_to_public(step) for step in steps]
        payload["step_count"] = len(steps)
    return payload


def step_to_public(step: TaskStep) -> dict:
    return step.model_dump()


@router.get("")
def list_tasks(session: Session = Depends(get_session)) -> list[dict]:
    tasks = session.exec(select(Task).order_by(Task.created_at.desc())).all()
    payload: list[dict] = []
    for task in tasks:
        steps = session.exec(select(TaskStep).where(TaskStep.task_id == task.id)).all()
        payload.append(task_to_public(task, steps))
    return payload


@router.post("")
def create_task(payload: TaskCreate, session: Session = Depends(get_session)) -> dict:
    task = Task(title=payload.title, objective=payload.objective)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task_to_public(task, [])


@router.get("/{task_id}")
def get_task(task_id: str, session: Session = Depends(get_session)) -> dict:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    steps = session.exec(select(TaskStep).where(TaskStep.task_id == task.id).order_by(TaskStep.created_at.desc())).all()
    return task_to_public(task, steps)


@router.patch("/{task_id}/status")
def update_task_status(task_id: str, payload: TaskStatusUpdate, session: Session = Depends(get_session)) -> dict:
    if payload.status not in {"draft", "running", "in_progress", "done", "failed", "archived"}:
        raise HTTPException(status_code=400, detail="unsupported task status")
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    task.status = payload.status
    task.updated_at = utc_now()
    if payload.status == "running" and task.started_at is None:
        task.started_at = utc_now()
    if payload.status in {"done", "failed", "archived"}:
        task.completed_at = utc_now()
    session.add(task)
    session.commit()
    session.refresh(task)
    steps = session.exec(select(TaskStep).where(TaskStep.task_id == task.id)).all()
    return task_to_public(task, steps)


@router.post("/{task_id}/run")
def run_task(task_id: str, session: Session = Depends(get_session)) -> dict:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    task.status = "running"
    task.started_at = task.started_at or utc_now()
    task.updated_at = utc_now()
    session.add(task)
    session.commit()
    return {"task_id": task_id, "status": task.status}


@router.post("/{task_id}/run-role/{role_id}")
async def run_role(
    task_id: str,
    role_id: str,
    payload: RunRoleRequest,
    session: Session = Depends(get_session),
) -> dict:
    account = select_account(session, payload.model)
    if account is None:
        raise HTTPException(status_code=400, detail="no active upstream account supports this model")

    role = session.get(CompanyRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="role not found")

    task = session.get(Task, task_id)
    if task is None:
        task = Task(id=task_id, title=payload.objective[:40] or "临时任务", objective=payload.objective, status="running")
        session.add(task)
        session.commit()
        session.refresh(task)

    role_title = role.title or payload.role_title or role_id
    role_prompt = role.prompt or payload.role_prompt or "请输出你的岗位执行结果，并尽量使用清晰的小标题和可执行条目。"

    task.status = "running"
    task.started_at = task.started_at or utc_now()
    task.updated_at = utc_now()

    step = TaskStep(
        task_id=task.id,
        role_id=role_id,
        role_title=role_title,
        status="running",
        objective=payload.objective,
    )
    session.add(task)
    session.add(step)
    session.commit()
    session.refresh(step)

    messages = [
        {"role": "system", "content": role_prompt},
        {
            "role": "user",
            "content": (
                f"任务 ID: {task.id}\n"
                f"岗位: {role_title}\n"
                f"Boss 目标: {payload.objective}\n\n"
                "请输出你的岗位执行结果，并尽量使用清晰的小标题和可执行条目。"
            ),
        },
    ]

    try:
        result = await run_openai_chat_completion(account, payload.model, messages)
    except RelayError as exc:
        log = ModelCallLog(
            task_id=task.id,
            task_step_id=step.id,
            role_id=role_id,
            upstream_account_id=account.id,
            provider_type=account.provider_type,
            model=payload.model,
            status="failed",
            error_code=str(exc.status_code or "upstream_error"),
            error_message=str(exc),
            request_summary=f"role={role_title}",
        )
        task.status = "failed"
        task.updated_at = utc_now()
        step.status = "failed"
        step.error_message = str(exc)
        step.updated_at = utc_now()
        step.completed_at = utc_now()
        account.last_error = str(exc)
        account.updated_at = utc_now()
        session.add(log)
        session.add(task)
        session.add(step)
        session.add(account)
        session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    usage = result["usage"]
    cache_hit_rate = usage["cached_tokens"] / usage["input_tokens"] if usage["input_tokens"] > 0 else 0
    account.total_request_count += 1
    account.total_input_tokens += usage["input_tokens"]
    account.total_output_tokens += usage["output_tokens"]
    account.total_cached_tokens += usage["cached_tokens"]
    account.last_error = None
    account.last_used_at = utc_now()
    account.updated_at = utc_now()

    log = ModelCallLog(
        task_id=task.id,
        task_step_id=step.id,
        role_id=role_id,
        upstream_account_id=account.id,
        provider_type=account.provider_type,
        model=payload.model,
        status="success",
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
        reasoning_tokens=usage["reasoning_tokens"],
        total_tokens=usage["total_tokens"],
        cache_hit_rate=cache_hit_rate,
        latency_ms=result["latency_ms"],
        request_summary=f"role={role_title}",
        response_summary=result["text"][:500],
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    task.status = "in_progress"
    task.result_summary = result["text"][:500]
    task.updated_at = utc_now()
    step.status = "success"
    step.output = result["text"]
    step.log_id = log.id
    step.input_tokens = usage["input_tokens"]
    step.output_tokens = usage["output_tokens"]
    step.cached_tokens = usage["cached_tokens"]
    step.total_tokens = usage["total_tokens"]
    step.updated_at = utc_now()
    step.completed_at = utc_now()

    session.add(account)
    session.add(task)
    session.add(step)
    session.commit()
    session.refresh(task)
    session.refresh(step)

    return {
        "task_id": task.id,
        "role_id": role_id,
        "role_title": role_title,
        "account": account_to_public(account),
        "output": result["text"],
        "usage": usage,
        "log_id": log.id,
        "step": step_to_public(step),
        "task": task_to_public(task, [step]),
    }
