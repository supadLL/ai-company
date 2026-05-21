import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  Building2,
  ClipboardList,
  Cpu,
  DatabaseZap,
  ExternalLink,
  FileText,
  Gauge,
  KeyRound,
  LogIn,
  Network,
  Play,
  Power,
  Radar,
  RefreshCw,
  Settings,
  ShieldCheck,
  TerminalSquare,
  Trash2,
  Users,
  X,
  Zap
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8787";
const DEFAULT_WORKSPACE_PATH = "D:\\桌面\\play\\ai-company";
const ACTIVE_WORKSPACE_KEY = "ai-company.active-workspace-id";

type PageId = "tasks" | "fuel" | "organization" | "workspaces" | "roles" | "logs" | "settings";

type Account = {
  id: string;
  label: string;
  provider_type: string;
  base_url: string;
  api_key_masked: string;
  models: string[];
  status: string;
  total_request_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_tokens: number;
  last_error?: string | null;
};

type ProviderPreset = {
  id: string;
  label: string;
  provider_type: string;
  base_url: string;
  models: string[];
  auth_url: string;
  auth_modes: string[];
  description: string;
};

type UsageSummary = {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_tokens: number;
  cache_hit_rate: number;
  total_request_count: number;
  success_request_count: number;
  failed_request_count: number;
  total_accounts: number;
  active_accounts: number;
};

type CallLog = {
  id: string;
  role_id?: string | null;
  task_id?: string | null;
  model: string;
  status: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  latency_ms: number;
  error_message?: string | null;
  response_summary: string;
  created_at: string;
};

type TaskStep = {
  id: string;
  task_id: string;
  role_id: string;
  role_title: string;
  status: string;
  output: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  total_tokens: number;
  created_at: string;
};

type TaskItem = {
  id: string;
  title: string;
  objective: string;
  status: string;
  result_summary: string;
  created_at: string;
  steps?: TaskStep[];
  step_count?: number;
};

type Workspace = {
  id: string;
  name: string;
  path: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type Role = {
  id: string;
  title: string;
  department: string;
  level: string;
  responsibility: string;
  prompt: string;
  enabled: boolean;
  sort_order?: number;
};

type SessionEvent = {
  id: string;
  session_id: string;
  role_id?: string | null;
  role_title?: string | null;
  kind: string;
  content: string;
  metadata_json: string;
  created_at: string;
};

type AgentWorkerRun = {
  id: string;
  workspace_id: string;
  session_id: string;
  role_id?: string | null;
  role_title?: string | null;
  status: string;
  cwd: string;
  model: string;
  upstream_account_id?: string | null;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  total_tokens: number;
  output: string;
  error_message?: string | null;
  started_at: string;
  finished_at?: string | null;
  created_at: string;
};

type AgentSession = {
  id: string;
  workspace_id: string;
  title: string;
  objective: string;
  status: string;
  mode: string;
  model: string;
  role_ids: string[];
  role_count: number;
  roles: Role[];
  event_count: number;
  worker_run_count?: number;
  next_role_index: number;
  tick_interval_seconds: number;
  last_tick_at?: string | null;
  last_error?: string | null;
  events?: SessionEvent[];
  worker_runs?: AgentWorkerRun[];
};

type RoleForm = {
  id: string;
  title: string;
  department: string;
  level: string;
  responsibility: string;
  prompt: string;
  enabled: boolean;
  sort_order: number;
};

type RoleResult = {
  output: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
    cached_tokens: number;
    reasoning_tokens: number;
    total_tokens: number;
  };
  account: Account;
};

const navItems: Array<{ id: PageId; label: string; icon: typeof ClipboardList }> = [
  { id: "tasks", label: "任务大厅", icon: ClipboardList },
  { id: "fuel", label: "燃料中心", icon: DatabaseZap },
  { id: "organization", label: "组织架构", icon: Network },
  { id: "workspaces", label: "工作区", icon: Building2 },
  { id: "roles", label: "岗位配置", icon: Users },
  { id: "logs", label: "调用日志", icon: TerminalSquare },
  { id: "settings", label: "设置中心", icon: Settings }
];

const defaultSummary: UsageSummary = {
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_cached_tokens: 0,
  cache_hit_rate: 0,
  total_request_count: 0,
  success_request_count: 0,
  failed_request_count: 0,
  total_accounts: 0,
  active_accounts: 0
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("zh-CN").format(Math.round(value || 0));
}

function statusText(status: string) {
  const map: Record<string, string> = {
    draft: "草稿",
    running: "运行中",
    in_progress: "推进中",
    success: "成功",
    failed: "失败",
    done: "完成",
    archived: "归档",
    active: "启用",
    disabled: "停用",
    idle: "待机",
    paused: "暂停",
    stopped: "停止",
    completed: "完成"
  };
  return map[status] ?? status;
}

function emptyRoleForm(): RoleForm {
  return {
    id: "",
    title: "",
    department: "管理层",
    level: "L3",
    responsibility: "",
    prompt: "",
    enabled: true,
    sort_order: 100
  };
}

function roleToForm(role: Role): RoleForm {
  return {
    id: role.id,
    title: role.title,
    department: role.department,
    level: role.level,
    responsibility: role.responsibility,
    prompt: role.prompt,
    enabled: role.enabled,
    sort_order: role.sort_order ?? 0
  };
}

function findWorkspaceByQuery(workspaces: Workspace[], query: string) {
  const needle = query.trim().toLowerCase();
  return workspaces.find((workspace) => {
    const haystack = `${workspace.id} ${workspace.name} ${workspace.path}`.toLowerCase();
    return haystack.includes(needle);
  });
}

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function App() {
  const [activePage, setActivePage] = useState<PageId>("workspaces");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [summary, setSummary] = useState<UsageSummary>(defaultSummary);
  const [logs, setLogs] = useState<CallLog[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [activeWorkspaceId, setActiveWorkspaceId] = useState("");
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [selectedRoleId, setSelectedRoleId] = useState("general-manager");
  const [editingRoleId, setEditingRoleId] = useState("");
  const [roleEditorOpen, setRoleEditorOpen] = useState(false);
  const [roleForm, setRoleForm] = useState<RoleForm>(() => emptyRoleForm());
  const [workspaceCommand, setWorkspaceCommand] = useState("star ai-company");
  const [status, setStatus] = useState("等待连接本地 API");
  const [busy, setBusy] = useState(false);
  const [roleResult, setRoleResult] = useState<RoleResult | null>(null);
  const [providerPresets, setProviderPresets] = useState<ProviderPreset[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState("openai");
  const [fuelForm, setFuelForm] = useState({
    provider_type: "openai",
    label: "OpenAI Compatible",
    base_url: "https://api.openai.com/v1",
    api_key: "",
    models: "gpt-4o-mini"
  });
  const [loginImportForm, setLoginImportForm] = useState({
    provider_type: "openai",
    label: "OpenAI 登录导入",
    credential: "",
    models: "gpt-4o-mini"
  });
  const [taskForm, setTaskForm] = useState({
    title: "AI Company 下一阶段规划",
    objective: "请总经理拆解 AI Company 桌面端 MVP 的下一阶段目标，并输出可执行任务。"
  });
  const [workspaceForm, setWorkspaceForm] = useState({
    name: "默认工作区",
    path: DEFAULT_WORKSPACE_PATH,
    description: "当前目录的持续协作工作区"
  });
  const [sessionForm, setSessionForm] = useState({
    title: "默认协作会话",
    objective: "请让多个角色在当前工作区中持续推进一个长期任务。",
    model: "gpt-4o-mini",
    tick_interval_seconds: 15,
    role_ids: ""
  });
  const [model, setModel] = useState("gpt-4o-mini");

  const selectedTask = useMemo(() => tasks.find((task) => task.id === selectedTaskId) ?? tasks[0], [selectedTaskId, tasks]);
  const selectedRole = useMemo(() => roles.find((role) => role.id === selectedRoleId) ?? roles[0], [roles, selectedRoleId]);
  const selectedWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === selectedWorkspaceId) ?? workspaces[0],
    [selectedWorkspaceId, workspaces]
  );
  const activeWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === activeWorkspaceId) ?? workspaces[0],
    [activeWorkspaceId, workspaces]
  );
  const activeSessions = useMemo(
    () => sessions.filter((session) => session.workspace_id === activeWorkspace?.id),
    [activeWorkspace?.id, sessions]
  );
  const selectedSession = useMemo(
    () => activeSessions.find((session) => session.id === selectedSessionId) ?? activeSessions[0],
    [activeSessions, selectedSessionId]
  );
  const activeFuel = useMemo(() => accounts.filter((account) => account.status === "active").length, [accounts]);

  async function loadDashboard() {
    try {
      const [presetData, accountData, summaryData, logData, taskData, roleData, workspaceData, activeWorkspaceData, sessionData] = await Promise.all([
        requestJson<ProviderPreset[]>("/relay/provider-presets"),
        requestJson<Account[]>("/relay/accounts"),
        requestJson<UsageSummary>("/relay/usage/summary"),
        requestJson<CallLog[]>("/relay/logs"),
        requestJson<TaskItem[]>("/tasks"),
        requestJson<Role[]>("/roles"),
        requestJson<Workspace[]>("/workspaces"),
        requestJson<Workspace>("/workspaces/active"),
        requestJson<AgentSession[]>("/workspaces/sessions")
      ]);
      setProviderPresets(presetData);
      setAccounts(accountData);
      setSummary(summaryData);
      setLogs(logData);
      setTasks(taskData);
      setRoles(roleData);
      setWorkspaces(workspaceData);
      setSessions(sessionData);
      setSelectedTaskId((current) => current || taskData[0]?.id || "");
      setSelectedWorkspaceId((current) => current || activeWorkspaceData.id || workspaceData[0]?.id || "");
      setActiveWorkspaceId((current) => {
        const saved = window.localStorage.getItem(ACTIVE_WORKSPACE_KEY);
        const candidate = activeWorkspaceData.id || current || saved || workspaceData[0]?.id || "";
        return workspaceData.some((workspace) => workspace.id === candidate) ? candidate : workspaceData[0]?.id || "";
      });
      setSelectedRoleId((current) => current || roleData[0]?.id || "general-manager");
      setSessionForm((current) => ({
        ...current,
        role_ids: current.role_ids || roleData.filter((role) => role.enabled).map((role) => role.id).join(", ")
      }));
      setStatus("本地 API 已连接");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "本地 API 未连接");
    }
  }

  async function refreshActiveWorkspace() {
    try {
      const workspace = await requestJson<Workspace>("/workspaces/active");
      setActiveWorkspaceId(workspace.id);
      setSelectedWorkspaceId((current) => current || workspace.id);
      setWorkspaces((current) => {
        const exists = current.some((item) => item.id === workspace.id);
        const next = exists ? current.map((item) => (item.id === workspace.id ? workspace : item)) : [workspace, ...current];
        return next.map((item) => ({ ...item, status: item.id === workspace.id ? "active" : item.status === "active" ? "idle" : item.status }));
      });
    } catch {
      // The dashboard loader reports connection errors; this poll stays quiet.
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      refreshActiveWorkspace();
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (activeWorkspaceId) {
      window.localStorage.setItem(ACTIVE_WORKSPACE_KEY, activeWorkspaceId);
    }
  }, [activeWorkspaceId]);

  useEffect(() => {
    if (!activeSessions.length) {
      setSelectedSessionId("");
      return;
    }
    if (!activeSessions.some((session) => session.id === selectedSessionId)) {
      setSelectedSessionId(activeSessions[0].id);
    }
  }, [activeSessions, selectedSessionId]);

  useEffect(() => {
    if (!selectedSessionId) return;
    refreshSession(selectedSessionId).catch(() => null);
  }, [selectedSessionId]);

  useEffect(() => {
    if (!selectedSessionId) return;
    const timer = window.setInterval(() => {
      refreshSession(selectedSessionId).catch(() => null);
    }, 6000);
    return () => window.clearInterval(timer);
  }, [selectedSessionId]);

  function applyProviderPreset(providerId: string) {
    const preset = providerPresets.find((item) => item.id === providerId) ?? providerPresets[0];
    if (!preset) return;
    const models = preset.models.join(", ");
    setSelectedProviderId(providerId);
    setFuelForm((current) => ({
      ...current,
      provider_type: preset.provider_type,
      label: preset.label,
      base_url: preset.base_url,
      models
    }));
    setLoginImportForm((current) => ({
      ...current,
      provider_type: preset.provider_type,
      label: `${preset.label} 登录导入`,
      models
    }));
  }

  async function addAccount() {
    setBusy(true);
    try {
      await requestJson<Account>("/relay/accounts", {
        method: "POST",
        body: JSON.stringify({
          ...fuelForm,
          models: fuelForm.models.split(",").map((item) => item.trim()).filter(Boolean)
        })
      });
      setFuelForm((current) => ({ ...current, api_key: "" }));
      await loadDashboard();
      setStatus("燃料账号已添加");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "添加燃料账号失败");
    } finally {
      setBusy(false);
    }
  }

  async function importLoginAccount() {
    setBusy(true);
    try {
      await requestJson<Account>("/relay/accounts/import-login", {
        method: "POST",
        body: JSON.stringify({
          ...loginImportForm,
          models: loginImportForm.models.split(",").map((item) => item.trim()).filter(Boolean)
        })
      });
      setLoginImportForm((current) => ({ ...current, credential: "" }));
      await loadDashboard();
      setStatus("登录凭据已导入燃料池");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "登录导入失败");
    } finally {
      setBusy(false);
    }
  }

  async function testAccount(accountId: string) {
    setBusy(true);
    try {
      const result = await requestJson<{ model_count: number }>(`/relay/accounts/${accountId}/test`, { method: "POST" });
      await loadDashboard();
      setStatus(`连接成功，发现 ${result.model_count} 个模型`);
    } catch (error) {
      await loadDashboard();
      setStatus(error instanceof Error ? error.message : "测试失败");
    } finally {
      setBusy(false);
    }
  }

  async function setAccountStatus(accountId: string, nextStatus: "active" | "disabled") {
    setBusy(true);
    try {
      await requestJson<Account>(`/relay/accounts/${accountId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus })
      });
      await loadDashboard();
      setStatus(nextStatus === "active" ? "燃料账号已启用" : "燃料账号已停用");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "状态更新失败");
    } finally {
      setBusy(false);
    }
  }

  async function deleteAccount(accountId: string) {
    setBusy(true);
    try {
      await requestJson(`/relay/accounts/${accountId}`, { method: "DELETE" });
      await loadDashboard();
      setStatus("燃料账号已删除");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "删除失败");
    } finally {
      setBusy(false);
    }
  }

  async function createTask() {
    setBusy(true);
    try {
      const task = await requestJson<TaskItem>("/tasks", {
        method: "POST",
        body: JSON.stringify(taskForm)
      });
      await loadDashboard();
      setSelectedTaskId(task.id);
      setStatus("任务已进入任务大厅");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "创建任务失败");
    } finally {
      setBusy(false);
    }
  }

  async function createWorkspace() {
    setBusy(true);
    try {
      const workspace = await requestJson<Workspace>("/workspaces", {
        method: "POST",
        body: JSON.stringify({
          ...workspaceForm,
          path: workspaceForm.path || DEFAULT_WORKSPACE_PATH
        })
      });
      await loadDashboard();
      setSelectedWorkspaceId(workspace.id);
      setStatus("工作区已创建，输入 star ai-company 可进入该工作区");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "创建工作区失败");
    } finally {
      setBusy(false);
    }
  }

  async function runWorkspaceCommand() {
    const normalized = workspaceCommand.trim().replace(/\s+/g, " ");
    if (!normalized.toLowerCase().startsWith("star ai-company")) {
      setStatus("当前仅支持 star ai-company");
      return;
    }
    const query = normalized.slice("star ai-company".length).trim();
    const target = query ? findWorkspaceByQuery(workspaces, query) : selectedWorkspace || activeWorkspace;
    const path = target?.path || query || selectedWorkspace?.path || activeWorkspace?.path;
    if (!path) {
      setStatus("未找到可进入的工作区路径");
      return;
    }
    setBusy(true);
    try {
      const workspace = await requestJson<Workspace>("/workspaces/activate", {
        method: "POST",
        body: JSON.stringify({
          path,
          name: target?.name,
          source: "app-command"
        })
      });
      await loadDashboard();
      setActiveWorkspaceId(workspace.id);
      setSelectedWorkspaceId(workspace.id);
      const firstSession = sessions.find((session) => session.workspace_id === workspace.id);
      setSelectedSessionId(firstSession?.id || "");
      setWorkspaceCommand("star ai-company");
      setStatus(`已进入工作区: ${workspace.name}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "进入工作区失败");
    } finally {
      setBusy(false);
    }
  }

  async function createSession() {
    const workspaceId = activeWorkspace?.id || selectedWorkspaceId;
    if (!workspaceId) {
      setStatus("请先进入一个工作区");
      return;
    }
    setBusy(true);
    try {
      const session = await requestJson<AgentSession>("/workspaces/sessions", {
        method: "POST",
        body: JSON.stringify({
          workspace_id: workspaceId,
          title: sessionForm.title,
          objective: sessionForm.objective,
          model: sessionForm.model,
          role_ids: sessionForm.role_ids.split(",").map((item) => item.trim()).filter(Boolean),
          mode: "round_robin",
          tick_interval_seconds: sessionForm.tick_interval_seconds
        })
      });
      await loadDashboard();
      setSelectedSessionId(session.id);
      setStatus("协作会话已创建");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "创建会话失败");
    } finally {
      setBusy(false);
    }
  }

  async function refreshSession(sessionId: string) {
    const detail = await requestJson<AgentSession>(`/workspaces/sessions/${sessionId}`);
    setSessions((current) => current.map((item) => (item.id === detail.id ? detail : item)));
  }

  async function startSession(sessionId: string) {
    setBusy(true);
    try {
      await requestJson(`/workspaces/sessions/${sessionId}/start`, { method: "POST" });
      await loadDashboard();
      setStatus("会话已启动");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "启动失败");
    } finally {
      setBusy(false);
    }
  }

  async function pauseSession(sessionId: string) {
    setBusy(true);
    try {
      await requestJson(`/workspaces/sessions/${sessionId}/pause`, { method: "POST" });
      await loadDashboard();
      setStatus("会话已暂停");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "暂停失败");
    } finally {
      setBusy(false);
    }
  }

  async function stopSession(sessionId: string) {
    setBusy(true);
    try {
      await requestJson(`/workspaces/sessions/${sessionId}/stop`, { method: "POST" });
      await loadDashboard();
      setStatus("会话已停止");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "停止失败");
    } finally {
      setBusy(false);
    }
  }

  async function tickSession(sessionId: string) {
    setBusy(true);
    try {
      await requestJson(`/workspaces/sessions/${sessionId}/tick`, { method: "POST" });
      await loadDashboard();
      await refreshSession(sessionId);
      setStatus("已推进一次会话");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "推进失败");
    } finally {
      setBusy(false);
    }
  }

  async function runSelectedRole() {
    if (!selectedTask || !selectedRole) {
      setStatus("请先创建任务并选择岗位");
      return;
    }
    setBusy(true);
    try {
      const result = await requestJson<RoleResult>(`/tasks/${selectedTask.id}/run-role/${selectedRole.id}`, {
        method: "POST",
        body: JSON.stringify({ objective: selectedTask.objective, model })
      });
      setRoleResult(result);
      await loadDashboard();
      setStatus(`${selectedRole.title} 执行完成`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "岗位执行失败");
    } finally {
      setBusy(false);
    }
  }

  async function saveRole() {
    if (!roleForm.title.trim() || !roleForm.prompt.trim()) {
      setStatus("岗位标题和提示词不能为空");
      return;
    }
    setBusy(true);
    try {
      const payload = { ...roleForm, id: roleForm.id.trim() || undefined };
      const saved = editingRoleId
        ? await requestJson<Role>(`/roles/${editingRoleId}`, { method: "PUT", body: JSON.stringify(payload) })
        : await requestJson<Role>("/roles", { method: "POST", body: JSON.stringify(payload) });
      await loadDashboard();
      setEditingRoleId(saved.id);
      setRoleForm(roleToForm(saved));
      setSelectedRoleId(saved.id);
      setRoleEditorOpen(false);
      setStatus(editingRoleId ? "岗位已更新" : "岗位已创建");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存岗位失败");
    } finally {
      setBusy(false);
    }
  }

  function startNewRole() {
    setEditingRoleId("");
    setRoleForm(emptyRoleForm());
    setRoleEditorOpen(true);
    setActivePage("roles");
  }

  function editRole(role: Role) {
    setEditingRoleId(role.id);
    setRoleForm(roleToForm(role));
    setRoleEditorOpen(true);
    setActivePage("roles");
  }

  function closeRoleEditor() {
    setRoleEditorOpen(false);
  }

  async function deleteRole(roleId: string) {
    setBusy(true);
    try {
      await requestJson(`/roles/${roleId}`, { method: "DELETE" });
      await loadDashboard();
      if (editingRoleId === roleId) {
        setEditingRoleId("");
        setRoleForm(emptyRoleForm());
        setRoleEditorOpen(false);
      }
      setStatus("岗位已删除");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "删除岗位失败");
    } finally {
      setBusy(false);
    }
  }

  async function toggleRoleEnabled(role: Role) {
    setBusy(true);
    try {
      await requestJson<Role>(`/roles/${role.id}/enabled`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !role.enabled })
      });
      await loadDashboard();
      setStatus(role.enabled ? "岗位已停用" : "岗位已启用");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "岗位状态更新失败");
    } finally {
      setBusy(false);
    }
  }

  const metrics = [
    { label: "输入 Tokens", value: formatNumber(summary.total_input_tokens), icon: Activity },
    { label: "输出 Tokens", value: formatNumber(summary.total_output_tokens), icon: Cpu },
    { label: "缓存命中", value: formatNumber(summary.total_cached_tokens), icon: Zap },
    { label: "可用燃料", value: `${activeFuel}/${summary.total_accounts}`, icon: ShieldCheck }
  ];

  const pageMeta: Record<PageId, { eyebrow: string; title: string }> = {
    tasks: { eyebrow: "Task Hall", title: "把 Boss 目标变成公司任务，再交给岗位 Agent 执行。" },
    fuel: { eyebrow: "Fuel Center", title: "添加上游账号作为 AI 公司的燃料，并统计真实 Token 消耗。" },
    organization: { eyebrow: "Org Map", title: "用“人 + AI = 公司”的方式组织管理层、部门和执行岗位。" },
    workspaces: { eyebrow: "Workspace Run", title: "通过 star ai-company 进入工作区，让角色持续协作。" },
    roles: { eyebrow: "Role Config", title: "编辑每个岗位的职责、层级和执行提示词。" },
    logs: { eyebrow: "Call Logs", title: "查看本地中转调用流水、事件和燃料消耗。" },
    settings: { eyebrow: "Settings", title: "本地优先的 AI 公司控制台设置。" }
  };

  return (
    <main className="appShell">
      <aside className="sideRail">
        <div className="brandBlock">
          <div className="brandIcon" aria-hidden="true">
            <Building2 size={24} />
          </div>
          <div>
            <strong>AI Company</strong>
            <span>Boss Command OS</span>
          </div>
        </div>

        <nav className="navList" aria-label="主导航">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={item.id === activePage ? "navItem active" : "navItem"}
                key={item.id}
                type="button"
                onClick={() => setActivePage(item.id)}
              >
                <span className="roundIcon">
                  <Icon size={18} />
                </span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="relayBox">
          <div className="relayIcon">
            <Radar size={20} />
          </div>
          <div>
            <strong>{activeWorkspace?.name ?? "Local Relay"}</strong>
            <span>{activeWorkspace?.path ?? status}</span>
          </div>
        </div>
      </aside>

      <section className="commandSurface">
        <header className="commandHeader">
          <div>
            <div className="statusLine">
              <span className="liveDot" />
              {pageMeta[activePage].eyebrow}
            </div>
            <h1>{pageMeta[activePage].title}</h1>
          </div>
          <div className="headerActions">
            <button className="ghostButton" type="button" onClick={loadDashboard}>
              <RefreshCw size={18} />
              刷新
            </button>
            <button className="primaryButton" type="button" onClick={runSelectedRole} disabled={busy || !selectedTask}>
              <Play size={18} />
              运行岗位
            </button>
          </div>
        </header>

        <section className="metricGrid" aria-label="燃料概况">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <article className="metricTile" key={metric.label}>
                <span className="roundIcon metricIcon">
                  <Icon size={18} />
                </span>
                <div>
                  <p>{metric.label}</p>
                  <strong>{metric.value}</strong>
                </div>
              </article>
            );
          })}
        </section>

        {activePage === "workspaces" ? (
          <WorkspaceRuntime
            activeWorkspace={activeWorkspace}
            busy={busy}
            commandValue={workspaceCommand}
            createSession={createSession}
            createWorkspace={createWorkspace}
            onCommand={runWorkspaceCommand}
            onPause={pauseSession}
            onStart={startSession}
            onStop={stopSession}
            onTick={tickSession}
            selectedSessionId={selectedSessionId}
            selectedWorkspaceId={selectedWorkspaceId}
            selectedSession={selectedSession}
            sessionForm={sessionForm}
            sessions={activeSessions}
            setCommandValue={setWorkspaceCommand}
            setSelectedSessionId={setSelectedSessionId}
            setSelectedWorkspaceId={setSelectedWorkspaceId}
            setSessionForm={setSessionForm}
            setWorkspaceForm={setWorkspaceForm}
            workspaceForm={workspaceForm}
            workspaces={workspaces}
          />
        ) : null}
        {activePage === "tasks" ? (
          <TaskHall
            busy={busy}
            createTask={createTask}
            model={model}
            roleResult={roleResult}
            roles={roles}
            runSelectedRole={runSelectedRole}
            selectedRoleId={selectedRoleId}
            selectedTask={selectedTask}
            selectedTaskId={selectedTaskId}
            setModel={setModel}
            setSelectedRoleId={setSelectedRoleId}
            setSelectedTaskId={setSelectedTaskId}
            setTaskForm={setTaskForm}
            taskForm={taskForm}
            tasks={tasks}
          />
        ) : null}
        {activePage === "fuel" ? (
          <FuelCenter
            accounts={accounts}
            addAccount={addAccount}
            applyProviderPreset={applyProviderPreset}
            busy={busy}
            deleteAccount={deleteAccount}
            form={fuelForm}
            importLoginAccount={importLoginAccount}
            loginForm={loginImportForm}
            logs={logs}
            providerPresets={providerPresets}
            roleResult={roleResult}
            setAccountStatus={setAccountStatus}
            setForm={setFuelForm}
            selectedProviderId={selectedProviderId}
            setLoginForm={setLoginImportForm}
            summary={summary}
            testAccount={testAccount}
          />
        ) : null}
        {activePage === "organization" ? <Organization roles={roles} tasks={tasks} /> : null}
        {activePage === "roles" ? (
          <RoleConfig
            busy={busy}
            editingRoleId={editingRoleId}
            editorOpen={roleEditorOpen}
            onDelete={deleteRole}
            onEdit={editRole}
            onCloseEditor={closeRoleEditor}
            onNew={startNewRole}
            onSave={saveRole}
            onToggleEnabled={toggleRoleEnabled}
            roleForm={roleForm}
            roles={roles}
            setRoleForm={setRoleForm}
          />
        ) : null}
        {activePage === "logs" ? <LogsPage logs={logs} /> : null}
        {activePage === "settings" ? <SettingsPage /> : null}
      </section>
    </main>
  );
}

function WorkspaceRuntime(props: {
  activeWorkspace?: Workspace;
  busy: boolean;
  commandValue: string;
  createSession: () => void;
  createWorkspace: () => void;
  onCommand: () => void;
  onPause: (sessionId: string) => void;
  onStart: (sessionId: string) => void;
  onStop: (sessionId: string) => void;
  onTick: (sessionId: string) => void;
  selectedSession?: AgentSession;
  selectedSessionId: string;
  selectedWorkspaceId: string;
  sessionForm: { title: string; objective: string; model: string; tick_interval_seconds: number; role_ids: string };
  sessions: AgentSession[];
  setCommandValue: (value: string) => void;
  setSelectedSessionId: (value: string) => void;
  setSelectedWorkspaceId: (value: string) => void;
  setSessionForm: (value: { title: string; objective: string; model: string; tick_interval_seconds: number; role_ids: string }) => void;
  setWorkspaceForm: (value: { name: string; path: string; description: string }) => void;
  workspaceForm: { name: string; path: string; description: string };
  workspaces: Workspace[];
}) {
  return (
    <section className="workspaceGrid">
      <section className="missionDeck">
        <div className="deckHeader">
          <div>
            <p className="kicker">Command</p>
            <h2>进入工作区</h2>
          </div>
          <span className="missionBadge">
            <Building2 size={16} />
            Runtime
          </span>
        </div>
        <div className="commandStrip">
          <div>
            <p className="kicker">Active Workspace</p>
            <strong>{props.activeWorkspace?.name ?? "未进入工作区"}</strong>
            <span>{props.activeWorkspace?.path ?? "选择工作区后执行 star ai-company"}</span>
          </div>
          <form
            className="commandForm"
            onSubmit={(event) => {
              event.preventDefault();
              props.onCommand();
            }}
          >
            <input value={props.commandValue} onChange={(event) => props.setCommandValue(event.target.value)} />
            <button className="primaryButton compact" type="submit" disabled={props.busy}>
              执行
            </button>
          </form>
        </div>
        <div className="formGrid">
          <label>
            名称
            <input value={props.workspaceForm.name} onChange={(event) => props.setWorkspaceForm({ ...props.workspaceForm, name: event.target.value })} />
          </label>
          <label>
            路径
            <input value={props.workspaceForm.path} onChange={(event) => props.setWorkspaceForm({ ...props.workspaceForm, path: event.target.value })} />
          </label>
        </div>
        <label className="editorBlock">
          描述
          <textarea
            className="missionInput editorTextarea"
            value={props.workspaceForm.description}
            onChange={(event) => props.setWorkspaceForm({ ...props.workspaceForm, description: event.target.value })}
          />
        </label>
        <button className="primaryButton" type="button" onClick={props.createWorkspace} disabled={props.busy}>
          <ClipboardList size={18} />
          创建工作区
        </button>
      </section>

      <section className="missionDeck">
        <div className="deckHeader">
          <div>
            <p className="kicker">Session</p>
            <h2>创建持续会话</h2>
          </div>
          <span className="missionBadge">
            <Bot size={16} />
            Loop
          </span>
        </div>
        <div className="formGrid">
          <label>
            标题
            <input value={props.sessionForm.title} onChange={(event) => props.setSessionForm({ ...props.sessionForm, title: event.target.value })} />
          </label>
          <label>
            模型
            <input value={props.sessionForm.model} onChange={(event) => props.setSessionForm({ ...props.sessionForm, model: event.target.value })} />
          </label>
          <label>
            轮询间隔
            <input
              type="number"
              value={props.sessionForm.tick_interval_seconds}
              onChange={(event) =>
                props.setSessionForm({ ...props.sessionForm, tick_interval_seconds: Number.parseInt(event.target.value || "15", 10) })
              }
            />
          </label>
          <label>
            角色 ID 列表
            <input value={props.sessionForm.role_ids} onChange={(event) => props.setSessionForm({ ...props.sessionForm, role_ids: event.target.value })} />
          </label>
        </div>
        <label className="editorBlock">
          协作目标
          <textarea
            className="missionInput editorTextarea"
            value={props.sessionForm.objective}
            onChange={(event) => props.setSessionForm({ ...props.sessionForm, objective: event.target.value })}
          />
        </label>
        <button className="primaryButton" type="button" onClick={props.createSession} disabled={props.busy || !props.activeWorkspace}>
          <Play size={18} />
          创建会话
        </button>
      </section>

      <section className="orgPanel">
        <div className="panelTitle">
          <h2>工作区列表</h2>
          <span>{props.workspaces.length} workspaces</span>
        </div>
        <div className="taskList">
          {props.workspaces.map((workspace) => (
            <button
              className={workspace.id === props.selectedWorkspaceId ? "taskCard selected" : "taskCard"}
              key={workspace.id}
              type="button"
              onClick={() => props.setSelectedWorkspaceId(workspace.id)}
            >
              <div>
                <strong>{workspace.name}</strong>
                <p>{workspace.path}</p>
                <p>{workspace.description}</p>
              </div>
              <span>{workspace.id === props.activeWorkspace?.id ? "运行中" : statusText(workspace.status)}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="orgPanel">
        <div className="panelTitle">
          <h2>持续会话</h2>
          <span>{props.sessions.length} sessions</span>
        </div>
        <div className="taskList">
          {props.sessions.map((session) => (
            <button
              className={session.id === props.selectedSessionId ? "taskCard selected" : "taskCard"}
              key={session.id}
              type="button"
              onClick={() => props.setSelectedSessionId(session.id)}
            >
              <div>
                <strong>{session.title}</strong>
                <p>{session.objective}</p>
                <p>{session.role_count} roles · {session.model} · {session.worker_run_count ?? session.worker_runs?.length ?? 0} runs</p>
              </div>
              <span>{statusText(session.status)}</span>
            </button>
          ))}
        </div>
      </section>

      <aside className="rightStack">
        <section className="focusPanel">
          <div className="orbitalIcon">
            <Radar size={25} />
          </div>
          <p className="kicker">Live Session</p>
          <h2>{props.selectedSession?.title ?? "暂无会话"}</h2>
          <p>{props.selectedSession?.objective ?? "先进入工作区，再创建持续会话。"}</p>
        </section>
        <section className="logPanel">
          <div className="panelTitle">
            <h2>会话控制</h2>
            <span>{props.selectedSession?.status ?? "idle"}</span>
          </div>
          {props.selectedSession ? (
            <div className="sessionControlStack">
              <div className="headerActions">
                <button className="ghostButton" type="button" onClick={() => props.onStart(props.selectedSession!.id)} disabled={props.busy}>
                  启动
                </button>
                <button className="ghostButton" type="button" onClick={() => props.onPause(props.selectedSession!.id)} disabled={props.busy}>
                  暂停
                </button>
                <button className="ghostButton" type="button" onClick={() => props.onStop(props.selectedSession!.id)} disabled={props.busy}>
                  停止
                </button>
                <button className="primaryButton" type="button" onClick={() => props.onTick(props.selectedSession!.id)} disabled={props.busy}>
                  单步
                </button>
              </div>
              <RecentEvents events={props.selectedSession.events ?? []} />
              <RecentWorkerRuns workerRuns={props.selectedSession.worker_runs ?? []} />
            </div>
          ) : (
            <p className="emptyState">没有可用会话。</p>
          )}
        </section>
      </aside>
    </section>
  );
}

function TaskHall(props: {
  busy: boolean;
  createTask: () => void;
  model: string;
  roleResult: RoleResult | null;
  roles: Role[];
  runSelectedRole: () => void;
  selectedRoleId: string;
  selectedTask?: TaskItem;
  selectedTaskId: string;
  setModel: (value: string) => void;
  setSelectedRoleId: (value: string) => void;
  setSelectedTaskId: (value: string) => void;
  setTaskForm: (value: { title: string; objective: string }) => void;
  taskForm: { title: string; objective: string };
  tasks: TaskItem[];
}) {
  return (
    <section className="taskGrid">
      <section className="missionDeck">
        <div className="deckHeader">
          <div>
            <p className="kicker">New Mission</p>
            <h2>创建公司任务</h2>
          </div>
          <span className="missionBadge">
            <FileText size={16} />
            Boss Goal
          </span>
        </div>
        <div className="formGrid singleLine">
          <label>
            任务标题
            <input value={props.taskForm.title} onChange={(event) => props.setTaskForm({ ...props.taskForm, title: event.target.value })} />
          </label>
        </div>
        <textarea
          className="missionInput"
          value={props.taskForm.objective}
          onChange={(event) => props.setTaskForm({ ...props.taskForm, objective: event.target.value })}
        />
        <button className="primaryButton" type="button" onClick={props.createTask} disabled={props.busy || !props.taskForm.objective}>
          <ClipboardList size={18} />
          创建任务
        </button>
      </section>

      <section className="missionDeck">
        <div className="deckHeader">
          <div>
            <p className="kicker">Dispatch</p>
            <h2>岗位调度台</h2>
          </div>
          <span className="missionBadge">
            <Bot size={16} />
            Agent Run
          </span>
        </div>
        <div className="formGrid">
          <label>
            执行任务
            <select value={props.selectedTaskId} onChange={(event) => props.setSelectedTaskId(event.target.value)}>
              {props.tasks.map((task) => (
                <option key={task.id} value={task.id}>
                  {task.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            执行岗位
            <select value={props.selectedRoleId} onChange={(event) => props.setSelectedRoleId(event.target.value)}>
              {props.roles.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            使用模型
            <input value={props.model} onChange={(event) => props.setModel(event.target.value)} />
          </label>
        </div>
        <button className="primaryButton" type="button" onClick={props.runSelectedRole} disabled={props.busy || !props.selectedTask}>
          <Play size={18} />
          执行选中岗位
        </button>
      </section>

      <section className="orgPanel">
        <div className="panelTitle">
          <h2>任务队列</h2>
          <span>{props.tasks.length} tasks</span>
        </div>
        <div className="taskList">
          {props.tasks.length === 0 ? (
            <p className="emptyState">还没有任务。先把 Boss 目标写进去。</p>
          ) : (
            props.tasks.map((task) => (
              <button
                className={task.id === props.selectedTaskId ? "taskCard selected" : "taskCard"}
                key={task.id}
                type="button"
                onClick={() => props.setSelectedTaskId(task.id)}
              >
                <div>
                  <strong>{task.title}</strong>
                  <p>{task.objective}</p>
                </div>
                <span>{statusText(task.status)}</span>
              </button>
            ))
          )}
        </div>
      </section>

      <aside className="rightStack">
        <section className="focusPanel">
          <div className="orbitalIcon">
            <Gauge size={25} />
          </div>
          <p className="kicker">Selected Mission</p>
          <h2>{props.selectedTask?.title ?? "等待创建任务"}</h2>
          <p>{props.selectedTask?.objective ?? "任务创建后会在这里展示目标。"}</p>
        </section>
        <ResultPanel roleResult={props.roleResult} />
      </aside>
    </section>
  );
}

function FuelCenter(props: {
  accounts: Account[];
  addAccount: () => void;
  applyProviderPreset: (providerId: string) => void;
  busy: boolean;
  deleteAccount: (accountId: string) => void;
  form: { provider_type: string; label: string; base_url: string; api_key: string; models: string };
  importLoginAccount: () => void;
  loginForm: { provider_type: string; label: string; credential: string; models: string };
  logs: CallLog[];
  providerPresets: ProviderPreset[];
  roleResult: RoleResult | null;
  setAccountStatus: (accountId: string, status: "active" | "disabled") => void;
  selectedProviderId: string;
  setForm: (value: { provider_type: string; label: string; base_url: string; api_key: string; models: string }) => void;
  setLoginForm: (value: { provider_type: string; label: string; credential: string; models: string }) => void;
  summary: UsageSummary;
  testAccount: (accountId: string) => void;
}) {
  const selectedPreset = props.providerPresets.find((preset) => preset.id === props.selectedProviderId);
  return (
    <section className="fuelGrid">
      <section className="missionDeck">
        <div className="deckHeader">
          <div>
            <p className="kicker">Add Fuel</p>
            <h2>添加模型燃料</h2>
          </div>
          <span className="missionBadge">
            <KeyRound size={16} />
            API Key
          </span>
        </div>
        <div className="providerPresetGrid">
          {props.providerPresets.map((preset) => (
            <button
              className={preset.id === props.selectedProviderId ? "providerPreset active" : "providerPreset"}
              key={preset.id}
              type="button"
              onClick={() => props.applyProviderPreset(preset.id)}
            >
              <strong>{preset.label}</strong>
              <span>{preset.description}</span>
            </button>
          ))}
        </div>
        <div className="formGrid">
          <label>
            Provider
            <select value={props.selectedProviderId} onChange={(event) => props.applyProviderPreset(event.target.value)}>
              {props.providerPresets.map((preset) => (
                <option value={preset.id} key={preset.id}>
                  {preset.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            名称
            <input value={props.form.label} onChange={(event) => props.setForm({ ...props.form, label: event.target.value })} />
          </label>
          <label>
            Base URL
            <input value={props.form.base_url} onChange={(event) => props.setForm({ ...props.form, base_url: event.target.value })} />
          </label>
          <label>
            API Key
            <input value={props.form.api_key} type="password" onChange={(event) => props.setForm({ ...props.form, api_key: event.target.value })} />
          </label>
          <label>
            模型列表
            <input value={props.form.models} onChange={(event) => props.setForm({ ...props.form, models: event.target.value })} />
          </label>
        </div>
        <button className="primaryButton" type="button" onClick={props.addAccount} disabled={props.busy || !props.form.api_key}>
          <DatabaseZap size={18} />
          添加燃料账号
        </button>
      </section>

      <section className="missionDeck loginFuelCard">
        <div className="deckHeader">
          <div>
            <p className="kicker">Login Import</p>
            <h2>通过登录凭据导入</h2>
          </div>
          <span className="missionBadge">
            <LogIn size={16} />
            Auth
          </span>
        </div>
        <p className="emptyState">
          当前 MVP 先支持从官方账号页获取 API Key / 登录凭据后导入燃料池；后续再接浏览器 OAuth、网页登录态同步和自动抓取额度。
        </p>
        <div className="formGrid">
          <label>
            导入名称
            <input value={props.loginForm.label} onChange={(event) => props.setLoginForm({ ...props.loginForm, label: event.target.value })} />
          </label>
          <label>
            模型列表
            <input value={props.loginForm.models} onChange={(event) => props.setLoginForm({ ...props.loginForm, models: event.target.value })} />
          </label>
          <label className="wideField">
            登录凭据 / API Key
            <input
              value={props.loginForm.credential}
              type="password"
              onChange={(event) => props.setLoginForm({ ...props.loginForm, credential: event.target.value })}
            />
          </label>
        </div>
        <div className="headerActions">
          {selectedPreset?.auth_url ? (
            <a className="ghostButton compact linkButton" href={selectedPreset.auth_url} target="_blank" rel="noreferrer">
              <ExternalLink size={14} />
              打开账号页
            </a>
          ) : null}
          <button className="primaryButton" type="button" onClick={props.importLoginAccount} disabled={props.busy || !props.loginForm.credential}>
            <LogIn size={18} />
            导入燃料池
          </button>
        </div>
      </section>

      <section className="orgPanel">
        <div className="panelTitle">
          <h2>上游燃料池</h2>
          <span>{props.accounts.length} accounts</span>
        </div>
        <div className="accountList">
          {props.accounts.map((account) => (
            <article className="accountCard" key={account.id}>
              <div>
                <strong>{account.label}</strong>
                <span className="providerPill">{account.provider_type}</span>
                <p>{account.base_url}</p>
                <p>{account.models.length ? account.models.join(", ") : "所有模型"}</p>
              </div>
              <div className="accountStats">
                <span>{statusText(account.status)}</span>
                <span>{formatNumber(account.total_input_tokens)} in</span>
                <span>{formatNumber(account.total_output_tokens)} out</span>
                <button className="ghostButton compact" type="button" onClick={() => props.testAccount(account.id)} disabled={props.busy}>
                  测试
                </button>
                <button
                  className="ghostButton compact"
                  type="button"
                  onClick={() => props.setAccountStatus(account.id, account.status === "active" ? "disabled" : "active")}
                  disabled={props.busy}
                >
                  <Power size={14} />
                  {account.status === "active" ? "停用" : "启用"}
                </button>
                <button className="ghostButton compact dangerButton" type="button" onClick={() => props.deleteAccount(account.id)} disabled={props.busy}>
                  <Trash2 size={14} />
                  删除
                </button>
              </div>
              {account.last_error ? <p className="errorText">{account.last_error}</p> : null}
            </article>
          ))}
          {props.accounts.length === 0 ? <p className="emptyState">还没有燃料账号。</p> : null}
        </div>
      </section>

      <aside className="rightStack">
        <section className="focusPanel">
          <div className="orbitalIcon">
            <Gauge size={25} />
          </div>
          <p className="kicker">Usage Pulse</p>
          <h2>缓存命中率 {(props.summary.cache_hit_rate * 100).toFixed(1)}%</h2>
          <div className="pulseMeter">
            <span style={{ width: `${Math.max(4, props.summary.cache_hit_rate * 100)}%` }} />
          </div>
        </section>
        <ResultPanel roleResult={props.roleResult} />
        <RecentLogs logs={props.logs} />
      </aside>
    </section>
  );
}

function Organization({ roles, tasks }: { roles: Role[]; tasks: TaskItem[] }) {
  return (
    <section className="mainGrid">
      <section className="workflowPanel">
        <div className="panelTitle">
          <h2>公司运转链路</h2>
          <span>Boss 到管理层到岗位</span>
        </div>
        <div className="workflowTrack">
          {["Boss 输入目标", "总经理制定计划", "副经理拆解协调", "岗位 Agent 执行", "日志与 Token 回收"].map((item, index) => (
            <article className={index < 2 ? "workflowNode done" : index === 2 ? "workflowNode active" : "workflowNode queued"} key={item}>
              <span className="roundIcon nodeIcon">
                <Bot size={18} />
              </span>
              <p>{item}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="orgPanel">
        <div className="panelTitle">
          <h2>组织岗位</h2>
          <span>{roles.length} roles</span>
        </div>
        <RoleMatrix roles={roles} />
      </section>
      <aside className="rightStack">
        <section className="focusPanel">
          <div className="orbitalIcon">
            <Building2 size={25} />
          </div>
          <p className="kicker">Company Mode</p>
          <h2>人 + AI = 公司</h2>
          <p>你作为 Boss 提供目标、判断和资源，AI 角色负责拆解、执行、复盘与交付。</p>
        </section>
        <RecentTasks tasks={tasks} />
      </aside>
    </section>
  );
}

function RoleConfig(props: {
  busy: boolean;
  editingRoleId: string;
  editorOpen: boolean;
  onCloseEditor: () => void;
  onDelete: (roleId: string) => void;
  onEdit: (role: Role) => void;
  onNew: () => void;
  onSave: () => void;
  onToggleEnabled: (role: Role) => void;
  roleForm: RoleForm;
  roles: Role[];
  setRoleForm: (value: RoleForm) => void;
}) {
  const selectedRole = props.editingRoleId ? props.roles.find((role) => role.id === props.editingRoleId) : null;

  return (
    <section className="rolePage">
      <section className="orgPanel roleConfigPanel">
        <div className="panelTitle">
          <div>
            <h2>岗位职责模板</h2>
            <p className="panelHint">点击卡片上的编辑，在弹窗里调整岗位职责、提示词和启用状态。</p>
          </div>
          <div className="headerActions">
            <span>{props.roles.length} roles</span>
            <button className="primaryButton compact" type="button" onClick={props.onNew} disabled={props.busy}>
              新建岗位
            </button>
          </div>
        </div>
        <div className="roleConfigList">
          {props.roles.map((role) => (
            <article className="roleConfigItem" key={role.id}>
              <div className="roleTopline">
                <span className="roleAvatar">
                  <Bot size={18} />
                </span>
                <span>{role.level}</span>
              </div>
              <strong>{role.title}</strong>
              <p className="department">{role.department}</p>
              <p>{role.responsibility}</p>
              <code>{role.prompt}</code>
              <div className="roleCardActions">
                <button className="ghostButton compact" type="button" onClick={() => props.onEdit(role)} disabled={props.busy}>
                  编辑
                </button>
                <button className="ghostButton compact" type="button" onClick={() => props.onToggleEnabled(role)} disabled={props.busy}>
                  {role.enabled ? "停用" : "启用"}
                </button>
                <button className="ghostButton compact dangerButton" type="button" onClick={() => props.onDelete(role.id)} disabled={props.busy}>
                  删除
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
      {props.editorOpen ? (
        <div className="modalOverlay" role="presentation" onMouseDown={props.onCloseEditor}>
          <section className="roleEditorModal" role="dialog" aria-modal="true" aria-labelledby="role-editor-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="panelTitle">
              <div>
                <p className="kicker">{props.editingRoleId ? "Edit Role" : "New Role"}</p>
                <h2 id="role-editor-title">{props.editingRoleId ? "编辑岗位" : "新建岗位"}</h2>
              </div>
              <button className="iconButton" type="button" onClick={props.onCloseEditor} aria-label="关闭岗位编辑弹窗">
                <X size={18} />
              </button>
            </div>
            <div className="formGrid">
              <label>
                岗位标题
                <input value={props.roleForm.title} onChange={(event) => props.setRoleForm({ ...props.roleForm, title: event.target.value })} />
              </label>
              <label>
                部门
                <input value={props.roleForm.department} onChange={(event) => props.setRoleForm({ ...props.roleForm, department: event.target.value })} />
              </label>
              <label>
                层级
                <select value={props.roleForm.level} onChange={(event) => props.setRoleForm({ ...props.roleForm, level: event.target.value })}>
                  {["L1", "L2", "L3", "L4"].map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                排序
                <input
                  type="number"
                  value={props.roleForm.sort_order}
                  onChange={(event) => props.setRoleForm({ ...props.roleForm, sort_order: Number.parseInt(event.target.value || "0", 10) })}
                />
              </label>
            </div>
            <label className="editorBlock">
              职责说明
              <textarea
                className="missionInput editorTextarea"
                value={props.roleForm.responsibility}
                onChange={(event) => props.setRoleForm({ ...props.roleForm, responsibility: event.target.value })}
              />
            </label>
            <label className="editorBlock">
              岗位提示词
              <textarea
                className="missionInput editorTextarea rolePromptTextarea"
                value={props.roleForm.prompt}
                onChange={(event) => props.setRoleForm({ ...props.roleForm, prompt: event.target.value })}
              />
            </label>
            <div className="modalFooter">
              <label className="toggleRow">
                <input
                  type="checkbox"
                  checked={props.roleForm.enabled}
                  onChange={(event) => props.setRoleForm({ ...props.roleForm, enabled: event.target.checked })}
                />
                <span>启用该岗位</span>
              </label>
              <div className="headerActions">
                <button className="ghostButton" type="button" onClick={props.onCloseEditor}>
                  取消
                </button>
                <button className="primaryButton" type="button" onClick={props.onSave} disabled={props.busy}>
                  保存岗位
                </button>
              </div>
            </div>
            {selectedRole ? <p className="emptyState">当前正在编辑 {selectedRole.title}。</p> : null}
          </section>
        </div>
      ) : null}
    </section>
  );
}

function LogsPage({ logs }: { logs: CallLog[] }) {
  return (
    <section className="logPage">
      <section className="orgPanel">
        <div className="panelTitle">
          <h2>调用流水</h2>
          <span>{logs.length} logs</span>
        </div>
        <div className="logTable">
          {logs.length === 0 ? (
            <p className="emptyState">还没有调用记录。</p>
          ) : (
            logs.map((log) => (
              <article className={log.status === "success" ? "logRow" : "logRow failed"} key={log.id}>
                <div>
                  <strong>{log.model}</strong>
                  <p>{log.task_id || "unknown task"} / {log.role_id || "unknown role"}</p>
                </div>
                <span>{statusText(log.status)}</span>
                <span>{formatNumber(log.input_tokens)} in</span>
                <span>{formatNumber(log.output_tokens)} out</span>
                <span>{log.latency_ms} ms</span>
                {log.error_message ? <p className="errorText compactError">{log.error_message}</p> : null}
              </article>
            ))
          )}
        </div>
      </section>
    </section>
  );
}

function SettingsPage() {
  return (
    <section className="mainGrid">
      <section className="orgPanel">
        <div className="panelTitle">
          <h2>本地设置</h2>
          <span>MVP</span>
        </div>
        <div className="settingsGrid">
          {[
            ["API 中转地址", API_BASE],
            ["账号燃料模式", "用户添加上游账号，本地中转调度"],
            ["任务存储", "SQLite 本地持久化"],
            ["当前策略", "用 active workspace 模拟 app 运行目录"]
          ].map(([label, value]) => (
            <article className="settingTile" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

function RoleMatrix({ roles }: { roles: Role[] }) {
  return (
    <div className="roleMatrix">
      {roles.map((role, index) => (
        <article className={["roleCard mint", "roleCard cyan", "roleCard amber", "roleCard rose"][index % 4]} key={role.id}>
          <div className="roleTopline">
            <span className="roleAvatar">
              <Bot size={18} />
            </span>
            <span>{role.level}</span>
          </div>
          <strong>{role.title}</strong>
          <p className="department">{role.department}</p>
          <p>{role.responsibility}</p>
        </article>
      ))}
    </div>
  );
}

function ResultPanel({ roleResult }: { roleResult: RoleResult | null }) {
  return (
    <section className="logPanel">
      <div className="panelTitle">
        <h2>岗位输出</h2>
        <span>{roleResult ? "latest result" : "waiting"}</span>
      </div>
      {roleResult ? (
        <div className="resultBox">
          <p>{roleResult.output}</p>
          <span>{formatNumber(roleResult.usage.input_tokens)} in / {formatNumber(roleResult.usage.output_tokens)} out</span>
        </div>
      ) : (
        <p className="emptyState">运行岗位后，这里会显示岗位输出和真实 Token 消耗。</p>
      )}
    </section>
  );
}

function RecentLogs({ logs }: { logs: CallLog[] }) {
  return (
    <section className="logPanel">
      <div className="panelTitle">
        <h2>最近调用</h2>
        <span>{logs.length} logs</span>
      </div>
      <div className="callLogList">
        {logs.length === 0 ? (
          <p className="emptyState">还没有调用记录。</p>
        ) : (
          logs.slice(0, 8).map((log) => (
            <article className={log.status === "success" ? "callLogItem" : "callLogItem failed"} key={log.id}>
              <div>
                <strong>{log.model}</strong>
                <p>{log.role_id || "unknown role"} / {statusText(log.status)}</p>
              </div>
              <span>{formatNumber(log.input_tokens)} / {formatNumber(log.output_tokens)}</span>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function RecentTasks({ tasks }: { tasks: TaskItem[] }) {
  return (
    <section className="logPanel">
      <div className="panelTitle">
        <h2>当前任务</h2>
        <span>{tasks.length} active</span>
      </div>
      <div className="callLogList">
        {tasks.slice(0, 5).map((task) => (
          <article className="callLogItem" key={task.id}>
            <div>
              <strong>{task.title}</strong>
              <p>{statusText(task.status)}</p>
            </div>
            <span>{task.step_count ?? task.steps?.length ?? 0} steps</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function RecentEvents({ events }: { events: SessionEvent[] }) {
  return (
    <div className="callLogList">
      {events.length === 0 ? (
        <p className="emptyState">还没有事件流。</p>
      ) : (
        events.slice(0, 6).map((event) => (
          <article className="callLogItem" key={event.id}>
            <div>
              <strong>{event.role_title || event.kind}</strong>
              <p>{event.kind}</p>
            </div>
            <span>{event.created_at.slice(11, 19)}</span>
            <p className="eventContent">{event.content}</p>
          </article>
        ))
      )}
    </div>
  );
}

function RecentWorkerRuns({ workerRuns }: { workerRuns: AgentWorkerRun[] }) {
  return (
    <section className="workerRunPanel">
      <div className="panelTitle">
        <h2>Worker 运行</h2>
        <span>{workerRuns.length} runs</span>
      </div>
      <div className="callLogList">
        {workerRuns.length === 0 ? (
          <p className="emptyState">还没有 worker 运行记录。</p>
        ) : (
          workerRuns.slice(0, 6).map((run) => (
            <article className={run.status === "failed" ? "callLogItem failed" : "callLogItem"} key={run.id}>
              <div>
                <strong>{run.role_title || "未命名岗位"}</strong>
                <p>{run.cwd}</p>
                <p>{run.model}</p>
              </div>
              <span>{statusText(run.status)}</span>
              <p className="eventContent">
                {formatNumber(run.input_tokens)} in / {formatNumber(run.output_tokens)} out
                {run.error_message ? `\n${run.error_message}` : ""}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
