#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3.12}"
command -v "$PYTHON" >/dev/null 2>&1 || { echo "Python 3.12 is required." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js 22 LTS is required." >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required." >&2; exit 1; }

if [[ ! -x .venv/bin/python ]]; then
  "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --timeout 120 --retries 5 -r backend/requirements.txt
NPM=(npm)
if [[ "$(npm --version | cut -d. -f1)" -lt 10 ]]; then
  NPM=(npx -y npm@11.6.2)
fi
"${NPM[@]}" --prefix frontend ci --no-audit --no-fund
(cd backend && ../.venv/bin/python -m app.detection train)
"${NPM[@]}" --prefix frontend run build
echo "RoadSecure setup complete. Run ./start.sh"
