from datetime import datetime, timezone
from typing import ClassVar
from uuid import uuid4

from sqlmodel import Field, SQLModel


def new_id() -> str:
    return uuid4().hex


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class UpstreamAccount(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    provider_type: str = "openai_compatible"
    label: str
    base_url: str
    api_key: str
    models_json: str = "[]"
    status: str = "active"
    priority: int = 0
    total_request_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    last_error: str | None = None
    last_used_at: datetime | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Workspace(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    path: str
    description: str = ""
    status: str = "active"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CompanyRole(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    title: str
    department: str
    level: str = "L3"
    responsibility: str
    prompt: str
    enabled: bool = True
    sort_order: int = 0
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Task(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    title: str
    objective: str
    status: str = Field(default="draft", index=True)
    priority: int = 0
    result_summary: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskStep(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    task_id: str = Field(index=True)
    role_id: str = Field(index=True)
    role_title: str
    status: str = Field(default="queued", index=True)
    objective: str = ""
    output: str = ""
    log_id: str | None = Field(default=None, index=True)
    error_message: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    completed_at: datetime | None = None


class AgentSession(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    workspace_id: str = Field(index=True)
    title: str
    objective: str
    status: str = Field(default="idle", index=True)
    mode: str = "round_robin"
    model: str = "gpt-4o-mini"
    role_ids_json: str = "[]"
    next_role_index: int = 0
    tick_interval_seconds: int = 15
    last_tick_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    started_at: datetime | None = None
    paused_at: datetime | None = None
    stopped_at: datetime | None = None


class AgentSessionEvent(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(index=True)
    role_id: str | None = Field(default=None, index=True)
    role_title: str | None = None
    kind: str = Field(default="message", index=True)
    content: str = ""
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=now_utc)


class AgentWorkerRun(SQLModel, table=True):
    __tablename__: ClassVar[str] = "agent_worker_runs"

    id: str = Field(default_factory=new_id, primary_key=True)
    workspace_id: str = Field(index=True)
    session_id: str = Field(index=True)
    role_id: str | None = Field(default=None, index=True)
    role_title: str | None = None
    status: str = Field(default="running", index=True)
    cwd: str
    model: str
    upstream_account_id: str | None = Field(default=None, index=True)
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    output: str = ""
    error_message: str | None = None
    metadata_json: str = "{}"
    started_at: datetime = Field(default_factory=now_utc)
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class RoleProcessConfig(SQLModel, table=True):
    __tablename__: ClassVar[str] = "role_process_configs"

    id: str = Field(default_factory=new_id, primary_key=True)
    role_id: str = Field(index=True)
    shell_type: str = "powershell"
    command: str = ""
    args: str = ""
    enabled: bool = True
    auto_restart: bool = False
    env_json: str = "{}"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class AgentProcess(SQLModel, table=True):
    __tablename__: ClassVar[str] = "agent_processes"

    id: str = Field(default_factory=new_id, primary_key=True)
    workspace_id: str = Field(index=True)
    session_id: str | None = Field(default=None, index=True)
    role_id: str = Field(index=True)
    role_title: str = ""
    shell_type: str = "powershell"
    command: str
    args: str = ""
    cwd: str
    pid: int | None = None
    status: str = Field(default="starting", index=True)
    exit_code: int | None = None
    last_error: str | None = None
    started_at: datetime = Field(default_factory=now_utc)
    stopped_at: datetime | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class AgentProcessLog(SQLModel, table=True):
    __tablename__: ClassVar[str] = "agent_process_logs"

    id: str = Field(default_factory=new_id, primary_key=True)
    process_id: str = Field(index=True)
    stream: str = Field(default="stdout", index=True)
    content: str = ""
    created_at: datetime = Field(default_factory=now_utc)


class ModelCallLog(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    task_id: str | None = Field(default=None, index=True)
    task_step_id: str | None = Field(default=None, index=True)
    role_id: str | None = Field(default=None, index=True)
    upstream_account_id: str | None = Field(default=None, index=True)
    provider_type: str = "openai_compatible"
    model: str
    status: str
    request_id: str | None = None
    upstream_request_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cache_hit_rate: float = 0
    latency_ms: int = 0
    is_stream: bool = False
    error_code: str | None = None
    error_message: str | None = None
    request_summary: str = ""
    response_summary: str = ""
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=now_utc)


class UsageSnapshot(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    captured_at: datetime = Field(default_factory=now_utc, index=True)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    total_reasoning_tokens: int = 0
    total_request_count: int = 0
    total_error_count: int = 0
    active_accounts: int = 0
    total_accounts: int = 0
