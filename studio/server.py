#!/usr/bin/env python3
"""Reverse Update Studio - local, responsive web UI for the toolkit."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
try:
    from format_probe import probe_file
except Exception:
    probe_file = None

APP_NAME = "Reverse Update Studio"
APP_VERSION = "0.2.0"
ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
# In the portable bundle the server lives beside runtime/, tools/ and reports/.
# In the source tree it lives under reverse_update/ and the workspace is one level up.
WORKSPACE = Path(os.environ.get("RU_WORKSPACE") or (BASE if (BASE / "runtime").exists() else BASE.parent))
STATIC = ROOT / "static"
WORK = Path(os.environ.get("RU_WORK") or (ROOT / "work"))
WORK.mkdir(parents=True, exist_ok=True)
UPLOAD = WORK / "uploads"
UPLOAD.mkdir(parents=True, exist_ok=True)

PY = os.environ.get("RU_PYTHON") or sys.executable
TOOLS = BASE / "tools"
WORKSPACE_TOOLS = WORKSPACE / "tools"
POWERSHELL = shutil.which("powershell") or r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe"
NODE = (os.environ.get("RU_NODE")
        or (WORKSPACE / "runtime" / "node" / "node.exe" if (WORKSPACE / "runtime" / "node" / "node.exe").exists() else None)
        or shutil.which("node") or r"C:\Program Files\nodejs\node.exe")
GHIDRA_DIR = Path(os.environ.get("GHIDRA_INSTALL_DIR") or (WORKSPACE / "tools" / "ghidra_12.1.4_PUBLIC"))
REA_BIN = WORKSPACE / "tools" / "rea-runtime" / "node_modules" / ".bin" / "rea.cmd"
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
sys.path.insert(0, str(BASE))
try:
    from path_trace import PathTracer
    TRACER = PathTracer(WORK / "traces.sqlite",
                        WORKSPACE / "path_library.json",
                        WORKSPACE / "path_model.json")
except Exception:
    TRACER = None
JOBS_FILE = WORK / "jobs.json"


def save_jobs():
    try:
        with JOBS_LOCK:
            jobs = sorted(JOBS.values(), key=lambda j: j.get("created", 0), reverse=True)[:100]
            text = json.dumps(jobs, ensure_ascii=False)
        tmp = JOBS_FILE.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(JOBS_FILE)
    except Exception:
        pass


def load_jobs():
    try:
        if not JOBS_FILE.exists():
            return
        data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return
        with JOBS_LOCK:
            for job in data[:100]:
                if not isinstance(job, dict) or not job.get("id"):
                    continue
                if job.get("status") in ("queued", "running"):
                    job["status"] = "failed"
                    job["error"] = "interrupted by app restart"
                    job["finished"] = time.time()
                JOBS[job["id"]] = job
    except Exception:
        pass


load_jobs()

EXECUTOR = ThreadPoolExecutor(max_workers=2)
ALLOWED_ROOTS: list[Path] = []
ACCESS_PIN = ""
CALLGRAPH_CACHE: dict[tuple[str, float, str], dict] = {}
CALLGRAPH_LOCK = threading.Lock()


def resolve_user_path(raw: str, must_exist: bool = True, allow_dir: bool = False) -> Path:
    p = Path(raw).expanduser().resolve()
    if ALLOWED_ROOTS:
        allowed = any(p == r or r in p.parents for r in ALLOWED_ROOTS)
        if not allowed:
            raise ValueError(f"path is outside allowed roots: {p}")
    if must_exist:
        if not p.exists():
            raise ValueError(f"path not found: {p}")
        if not allow_dir and not p.is_file():
            raise ValueError(f"not a file: {p}")
    return p


def json_load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def tool_exists(name: str) -> bool:
    return (TOOLS / name).exists()


def node_exists() -> bool:
    return bool(NODE and Path(NODE).exists())


def find_vscode() -> str | None:
    found = shutil.which("code")
    if found:
        return found
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft VS Code" / "Code.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft VS Code" / "Code.exe",
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return None


def detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        with path.open("rb") as f:
            head = f.read(64)
            f.seek(0x1C)
            magic1c = f.read(4)
    except Exception:
        return "unreadable"
    if head.startswith(b"MZ"):
        return "PE / Windows executable"
    if head.startswith(b"\x7fELF"):
        return "ELF executable"
    if head.startswith(b"RVZ"):
        return "GameCube/Wii RVZ"
    if head.startswith(b"SCEUF"):
        return "PS3 firmware PUP"
    if head.startswith(b"PK\x03\x04"):
        return "ZIP archive"
    if magic1c == b"\xc2\x33\x9f\x3d":
        return "GameCube disc image" + (" (NKit)" if suffix == ".nkit.iso" else "")
    if suffix in (".gba", ".gb", ".gbc"):
        return "Game Boy / GBA ROM"
    if suffix == ".dol":
        return "GameCube/Wii DOL"
    if suffix in (".iso", ".bin", ".cue"):
        return "Disc image"
    return "unknown"


def safe_file_info(path: Path, do_hash: bool = True) -> dict:
    probe = probe_file(path) if probe_file else None
    info = {
        "path": str(path),
        "name": path.name,
        "size": path.stat().st_size,
        "format": (probe or {}).get("format") or detect_format(path),
        "suffix": path.suffix.lower(),
    }
    if probe:
        info["probe"] = probe
        info["capabilities"] = probe.get("capabilities", [])
        info["function_diff"] = bool(probe.get("function_diff"))
    if do_hash and info["size"] <= 256 * 1024 * 1024:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        info["sha256"] = h.hexdigest()
    else:
        info["sha256"] = None
        info["hash_note"] = "skipped for files over 256 MB"
    return info


def parse_output(text: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    if start >= 0:
        try:
            return json.loads(text[start:])
        except Exception:
            pass
    return {"raw": text[-4000:]}


def run_cmd(cmd: list[str], timeout: int = 600) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(BASE))
    return {
        "returncode": p.returncode,
        "stdout": p.stdout[-12000:],
        "stderr": p.stderr[-6000:],
        "parsed": parse_output(p.stdout),
    }


def latest_ghidra_csv() -> Path | None:
    candidates = sorted((WORK.glob("*/functions.csv")), key=lambda p: p.stat().st_mtime, reverse=True)
    fallback = BASE / "reports" / "metroid_ghidra_functions.csv"
    if fallback.exists():
        candidates.append(fallback)
    return candidates[0] if candidates else None


def load_functions(csv_path: Path) -> list[dict]:
    funcs = []
    with csv_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith("address,"):
                continue
            parts = line.split(",")
            if len(parts) < 3:
                continue
            try:
                start = int(parts[0], 16)
                size = int(parts[2])
            except ValueError:
                continue
            funcs.append({"address": start, "name": parts[1], "size": size,
                          "thunk": parts[3].lower() == "true" if len(parts) > 3 else False})
    funcs.sort(key=lambda x: x["address"])
    return funcs


def find_function(funcs: list[dict], address: int):
    for f in funcs:
        if f["address"] == address:
            return f
    candidates = [f for f in funcs if f["address"] <= address < f["address"] + max(1, f["size"])]
    return max(candidates, key=lambda x: x["address"]) if candidates else None


def function_context(elf: Path, address: int, csv_path: Path | None) -> dict:
    sys.path.insert(0, str(WORKSPACE / ".pylibs"))
    sys.path.insert(0, str(TOOLS))
    try:
        import capstone
    except ImportError as e:
        raise ValueError("capstone is not installed; run: pip install -r studio/requirements.txt") from e
    import isolate_code

    if csv_path is None:
        csv_path = latest_ghidra_csv()
    if csv_path is None or not csv_path.exists():
        raise ValueError("no Ghidra function CSV found; run Ghidra first or provide csv")

    key = (str(elf), elf.stat().st_mtime, str(csv_path), csv_path.stat().st_mtime)
    with CALLGRAPH_LOCK:
        cache = CALLGRAPH_CACHE.get(key)
    if cache is None:
        b, machine, entry, segs = isolate_code.elf_segments(str(elf))
        if machine != 20:
            raise ValueError("function inspector currently supports PowerPC ELF")
        md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
        md.skipdata = True
        edges = []
        for s in segs:
            code = b[s["off"]:s["off"] + s["size"]]
            for ins in md.disasm(code, s["vaddr"]):
                if ins.mnemonic == "bl" and ins.op_str.startswith("0x"):
                    try:
                        target = int(ins.op_str, 16)
                    except ValueError:
                        continue
                    edges.append((ins.address, target))
        cache = {"bytes": b, "segs": segs, "edges": edges, "entry": entry}
        with CALLGRAPH_LOCK:
            CALLGRAPH_CACHE.clear()
            CALLGRAPH_CACHE[key] = cache

    funcs = load_functions(csv_path)
    fn = find_function(funcs, address)
    if fn is None:
        raise ValueError(f"no function contains {hex(address)}")
    start, size = fn["address"], max(1, fn["size"])
    end = start + size
    seg = next((s for s in cache["segs"] if s["vaddr"] <= start < s["vaddr"] + s["size"]), None)
    if seg is None:
        raise ValueError("function is not inside an executable segment")
    off = seg["off"] + (start - seg["vaddr"])
    code = cache["bytes"][off:off + min(size, 4096)]
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    md.skipdata = True
    disasm = []
    for ins in md.disasm(code, start):
        disasm.append({"address": hex(ins.address), "mnemonic": ins.mnemonic, "op_str": ins.op_str})
        if len(disasm) >= 250:
            break

    def name_of(addr):
        f = find_function(funcs, addr)
        return f["name"] if f else hex(addr)

    calls = [{"address": hex(src), "target": hex(dst), "name": name_of(dst)}
             for src, dst in cache["edges"] if start <= src < end]
    callers = [{"address": hex(src), "name": name_of(src)}
               for src, dst in cache["edges"] if start <= dst < end]
    calls = calls[:80]
    callers = callers[:80]

    pseudo = None
    for d in (BASE / "reports" / "metroid_top20_decomp", WORK):
        if not d.exists():
            continue
        for p in d.rglob(f"{hex(start)}_*.c"):
            pseudo = p.read_text(encoding="utf-8", errors="replace")[:30000]
            break
        if pseudo:
            break

    return {
        "elf": str(elf), "csv": str(csv_path), "function": {
            "address": hex(start), "name": fn["name"], "size": size, "end": hex(end), "thunk": fn["thunk"],
        },
        "disassembly": disasm,
        "calls": calls, "callers": callers,
        "pseudocode": pseudo,
    }


def job_worker(job_id: str, action: str, params: dict):
    out_dir = WORK / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        if action == "structure":
            cmd = [PY, str(TOOLS / "structure_scan.py"), params["path"], "--out", str(out_dir / "structure")]
        elif action == "dol":
            cmd = [PY, str(TOOLS / "rea_bridge.py"), params["path"], "--out", str(out_dir / "bridge")]
        elif action == "isolate":
            cmd = [PY, str(TOOLS / "isolate_code.py"), params["path"], "--out", str(out_dir / "isolated")]
        elif action == "triage":
            cmd = [PY, str(TOOLS / "pe_triage.py"), params["path"]]
        elif action == "ghidra":
            csv = out_dir / "functions.csv"
            cmd = [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                   str(WORKSPACE_TOOLS / "run_ghidra_ppc.ps1"),
                   "-InputElf", params["path"], "-OutputCsv", str(csv)]
        elif action == "release_diff":
            cmd = [PY, str(BASE / "release_diff.py"),
                   "--a", params["a"], "--b", params["b"],
                   "--label-a", params.get("label_a", "A"), "--label-b", params.get("label_b", "B"),
                   "--outdir", str(out_dir)]
        elif action == "ppc_diff":
            cmd = [PY, str(BASE / "ppc_diff.py"),
                   "--elf-a", params["elf_a"], "--csv-a", params["csv_a"],
                   "--elf-b", params["elf_b"], "--csv-b", params["csv_b"],
                   "--label-a", params.get("label_a", "A"), "--label-b", params.get("label_b", "B"),
                   "--outdir", str(out_dir)]
        elif action == "apk_diff":
            cmd = [PY, str(BASE / "apk_diff.py"),
                   "--a", params["a"], "--b", params["b"],
                   "--label-a", params.get("label_a", "A"), "--label-b", params.get("label_b", "B"),
                   "--outdir", str(out_dir)]
        elif action == "patch_apply":
            out = out_dir / (Path(params["output"]).name or "output")
            cmd = [NODE, str(TOOLS / "rp_cli.js"), "apply", params["clean"], params["patch"], str(out)]
        elif action == "patch_create":
            out = out_dir / (Path(params["output"]).name or "output")
            cmd = [NODE, str(TOOLS / "rp_cli.js"), "create", params["original"], params["modified"], params["format"], str(out)]
        else:
            raise ValueError("unknown action")
        result = run_cmd(cmd, timeout=900 if action != "ghidra" else 1500)
        if action == "ghidra" and result["returncode"] == 0:
            csv = out_dir / "functions.csv"
            rows = 0
            if csv.exists():
                rows = max(0, sum(1 for _ in csv.open("r", encoding="utf-8", errors="replace")) - 1)
            result["parsed"] = {"rows": rows, "csv": str(csv)}
        elif action == "release_diff" and result["returncode"] == 0:
            cmp_path = out_dir / "compare.json"
            if cmp_path.exists():
                payload = json.loads(cmp_path.read_text(encoding="utf-8"))
                summary = dict(payload.get("summary", {}))
                summary["builds"] = payload.get("builds")
                summary["outputs"] = {
                    "compare": str(cmp_path),
                    "pairs": str(out_dir / "pairs.csv"),
                    "changed": str(out_dir / "changed.csv"),
                }
                summary["changed_functions"] = [
                    {"name": p["name_a"], "source_a": p.get("source_a", ""),
                     "source_b": p.get("source_b", ""), "size_a": p["size_a"], "size_b": p["size_b"]}
                    for p in payload.get("pairs", []) if p.get("code_relation") == "changed"
                ][:200]
                result["parsed"] = summary
        elif action == "ppc_diff" and result["returncode"] == 0:
            res_path = out_dir / "result.json"
            if res_path.exists():
                payload = json.loads(res_path.read_text(encoding="utf-8"))
                summary = dict(payload.get("summary", {}))
                summary["builds"] = payload.get("builds")
                summary["outputs"] = payload.get("outputs")
                result["parsed"] = summary
        elif action == "apk_diff" and result["returncode"] == 0:
            res_path = out_dir / "result.json"
            if res_path.exists():
                payload = json.loads(res_path.read_text(encoding="utf-8"))
                summary = dict(payload.get("summary", {}))
                summary["builds"] = payload.get("builds")
                summary["outputs"] = payload.get("outputs")
                summary["changed_methods"] = [
                    {"class": p["a"]["class"], "name": p["a"]["name"],
                     "prototype": p["a"]["prototype"], "code_a": p["a"]["code_bytes"],
                     "code_b": p["b"]["code_bytes"]}
                    for p in payload.get("pairs", [])[:200]
                ]
                result["parsed"] = summary
        status = "done" if result["returncode"] == 0 else "failed"
        with JOBS_LOCK:
            JOBS[job_id].update({"status": status, "result": result, "finished": time.time()})
        save_jobs()
    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id].update({"status": "failed", "error": str(e), "finished": time.time()})
        save_jobs()


def new_job(action: str, params: dict) -> dict:
    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "action": action,
            "params": params,
            "status": "queued",
            "created": time.time(),
        }
    EXECUTOR.submit(job_worker, job_id, action, params)
    save_jobs()
    return JOBS[job_id]


def status_payload() -> dict:
    metrics = json_load(BASE / "reports" / "report_metrics.json", {}) or {}
    summary = (metrics.get("pairs", {}) or {}).get("v0.5.5->v0.5.6", {}).get("summary", {}) or {}
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "auth_required": bool(ACCESS_PIN),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "node": Path(NODE).name if node_exists() else None,
        "tools": {
            "dol_to_elf": tool_exists("dol_to_elf.py"),
            "rea_bridge": tool_exists("rea_bridge.py"),
            "structure_scan": tool_exists("structure_scan.py"),
            "isolate_code": tool_exists("isolate_code.py"),
            "constant_scan": tool_exists("constant_scan.py"),
            "pe_triage": tool_exists("pe_triage.py"),
            "patch_cli": node_exists() and tool_exists("rp_cli.js"),
            "ghidra": (GHIDRA_DIR / "support").exists(),
            "rea": REA_BIN.exists(),
        },
        "benchmark": {
            "functions": summary.get("symbols_a"),
            "matched": summary.get("matched_pairs"),
            "changed": summary.get("changed"),
        },
        "jobs": len(JOBS),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ReverseUpdateStudio/0.1"

    def log_message(self, fmt, *args):
        line = fmt % args
        line = re.sub(r"pin=[^&\s]+", "pin=[redacted]", line)
        sys.stderr.write("%s - %s\n" % (self.address_string(), line))

    def pin_ok(self):
        if not ACCESS_PIN:
            return True
        supplied = self.headers.get("X-RU-Pin", "")
        if not supplied:
            supplied = parse_qs(urlparse(self.path).query).get("pin", [""])[0]
        return bool(supplied) and hmac.compare_digest(str(supplied), str(ACCESS_PIN))

    def require_pin(self):
        if self.pin_ok():
            return True
        self.send_json({"error": "PIN required", "auth_required": True}, 401)
        return False

    def send_json(self, obj, code=200):
        data = json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_static(self, rel: str, content_type: str):
        path = (STATIC / rel).resolve()
        if not path.is_relative_to(STATIC.resolve()) or not path.exists() or not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache" if rel.endswith(".html") else "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def send_download(self, job_id: str, kind: str):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
        outputs = (job or {}).get("result", {}).get("parsed", {}).get("outputs", {})
        raw = outputs.get(kind)
        if not raw:
            self.send_error(404)
            return
        p = Path(raw).resolve()
        if not p.is_relative_to((WORK / job_id).resolve()) or not p.is_file():
            self.send_error(404)
            return
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json" if kind == "compare" else "text/csv")
        self.send_header("Content-Disposition", f'attachment; filename="{kind}-{job_id}.{"json" if kind == "compare" else "csv"}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/") and path != "/api/status" and not self.pin_ok():
            self.send_json({"error": "PIN required", "auth_required": True}, 401)
            return
        dl = re.fullmatch(r"/api/jobs/([A-Za-z0-9_-]+)/download/(changed|pairs|compare)", path)
        if dl:
            self.send_download(dl.group(1), dl.group(2))
            return
        if path == "/api/traces":
            self.send_json({"traces": TRACER.traces() if TRACER else []})
            return
        if path == "/api/puzzles":
            self.send_json({"puzzles": TRACER.puzzles() if TRACER else []})
            return
        if path in ("/", "/index.html"):
            self.send_static("index.html", "text/html; charset=utf-8")
        elif path == "/app.css":            self.send_static("app.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self.send_static("app.js", "application/javascript; charset=utf-8")
        elif path == "/manifest.webmanifest":
            self.send_static("manifest.webmanifest", "application/manifest+json")
        elif path == "/icon.svg":
            self.send_static("icon.svg", "image/svg+xml")
        elif re.fullmatch(r"/icon-\d+\.png", path):
            self.send_static(path.lstrip("/"), "image/png")
        elif path == "/sw.js":
            self.send_static("sw.js", "application/javascript; charset=utf-8")
        elif path == "/api/status":
            if ACCESS_PIN and not self.pin_ok():
                self.send_json({"app": APP_NAME, "version": APP_VERSION, "auth_required": True})
            else:
                self.send_json(status_payload())
        elif path == "/api/jobs":
            with JOBS_LOCK:
                jobs = sorted(JOBS.values(), key=lambda j: j["created"], reverse=True)
            self.send_json({"jobs": jobs[:50]})
        elif path.startswith("/api/jobs/"):
            jid = path.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = JOBS.get(jid)
            self.send_json(job or {"error": "not found"}, 200 if job else 404)
        else:
            self.send_error(404)

    def handle_upload(self):
        try:
            ctype = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in ctype:
                raise ValueError("multipart/form-data required")
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("empty upload")
            if length > 128 * 1024 * 1024:
                raise ValueError("upload limit is 128 MB; use a host path for large files")
            body = self.rfile.read(length)
            msg = BytesParser(policy=email_policy).parsebytes(
                b"Content-Type: " + ctype.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
            )
            saved = None
            for part in msg.iter_parts():
                filename = part.get_filename()
                data = part.get_payload(decode=True)
                if not filename or data is None:
                    continue
                safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name)[:120] or "upload.bin"
                out = UPLOAD / f"{uuid.uuid4().hex[:8]}_{safe}"
                out.write_bytes(data)
                saved = out
                break
            if not saved:
                raise ValueError("no file part found")
            self.send_json(safe_file_info(saved))
        except Exception as e:
            self.send_json({"error": str(e)}, 400)

    def do_POST(self):
        parsed = urlparse(self.path)
        if not self.require_pin():
            return
        if parsed.path == "/api/upload":
            self.handle_upload()
            return
        if parsed.path not in ("/api/inspect", "/api/function", "/api/browse", "/api/open_source", "/api/jobs", "/api/trace"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_000_000:
                raise ValueError("request too large")
            body = self.rfile.read(length) if length else b"{}"
            data = json.loads(body.decode("utf-8"))
        except Exception as e:
            self.send_json({"error": f"bad request: {e}"}, 400)
            return
        if parsed.path == "/api/inspect":
            raw = (data.get("path") or "").strip()
            if not raw:
                self.send_json({"error": "path required"}, 400)
                return
            p = resolve_user_path(raw, must_exist=True)
            try:
                self.send_json(safe_file_info(p))
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return
        if parsed.path == "/api/function":
            try:
                elf = resolve_user_path(data.get("elf", ""), must_exist=True)
                raw_addr = str(data.get("address", "")).strip()
                address = int(raw_addr, 16) if raw_addr.lower().startswith("0x") else int(raw_addr)
                csv_raw = str(data.get("csv", "")).strip()
                csv_path = resolve_user_path(csv_raw, must_exist=True) if csv_raw else None
                self.send_json(function_context(elf, address, csv_path))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if parsed.path == "/api/browse":
            try:
                kind = str(data.get("kind", "file")).lower()
                if kind not in ("file", "folder"):
                    raise ValueError("kind must be file or folder")
                title = str(data.get("title", "Select"))[:120]
                script = TOOLS / "browse_dialog.ps1"
                if not script.exists():
                    raise ValueError("browse dialog is not available in this build")
                r = run_cmd([POWERSHELL, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
                             "-File", str(script), "-Kind", kind, "-Title", title], timeout=300)
                if r["returncode"] != 0:
                    raise ValueError((r["stderr"] or "browse dialog failed")[-1000:])
                self.send_json(r["parsed"])
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if parsed.path == "/api/open_source":
            try:
                raw = str(data.get("path", "")).strip()
                if not raw:
                    raise ValueError("path required")
                p = Path(raw).expanduser().resolve()
                if ALLOWED_ROOTS and not any(p == r or r in p.parents for r in ALLOWED_ROOTS):
                    raise ValueError(f"path is outside allowed roots: {p}")
                if not p.exists() or not p.is_file():
                    raise ValueError(f"source file not found: {p}")
                if p.suffix.lower() not in (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
                                            ".inl", ".cs", ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt"):
                    raise ValueError(f"not a source/text file: {p.suffix}")
                line = max(1, int(data.get("line", 1)))
                code = find_vscode()
                if code:
                    if code.lower().endswith((".cmd", ".bat")):
                        cmd = ["cmd.exe", "/c", code, "-g", f"{p}:{line}"]
                    else:
                        cmd = [code, "-g", f"{p}:{line}"]
                    subprocess.Popen(cmd, cwd=str(p.parent), close_fds=True)
                    self.send_json({"opened": "vscode", "path": str(p), "line": line})
                else:
                    explorer = Path(os.environ.get("WINDIR", r"C:\Windows")) / "explorer.exe"
                    subprocess.Popen([str(explorer), "/select,", str(p)], close_fds=True)
                    self.send_json({"opened": "explorer", "path": str(p), "line": line})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if parsed.path == "/api/trace":
            try:
                if TRACER is None:
                    raise ValueError("path tracer unavailable")
                nodes = data.get("nodes", [])
                if isinstance(nodes, str):
                    nodes = [x.strip() for x in nodes.replace("\n", ",").split(",") if x.strip()]
                self.send_json(TRACER.trace(nodes))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        action = (data.get("action") or "").strip()
        allowed = {"structure", "dol", "isolate", "triage", "ghidra", "release_diff", "ppc_diff", "apk_diff", "patch_apply", "patch_create"}
        if action not in allowed:
            self.send_json({"error": f"action must be one of {sorted(allowed)}"}, 400)
            return
        params = data.get("params") or {}
        required = {
            "structure": ["path"], "dol": ["path"], "isolate": ["path"], "triage": ["path"],
            "ghidra": ["path"], "release_diff": ["a", "b"],
            "ppc_diff": ["elf_a", "csv_a", "elf_b", "csv_b"],
            "apk_diff": ["a", "b"],
            "patch_apply": ["clean", "patch", "output"],
            "patch_create": ["original", "modified", "format", "output"],
        }[action]
        missing = [k for k in required if not str(params.get(k, "")).strip()]
        if missing:
            self.send_json({"error": f"missing: {', '.join(missing)}"}, 400)
            return
        try:
            for key in ("path", "clean", "patch", "original", "modified", "output", "a", "b", "elf_a", "csv_a", "elf_b", "csv_b"):
                if params.get(key):
                    allow_dir = action == "release_diff" and key in ("a", "b")
                    params[key] = str(resolve_user_path(params[key], must_exist=(key != "output"), allow_dir=allow_dir))
        except Exception as e:
            self.send_json({"error": str(e)}, 400)
            return
        self.send_json(new_job(action, params), 202)


def main():
    # pythonw.exe has no console; keep startup prints from crashing the app.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true", help="open the browser")
    ap.add_argument("--pin", default=os.environ.get("RU_PIN", ""), help="require this PIN for API access")
    ap.add_argument("--allow-root", action="append", default=[], help="allow file paths under this root (repeatable)")
    args = ap.parse_args()
    global ALLOWED_ROOTS, ACCESS_PIN
    ALLOWED_ROOTS = [Path(x).expanduser().resolve() for x in args.allow_root]
    ACCESS_PIN = str(args.pin or "").strip()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print("WARNING: binding to a non-local address. Use only on a trusted LAN.", file=sys.stderr)
        if not ACCESS_PIN:
            print("ERROR: --pin is required when binding to a non-local address.", file=sys.stderr)
            sys.exit(2)
        if not ALLOWED_ROOTS:
            ALLOWED_ROOTS = [WORKSPACE]
            print(f"No --allow-root supplied; restricting paths to {WORKSPACE}", file=sys.stderr)
    if ACCESS_PIN:
        print("PIN protection enabled.", file=sys.stderr)
    if ALLOWED_ROOTS:
        print("Allowed roots:")
        for r in ALLOWED_ROOTS:
            print(f"  {r}")
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}/"
    print(f"{APP_NAME} {APP_VERSION}")
    print(f"Open: {url}")
    print("Press Ctrl+C to stop.")
    if args.open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
