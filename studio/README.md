# Reverse Update Studio

A local, responsive web UI over the Reverse Update toolkit.

One codebase runs in:

- desktop browsers on Windows, macOS and Linux;
- Android tablets/phones;
- iPad/iPadOS browsers;
- any modern browser on the same network.

It is a **web app**, not a native APK. Files are read from the host filesystem; nothing is uploaded to a cloud service.

## Run

```powershell
python studio/server.py --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

Auto-open the browser:

```powershell
python studio/server.py --port 8765 --open
```

Or double-click `studio\start.cmd` on Windows, or run `studio/start.sh`.

### Phone / tablet on the same LAN

```powershell
python studio/server.py --host 0.0.0.0 --port 8765 --pin 2468 --allow-root "/path/to/games"
```

Then open `http://<host-lan-ip>:8765/` on the tablet or phone. Enter the PIN in the lock screen.

Use a trusted network only. The PIN is sent over plain HTTP; it is not a substitute for TLS on an untrusted network. When binding to LAN, the server defaults to allowing only the workspace; add `--allow-root` for the folders you want to inspect.

### Uploads

Small files (up to 128 MB) can be uploaded from a phone/tablet using the **Upload** buttons. Large game ISOs should stay on the host and be referenced by path.

## What it can do

| View | Actions |
|---|---|
| Dashboard | tool availability, benchmark numbers, recent jobs |
| Analyze | inspect a file; structure scan; Ghidra PPC functions; DOL/ISO -> ELF; code isolation; PE triage; **compare two PE/PDB builds with source locations and Open**; **compare two PPC/ELF builds**; **compare two APK/DEX builds**; **Trace** path library/puzzle IDs/priority |
| Formats | PE/PDB, ELF, Mach-O, APK, IPA, JAR/class, WASM and archives â€” inspect; PE/PDB and PPC ELF also diff |
| Inspector | address/function context: boundaries, calls, callers, disassembly, saved pseudocode |
| Paths | native **Browse** dialog on Windows; typing a path still works |
| Patch | apply IPS/UPS/BPS/PPF/xdelta; create a patch |
| Jobs | background queue, persistent history, status, result JSON download |
| About | deployment and boundaries |

Long actions run in a two-worker background queue. The UI polls job status.

## API

```text
GET  /api/status
GET  /api/jobs
GET  /api/jobs/<id>
POST /api/inspect          {"path": "..."}
POST /api/browse           {"kind": "file" | "folder", "title": "..."}
POST /api/jobs             {"action": "structure", "params": {"path": "..."}}
```

Actions: `structure`, `dol`, `isolate`, `triage`, `ghidra`, `release_diff`, `ppc_diff`, `patch_apply`, `patch_create`.

Release diff:

```json
POST /api/jobs
{"action": "release_diff", "params": {
  "a": "C:\\build-a", "b": "C:\\build-b",
  "label_a": "0.27.0", "label_b": "0.27.1"
}}
```

`a` and `b` may be build folders or executables with matching PDBs. The job auto-detects x86/x64.

PowerPC diff:

```json
POST /api/jobs
{"action": "ppc_diff", "params": {
  "elf_a": "C:\\build-a\\main.elf", "csv_a": "C:\\build-a\\functions.csv",
  "elf_b": "C:\\build-b\\main.elf", "csv_b": "C:\\build-b\\functions.csv"
}}
```

Downloads for a finished diff job:

```text
GET /api/jobs/<id>/download/changed
GET /api/jobs/<id>/download/pairs
GET /api/jobs/<id>/download/compare
```

## Requirements

- Python 3.11+ (standard library only for the server);
- `capstone` and `pefile` for the analysis tools;
- Node 18+ for patch actions;
- optional Ghidra/REA for deeper analysis (not required by the UI).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r studio/requirements.txt
```

On a fresh machine, install these before the first analysis; the Inspector and structure scan need `capstone`, and PE triage needs `pefile`.

## Native packaging later

The same UI can be wrapped with Tauri or Capacitor for a desktop/mobile shell. The engine stays local; the wrapper only adds a window and file picker.

## Boundaries

- Static analysis only; the server does not execute games.
- No DRM, anti-cheat or signature bypass.
- Analysis is not a native port.
- The UI is local-first; binding to `0.0.0.0` exposes it to the LAN. Use `--pin` on any shared network.

