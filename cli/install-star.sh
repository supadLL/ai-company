#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.ai-company/bin"

mkdir -p "$INSTALL_DIR"
cp "${SOURCE_DIR}/star" "${INSTALL_DIR}/star"
chmod +x "${INSTALL_DIR}/star"

case ":${PATH}:" in
  *":${INSTALL_DIR}:"*)
    echo "star command is already on PATH."
    ;;
  *)
    echo "Installed star command to ${INSTALL_DIR}."
    echo "Add this to your shell profile:"
    echo "export PATH=\"${INSTALL_DIR}:\$PATH\""
    ;;
esac

echo "Run: star ai-company"
