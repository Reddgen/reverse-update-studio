#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo "Not installed yet. Run: $ROOT/install.sh" >&2
  exit 1
fi
cd "$ROOT"
exec "$ROOT/.venv/bin/python" studio/server.py --port 8765 --open
