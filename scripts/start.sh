#!/usr/bin/env bash
# Manual start (systemd handles auto-start after setup.sh).
set -euo pipefail
INSTALL_DIR="/opt/japanesetutor"
export TUTOR_BASE_DIR="${INSTALL_DIR}"
cd "${INSTALL_DIR}"
"${INSTALL_DIR}/venv/bin/uvicorn" server.main:app --host 127.0.0.1 --port 8000
