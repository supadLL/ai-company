# `star ai-company` 命令入口

`star ai-company` 用来把当前终端目录注册为 AI Company 的活跃工作区。

## 使用方式

先确保本地 API 正在运行：

```powershell
cd D:\桌面\play\ai-company\services\api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
```

安装命令：

```powershell
cd D:\桌面\play\ai-company
npm run cli:install
```

进入任意工作区后执行：

```powershell
star ai-company
```

也可以显式传入路径：

```powershell
star ai-company D:\some\workspace
```

## 行为

- CLI 读取当前目录或传入路径。
- 请求本地 API：`POST /workspaces/activate`。
- 如果路径对应的工作区不存在，自动创建。
- 如果存在，切换为当前活跃工作区。
- 其他 active 工作区会被标记为 `idle`。
- 前端会定期读取 `/workspaces/active`，自动同步当前活跃工作区。

## 环境变量

默认 API 地址是：

```text
http://127.0.0.1:8787
```

可以通过 `AI_COMPANY_API` 覆盖：

```powershell
$env:AI_COMPANY_API = "http://127.0.0.1:8787"
star ai-company
```
