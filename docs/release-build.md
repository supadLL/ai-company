# Release Build

AI Company uses GitHub Actions to build desktop packages when a version tag is pushed.

## Trigger

```powershell
git tag v0.1.0
git push origin v0.1.0
```

The release workflow builds:

- Windows x64
- Linux x64
- macOS Intel
- macOS Apple Silicon

## What Gets Packaged

The desktop app is a Tauri shell. The local FastAPI service is packaged as a Tauri sidecar:

```text
Tauri app
└── ai-company-api sidecar
    └── FastAPI local relay on 127.0.0.1:8787
```

The sidecar stores runtime data in a user data directory:

- Windows: `%LOCALAPPDATA%\AI Company`
- macOS: `~/Library/Application Support/AI Company`
- Linux: `$XDG_DATA_HOME/ai-company` or `~/.local/share/ai-company`

## Generated Release

The workflow creates a draft GitHub Release and uploads the installers/bundles produced by Tauri.

The draft release should be reviewed before publishing, especially while code signing and notarization are not configured.

## Current Signing Status

- Windows: unsigned
- macOS: unsigned and not notarized
- Linux: unsigned

Unsigned builds are usable for testing but may show operating system warnings.
