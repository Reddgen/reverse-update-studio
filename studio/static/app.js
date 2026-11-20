(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const state = { status: null, jobs: new Map(), polls: new Map() };
  let accessPin = sessionStorage.getItem("ru-pin") || "";

  const fmtBytes = (n) => {
    if (!Number.isFinite(n)) return "—";
    const u = ["B", "KB", "MB", "GB", "TB"];
    let i = 0, v = n;
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
    return `${v.toFixed(i ? 1 : 0)} ${u[i]}`;
  };
  const timeAgo = (ts) => {
    if (!ts) return "";
    const s = Math.max(0, Math.round(Date.now() / 1000 - ts));
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.round(s / 60)}m ago`;
    return `${Math.round(s / 3600)}h ago`;
  };
  const toast = (msg) => {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2600);
  };
  async function api(path, opts = {}) {
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    if (accessPin) headers["X-RU-Pin"] = accessPin;
    const res = await fetch(path, { ...opts, headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || `HTTP ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }
  function escape(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  const downloadHref = (id, kind) => `/api/jobs/${encodeURIComponent(id)}/download/${kind}${accessPin ? `?pin=${encodeURIComponent(accessPin)}` : ""}`;
  function sourceParts(s) {
    if (!s) return null;
    const m = String(s).match(/^(.*?):(\d+)$/);
    const raw = m ? m[1] : String(s);
    const line = m ? Number(m[2]) : 1;
    const sm = raw.match(/[\\/]source[\\/](.+)$/i);
    if (!sm) return null;
    return { rel: "source/" + sm[1].replace(/\\/g, "/"), line };
  }
  function sourceLabel(s) {
    const p = sourceParts(s);
    return p ? `${p.rel}:${p.line}` : (s || "—");
  }
  function localSource(s) {
    const p = sourceParts(s);
    const root = $("#sourceRoot")?.value.trim();
    if (!p || !root) return null;
    return root.replace(/[\\/]+$/, "") + "\\" + p.rel.replace(/\//g, "\\");
  }
  const sourceRoot = $("#sourceRoot");
  if (sourceRoot) {
    sourceRoot.value = localStorage.getItem("ru-source-root") || "";
    sourceRoot.addEventListener("input", () => localStorage.setItem("ru-source-root", sourceRoot.value));
  }
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".open-src");
    if (!btn) return;
    const parts = sourceParts(btn.dataset.src);
    const path = localSource(btn.dataset.src);
    if (!parts) { toast("No source mapping for this function."); return; }
    if (!path) {
      toast("Set a Source root first.");
      sourceRoot?.focus();
      return;
    }
    try {
      const r = await api("/api/open_source", { method: "POST", body: JSON.stringify({ path, line: parts.line }) });
      toast(r.opened === "vscode" ? "Opened in VS Code" : "Opened source file");
    } catch (err) {
      toast(err.message);
    }
  });

  // navigation
  function showView(name) {
    $$(".view").forEach(v => v.classList.toggle("active", v.id === `view-${name}`));
    $$("[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === name));
    if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (name === "jobs") refreshJobs();
    if (name === "trace") loadPuzzles();
  }
  $("#helpBtn")?.addEventListener("click", () => showView("tutorial"));
  $$("[data-view]").forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));
  $$("[data-goto]").forEach(b => b.addEventListener("click", () => showView(b.dataset.goto)));
  window.addEventListener("hashchange", () => {
    const n = location.hash.replace("#", "") || "dashboard";
    if ($(`#view-${n}`)) showView(n);
  });

  // theme
  const saved = localStorage.getItem("ru-theme");
  if (saved) document.documentElement.dataset.theme = saved;
  $("#themeBtn").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("ru-theme", next);
  });

  // PIN gate for LAN mode
  function showPinGate(message) {
    $("#pinGate").classList.remove("hidden");
    $("#pinError").textContent = message || "";
    $("#pinError").classList.toggle("hidden", !message);
    $("#pinInput").focus();
  }
  function hidePinGate() {
    $("#pinGate").classList.add("hidden");
    $("#pinError").classList.add("hidden");
  }
  async function unlock() {
    const val = $("#pinInput").value.trim();
    if (!val) return;
    accessPin = val;
    sessionStorage.setItem("ru-pin", val);
    try {
      const s = await api("/api/status");
      if (!s.tools) {
        accessPin = ""; sessionStorage.removeItem("ru-pin");
        showPinGate("Wrong PIN.");
        return;
      }
      hidePinGate();
      state.status = s;
      renderStatus(s);
      refreshJobs();
      toast("Unlocked");
    } catch (e) {
      accessPin = ""; sessionStorage.removeItem("ru-pin");
      showPinGate(e.status === 401 ? "Wrong PIN." : e.message);
    }
  }
  $("#pinBtn").addEventListener("click", unlock);
  $("#pinInput").addEventListener("keydown", (e) => { if (e.key === "Enter") unlock(); });

  // status
  async function loadStatus() {
    try {
      const s = await api("/api/status");
      if (!s.tools) { showPinGate(); return; }
      state.status = s;
      renderStatus(s);
    } catch (e) {
      if (e.status === 401) { accessPin = ""; sessionStorage.removeItem("ru-pin"); showPinGate("PIN required."); return; }
      $("#statusPill").className = "pill bad";
      $("#statusPill").lastElementChild.textContent = "offline";
      toast(`Status failed: ${e.message}`);
    }
  }
  function renderStatus(s) {
      $("#statusPill").className = "pill ok";
      $("#statusPill").lastElementChild.textContent = "ready";
      if (s.benchmark) {
        if (s.benchmark.functions) $("#statFunctions").textContent = s.benchmark.functions.toLocaleString();
        if (s.benchmark.matched) $("#statMatched").textContent = s.benchmark.matched.toLocaleString();
        if (s.benchmark.changed) $("#statChanged").textContent = s.benchmark.changed.toLocaleString();
      }
      const tools = [
        ["DOL → ELF", s.tools.dol_to_elf],
        ["REA bridge", s.tools.rea_bridge],
        ["Structure scan", s.tools.structure_scan],
        ["Code isolation", s.tools.isolate_code],
        ["PE triage", s.tools.pe_triage],
        ["Patch CLI", s.tools.patch_cli],
        ["Ghidra env", s.tools.ghidra],
        ["REA CLI", s.tools.rea],
      ];
      $("#toolList").innerHTML = tools.map(([n, ok]) =>
        `<li><span>${escape(n)}</span><span class="${ok ? "yes" : "no"}">${ok ? "ready" : "missing"}</span></li>`
      ).join("");
      $("#toolTag").textContent = `${s.python} · ${s.platform.split("-")[0]}`;
      $("#toolTag").className = "tag ok";
      const mark = (id, ok, label) => { const el = $(id); if (el) { el.textContent = label + (ok ? "" : " missing"); el.className = ok ? "ok" : "bad"; } };
      mark("#tutReady", true, "ready");
      mark("#tutGhidra", !!s.tools.ghidra, "Ghidra");
      mark("#tutRea", !!s.tools.rea, "REA");
      const tp = $("#tutPython"); if (tp) tp.textContent = s.python || "Python";
  }

  // inspect
  $("#inspectForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const path = new FormData(e.target).get("path").trim();
    const box = $("#inspectResult");
    box.classList.remove("hidden");
    box.innerHTML = `<p class="muted">Reading…</p>`;
    try {
      const info = await api("/api/inspect", { method: "POST", body: JSON.stringify({ path }) });
      const rows = [
        ["File", info.name], ["Format", info.format], ["Size", fmtBytes(info.size)],
        ["Path", info.path], ["SHA-256", info.sha256 || info.hash_note || "—"],
      ];
      const details = info.probe?.details || {};
      const detailRows = Object.entries(details).map(([k, v]) => {
        let text;
        if (Array.isArray(v)) text = v.slice(0, 20).join(", ");
        else if (v && typeof v === "object") text = JSON.stringify(v);
        else text = String(v);
        return [k, text];
      });
      const caps = (info.capabilities || []).join(" · ");
      box.innerHTML = `<h3 class="result-title">File result</h3><dl class="kv">${rows.map(([k, v]) =>
        `<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`).join("")}</dl>
        ${caps ? `<p class="muted">Capabilities: ${escape(caps)} · function diff: ${info.function_diff ? "yes" : "no"}</p>` : ""}
        ${detailRows.length ? `<h3 class="result-title">Structure</h3><dl class="kv">${detailRows.map(([k, v]) =>
          `<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`).join("")}</dl>` : ""}`;
    } catch (err) {
      box.innerHTML = `<p class="error">${escape(err.message)}</p>`;
    }
  });

  // action form
  const hints = {
    structure: "Ranks pointer tables, vtables and call targets. Fast on a prepared ELF.",
    ghidra: "Runs Ghidra headless on a GameCube PPC ELF. Three to five minutes, then returns the function count and CSV.",
    dol: "Extracts the DOL from an ISO or converts a DOL to ELF32 big-endian PowerPC.",
    isolate: "Extracts code sections, instruction counts and candidate functions.",
    triage: "Static imports, strings, base64 and process-injection API chain.",
  };
  $("#actionSelect").addEventListener("change", () => {
    $("#actionHint").textContent = hints[$("#actionSelect").value] || "";
  });
  $("#actionForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const action = fd.get("action");
    const path = fd.get("path").trim();
    try {
      const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({ action, params: { path } }) });
      toast(`Queued ${action} · ${job.id}`);
      watchJob(job.id);
      showView("jobs");
    } catch (err) { toast(err.message); }
  });

  // patch forms
  $("#applyForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({
        action: "patch_apply",
        params: { clean: fd.get("clean").trim(), patch: fd.get("patch").trim(), output: fd.get("output").trim() },
      }) });
      toast(`Queued patch · ${job.id}`);
      watchJob(job.id); showView("jobs");
    } catch (err) { toast(err.message); }
  });
  $("#createForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({
        action: "patch_create",
        params: {
          original: fd.get("original").trim(), modified: fd.get("modified").trim(),
          format: fd.get("format"), output: fd.get("output").trim(),
        },
      }) });
      toast(`Queued patch creation · ${job.id}`);
      watchJob(job.id); showView("jobs");
    } catch (err) { toast(err.message); }
  });

  // release diff
  function diffHtml(j) {
    const p = j.result?.parsed;
    if (!p) return "";
    const b = p.builds || {};
    const stat = (label, value) => `<div class="stat"><span class="label">${escape(label)}</span><strong>${Number(value || 0).toLocaleString()}</strong></div>`;
    const srcCell = v => {
      const ok = sourceParts(v);
      return `<div class="src-cell"><span>${escape(sourceLabel(v))}</span>${ok ? `<button type="button" class="mini open-src" data-src="${escape(v)}">Open</button>` : ""}</div>`;
    };
    return `<div class="grid cards" style="margin:12px 0">
      ${stat("matched", p.matched_pairs)}
      ${stat("changed", p.changed)}
      ${stat("removed", p.removed)}
      ${stat("added", p.added)}
    </div>
    <dl class="kv">
      <dt>Build A</dt><dd>${escape(b.a?.exe || "")} - ${escape(b.a?.arch || "")} - ${Number(b.a?.functions || 0).toLocaleString()} functions</dd>
      <dt>Build B</dt><dd>${escape(b.b?.exe || "")} - ${escape(b.b?.arch || "")} - ${Number(b.b?.functions || 0).toLocaleString()} functions</dd>
      <dt>Match rate</dt><dd>${p.symbols_a ? (100 * p.matched_pairs / p.symbols_a).toFixed(1) : "-"}%</dd>
    </dl>
    ${(p.changed_functions || []).length ? `<div class="card-head"><h3 class="result-title">Changed functions</h3><span class="tag">${p.changed_functions.length} shown</span></div>
      <div class="source-table-wrap"><table class="source-table"><thead><tr><th>Function</th><th>Source A</th><th>Source B</th><th>Size</th></tr></thead><tbody>
      ${p.changed_functions.map(x => `<tr><td>${escape(x.name)}</td><td>${srcCell(x.source_a)}</td><td>${srcCell(x.source_b)}</td><td>${Number(x.size_a)} -> ${Number(x.size_b)}</td></tr>`).join("")}
      </tbody></table></div>` : ""}
    <div class="result-actions">
      <a class="btn" href="${downloadHref(j.id, "changed")}">Download changed CSV</a>
      <a class="btn" href="${downloadHref(j.id, "compare")}">Download full JSON</a>
    </div>`;
  }
  function renderDiff(j) {
    const box = $("#diffResult");
    const err = $("#diffError");
    box.classList.remove("hidden");
    err.classList.add("hidden");
    if (j.status === "failed") {
      box.classList.add("hidden");
      err.textContent = j.error || j.result?.stderr || "Comparison failed";
      err.classList.remove("hidden");
      return;
    }
    if (j.status !== "done" || !j.result?.parsed) {
      box.innerHTML = `<p class="muted">Comparing builds... this can take a minute.</p>`;
      return;
    }
    box.innerHTML = diffHtml(j);
  }
  $("#diffForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const err = $("#diffError"), box = $("#diffResult");
    err.classList.add("hidden"); box.classList.add("hidden");
    box.innerHTML = `<p class="muted">Queued. Reading symbols and disassembling both builds…</p>`;
    box.classList.remove("hidden");
    try {
      const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({
        action: "release_diff",
        params: {
          a: fd.get("a").trim(), b: fd.get("b").trim(),
          label_a: (fd.get("label_a") || "A").trim(), label_b: (fd.get("label_b") || "B").trim(),
        },
      }) });
      toast(`Queued comparison · ${job.id}`);
      const id = job.id;
      const timer = setInterval(async () => {
        try {
          const j = await api(`/api/jobs/${id}`);
          state.jobs.set(id, j);
          renderDiff(j);
          if (j.status === "done" || j.status === "failed") {
            clearInterval(timer);
            toast(j.status === "done" ? "Comparison complete" : "Comparison failed");
          }
        } catch (_) { /* keep polling */ }
      }, 1500);
    } catch (e2) {
      box.classList.add("hidden");
      err.textContent = e2.message;
      err.classList.remove("hidden");
    }
  });

  // PPC diff
  function renderPpcDiff(j) {
    const box = $("#ppcResult"), err = $("#ppcError");
    box.classList.remove("hidden"); err.classList.add("hidden");
    if (j.status === "failed") {
      box.classList.add("hidden");
      err.textContent = j.error || j.result?.stderr || "PPC comparison failed";
      err.classList.remove("hidden"); return;
    }
    if (j.status !== "done" || !j.result?.parsed) {
      box.innerHTML = `<p class="muted">Fingerprinting both PowerPC builds…</p>`; return;
    }
    const p = j.result.parsed, b = p.builds || {};
    const stat = (label, value) => `<div class="stat"><span class="label">${escape(label)}</span><strong>${Number(value || 0).toLocaleString()}</strong></div>`;
    box.innerHTML = `<div class="grid cards" style="margin:12px 0">
      ${stat("matched", p.matched)}
      ${stat("changed", p.changed)}
      ${stat("removed", p.removed)}
      ${stat("added", p.added)}
    </div>
    <dl class="kv">
      <dt>Build A</dt><dd>${escape(b.a?.elf || "")} · ${Number(p.functions_a || 0).toLocaleString()} functions</dd>
      <dt>Build B</dt><dd>${escape(b.b?.elf || "")} · ${Number(p.functions_b || 0).toLocaleString()} functions</dd>
      <dt>Match rate</dt><dd>${p.match_rate ?? "—"}%</dd>
    </dl>
    <div class="result-actions">
      <a class="btn" href="${downloadHref(j.id, "changed")}">Download changed CSV</a>
      <a class="btn" href="${downloadHref(j.id, "pairs")}">Download all pairs</a>
      <a class="btn" href="${downloadHref(j.id, "compare")}">Download JSON</a>
    </div>`;
  }
  $("#ppcForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const box = $("#ppcResult"), err = $("#ppcError");
    err.classList.add("hidden"); box.classList.remove("hidden");
    box.innerHTML = `<p class="muted">Queued. Fingerprinting both builds…</p>`;
    try {
      const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({
        action: "ppc_diff",
        params: {
          elf_a: fd.get("elf_a").trim(), csv_a: fd.get("csv_a").trim(),
          elf_b: fd.get("elf_b").trim(), csv_b: fd.get("csv_b").trim(),
          label_a: (fd.get("label_a") || "A").trim(), label_b: (fd.get("label_b") || "B").trim(),
        },
      }) });
      toast(`Queued PPC comparison · ${job.id}`);
      const id = job.id;
      const timer = setInterval(async () => {
        try {
          const j = await api(`/api/jobs/${id}`);
          state.jobs.set(id, j); renderPpcDiff(j);
          if (j.status === "done" || j.status === "failed") {
            clearInterval(timer);
            toast(j.status === "done" ? "PPC comparison complete" : "PPC comparison failed");
          }
        } catch (_) { /* keep polling */ }
      }, 1500);
    } catch (e2) {
      box.classList.add("hidden"); err.textContent = e2.message; err.classList.remove("hidden");
    }
  });

  // APK diff
  function apkHtml(j) {
    const p = j.result?.parsed;
    if (!p) return "";
    const b = p.builds || {};
    const stat = (label, value, suffix = "") => `<div class="stat"><span class="label">${escape(label)}</span><strong>${Number(value || 0).toLocaleString()}${suffix}</strong></div>`;
    return `<div class="grid cards" style="margin:12px 0">
      ${stat("matched", p.matched)}
      ${stat("identical", p.identical)}
      ${stat("changed", p.changed)}
      ${stat("removed", p.removed)}
      ${stat("added", p.added)}
      ${stat("match rate", p.match_rate, "%")}
    </div>
    <dl class="kv">
      <dt>APK A</dt><dd>${escape(b.a?.path || "")}</dd>
      <dt>APK B</dt><dd>${escape(b.b?.path || "")}</dd>
    </dl>
    ${(p.changed_methods || []).length ? `<div class="card-head"><h3 class="result-title">Changed methods</h3><span class="tag">${p.changed_methods.length} shown</span></div>
      <div class="source-table-wrap"><table class="source-table"><thead><tr><th>Class</th><th>Method</th><th>Prototype</th><th>Code A</th><th>Code B</th></tr></thead><tbody>
      ${p.changed_methods.map(x => `<tr><td>${escape(x.class)}</td><td>${escape(x.name)}</td><td>${escape(x.prototype)}</td><td>${Number(x.code_a)}</td><td>${Number(x.code_b)}</td></tr>`).join("")}
      </tbody></table></div>` : `<p class="muted">No method-level changes in the comparable set.</p>`}
    <div class="result-actions">
      <a class="btn" href="${downloadHref(j.id, "changed")}">Download changed CSV</a>
      <a class="btn" href="${downloadHref(j.id, "compare")}">Download full JSON</a>
    </div>`;
  }
  function renderApkDiff(j) {
    const box = $("#apkResult"), err = $("#apkError");
    box.classList.remove("hidden"); err.classList.add("hidden");
    if (j.status === "failed") {
      box.classList.add("hidden");
      err.textContent = j.error || j.result?.stderr || "APK comparison failed";
      err.classList.remove("hidden"); return;
    }
    if (j.status !== "done" || !j.result?.parsed) {
      box.innerHTML = `<p class="muted">Parsing DEX and comparing methods...</p>`; return;
    }
    box.innerHTML = apkHtml(j);
  }
  $("#apkForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const box = $("#apkResult"), err = $("#apkError");
    err.classList.add("hidden"); box.classList.remove("hidden");
    box.innerHTML = `<p class="muted">Queued. Parsing DEX files...</p>`;
    try {
      const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({
        action: "apk_diff",
        params: {
          a: fd.get("a").trim(), b: fd.get("b").trim(),
          label_a: (fd.get("label_a") || "A").trim(), label_b: (fd.get("label_b") || "B").trim(),
        },
      }) });
      toast(`Queued APK comparison - ${job.id}`);
      const id = job.id;
      const timer = setInterval(async () => {
        try {
          const j = await api(`/api/jobs/${id}`);
          state.jobs.set(id, j); renderApkDiff(j);
          if (j.status === "done" || j.status === "failed") {
            clearInterval(timer);
            toast(j.status === "done" ? "APK comparison complete" : "APK comparison failed");
          }
        } catch (_) { /* keep polling */ }
      }, 1500);
    } catch (e2) {
      box.classList.add("hidden"); err.textContent = e2.message; err.classList.remove("hidden");
    }
  });

  // path trace
  function traceHtml(r) {
    const pct = (r.priority * 100).toFixed(1);
    const cls = r.priority_label === "critical" ? "bad" : r.priority_label === "high" ? "warn" : r.priority_label === "medium" ? "" : "ok";
    return `<div class="grid cards" style="margin:12px 0">
      <div class="stat"><span class="label">priority</span><strong>${pct}%</strong></div>
      <div class="stat"><span class="label">level</span><strong class="${cls}">${escape(r.priority_label)}</strong></div>
      <div class="stat"><span class="label">library matches</span><strong>${r.matches.length}</strong></div>
      <div class="stat"><span class="label">puzzle pieces</span><strong>${r.puzzles.length}</strong></div>
    </div>
    <dl class="kv"><dt>Trace ID</dt><dd><code>${escape(r.trace_id)}</code></dd>
      <dt>Features</dt><dd>${escape(JSON.stringify(r.features))}</dd></dl>
    ${r.matches.length ? `<div class="card-head"><h3 class="result-title">Library matches</h3></div>
      <div class="source-table-wrap"><table class="source-table"><thead><tr><th>Library ID</th><th>Name</th><th>Start</th><th>End</th><th>Confidence</th></tr></thead><tbody>
      ${r.matches.map(m => `<tr><td>${escape(m.library_id)}</td><td>${escape(m.name)}</td><td>${m.start}</td><td>${m.end}</td><td>${m.confidence}</td></tr>`).join("")}
      </tbody></table></div>` : `<p class="muted">No library match. Every node is a puzzle piece.</p>`}
    ${r.puzzles.length ? `<div class="card-head"><h3 class="result-title">Puzzle pieces</h3><span class="tag">stable IDs</span></div>
      <div class="source-table-wrap"><table class="source-table"><thead><tr><th>ID</th><th>Nodes</th><th>Occurrences</th></tr></thead><tbody>
      ${r.puzzles.map(x => `<tr><td><code>${escape(x.id)}</code></td><td>${escape(x.nodes.join(" → "))}</td><td>${x.occurrences}</td></tr>`).join("")}
      </tbody></table></div>` : ""}`;
  }
  async function loadPuzzles() {
    try {
      const r = await api("/api/puzzles");
      const el = $("#puzzleList"); if (!el) return;
      el.innerHTML = r.puzzles.length ? r.puzzles.map(x =>
        `<div class="job"><div><div class="name"><code>${escape(x.id)}</code></div><div class="meta">${escape(x.signature)} · ${x.occurrences}×</div></div><span class="badge">${escape(x.status)}</span></div>`
      ).join("") : `<p class="muted">No puzzle pieces yet.</p>`;
    } catch (_) { /* silent */ }
  }
  $("#traceForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const box = $("#traceResult"), err = $("#traceError");
    err.classList.add("hidden"); box.classList.remove("hidden");
    box.innerHTML = `<p class="muted">Matching path...</p>`;
    try {
      const r = await api("/api/trace", { method: "POST", body: JSON.stringify({ nodes: $("#traceNodes").value }) });
      box.innerHTML = traceHtml(r);
      loadPuzzles();
    } catch (e2) {
      box.classList.add("hidden"); err.textContent = e2.message; err.classList.remove("hidden");
    }
  });
  $("#puzzleRefresh").addEventListener("click", loadPuzzles);

  // jobs
  const badge = (s) => `<span class="badge ${escape(s)}">${escape(s)}</span>`;
  function jobRow(j) {
    const label = j.action === "patch_apply" ? "apply patch" : j.action === "patch_create" ? "create patch" : j.action === "release_diff" ? "release diff" : j.action === "ppc_diff" ? "ppc diff" : j.action === "apk_diff" ? "apk diff" : j.action;
    const where = j.action === "release_diff" ? `${j.params?.a || ""} → ${j.params?.b || ""}` : j.action === "ppc_diff" ? `${j.params?.elf_a || ""} → ${j.params?.elf_b || ""}` : j.action === "apk_diff" ? `${j.params?.a || ""} → ${j.params?.b || ""}` : (j.params?.path || j.params?.clean || j.params?.original || "");
    return `<div class="job" data-job="${escape(j.id)}">
      <div><div class="name">${escape(label)} · ${escape(j.id)}</div>
      <div class="meta">${escape(where)} · ${timeAgo(j.created)}</div></div>
      ${badge(j.status)}
    </div>`;
  }
  function bindRows(root) {
    $$(".job", root).forEach(el => el.addEventListener("click", () => {
      const j = state.jobs.get(el.dataset.job);
      if (j) renderJob(j);
    }));
  }
  async function refreshJobs() {
    try {
      const data = await api("/api/jobs");
      data.jobs.forEach(j => state.jobs.set(j.id, j));
      const list = data.jobs;
      const html = list.length ? list.map(jobRow).join("") : `<p class="muted">No jobs yet.</p>`;
      ["#allJobs", "#recentJobs", "#analyzeJobs", "#patchJobs"].forEach(sel => {
        const el = $(sel); if (!el) return;
        if (sel === "#recentJobs") el.innerHTML = list.slice(0, 4).length ? list.slice(0, 4).map(jobRow).join("") : `<p class="muted">No jobs yet.</p>`;
        else if (sel === "#analyzeJobs") el.innerHTML = list.filter(j => ["structure","ghidra","dol","isolate","triage","release_diff","ppc_diff","apk_diff"].includes(j.action)).slice(0,6).map(jobRow).join("") || `<p class="muted">No jobs yet.</p>`;
        else if (sel === "#patchJobs") el.innerHTML = list.filter(j => j.action.startsWith("patch")).slice(0,6).map(jobRow).join("") || `<p class="muted">No jobs yet.</p>`;
        else el.innerHTML = html;
        bindRows(el);
      });
    } catch (e) { /* silent */ }
  }
  async function getJob(id) {
    const j = await api(`/api/jobs/${id}`);
    state.jobs.set(id, j);
    return j;
  }
  function watchJob(id) {
    if (state.polls.has(id)) return;
    const tick = async () => {
      try {
        const j = await getJob(id);
        renderJob(j);
        refreshJobs();
        if (j.status === "done" || j.status === "failed") {
          clearInterval(state.polls.get(id)); state.polls.delete(id);
          toast(j.status === "done" ? "Job complete" : "Job failed");
        }
      } catch (e) { /* keep polling */ }
    };
    state.polls.set(id, setInterval(tick, 1200));
    tick();
  }
  function renderJob(j) {
    const inJobs = $("#view-jobs")?.classList.contains("active");
    const box = inJobs ? $("#jobDetail") : $("#jobResult");
    if (!box) return;
    if (inJobs) $("#jobDetailCard")?.classList.remove("hidden");
    box.classList.remove("hidden");
    const result = j.result?.parsed ?? j.result ?? j.error ?? null;
    const meta = [["Job", j.id], ["Action", j.action], ["Status", j.status]];
    if (j.result?.returncode !== undefined) meta.push(["Exit", String(j.result.returncode)]);
    const custom = (j.action === "release_diff" && j.result?.parsed) ? diffHtml(j) : (j.action === "apk_diff" && j.result?.parsed) ? apkHtml(j) : (result ? `<pre>${escape(JSON.stringify(result, null, 2))}</pre>` : "");
    box.innerHTML = `<div class="card-head"><h3 class="result-title">Job ${escape(j.id)}</h3>${badge(j.status)}</div>
      <dl class="kv">${meta.map(([k,v]) => `<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`).join("")}</dl>
      ${custom}
      ${j.result?.stderr ? `<details><summary>stderr</summary><pre>${escape(j.result.stderr)}</pre></details>` : ""}
      <div class="result-actions">
        <button class="btn" id="downloadJson">Download JSON</button>
        ${j.action === "ghidra" && j.result?.parsed?.csv ? `<button class="btn primary" id="inspectJob">Inspect functions</button>` : ""}
      </div>`;
    const inspectBtn = box.querySelector("#inspectJob");
    if (inspectBtn) inspectBtn.addEventListener("click", () => {
      $("#inspectorElf").value = j.params?.path || "";
      $("#inspectorCsv").value = j.result.parsed.csv || "";
      $("#inspectorAddress").value = "0x80003140";
      showView("inspector");
      $("#inspectorForm").requestSubmit();
    });
    const dl = box.querySelector("#downloadJson");
    if (dl) dl.addEventListener("click", () => {
      const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
      a.download = `reverse-update-${j.id}.json`; a.click(); URL.revokeObjectURL(a.href);
    });
  }
  $("#refreshJobs").addEventListener("click", refreshJobs);
  $$("#allJobs .job").forEach(() => {});

  // inspector
  function linkChips(items, kind) {
    if (!items || !items.length) return `<p class="muted">No ${kind} in the Ghidra map.</p>`;
    return `<div class="link-list">${items.map(x =>
      `<button type="button" class="link-chip" data-addr="${escape(x.target || x.address)}" title="${escape(x.address)}">${escape(x.name)}</button>`
    ).join("")}</div>`;
  }
  function renderInspector(d) {
    const f = d.function;
    $("#inspectorResult").classList.remove("hidden");
    $("#inspectorMeta").innerHTML = `<h2 class="inspector-title">${escape(f.name)}</h2>
      <p class="inspector-sub">${escape(f.address)} – ${escape(f["end"])} · ${f.size.toLocaleString()} bytes</p>
      <dl class="kv">
        <dt>Thunk</dt><dd>${f.thunk ? "yes" : "no"}</dd>
        <dt>ELF</dt><dd>${escape(d.elf)}</dd>
        <dt>CSV</dt><dd>${escape(d.csv)}</dd>
      </dl>`;
    $("#inspectorLinks").innerHTML = `<h2>Calls</h2>${linkChips(d.calls, "calls")}
      <h2 style="margin-top:14px">Callers</h2>${linkChips(d.callers, "callers")}`;
    const p = $("#inspectorPseudo"), pt = $("#pseudoTag");
    if (d.pseudocode) {
      p.innerHTML = `<pre>${escape(d.pseudocode)}</pre>`;
      pt.textContent = "saved decompilation"; pt.className = "tag ok";
    } else {
      p.innerHTML = `<p class="muted">No saved pseudocode for this function. Run Ghidra/DecompileAt for it.</p>`;
      pt.textContent = "not cached"; pt.className = "tag";
    }
    $("#disasmTag").textContent = `${d.disassembly.length} instructions`;
    $("#inspectorDisasm").innerHTML = `<table class="disasm-table"><tbody>${d.disassembly.map(i =>
      `<tr><td>${escape(i.address)}</td><td>${escape(i.mnemonic)}</td><td>${escape(i.op_str)}</td></tr>`
    ).join("")}</tbody></table>`;
    $("#inspectorResult").scrollIntoView({ behavior: "smooth", block: "start" });
  }
  $("#inspectorForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = { elf: fd.get("elf").trim(), csv: fd.get("csv").trim(), address: fd.get("address").trim() };
    const box = $("#inspectorResult");
    const errBox = $("#inspectorError");
    errBox.classList.add("hidden");
    errBox.textContent = "";
    box.classList.add("hidden");
    try {
      const d = await api("/api/function", { method: "POST", body: JSON.stringify(body) });
      renderInspector(d);
    } catch (err) {
      errBox.textContent = err.message;
      errBox.classList.remove("hidden");
    }
  });
  $("#inspectorResult").addEventListener("click", (e) => {
    const b = e.target.closest("[data-addr]");
    if (!b) return;
    $("#inspectorAddress").value = b.dataset.addr;
    $("#inspectorForm").requestSubmit();
  });

  // native path picker (desktop)
  const browseTargets = [
    ["inspectPath", "file", "Select a file"],
    ["actionPath", "file", "Select an input file"],
    ["applyClean", "file", "Select the clean file"],
    ["applyPatch", "file", "Select the patch file"],
    ["createOriginal", "file", "Select the original file"],
    ["createModified", "file", "Select the modified file"],
    ["inspectorElf", "file", "Select a PowerPC ELF"],
    ["inspectorCsv", "file", "Select a Ghidra CSV"],
    ["diffA", "folder", "Select build A folder"],
    ["diffB", "folder", "Select build B folder"],
    ["sourceRoot", "folder", "Select source root"],
    ["ppcElfA", "file", "Select ELF A"],
    ["ppcCsvA", "file", "Select Ghidra CSV A"],
    ["ppcElfB", "file", "Select ELF B"],
    ["ppcCsvB", "file", "Select Ghidra CSV B"],
  ];
  browseTargets.forEach(([id, kind, title]) => {
    const input = document.getElementById(id);
    if (!input) return;
    let row = input.closest(".path-row");
    if (!row) {
      row = document.createElement("div");
      row.className = "path-row";
      input.parentNode.insertBefore(row, input);
      row.appendChild(input);
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn browse-btn";
    btn.textContent = "Browse";
    btn.addEventListener("click", async () => {
      const old = btn.textContent;
      btn.disabled = true; btn.textContent = "…";
      try {
        const d = await api("/api/browse", { method: "POST", body: JSON.stringify({ kind, title }) });
        if (d.path) {
          input.value = d.path;
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }
      } catch (e) {
        toast(e.message);
      } finally {
        btn.disabled = false; btn.textContent = old;
      }
    });
    row.appendChild(btn);
  });

  // uploads (for phone/tablet and small files)
  $$(".upload-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.uploadFor);
      const picker = document.createElement("input");
      picker.type = "file";
      picker.onchange = async () => {
        const file = picker.files && picker.files[0];
        if (!file) return;
        if (file.size > 128 * 1024 * 1024) {
          toast("Upload limit is 128 MB. Use a host path for a game ISO.");
          return;
        }
        const old = btn.textContent;
        btn.disabled = true; btn.textContent = "Uploading…";
        try {
          const fd = new FormData(); fd.append("file", file);
          const res = await fetch("/api/upload", { method: "POST", headers: accessPin ? { "X-RU-Pin": accessPin } : {}, body: fd });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
          target.value = data.path;
          target.dispatchEvent(new Event("input", { bubbles: true }));
          toast(`Uploaded ${data.name} (${fmtBytes(data.size)})`);
        } catch (e) {
          toast(e.message);
        } finally {
          btn.disabled = false; btn.textContent = old;
        }
      };
      picker.click();
    });
  });

  // service worker
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }

  // boot
  const initial = location.hash.replace("#", "") || "dashboard";
  showView($(`#view-${initial}`) ? initial : "dashboard");
  loadStatus();
  refreshJobs();
  setInterval(loadStatus, 30000);
  setInterval(refreshJobs, 5000);
})();
