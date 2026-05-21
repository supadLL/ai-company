# 角色进程 Worker MVP

本轮实现的是“每个岗位可以启动自己的持续命令进程”的第一版能力，用来支撑 AI Company 里不同角色在同一工作区或不同工作区内长期协作。

## 已实现内容

- 每个角色拥有独立的进程启动配置：控制工具、启动命令、参数、启用状态、自动重启。
- 支持的控制工具预设包括 PowerShell、CMD、Bash、Python、Node 和 Custom。
- 角色进程启动时使用所属工作区路径作为 `cwd`。
- 进程环境变量会注入当前 AI Company 上下文：
  - `AI_COMPANY_API`
  - `AI_COMPANY_WORKSPACE`
  - `AI_COMPANY_WORKSPACE_ID`
  - `AI_COMPANY_SESSION_ID`
  - `AI_COMPANY_ROLE_ID`
  - `AI_COMPANY_ROLE_TITLE`
  - `AI_COMPANY_MODEL`
- 前端工作区页面可以对选中会话里的角色执行启动、停止、重启、查看日志。
- 后端会记录进程状态、PID、退出码、stdout/stderr/system 日志。
- 如果角色配置开启自动重启，且所属会话仍处于 `running`，进程异常退出后会自动再次启动。

## 后端接口

```text
GET  /workspaces/role-process-configs
PUT  /workspaces/role-process-configs/{role_id}
GET  /workspaces/agent-processes
GET  /workspaces/agent-processes/{process_id}/logs
POST /workspaces/sessions/{session_id}/roles/{role_id}/process/start
POST /workspaces/sessions/{session_id}/roles/{role_id}/process/restart
POST /workspaces/agent-processes/{process_id}/stop
```

## 当前边界

- 这是非交互式进程管理，不是完整终端模拟器；暂未接入 PTY 或 xterm.js。
- Windows 下当前使用普通进程终止，后续需要补进程树清理。
- App 重启后可以看到历史进程记录，但内存里的进程句柄不会恢复，后续需要做 supervisor/heartbeat。
- 自动重启是 MVP 级别，后续应接入持久任务队列和失败退避策略。

## 下一步建议

- 接入 xterm.js + PTY，让角色进程成为真正可交互的终端会话。
- 为每个角色配置默认 Agent 命令模板，例如 Codex、Claude Code、本地脚本、测试命令。
- 增加工作区权限策略，限制角色进程可读写目录。
- 增加心跳、超时、退避重启和 App 重启恢复。
