# AI Company

本地优先的 AI 公司桌面工作台。用户作为 Boss 配置一个由总经理、副经理和部门岗位 Agent 组成的虚拟公司，并通过本地 API 中转服务调度多个 Agent 协作完成任务。

## Project Layout

```text
ai-company/
├── ai-company-mvp-todo.md
├── apps/
│   └── desktop/          # Tauri + React desktop shell
├── services/
│   └── api/              # FastAPI local API relay
├── cli/                  # star ai-company command
└── docs/
```

## MVP Stack

- Desktop: Tauri
- Frontend: React + TypeScript + Vite
- Local API: FastAPI
- Database: SQLite
- Model calls: local API relay only

## Project Docs

- [MVP TODO](ai-company-mvp-todo.md)
- [Architecture](docs/architecture.md)
- [Star Command](docs/star-command.md)
- [Release Build](docs/release-build.md)
- [Upstream Relay Fuel Reference](docs/upstream-relay-fuel-reference.md)

## First Run

Desktop:

```bash
cd apps/desktop
npm install
npm run dev
```

API:

```bash
cd services/api
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --port 8787
```

Install the workspace command:

```powershell
npm run cli:install
```

Open a new terminal in any project directory:

```powershell
star ai-company
```

## Release Build

Push a version tag to build desktop packages:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions will build Windows, Linux, macOS Intel, and macOS Apple Silicon packages with the FastAPI local relay included as a Tauri sidecar. Tags matching `v*` or `V*` trigger the release workflow.
