#!/usr/bin/env python3
"""Smoke test for a running Reverse Update Studio server."""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def req(base, path, method="GET", body=None, timeout=60):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type", "")
        return resp.status, (json.loads(raw) if "json" in ctype else raw)


def check(name, fn):
    try:
        fn()
        print(f"PASS  {name}")
        return True
    except Exception as e:
        print(f"FAIL  {name}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--apk-a", required=True)
    ap.add_argument("--apk-b", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/")
    ok = []

    def status():
        s, j = req(base, "/api/status")
        assert j["app"] == "Reverse Update Studio"
        assert j["tools"]["ghidra"] is True
        assert j["tools"]["rea"] is True

    def home():
        s, b = req(base, "/")
        text = b.decode("utf-8", "replace")
        assert "Start here" in text
        assert "Compare two APKs" in text
        assert "helpBtn" in text

    def js():
        s, b = req(base, "/app.js")
        text = b.decode("utf-8", "replace")
        assert "apkHtml" in text
        assert "sourceRoot" in text

    def inspect_apk():
        s, j = req(base, "/api/inspect", "POST", {"path": args.apk_a})
        assert j["format"] == "Android APK"
        assert j["probe"]["details"]["dex_methods"] > 1000

    def trace():
        s, j = req(base, "/api/trace", "POST", {"nodes": "LoadConfig,ResolvePath,ParseXML,ApplyConfig,UnknownA"})
        assert j["trace_id"].startswith("tr_")
        assert j["puzzles"][0]["id"].startswith("pz_")
        assert 0 <= j["priority"] <= 1

    def puzzles():
        s, j = req(base, "/api/puzzles")
        assert isinstance(j["puzzles"], list)

    def apk_self():
        s, job = req(base, "/api/jobs", "POST", {
            "action": "apk_diff",
            "params": {"a": args.apk_a, "b": args.apk_b, "label_a": "self", "label_b": "self"},
        })
        jid = job["id"]
        for _ in range(120):
            s, j = req(base, f"/api/jobs/{jid}")
            if j["status"] in ("done", "failed"):
                break
            time.sleep(2)
        assert j["status"] == "done", j.get("error") or j.get("result", {}).get("stderr")
        p = j["result"]["parsed"]
        assert p["changed"] == 0, p
        assert p["removed"] == 0, p
        assert p["added"] == 0, p
        assert p["match_rate"] == 100.0, p
        s, csv = req(base, f"/api/jobs/{jid}/download/changed")
        assert csv.decode().startswith("class,method,prototype")

    for name, fn in [
        ("status/tools", status),
        ("dashboard HTML", home),
        ("app JS", js),
        ("path trace", trace),
        ("puzzle catalog", puzzles),
        ("APK inspect", inspect_apk),
        ("APK self-control", apk_self),
    ]:
        ok.append(check(name, fn))

    print(f"\n{sum(ok)}/{len(ok)} checks passed")
    sys.exit(0 if all(ok) else 1)


if __name__ == "__main__":
    main()
