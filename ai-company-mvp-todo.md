# AI Company 桌面端 MVP TODO

## 1. 产品定位

AI Company 是一个本地优先的桌面端“AI 公司”工作台。

用户作为 Boss，可以创建一个由多个 AI 岗位组成的虚拟公司。每个岗位都是一个可配置、可运行、可记录的 Agent，例如总经理、副经理、产品经理、技术负责人、工程师、测试员、运营等。

第一版的核心不是做一个简单聊天工具，而是验证：

- 人 + AI = 公司。
- 用户可以编辑不同角色，让它们拥有不同职责、Prompt、模型和工具权限。
- 多个 Agent 可以围绕一个或多个工作区持续协作，而不是只执行一次模型调用。
- 所有模型调用都通过本地 API 中转，并由上游账号作为“燃料”驱动。

## 2. 第一版用户主动补充功能

这些是第一版讨论中明确追加进 MVP 路线的功能，后续实现不能丢：

- [x] 保留总经理、副经理等管理角色，形成“公司式”层级。
- [x] 角色必须是可编辑的，而不是写死在前端。
- [x] 支持创建不同角色，配置岗位职责、Prompt、模型、启用状态。
- [x] 支持上游账号作为本地 AI Company 的“燃料”。
- [x] 支持通过官方登录/API Key 页面获取凭据后导入燃料池。
- [x] 支持本地 API 中转：上游账号 -> 本地中转 -> 下游角色/任务调用。
- [x] 支持 GPT、DeepSeek、Qwen、GLM 等 OpenAI-compatible 模型供应商预设。
- [x] 支持查看 token 消耗概况，包括输入、输出、缓存命中等统计字段。
- [x] 支持工作区概念，任务和 Agent 会话属于具体工作区。
- [x] 支持用户在当前目录运行 `star ai-company` 后，将 App 活跃运行目录切换到该目录对应工作区。
- [x] 支持真实 CLI 入口 `star ai-company`，把命令执行目录发送给本地 API。
- [x] 支持持续协作会话的第一版数据结构和事件流。
- [x] 支持 Agent Worker Run 记录，以工作区路径作为 cwd 执行边界。
- [ ] 支持真实 Agent Worker 进程以工作区路径作为 cwd 长时间运行。
- [ ] 支持多个工作区同时存在，且每个工作区拥有独立 Agent 会话、状态和日志。
- [ ] 支持持续任务队列，避免只依赖内存线程。
- [ ] 支持工作区文件工具权限，控制 Agent 能读写哪些目录和文件。

## 3. MVP 目标

第一版只验证一件事：

> 用户可以创建和配置一个 AI 公司，并让总经理、副经理和若干岗位 Agent 在指定工作区内完成一条可追踪、可继续推进的协作流程。

MVP 不追求复杂自治，也不做完全开放式多 Agent 网络。先做固定组织结构 + 可编辑岗位 + 本地中转 + 工作区会话 + 半自动持续执行流。

## 4. 技术路线

- [x] 桌面端：Tauri
- [x] 前端：React + TypeScript + Vite
- [x] 本地 API：FastAPI
- [x] 本地数据库：SQLite + SQLModel
- [x] 模型调用：通过本地 API 服务统一中转
- [x] 状态持久化：SQLite
- [ ] 长时间任务执行：独立 worker / 队列 / 进程管理

## 5. 已完成的第一轮骨架

- [x] 创建项目级目录 `ai-company`
- [x] 初始化前端桌面应用骨架
- [x] 初始化 FastAPI 服务骨架
- [x] 接入 SQLite 数据库
- [x] 创建基础 README 和项目文档目录
- [x] 整理参考文档内容到项目文档
- [x] 整理 `new-api` 与 `codex-proxy` 可复用内容到 `docs/upstream-relay-fuel-reference.md`
- [x] 设计现代化深色科技感操作页面
- [x] 实现左侧 Tab 页面切换

## 6. 核心概念

### 6.1 公司 Company

- [ ] 创建默认 AI 公司
- [ ] 设置公司名称
- [ ] 设置公司描述
- [ ] 保存公司基础配置
- [ ] 展示公司当前组织架构

第一版可以只支持一个公司，暂不做多公司切换。

### 6.2 岗位 Role / Agent

每个岗位都是一个可执行 Agent。

建议字段：

- `id`
- `name`
- `title`
- `department`
- `level`
- `parent_role_id`
- `responsibility`
- `system_prompt`
- `output_format`
- `model_provider`
- `model_name`
- `tool_permissions`
- `enabled`

TODO:

- [x] 内置默认岗位模板
- [x] 支持查看岗位列表
- [x] 支持新增岗位
- [x] 支持编辑岗位名称
- [x] 支持编辑岗位职责
- [x] 支持编辑岗位 system prompt
- [x] 支持启用/停用岗位
- [x] 支持删除岗位
- [x] 支持配置使用模型
- [x] 支持保存岗位配置到 SQLite
- [ ] 支持配置直属上级并在组织架构中展示
- [ ] 总经理和副经理默认不可删除或需要二次确认
- [ ] 支持岗位工具权限配置

### 6.3 默认组织架构

```text
Boss / 用户
└── 总经理
    └── 副经理
        ├── 产品经理
        ├── 技术负责人
        ├── 工程师
        ├── 测试员
        └── 运营 / 市场
```

角色职责：

- 总经理：理解用户目标，制定公司级计划，最终汇总交付。
- 副经理：拆解任务，分派岗位，跟进输出，做中间整合。
- 产品经理：梳理需求、用户故事、验收标准。
- 技术负责人：设计技术方案、模块边界、风险点。
- 工程师：输出实现方案、代码草案、操作步骤。
- 测试员：检查边界条件、测试用例、质量风险。
- 运营 / 市场：输出推广、表达、用户侧建议。

TODO:

- [x] 生成默认岗位数据
- [x] 组织架构页面展示角色概览
- [x] 任务执行时只调用 enabled 岗位
- [ ] 组织架构页面展示上下级关系
- [ ] 支持拖动或选择方式调整上下级关系

## 7. 工作区与持续运行

用户希望真实使用方式更接近：

1. 用户进入某个项目目录。
2. 用户执行命令 `star ai-company`。
3. App 将当前活跃运行目录切换到这个命令执行目录。
4. 后续 Agent 会话、任务、日志、文件操作都围绕该工作区持续进行。

当前状态：

- [x] 新增工作区模型 `Workspace`
- [x] 新增 Agent 会话模型 `AgentSession`
- [x] 新增会话事件模型 `AgentSessionEvent`
- [x] 支持工作区列表、新建和选择
- [x] 支持 `star ai-company` 命令切换活跃工作区
- [x] 支持 `star ai-company <name/path/id>` 匹配并切换工作区
- [x] 前端按活跃工作区过滤会话
- [x] 会话支持 start / pause / stop / tick
- [x] 会话事件流可以查看
- [x] 命令行侧真正注册 `star ai-company`
- [x] 从命令执行目录自动创建或绑定工作区
- [x] 后端提供 `POST /workspaces/activate` 和 `GET /workspaces/active`
- [x] 前端轮询 active workspace，外部命令执行后自动同步
- [x] 将工作区路径传递给 Agent Worker Run cwd
- [ ] 将工作区路径传递给真实 worker 进程 cwd
- [ ] 支持多个持续会话并发运行
- [ ] 支持 App 重启后恢复会话状态
- [ ] 支持会话心跳、失败恢复和超时处理

## 8. 协作执行流

MVP 固定执行流：

```text
1. Boss 输入任务
2. 总经理理解目标并制定总体计划
3. 副经理拆解任务并选择参与岗位
4. 各岗位分别执行自己的部分
5. 副经理整合岗位输出并检查缺口
6. 总经理生成最终交付结果
```

TODO:

- [x] 创建任务
- [x] 保存任务目标
- [x] 记录任务状态
- [x] 支持手动运行某个岗位
- [x] 记录任务步骤输入和输出
- [ ] 选择任务参与岗位
- [ ] 支持一键运行完整公司协作流程
- [ ] 支持失败重试
- [ ] 支持用户打回后追加要求
- [ ] 支持在持续会话中按节奏自动推进任务

第一版任务状态：

- `draft`
- `running`
- `waiting_review`
- `completed`
- `failed`

## 9. 本地 API 中转与燃料中心

前端不直接调用模型 API。所有模型调用都经过本地服务。

本地中转职责：

- 检查登录状态
- 读取岗位配置
- 拼接 Agent prompt
- 选择可用上游账号
- 调用外部模型 API
- 保存调用日志
- 统计 token 消耗
- 返回结果给桌面端

当前状态：

- [x] 实现本地 FastAPI 服务
- [x] 前端请求 localhost API
- [x] 新增上游账号 / 燃料账号模型
- [x] 支持 OpenAI-compatible API Key 作为第一类燃料
- [x] 支持 Provider 预设：OpenAI/GPT、DeepSeek、Qwen/DashScope、GLM/智谱、GLM/Z.AI、SiliconFlow、自定义兼容上游
- [x] 支持登录凭据导入接口 `/relay/accounts/import-login`
- [x] 支持前端从官方账号页获取凭据后导入燃料池
- [x] DeepSeek 预设加入 `deepseek-v4-flash`、`deepseek-v4-pro`
- [x] 支持配置 `base_url`、`api_key`、支持模型、状态、优先级
- [x] 支持上游账号启用 / 停用
- [x] 支持上游账号测试
- [x] 支持删除上游账号
- [x] 支持模型调用中转 `/relay/*`
- [x] 支持调用日志保存
- [x] 支持 usage summary 概况接口
- [x] 前端燃料中心展示概况卡片
- [x] 支持记录 input_tokens / output_tokens / cached_tokens
- [ ] 支持 least_used 账号选择策略
- [ ] 支持真正的浏览器 OAuth / 网页登录态自动同步
- [ ] 支持按供应商显示剩余额度、到期时间和可用模型
- [ ] 支持跳过额度耗尽或不可用账号
- [ ] 支持真实缓存命中率精确统计
- [ ] 支持账号级额度、预算和告警

参考文档：

- [docs/upstream-relay-fuel-reference.md](docs/upstream-relay-fuel-reference.md)

已规划接口：

```text
GET    /relay/accounts
POST   /relay/accounts
PUT    /relay/accounts/{account_id}
DELETE /relay/accounts/{account_id}
POST   /relay/accounts/{account_id}/test

GET    /relay/usage/summary
GET    /relay/logs
POST   /relay/chat/completions
```

## 10. 数据表

当前已纳入或规划的数据表：

- [ ] companies
- [x] roles
- [x] tasks
- [x] task_steps
- [x] relay_accounts
- [x] model_call_logs
- [x] workspaces
- [x] agent_sessions
- [x] agent_session_events
- [ ] messages
- [ ] provider_settings
- [ ] local_sessions

后续需要补充：

- [ ] workspace_files
- [x] agent_worker_runs
- [ ] agent_memory_items
- [ ] task_queue_items

## 11. 前端页面

当前页面：

- [x] 任务大厅
- [x] 燃料中心
- [x] 组织架构
- [x] 工作区
- [x] 岗位配置
- [x] 调用日志
- [x] 设置中心

前端设计要求：

- [x] 现代化深色科技感控制台
- [x] 圆角图标和现代化操作页面
- [x] 左侧导航 Tab 切换
- [x] 当前活跃工作区展示
- [x] 命令输入条支持 `star ai-company`
- [ ] 页面动效和状态反馈进一步打磨
- [ ] 表单校验和错误提示完善
- [ ] 空状态、加载态、失败态完善

## 12. Prompt 模板

### 12.1 总经理

```text
你是这家 AI 公司的总经理。你的职责是理解 Boss 的目标，制定总体计划，判断需要哪些岗位参与，并在所有岗位输出后生成最终交付结果。

你需要：
1. 明确任务目标
2. 识别关键约束
3. 给副经理分派拆解方向
4. 最终汇总为可执行、清晰、对 Boss 有价值的结果
```

### 12.2 副经理

```text
你是这家 AI 公司的副经理。你的职责是把总经理的计划拆成岗位任务，协调不同岗位执行，并检查输出是否完整。

你需要：
1. 拆分任务
2. 指定参与岗位
3. 给每个岗位明确输入
4. 整合各岗位输出
5. 指出缺口和风险
```

## 13. MVP 验收标准

第一版完成时，需要能做到：

- [ ] 用户可以打开桌面端 App
- [ ] 用户可以配置上游燃料账号
- [ ] 用户可以查看 token 消耗概况
- [ ] 系统自动生成默认 AI 公司
- [x] 系统自动生成总经理、副经理和至少 4 个部门岗位
- [x] 用户可以创建、编辑、启用、停用岗位
- [x] 岗位配置改为弹窗式编辑，点击编辑/新建后在 Modal 中操作
- [x] 用户可以创建任务
- [x] 每个岗位输出能被保存和查看
- [x] 所有模型调用都经过本地 API 中转
- [x] 任务历史保存到 SQLite
- [x] 用户可以创建或选择工作区
- [x] 用户可以通过 `star ai-company` 切换 App 当前活跃工作区
- [x] Agent Worker Run 能记录工作区 cwd、角色、模型、状态和 token
- [x] 持续会话 Worker Run 的 token 会同步进入模型调用日志和燃料消耗统计
- [ ] Agent Worker 真实进程在工作区 cwd 中运行
- [ ] 多角色可以在工作区内持续推进一个任务
- [ ] App 重启后可以恢复工作区、任务和会话状态

## 14. 暂不做的功能

- [ ] 多公司管理
- [ ] 多用户协作
- [ ] 云端同步
- [ ] 复杂权限体系
- [ ] Agent 自主创建新 Agent
- [ ] 无限递归协作
- [ ] 插件市场
- [ ] 浏览器自动化
- [ ] 长期记忆系统
- [ ] 成本预算和额度控制的完整商业化版本

注意：工作区文件工具、真实 worker cwd、持续任务队列虽然复杂，但已经进入后续 MVP 路线，不再归类为“暂不做”。

## 15. 下一步代码实现顺序

建议继续按下面顺序推进：

- [x] 第一轮：项目骨架、文档、前端基础页面、API 基础结构
- [x] 第二轮：左侧 Tab 切换、燃料中心、调用日志、概况卡片
- [x] 第三轮：可编辑角色、岗位配置 CRUD、任务持久化
- [x] 第四轮：工作区、持续会话数据结构、`star ai-company` 活跃工作区切换
- [x] 第五轮：命令行入口，支持从真实 cwd 执行 `star ai-company`
- [x] 第六轮：Agent Worker 抽象，让 worker 在工作区 cwd 中执行
- [ ] 第七轮：持续任务队列，把内存线程替换为可恢复 worker 运行记录
- [ ] 第八轮：文件工具权限和工作区读写能力
- [ ] 第九轮：多角色协作编排器，总经理/副经理/岗位轮转推进任务
- [ ] 第十轮：会话恢复、失败重试、运行监控和交付结果页面
