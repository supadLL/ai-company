import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIDECAR_NAME = "ai-company-api"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--onefile",
            "--name",
            SIDECAR_NAME,
            "--paths",
            str(ROOT / "services" / "api"),
            str(ROOT / "services" / "api" / "sidecar_main.py"),
        ],
        cwd=ROOT,
        check=True,
    )

    extension = ".exe" if sys.platform == "win32" else ""
    source = ROOT / "dist" / f"{SIDECAR_NAME}{extension}"
    destination_dir = ROOT / "apps" / "desktop" / "src-tauri" / "binaries"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{SIDECAR_NAME}-{args.target}{extension}"
    shutil.copy2(source, destination)
    print(f"Prepared Tauri sidecar: {destination}")


if __name__ == "__main__":
    main()
