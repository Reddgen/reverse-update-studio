#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10+." >&2
  exit 1
fi
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "ERROR: Python 3.10+ required." >&2
  exit 1
fi

echo "Creating virtual environment..."
"$PYTHON" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --upgrade pip >/dev/null
"$ROOT/.venv/bin/pip" install -r "$ROOT/studio/requirements.txt"

BIN="${HOME}/.local/bin"
mkdir -p "$BIN"
cat > "$BIN/reverse-update" <<EOF
#!/usr/bin/env bash
exec "$ROOT/.venv/bin/python" "$ROOT/cli.py" "\$@"
EOF
chmod +x "$BIN/reverse-update"

echo
echo "Installed."
echo "Run:        $ROOT/run.sh"
echo "CLI:        $BIN/reverse-update version"
echo "If ~/.local/bin is not on PATH, add it:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
echo
echo "Optional tools (not bundled):"
echo "  GHIDRA_INSTALL_DIR=/opt/ghidra"
echo "  JAVA_HOME=/usr/lib/jvm/..."
echo "  RU_NODE=/usr/bin/node"
