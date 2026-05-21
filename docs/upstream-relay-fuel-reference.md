# 上游中转燃料层参考总结

## 1. 目标

本项目 `AI Company` 需要一个本地优先的模型调用中转层。

推荐抽象为：

```text
下游调用方
  AI 公司桌面端 / 各岗位 Agent / 本地插件
        ↓
本地中转层
  登录鉴权 / 账号池 / 渠道路由 / 协议转换 / 用量统计 / 日志审计
        ↓
上游燃料
  OpenAI-compatible API Key / Codex 或 ChatGPT 账号 / Anthropic / Gemini / OpenRouter / 本地模型
```

这里的“燃料”指可被本地 AI 公司消耗的上游账号或 API Key。用户可以添加多个上游账号，系统根据模型、角色、任务、额度、状态和策略选择合适的上游执行请求。

## 2. 参考来源

### 2.1 `D:\桌面\play\new-api`

主要可借鉴内容：

- 渠道管理
- 上游 Base URL / Key / Model / Group 配置
- 多 Key 轮询
- 渠道权重、优先级、分组与失败重试
- 用户额度、Token 额度、预扣费、实际结算、失败退款
- 模型倍率、计费表达式、缓存 Token 维度
- 请求日志、错误日志、用量按时间聚合

重点文件：

- `model/channel.go`
- `service/channel_select.go`
- `service/billing_session.go`
- `service/pre_consume_quota.go`
- `service/token_counter.go`
- `model/log.go`
- `controller/usedata.go`
- `setting/ratio_setting/model_ratio.go`
- `pkg/billingexpr/types.go`

### 2.2 `D:\桌面\play\codex-proxy`

主要可借鉴内容：

- 多账号池
- free / plus / team / business 等 plan 路由
- 上游账号状态管理
- Token / refresh token 导入、刷新、过期、封禁、限流状态
- 账号轮换策略：least_used / round_robin / sticky
- session affinity，长对话尽量粘同一账号
- 真实 Token usage 抽取
- cached_tokens / cache hit rate 统计
- quota window / rate limit headers 解析
- 用量概况接口和历史快照
- API Key Provider 池与自定义模型路由

重点文件：

- `src/auth/account-pool.ts`
- `src/auth/account-registry.ts`
- `src/auth/account-lifecycle.ts`
- `src/auth/rotation-strategy.ts`
- `src/auth/types.ts`
- `src/auth/usage-stats.ts`
- `src/auth/quota-skip.ts`
- `src/routes/admin/usage-stats.ts`
- `src/routes/shared/streaming-handler.ts`
- `src/routes/shared/proxy-usage-log.ts`
- `src/routes/shared/proxy-rate-limit.ts`
- `src/translation/codex-event-extractor.ts`
- `web/src/pages/UsageStats.tsx`
- `shared/hooks/use-usage-stats.ts`
- `config/default.yaml`
- `src/config-schema.ts`

## 3. 可吸收到 AI Company 的核心设计

## 3.1 上游燃料模型

`new-api` 的 Channel 和 `codex-proxy` 的 AccountEntry 可以合并成 `AI Company` 的上游燃料模型。

建议拆成两个层级：

```text
Upstream Provider
  表示一种上游类型，例如 OpenAI-compatible、Anthropic、Gemini、Codex Account、本地 Ollama。

Fuel Account / Channel
  表示一个可实际消耗的账号、API Key 或多 Key 渠道。
```

建议字段：

```text
upstream_accounts
- id
- provider_type
- label
- account_kind            # api_key / oauth_account / local_model
- base_url
- encrypted_api_key
- encrypted_access_token
- encrypted_refresh_token
- plan_type               # free / plus / team / business / unknown
- status                  # active / disabled / expired / banned / quota_exhausted / rate_limited
- supported_models
- model_mapping
- group_name
- priority
- weight
- rotation_mode
- proxy_url
- last_used_at
- quota_fetched_at
- created_at
- updated_at
```

第一版可以只实现：

- OpenAI-compatible API Key
- 自定义 Base URL
- Codex / ChatGPT 账号先只保留表结构和 UI 入口，后续实现

## 3.2 上游选择策略

可从 `new-api` 借鉴：

- 按模型过滤可用渠道
- 按 group 区分用途
- 按 priority 优先级重试
- 按 weight 做加权选择
- 支持 auto group，从一个组失败后切换到下一组

可从 `codex-proxy` 借鉴：

- `least_used`：优先选择累计请求少的账号
- `round_robin`：按顺序轮询
- `sticky`：长任务或同一会话尽量粘同一个账号
- `skip_exhausted`：额度耗尽账号不再参与选择
- `max_concurrent_per_account`：单账号并发上限
- plan routing：某些模型只允许特定 plan 的账号执行

建议 MVP 策略：

```text
1. 过滤 enabled / active 账号
2. 过滤支持目标模型的账号
3. 跳过 quota_exhausted / rate_limited
4. 优先使用当前任务已绑定的 sticky account
5. 否则按 least_used 选择
6. 请求失败时按 priority / round_robin 重试
```

## 3.3 本地中转接口

本项目原有 `services/api` 可以扩展为本地 relay。

建议新增接口：

```text
GET  /relay/providers
POST /relay/providers
PUT  /relay/providers/{provider_id}

GET  /relay/accounts
POST /relay/accounts
PUT  /relay/accounts/{account_id}
POST /relay/accounts/{account_id}/test
POST /relay/accounts/{account_id}/refresh
POST /relay/accounts/{account_id}/disable

POST /relay/chat/completions
POST /relay/responses

GET  /relay/usage/summary
GET  /relay/usage/history
GET  /relay/logs
```

AI 公司内部调用时不直接拿上游 Key，而是调用：

```text
POST /tasks/{task_id}/run-role/{role_id}
```

服务端再内部走：

```text
role config
  → select fuel account
  → build upstream request
  → relay call
  → extract usage
  → write logs
  → return role output
```

## 3.4 真实 Token 用量统计

`codex-proxy` 中最值得吸收的是真实 usage 抽取。

建议统计字段：

```text
usage
- input_tokens
- output_tokens
- cached_tokens
- reasoning_tokens
- image_input_tokens
- image_output_tokens
- request_count
- error_count
- empty_response_count
```

概况页需要展示：

```text
总输入 Tokens
总输出 Tokens
总缓存命中 Tokens
缓存命中率
总请求数
失败请求数
启用上游账号数
当前可用账号数
按角色消耗
按任务消耗
按模型消耗
按上游账号消耗
```

缓存命中率：

```text
cache_hit_rate = cached_tokens / input_tokens
```

建议保留 `uncached_tokens`：

```text
uncached_tokens = input_tokens - cached_tokens
```

这对 AI 公司很有价值，因为多 Agent 协作会重复携带任务上下文，缓存命中能直接反映“上下文复用效率”。

## 3.5 用量历史快照

`codex-proxy` 的 `UsageStatsStore` 思路适合直接吸收：

- 定时记录累计快照
- 概况接口返回当前总量
- 历史接口返回 raw / five_min / hourly / daily 粒度
- 保留 baseline，避免删除账号后历史用量丢失

建议数据表：

```text
usage_snapshots
- id
- captured_at
- total_input_tokens
- total_output_tokens
- total_cached_tokens
- total_reasoning_tokens
- total_request_count
- total_error_count
- active_accounts
- total_accounts
```

```text
usage_baselines
- id
- scope
- input_tokens
- output_tokens
- cached_tokens
- reasoning_tokens
- request_count
- error_count
- updated_at
```

第一版可以不做复杂 baseline，但数据表需要预留。

## 3.6 预估扣费、实际结算、失败退款

`new-api` 的 BillingSession 设计可以转成 AI Company 的本地统计逻辑。

第一版不需要เงินจริง扣费，但需要类似生命周期：

```text
请求开始
  → 估算 tokens / 预算
  → 标记 running
  → 上游返回
  → 读取真实 usage
  → 写入 actual_usage
  → 更新账号累计消耗
  → 写入任务步骤日志

请求失败
  → 标记 failed
  → 不计入成功消耗
  → 记录错误与上游账号
```

后续如果需要“燃料余额”或“预算限制”，可以扩展成：

```text
pre_reserved_tokens
actual_tokens
delta_tokens
refund_tokens
```

## 3.7 调用日志与审计

`new-api` 的 Log 模型适合简化后吸收。

建议 `model_call_logs` 扩展：

```text
model_call_logs
- id
- task_id
- task_step_id
- role_id
- provider_account_id
- provider_type
- model
- status
- request_id
- upstream_request_id
- input_tokens
- output_tokens
- cached_tokens
- reasoning_tokens
- total_tokens
- cache_hit_rate
- latency_ms
- is_stream
- error_code
- error_message
- request_summary
- response_summary
- metadata_json
- created_at
```

其中 `metadata_json` 可放：

```text
selected_strategy
retry_count
plan_type
quota_snapshot
rate_limit_reset_at
cache_key
```

## 3.8 概况模板

需要在前端新增“燃料概况”页面或卡片。

建议第一版信息架构：

```text
燃料概况
├── 总消耗
│   ├── Input Tokens
│   ├── Output Tokens
│   ├── Cached Tokens
│   ├── Cache Hit Rate
│   └── Request Count
├── 上游账号池
│   ├── Total Accounts
│   ├── Active Accounts
│   ├── Disabled / Expired / Banned
│   └── Quota Exhausted
├── 消耗排行
│   ├── 按角色
│   ├── 按任务
│   ├── 按模型
│   └── 按上游账号
└── 历史趋势
    ├── 近 1 小时
    ├── 近 24 小时
    ├── 近 7 天
    └── 全部
```

前端卡片建议：

```text
Total Input
Total Output
Cached Tokens
Cache Hit Rate
Requests
Active Fuel
```

折线图建议：

- 蓝色：input tokens
- 绿色：output tokens
- 紫色：cached tokens
- 黄色：request count
- 青色：cache hit rate

## 4. 适配到 AI 公司角色系统

AI Company 和普通 API 网关不同，消耗应绑定到“公司执行链路”。

建议把每次模型调用同时归因到：

```text
公司 company
任务 task
任务步骤 task_step
岗位 role
上游账号 upstream_account
模型 model
```

这样概况页可以回答：

- 哪个岗位最耗 token？
- 哪个任务最耗 token？
- 总经理和副经理这种管理角色是否消耗过高？
- 哪些模型最常用？
- 哪个上游账号正在被频繁消耗？
- prompt cache 是否有效？

## 5. MVP 实施顺序

建议按以下顺序进入开发：

- [ ] 新增 `upstream_accounts` 数据表
- [ ] 新增 `relay_usage_snapshots` 数据表
- [ ] 扩展 `model_call_logs` 字段
- [ ] 实现 OpenAI-compatible Provider 配置
- [ ] 实现本地 relay 调用方法
- [ ] 实现 least_used 上游选择策略
- [ ] 实现真实 usage 提取并写入日志
- [ ] 实现 `/relay/usage/summary`
- [ ] 实现 `/relay/usage/history`
- [ ] 前端新增“燃料概况”卡片
- [ ] 前端新增上游账号管理入口
- [ ] 将角色执行流接入 relay，而不是直接调用模型

## 6. 第一版不要做的内容

为避免 MVP 失控，以下内容建议后置：

- [ ] 完整支付系统
- [ ] 多租户额度售卖
- [ ] 复杂的模型倍率后台
- [ ] 任意协议双向转换
- [ ] 自动绕过上游限制
- [ ] 非授权账号导入
- [ ] 大规模账号池并发调度
- [ ] 复杂风控规避逻辑
- [ ] WebSocket 池复用
- [ ] 多实例 Redis 分布式调度

## 7. 合规与边界

本项目应只支持用户添加其合法拥有、合法授权使用的上游账号或 API Key。

需要在 UI 和文档中明确：

- 上游账号是用户自己的“燃料”
- 本地中转只做统一调用、统计、审计和路由
- 不提供绕过上游服务条款的能力
- free / plus / team 等 plan 只用于能力识别和路由，不用于规避限制
- 敏感 token 必须加密存储
- 日志默认不保存完整 prompt，除非用户显式开启调试

## 8. 对当前项目文件的影响

建议后续修改点：

```text
services/api/app/routes/
  新增 relay.py
  新增 usage.py
  新增 upstream_accounts.py

services/api/app/db/
  新增 models.py 或拆分 schema

apps/desktop/src/
  新增 FuelOverview 页面
  新增 UpstreamAccounts 页面
  在当前指挥舱加入燃料概况卡片

ai-company-mvp-todo.md
  补充“燃料层 / 上游账号池 / Token 概况”任务
```

## 9. 推荐命名

为了贴合“AI 公司”的产品语言，建议不要直接叫 channel/account pool。

可以使用：

```text
Fuel Account      燃料账号
Fuel Pool         燃料池
Relay             本地中转
Provider          上游供应商
Usage Overview    消耗概况
Fuel Ledger       燃料账本
Call Audit        调用审计
```

其中 MVP 页面可以叫：

```text
燃料中心
```

