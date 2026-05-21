import asyncio
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db.models import AgentSession, AgentSessionEvent, AgentWorkerRun, CompanyRole, ModelCallLog, UpstreamAccount, Workspace
from app.db.session import engine, get_session
from app.relay.client import RelayError, run_openai_chat_completion
from app.routes.relay import account_to_public, select_account


router = APIRouter()

PROJECT_ROOT = str(Path(__file__).resolve().parents[4])
RUNNER_STOP_FLAGS: dict[str, threading.Event] = {}
RUNNER_THREADS: dict[str, threading.Thread] = {}


class WorkspaceCreate(BaseModel):
    name: str
    path: str = PROJECT_ROOT
    description: str = ""


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    path: str | None = None
    description: str | None = None
    status: str | None = None


class WorkspaceActivate(BaseModel):
    path: str
    name: str | None = None
    source: str = "cli"


class SessionCreate(BaseModel):
    workspace_id: str
    title: str
    objective: str
    model: str = "gpt-4o-mini"
    role_ids: list[str] = Field(default_factory=list)
    mode: str = "round_robin"
    tick_interval_seconds: int = 15


class SessionUpdate(BaseModel):
    title: str | None = None
    objective: str | None = None
    model: str | None = None
    role_ids: list[str] | None = None
    mode: str | None = None
    tick_interval_seconds: int | None = None


class SessionStatusUpdate(BaseModel):
    status: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def seed_default_workspace(session: Session) -> None:
    existing = session.exec(select(Workspace)).first()
    if existing is not None:
        return
    workspace = Workspace(
        name="默认工作区",
        path=PROJECT_ROOT,
        description="AI Company 当前目录工作区",
    )
    session.add(workspace)
    session.commit()


def seed_default_session(session: Session, workspace_id: str) -> None:
    existing = session.exec(select(AgentSession)).first()
    if existing is not None:
        return
    role_ids = [role.id for role in session.exec(select(CompanyRole).where(CompanyRole.enabled == True)).all()]  # noqa: E712
    agent_session = AgentSession(
        workspace_id=workspace_id,
        title="默认协作会话",
        objective="把当前目录里的 AI Company 持续运行起来。",
        role_ids_json=json.dumps(role_ids, ensure_ascii=False),
        model="gpt-4o-mini",
        mode="round_robin",
    )
    session.add(agent_session)
    session.commit()


def ensure_seed_data(session: Session) -> Workspace:
    seed_default_workspace(session)
    workspace = session.exec(select(Workspace).order_by(Workspace.created_at.asc())).first()
    if workspace is None:
        raise RuntimeError("workspace seeding failed")
    seed_default_session(session, workspace.id)
    return workspace


def workspace_to_public(workspace: Workspace) -> dict:
    return workspace.model_dump()


def normalize_workspace_path(path: str) -> str:
    clean = path.strip().strip('"')
    if not clean:
        raise HTTPException(status_code=400, detail="path is required")
    return str(Path(clean).expanduser().resolve())


def default_workspace_name(path: str) -> str:
    name = Path(path).name
    return name or path


def activate_workspace_by_path(session: Session, path: str, name: str | None = None, source: str = "cli") -> Workspace:
    normalized_path = normalize_workspace_path(path)
    workspaces = session.exec(select(Workspace)).all()
    workspace = next((item for item in workspaces if normalize_workspace_path(item.path) == normalized_path), None)
    now = utc_now()
    if workspace is None:
        workspace = Workspace(
            name=name or default_workspace_name(normalized_path),
            path=normalized_path,
            description=f"由 {source} 激活的工作区",
            status="active",
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        workspaces = session.exec(select(Workspace)).all()
    else:
        if name:
            workspace.name = name
        workspace.path = normalized_path
        workspace.status = "active"
        workspace.updated_at = now
        session.add(workspace)

    for item in workspaces:
        if item.id != workspace.id and item.status == "active":
            item.status = "idle"
            item.updated_at = now
            session.add(item)
    session.commit()
    session.refresh(workspace)
    return workspace


def role_ids_for_session(agent_session: AgentSession) -> list[str]:
    try:
        data = json.loads(agent_session.role_ids_json or "[]")
        return [item for item in data if isinstance(item, str)]
    except json.JSONDecodeError:
        return []


def session_to_public(
    agent_session: AgentSession,
    roles: list[CompanyRole] | None = None,
    event_count: int | None = None,
    worker_run_count: int | None = None,
) -> dict:
    payload = agent_session.model_dump()
    payload["role_ids"] = role_ids_for_session(agent_session)
    payload["role_count"] = len(payload["role_ids"])
    payload["roles"] = [role.model_dump() for role in roles] if roles is not None else []
    if event_count is not None:
        payload["event_count"] = event_count
    if worker_run_count is not None:
        payload["worker_run_count"] = worker_run_count
    return payload


def event_to_public(event: AgentSessionEvent) -> dict:
    return event.model_dump()


def worker_run_to_public(worker_run: AgentWorkerRun) -> dict:
    return worker_run.model_dump()


def get_session_roles(session: Session, agent_session: AgentSession) -> list[CompanyRole]:
    role_ids = role_ids_for_session(agent_session)
    if role_ids:
        roles: list[CompanyRole] = []
        for role_id in role_ids:
            role = session.get(CompanyRole, role_id)
            if role is not None and role.enabled:
                roles.append(role)
        return roles
    return session.exec(
        select(CompanyRole)
        .where(CompanyRole.enabled == True)  # noqa: E712
        .order_by(CompanyRole.sort_order.asc(), CompanyRole.created_at.asc())
    ).all()


def append_event(
    session: Session,
    session_id: str,
    kind: str,
    content: str,
    role_id: str | None = None,
    role_title: str | None = None,
    metadata: dict | None = None,
) -> AgentSessionEvent:
    event = AgentSessionEvent(
        session_id=session_id,
        role_id=role_id,
        role_title=role_title,
        kind=kind,
        content=content,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def build_messages(
    agent_session: AgentSession,
    role: CompanyRole,
    events: list[AgentSessionEvent],
    workspace: Workspace,
) -> list[dict]:
    recent_lines = []
    for event in events[-6:]:
        prefix = event.role_title or event.kind
        recent_lines.append(f"{prefix}: {event.content}")
    context_text = "\n".join(recent_lines) if recent_lines else "暂无历史上下文。"
    system_prompt = (
        f"{role.prompt}\n\n"
        f"工作区目标: {agent_session.objective}\n"
        f"工作区名称: {workspace.name}\n"
        f"工作区 cwd: {workspace.path}\n"
        f"当前会话模式: {agent_session.mode}\n"
        "你正在一个持续运行的多 agent 工作区中协作。后续涉及文件或命令时，必须以这个 cwd 作为运行边界。"
    )
    user_prompt = (
        f"会话 ID: {agent_session.id}\n"
        f"工作区目标: {agent_session.objective}\n"
        f"工作区 cwd: {workspace.path}\n"
        f"当前角色: {role.title}\n\n"
        f"最近上下文:\n{context_text}\n\n"
        "请给出你这一轮的输出，并尽量说明你需要交接给下一位角色的内容。"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def run_session_tick(session_id: str) -> dict | None:
    worker_run_id: str | None = None
    account_id: str | None = None
    account_provider_type = "openai_compatible"
    with Session(engine) as db:
        agent_session = db.get(AgentSession, session_id)
        if agent_session is None or agent_session.status != "running":
            return None
        workspace = db.get(Workspace, agent_session.workspace_id)
        if workspace is None:
            agent_session.status = "failed"
            agent_session.last_error = "workspace not found"
            agent_session.updated_at = utc_now()
            db.add(agent_session)
            db.commit()
            return None

        roles = get_session_roles(db, agent_session)
        if not roles:
            agent_session.status = "failed"
            agent_session.last_error = "no enabled roles in workspace"
            agent_session.updated_at = utc_now()
            db.add(agent_session)
            db.commit()
            return None

        role = roles[agent_session.next_role_index % len(roles)]
        account = select_account(db, agent_session.model)
        if account is None:
            agent_session.status = "failed"
            agent_session.last_error = "no active upstream account supports session model"
            agent_session.updated_at = utc_now()
            db.add(agent_session)
            db.commit()
            return None
        account_id = account.id
        account_provider_type = account.provider_type

        events = db.exec(
            select(AgentSessionEvent)
            .where(AgentSessionEvent.session_id == session_id)
            .order_by(AgentSessionEvent.created_at.asc())
        ).all()
        messages = build_messages(agent_session, role, events, workspace)
        worker_run = AgentWorkerRun(
            workspace_id=workspace.id,
            session_id=session_id,
            role_id=role.id,
            role_title=role.title,
            status="running",
            cwd=workspace.path,
            model=agent_session.model,
            upstream_account_id=account.id,
            metadata_json=json.dumps(
                {
                    "mode": agent_session.mode,
                    "next_role_index": agent_session.next_role_index,
                },
                ensure_ascii=False,
            ),
        )
        db.add(worker_run)
        db.commit()
        db.refresh(worker_run)
        worker_run_id = worker_run.id
        append_event(
            db,
            session_id,
            "turn_start",
            f"{role.title} 开始在 {workspace.path} 执行",
            role.id,
            role.title,
            {"model": agent_session.model, "cwd": workspace.path, "worker_run_id": worker_run_id},
        )

    try:
        result = await run_openai_chat_completion(account, agent_session.model, messages)
    except RelayError as exc:
        with Session(engine) as db:
            agent_session = db.get(AgentSession, session_id)
            if agent_session is not None:
                agent_session.status = "failed"
                agent_session.last_error = str(exc)
                agent_session.updated_at = utc_now()
                db.add(agent_session)
            if worker_run_id is not None:
                worker_run = db.get(AgentWorkerRun, worker_run_id)
                if worker_run is not None:
                    worker_run.status = "failed"
                    worker_run.error_message = str(exc)
                    worker_run.finished_at = utc_now()
                    worker_run.updated_at = utc_now()
                    db.add(worker_run)
            if account_id is not None:
                account_record = db.get(UpstreamAccount, account_id)
                if account_record is not None:
                    account_record.last_error = str(exc)
                    account_record.updated_at = utc_now()
                    db.add(account_record)
            log = ModelCallLog(
                role_id=role.id,
                upstream_account_id=account_id,
                provider_type=account_provider_type,
                model=agent_session.model,
                status="failed",
                error_code=str(exc.status_code or "upstream_error"),
                error_message=str(exc),
                request_summary=json.dumps({"session_id": session_id, "worker_run_id": worker_run_id}, ensure_ascii=False),
                metadata_json=json.dumps({"session_id": session_id, "worker_run_id": worker_run_id}, ensure_ascii=False),
            )
            db.add(log)
            append_event(
                db,
                session_id,
                "error",
                str(exc),
                role.id,
                role.title,
                {"status_code": exc.status_code, "worker_run_id": worker_run_id},
            )
            db.commit()
        return None

    with Session(engine) as db:
        agent_session = db.get(AgentSession, session_id)
        if agent_session is None:
            return None
        usage = result["usage"]
        agent_session.next_role_index = (agent_session.next_role_index + 1) % len(roles)
        agent_session.last_tick_at = utc_now()
        agent_session.last_error = None
        agent_session.updated_at = utc_now()
        db.add(agent_session)
        if worker_run_id is not None:
            worker_run = db.get(AgentWorkerRun, worker_run_id)
            if worker_run is not None:
                worker_run.status = "success"
                worker_run.input_tokens = usage["input_tokens"]
                worker_run.output_tokens = usage["output_tokens"]
                worker_run.cached_tokens = usage["cached_tokens"]
                worker_run.total_tokens = usage["total_tokens"]
                worker_run.output = result["text"][:2000]
                worker_run.finished_at = utc_now()
                worker_run.updated_at = utc_now()
                db.add(worker_run)
        if account_id is not None:
            account_record = db.get(UpstreamAccount, account_id)
            if account_record is not None:
                account_record.total_request_count += 1
                account_record.total_input_tokens += usage["input_tokens"]
                account_record.total_output_tokens += usage["output_tokens"]
                account_record.total_cached_tokens += usage["cached_tokens"]
                account_record.last_error = None
                account_record.last_used_at = utc_now()
                account_record.updated_at = utc_now()
                db.add(account_record)
        log = ModelCallLog(
            role_id=role.id,
            upstream_account_id=account_id,
            provider_type=account_provider_type,
            model=agent_session.model,
            status="success",
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
            reasoning_tokens=usage["reasoning_tokens"],
            total_tokens=usage["total_tokens"],
            cache_hit_rate=usage["cached_tokens"] / usage["input_tokens"] if usage["input_tokens"] > 0 else 0,
            response_summary=result["text"][:500],
            request_summary=json.dumps({"session_id": session_id, "worker_run_id": worker_run_id}, ensure_ascii=False),
            metadata_json=json.dumps(
                {
                    "session_id": session_id,
                    "worker_run_id": worker_run_id,
                    "workspace_id": agent_session.workspace_id,
                    "cwd": worker_run.cwd if worker_run_id is not None and worker_run is not None else None,
                },
                ensure_ascii=False,
            ),
        )
        db.add(log)
        append_event(
            db,
            session_id,
            "message",
            result["text"],
            role.id,
            role.title,
            {"usage": usage, "account": account_to_public(account), "worker_run_id": worker_run_id},
        )
        db.commit()
        return {
            "session_id": session_id,
            "worker_run_id": worker_run_id,
            "role_id": role.id,
            "role_title": role.title,
            "cwd": worker_run.cwd if worker_run_id is not None and worker_run is not None else None,
            "account": account_to_public(account),
            "usage": usage,
            "output": result["text"],
        }


def session_loop(session_id: str) -> None:
    stop_flag = RUNNER_STOP_FLAGS.setdefault(session_id, threading.Event())
    while not stop_flag.is_set():
        with Session(engine) as db:
            agent_session = db.get(AgentSession, session_id)
            if agent_session is None or agent_session.status != "running":
                break
            interval = max(3, agent_session.tick_interval_seconds)
        asyncio.run(run_session_tick(session_id))
        with Session(engine) as db:
            agent_session = db.get(AgentSession, session_id)
            if agent_session is None or agent_session.status != "running":
                break
            interval = max(3, agent_session.tick_interval_seconds)
        stop_flag.wait(interval)


def launch_runner(session_id: str) -> None:
    thread = RUNNER_THREADS.get(session_id)
    if thread and thread.is_alive():
        return
    stop_flag = RUNNER_STOP_FLAGS.setdefault(session_id, threading.Event())
    stop_flag.clear()
    thread = threading.Thread(target=session_loop, args=(session_id,), daemon=True)
    RUNNER_THREADS[session_id] = thread
    thread.start()


def stop_runner(session_id: str) -> None:
    flag = RUNNER_STOP_FLAGS.get(session_id)
    if flag is not None:
        flag.set()


@router.get("")
def list_workspaces(session: Session = Depends(get_session)) -> list[dict]:
    ensure_seed_data(session)
    workspaces = session.exec(select(Workspace).order_by(Workspace.created_at.desc())).all()
    return [workspace_to_public(workspace) for workspace in workspaces]


@router.post("")
def create_workspace(payload: WorkspaceCreate, session: Session = Depends(get_session)) -> dict:
    workspace = Workspace(**payload.model_dump())
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace_to_public(workspace)


@router.get("/active")
def get_active_workspace(session: Session = Depends(get_session)) -> dict:
    ensure_seed_data(session)
    workspace = session.exec(
        select(Workspace)
        .where(Workspace.status == "active")
        .order_by(Workspace.updated_at.desc(), Workspace.created_at.desc())
    ).first()
    if workspace is None:
        workspace = session.exec(select(Workspace).order_by(Workspace.created_at.desc())).first()
    if workspace is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    return workspace_to_public(workspace)


@router.post("/activate")
def activate_workspace(payload: WorkspaceActivate, session: Session = Depends(get_session)) -> dict:
    ensure_seed_data(session)
    workspace = activate_workspace_by_path(session, payload.path, payload.name, payload.source)
    return workspace_to_public(workspace)


@router.get("/worker-runs")
def list_worker_runs(
    workspace_id: str | None = None,
    session_id: str | None = None,
    limit: int = 30,
    session: Session = Depends(get_session),
) -> list[dict]:
    query = select(AgentWorkerRun)
    if workspace_id:
        query = query.where(AgentWorkerRun.workspace_id == workspace_id)
    if session_id:
        query = query.where(AgentWorkerRun.session_id == session_id)
    worker_runs = session.exec(
        query.order_by(AgentWorkerRun.created_at.desc()).limit(max(1, min(limit, 100)))
    ).all()
    return [worker_run_to_public(worker_run) for worker_run in worker_runs]


@router.put("/{workspace_id}")
def update_workspace(workspace_id: str, payload: WorkspaceUpdate, session: Session = Depends(get_session)) -> dict:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    update = payload.model_dump(exclude_unset=True)
    for key, value in update.items():
        setattr(workspace, key, value)
    workspace.updated_at = utc_now()
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace_to_public(workspace)


@router.get("/sessions")
def list_sessions(workspace_id: str | None = None, session: Session = Depends(get_session)) -> list[dict]:
    ensure_seed_data(session)
    query = select(AgentSession)
    if workspace_id:
        query = query.where(AgentSession.workspace_id == workspace_id)
    sessions = session.exec(query.order_by(AgentSession.created_at.desc())).all()
    payload: list[dict] = []
    for agent_session in sessions:
        roles = get_session_roles(session, agent_session)
        events = session.exec(select(AgentSessionEvent).where(AgentSessionEvent.session_id == agent_session.id)).all()
        worker_runs = session.exec(select(AgentWorkerRun).where(AgentWorkerRun.session_id == agent_session.id)).all()
        payload.append(session_to_public(agent_session, roles, len(events), len(worker_runs)))
    return payload


@router.post("/sessions")
def create_session(payload: SessionCreate, session: Session = Depends(get_session)) -> dict:
    workspace = session.get(Workspace, payload.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    agent_session = AgentSession(
        workspace_id=payload.workspace_id,
        title=payload.title,
        objective=payload.objective,
        model=payload.model,
        role_ids_json=json.dumps(payload.role_ids, ensure_ascii=False),
        mode=payload.mode,
        tick_interval_seconds=payload.tick_interval_seconds,
    )
    session.add(agent_session)
    session.commit()
    session.refresh(agent_session)
    roles = get_session_roles(session, agent_session)
    return session_to_public(agent_session, roles, 0)


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str, session: Session = Depends(get_session)) -> dict:
    agent_session = session.get(AgentSession, session_id)
    if agent_session is None:
        raise HTTPException(status_code=404, detail="session not found")
    roles = get_session_roles(session, agent_session)
    events = session.exec(
        select(AgentSessionEvent)
        .where(AgentSessionEvent.session_id == session_id)
        .order_by(AgentSessionEvent.created_at.desc())
    ).all()
    worker_runs = session.exec(
        select(AgentWorkerRun)
        .where(AgentWorkerRun.session_id == session_id)
        .order_by(AgentWorkerRun.created_at.desc())
        .limit(12)
    ).all()
    payload = session_to_public(agent_session, roles, len(events), len(worker_runs))
    payload["events"] = [event_to_public(event) for event in events]
    payload["worker_runs"] = [worker_run_to_public(worker_run) for worker_run in worker_runs]
    return payload


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, payload: SessionUpdate, session: Session = Depends(get_session)) -> dict:
    agent_session = session.get(AgentSession, session_id)
    if agent_session is None:
        raise HTTPException(status_code=404, detail="session not found")
    update = payload.model_dump(exclude_unset=True)
    if "role_ids" in update:
        agent_session.role_ids_json = json.dumps(update.pop("role_ids") or [], ensure_ascii=False)
    for key, value in update.items():
        setattr(agent_session, key, value)
    agent_session.updated_at = utc_now()
    session.add(agent_session)
    session.commit()
    session.refresh(agent_session)
    roles = get_session_roles(session, agent_session)
    return session_to_public(agent_session, roles)


@router.patch("/sessions/{session_id}/status")
def update_session_status(session_id: str, payload: SessionStatusUpdate, session: Session = Depends(get_session)) -> dict:
    agent_session = session.get(AgentSession, session_id)
    if agent_session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if payload.status not in {"idle", "running", "paused", "stopped", "failed", "completed"}:
        raise HTTPException(status_code=400, detail="unsupported status")
    agent_session.status = payload.status
    now = utc_now()
    if payload.status == "running" and agent_session.started_at is None:
        agent_session.started_at = now
    if payload.status == "paused":
        agent_session.paused_at = now
    if payload.status in {"stopped", "completed"}:
        agent_session.stopped_at = now
        stop_runner(session_id)
    agent_session.updated_at = now
    session.add(agent_session)
    session.commit()
    session.refresh(agent_session)
    roles = get_session_roles(session, agent_session)
    return session_to_public(agent_session, roles)


@router.post("/sessions/{session_id}/start")
def start_session(session_id: str, session: Session = Depends(get_session)) -> dict:
    agent_session = session.get(AgentSession, session_id)
    if agent_session is None:
        raise HTTPException(status_code=404, detail="session not found")
    agent_session.status = "running"
    agent_session.started_at = agent_session.started_at or utc_now()
    agent_session.updated_at = utc_now()
    session.add(agent_session)
    session.commit()
    launch_runner(session_id)
    roles = get_session_roles(session, agent_session)
    return session_to_public(agent_session, roles)


@router.post("/sessions/{session_id}/pause")
def pause_session(session_id: str, session: Session = Depends(get_session)) -> dict:
    agent_session = session.get(AgentSession, session_id)
    if agent_session is None:
        raise HTTPException(status_code=404, detail="session not found")
    agent_session.status = "paused"
    agent_session.paused_at = utc_now()
    agent_session.updated_at = utc_now()
    session.add(agent_session)
    session.commit()
    stop_runner(session_id)
    roles = get_session_roles(session, agent_session)
    return session_to_public(agent_session, roles)


@router.post("/sessions/{session_id}/stop")
def stop_session(session_id: str, session: Session = Depends(get_session)) -> dict:
    agent_session = session.get(AgentSession, session_id)
    if agent_session is None:
        raise HTTPException(status_code=404, detail="session not found")
    agent_session.status = "stopped"
    agent_session.stopped_at = utc_now()
    agent_session.updated_at = utc_now()
    session.add(agent_session)
    session.commit()
    stop_runner(session_id)
    roles = get_session_roles(session, agent_session)
    return session_to_public(agent_session, roles)


@router.post("/sessions/{session_id}/tick")
async def tick_session(session_id: str) -> dict:
    result = await run_session_tick(session_id)
    if result is None:
      raise HTTPException(status_code=400, detail="session is not runnable")
    return result


@router.get("/sessions/{session_id}/events")
def list_session_events(session_id: str, session: Session = Depends(get_session)) -> list[dict]:
    events = session.exec(
        select(AgentSessionEvent)
        .where(AgentSessionEvent.session_id == session_id)
        .order_by(AgentSessionEvent.created_at.desc())
    ).all()
    return [event_to_public(event) for event in events]
