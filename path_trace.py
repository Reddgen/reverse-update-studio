"""Path tracing with a reusable library, puzzle-piece IDs and priority scoring.

A "path" is an ordered sequence of normalized node labels (function names,
library calls, file steps).  Known paths come from a JSON library.  Unknown
runs become deterministic puzzle pieces so they can be logged, counted and
reused across traces.
"""
import hashlib
import json
import math
import sqlite3
import threading
import time
import uuid
from pathlib import Path

FEATURES = ["novelty", "coverage", "library_hits", "reuse", "unknown_count"]
DEFAULT_WEIGHTS = {"novelty": 0.45, "coverage": -0.25, "library_hits": -0.15,
                   "reuse": 0.25, "unknown_count": 0.10, "bias": -0.15}


def norm(node: str) -> str:
    s = " ".join(str(node).strip().split())
    return s.lower()


def signature(nodes):
    return "|".join(norm(n) for n in nodes)


def puzzle_id(nodes):
    return "pz_" + hashlib.sha256(signature(nodes).encode("utf-8")).hexdigest()[:12]


def trace_id():
    return "tr_" + uuid.uuid4().hex[:12]


def _sigmoid(x):
    if x >= 0:
        return 1 / (1 + math.exp(-x))
    e = math.exp(x)
    return e / (1 + e)


def load_library(path: Path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("paths", data if isinstance(data, list) else [])


def match_sequences(nodes, templates):
    """Greedy longest contiguous matches. Returns (matches, matched_indices)."""
    n = len(nodes)
    matched = [False] * n
    matches = []
    candidates = []
    for t in templates:
        seq = [norm(x) for x in t.get("sequence", [])]
        if not seq:
            continue
        for start in range(0, n - len(seq) + 1):
            if [norm(x) for x in nodes[start:start + len(seq)]] == seq:
                candidates.append((len(seq), start, t))
    candidates.sort(key=lambda x: (-x[0], x[1]))
    for length, start, t in candidates:
        if any(matched[start:start + length]):
            continue
        for i in range(start, start + length):
            matched[i] = True
        matches.append({"library_id": t.get("id", ""), "name": t.get("name", ""),
                        "start": start, "end": start + length,
                        "confidence": float(t.get("confidence", 0.8)),
                        "tags": t.get("tags", [])})
    # deterministic order by position
    matches.sort(key=lambda m: m["start"])
    return matches, matched


def unmatched_runs(nodes, matched):
    runs, start = [], None
    for i, ok in enumerate(matched):
        if not ok and start is None:
            start = i
        if ok and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(nodes)))
    return runs


def features_for(nodes, matches, matched, reuse):
    total = max(1, len(nodes))
    unknown = sum(1 for x in matched if not x)
    return {
        "novelty": round(unknown / total, 4),
        "coverage": round((total - unknown) / total, 4),
        "library_hits": len(matches),
        "reuse": float(reuse),
        "unknown_count": unknown,
    }


def score(features, model=None):
    if model:
        w = {k: float(v) for k, v in model.get("weights", {}).items()}
        bias = float(model.get("bias", 0.0))
        # normalize the count feature for the model
        vals = dict(features)
        vals["unknown_count"] = min(1.0, vals["unknown_count"] / 10.0)
        z = bias + sum(w.get(k, 0.0) * vals.get(k, 0.0) for k in FEATURES)
        return round(_sigmoid(z), 4)
    w = DEFAULT_WEIGHTS
    z = w["bias"]
    z += w["novelty"] * features["novelty"]
    z += w["coverage"] * features["coverage"]
    z += w["library_hits"] * min(1.0, features["library_hits"] / 3.0)
    z += w["reuse"] * min(1.0, features["reuse"] / 5.0)
    z += w["unknown_count"] * min(1.0, features["unknown_count"] / 10.0)
    return round(_sigmoid(z), 4)


def label(priority):
    if priority >= 0.75:
        return "critical"
    if priority >= 0.55:
        return "high"
    if priority >= 0.35:
        return "medium"
    return "low"


class PathTracer:
    def __init__(self, db_path: Path, library_path: Path = None, model_path: Path = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.model = json.loads(Path(model_path).read_text()) if model_path and Path(model_path).exists() else None
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._schema()
        if library_path and Path(library_path).exists():
            self.import_library(Path(library_path))

    def _schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS library (
          id TEXT PRIMARY KEY, name TEXT, sequence TEXT, tags TEXT,
          confidence REAL, source TEXT, updated REAL
        );
        CREATE TABLE IF NOT EXISTS traces (
          id TEXT PRIMARY KEY, input TEXT, matches TEXT, puzzles TEXT,
          features TEXT, priority REAL, label TEXT, created REAL
        );
        CREATE TABLE IF NOT EXISTS puzzles (
          id TEXT PRIMARY KEY, signature TEXT, first_seen REAL, last_seen REAL,
          occurrences INTEGER, status TEXT, notes TEXT
        );
        """)
        self.conn.commit()

    def import_library(self, path: Path):
        for item in load_library(path):
            self.conn.execute(
                "INSERT INTO library(id,name,sequence,tags,confidence,source,updated) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name,sequence=excluded.sequence,"
                "tags=excluded.tags,confidence=excluded.confidence,source=excluded.source,updated=excluded.updated",
                (item.get("id", ""), item.get("name", ""), signature(item.get("sequence", [])),
                 json.dumps(item.get("tags", [])), float(item.get("confidence", 0.8)),
                 item.get("source", "library"), time.time()))
        self.conn.commit()

    def _templates(self):
        rows = self.conn.execute("SELECT * FROM library").fetchall()
        out = []
        for r in rows:
            out.append({"id": r["id"], "name": r["name"], "sequence": r["sequence"].split("|"),
                        "tags": json.loads(r["tags"] or "[]"), "confidence": r["confidence"]})
        return out

    def trace(self, nodes):
        with self.lock:
            return self._trace(nodes)

    def _trace(self, nodes):
        nodes = [str(n) for n in nodes if str(n).strip()]
        if not nodes:
            raise ValueError("empty path")
        matches, matched = match_sequences(nodes, self._templates())
        runs = unmatched_runs(nodes, matched)
        puzzles = []
        reuse = 1
        for start, end in runs:
            seg = nodes[start:end]
            pid = puzzle_id(seg)
            row = self.conn.execute("SELECT occurrences FROM puzzles WHERE id=?", (pid,)).fetchone()
            occurs = (row["occurrences"] if row else 0) + 1
            self.conn.execute(
                "INSERT INTO puzzles(id,signature,first_seen,last_seen,occurrences,status,notes) "
                "VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,"
                "occurrences=excluded.occurrences",
                (pid, signature(seg), time.time(), time.time(), occurs, "unknown", ""))
            reuse = max(reuse, occurs)
            puzzles.append({"id": pid, "nodes": seg, "start": start, "end": end,
                            "occurrences": occurs, "status": "unknown"})
        feats = features_for(nodes, matches, matched, reuse)
        pr = score(feats, self.model)
        tid = trace_id()
        result = {
            "trace_id": tid, "nodes": nodes, "matches": matches, "puzzles": puzzles,
            "features": feats, "priority": pr, "priority_label": label(pr),
            "created": time.time(),
        }
        self.conn.execute("INSERT INTO traces(id,input,matches,puzzles,features,priority,label,created) "
                          "VALUES(?,?,?,?,?,?,?,?)",
                          (tid, json.dumps(nodes), json.dumps(matches), json.dumps(puzzles),
                           json.dumps(feats), pr, result["priority_label"], result["created"]))
        self.conn.commit()
        return result

    def traces(self, limit=50):
        with self.lock:
            rows = self.conn.execute("SELECT * FROM traces ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r, matches=json.loads(r["matches"]), puzzles=json.loads(r["puzzles"]),
                     features=json.loads(r["features"])) for r in rows]

    def puzzles(self, limit=100):
        with self.lock:
            rows = self.conn.execute("SELECT * FROM puzzles ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def train(rows, iterations=1500, lr=0.08):
    """Train logistic regression from rows: {"features": {...}, "label": 0|1}."""
    xs, ys = [], []
    for r in rows:
        f = r.get("features", r)
        vals = [float(f.get("novelty", 0)), float(f.get("coverage", 0)),
                min(1.0, float(f.get("library_hits", 0)) / 3.0),
                min(1.0, float(f.get("reuse", 1)) / 5.0),
                min(1.0, float(f.get("unknown_count", 0)) / 10.0)]
        xs.append(vals)
        ys.append(float(r.get("label", r.get("priority", 0))))
    w = [0.0] * len(FEATURES)
    b = 0.0
    for _ in range(iterations):
        gw = [0.0] * len(w)
        gb = 0.0
        for x, y in zip(xs, ys):
            p = _sigmoid(b + sum(wi * xi for wi, xi in zip(w, x)))
            err = p - y
            for i in range(len(w)):
                gw[i] += err * x[i]
            gb += err
        n = max(1, len(xs))
        w = [wi - lr * (gwi / n + 0.001 * wi) for wi, gwi in zip(w, gw)]
        b -= lr * gb / n
    return {"features": FEATURES, "weights": dict(zip(FEATURES, [round(x, 6) for x in w])),
            "bias": round(b, 6)}
