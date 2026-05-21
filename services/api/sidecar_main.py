import os
import sys
from pathlib import Path

import uvicorn


def app_data_dir() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "AI Company"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AI Company"
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "ai-company"


def main() -> None:
    data_dir = app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{data_dir / 'ai_company.db'}")
    os.environ.setdefault("LOCAL_SESSION_SECRET", "local-sidecar-session")

    host = os.environ.get("AI_COMPANY_API_HOST", "127.0.0.1")
    port = int(os.environ.get("AI_COMPANY_API_PORT", "8787"))
    uvicorn.run("app.main:app", host=host, port=port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
