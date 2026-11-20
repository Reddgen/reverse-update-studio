#!/usr/bin/env bash
# Build a Linux x86-64 AppImage on Linux.
# Requires: python3, python3-venv, pip, appimagetool.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${ROOT}/build/AppDir"
APPDIR="${BUILD}/ReverseUpdateStudio.AppDir"
DEST="${ROOT}/reports/Reverse_Update_Studio-x86_64.AppImage"

if [ "$(uname -s)" != "Linux" ]; then
  echo "ERROR: AppImage must be built on Linux." >&2
  exit 1
fi
command -v appimagetool >/dev/null || { echo "ERROR: appimagetool not installed." >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 not installed." >&2; exit 1; }

rm -rf "$BUILD"
mkdir -p "$APPDIR/usr/lib/reverse-update"
cp -a "${ROOT}/studio" "$APPDIR/usr/lib/reverse-update/"
for f in cli.py update_format.py update_cli.py path_trace.py path_cli.py \
         path_library.json path_model.json release_diff.py ppc_diff.py \
         ppc_fingerprint.py ppc_compare.py compare.py fingerprint.py \
         pdb_lines.py apk_diff.py enum_pdb.py; do
  [ -f "${ROOT}/${f}" ] && cp "${ROOT}/${f}" "$APPDIR/usr/lib/reverse-update/"
done
cp -a "${ROOT}/tools" "$APPDIR/usr/lib/reverse-update/" || true
mkdir -p "$APPDIR/usr/share/applications"

echo "Creating bundled Python environment..."
python3 -m venv "$APPDIR/usr/lib/reverse-update/.venv"
"$APPDIR/usr/lib/reverse-update/.venv/bin/python" -m pip install --upgrade pip >/dev/null
"$APPDIR/usr/lib/reverse-update/.venv/bin/pip" install -r "$APPDIR/usr/lib/reverse-update/studio/requirements.txt"

cat > "$APPDIR/reverse-update.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Reverse Update Studio
Exec=AppRun
Icon=reverse-update
Categories=Development;Utility;
Terminal=false
EOF
cp "$APPDIR/reverse-update.desktop" "$APPDIR/usr/share/applications/"
cp "${ROOT}/studio/static/icon-512.png" "$APPDIR/reverse-update.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
cd "$HERE/usr/lib/reverse-update"
exec "$HERE/usr/lib/reverse-update/.venv/bin/python" studio/server.py --port 8765 --open
EOF
chmod +x "$APPDIR/AppRun"

mkdir -p "$(dirname "$DEST")"
echo "Building AppImage..."
ARCH=x86_64 appimagetool --no-appstream "$APPDIR" "$DEST"
echo "Built: $DEST"
