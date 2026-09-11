"use strict";

/* ======================================================================
   Storage — every case lives only in this browser's localStorage. The
   backend never keeps a copy after it answers /api/process (see
   server/app.py's docstring). If localStorage is unavailable (private
   window, blocked site data) cases simply won't persist across reloads —
   handled gracefully below, never a hard crash.
   ====================================================================== */
const Store = {
  KEY: "casemap.cases.v1",
  all() {
    try { return JSON.parse(localStorage.getItem(this.KEY) || "[]"); }
    catch { return []; }
  },
  save(list) {
    try { localStorage.setItem(this.KEY, JSON.stringify(list)); return true; }
    catch { return false; }
  },
  add(caseObj) {
    const list = this.all();
    list.unshift(caseObj);
    this.save(list);
  },
  get(id) { return this.all().find(c => c.id === id); },
  remove(id) { this.save(this.all().filter(c => c.id !== id)); },
};

// Only real provisions/grounds/prayers/relief content — NOT SYNOPSIS,
// ANNEXURE, EXHIBIT, or AFFIDAVIT (those are ordinary document sections and
// belong in Documents insights like everything else, not filed under
// Provisions just because ANNEXURE_PATTERN also recognizes them as headings
// on the backend).
const PROVISION_HEADING_RE = /\bPRAYER\b|\bGROUNDS\b|\bRELIEF\b|QUESTIONS?\s*\(?S?\)?\s*OF\s*LAW/i;
const API = { health: "/api/health", process: "/api/process" };

/* ======================================================================
   HandleStore — "reprocess without re-browsing".
   Browsers never expose a real filesystem path to JavaScript (a
   deliberate security restriction — <input type=file> only ever gives a
   filename). The closest real equivalent: Chrome/Edge's File System
   Access API can hand back a FileSystemFileHandle that the browser can
   re-read later after a one-click permission re-grant, with no path ever
   touching this code. That handle is stored in IndexedDB (the one
   browser storage that can hold a handle object at all — localStorage
   only holds strings). Firefox/Safari don't implement this API at all;
   Reprocess simply isn't offered there — there's no workaround for that,
   it's not implemented client-side by those browsers.
   ====================================================================== */
const HandleStore = {
  supported: typeof window.showOpenFilePicker === "function",
  _dbPromise: null,
  _db() {
    if (!this._dbPromise) {
      this._dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open("casemap-handles", 1);
        req.onupgradeneeded = () => req.result.createObjectStore("handles");
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }
    return this._dbPromise;
  },
  async save(caseId, handles) {
    try {
      const db = await this._db();
      await new Promise((res, rej) => {
        const tx = db.transaction("handles", "readwrite");
        tx.objectStore("handles").put(handles, caseId);
        tx.oncomplete = res;
        tx.onerror = () => rej(tx.error);
      });
    } catch { /* Reprocess just won't be offered for this case */ }
  },
  async get(caseId) {
    try {
      const db = await this._db();
      return await new Promise((res, rej) => {
        const r = db.transaction("handles", "readonly").objectStore("handles").get(caseId);
        r.onsuccess = () => res(r.result || null);
        r.onerror = () => rej(r.error);
      });
    } catch { return null; }
  },
  async remove(caseId) {
    try {
      const db = await this._db();
      db.transaction("handles", "readwrite").objectStore("handles").delete(caseId);
    } catch { /* ignore */ }
  },
};

/* ======================================================================
   Router
   ====================================================================== */
const Router = {
  current: "dashboard",
  go(view, arg) {
    document.querySelectorAll("main > section").forEach(s => s.classList.add("hidden"));
    this.current = view;
    if (view === "dashboard") {
      document.getElementById("dashboard").classList.remove("hidden");
      document.title = "CaseMap";
      App.renderDashboard();
    } else if (view === "upload") {
      document.getElementById("uploadView").classList.remove("hidden");
      document.title = "CaseMap — new case";
      App.resetUpload();
    } else if (view === "case") {
      document.getElementById("caseView").classList.remove("hidden");
      App.renderCase(arg);
    }
    window.scrollTo(0, 0);
  },
};

/* ======================================================================
   App
   ====================================================================== */
const App = {
  pendingFiles: [],
  activeCase: null,

  async init() {
    this.wireDropzone();
    Router.go("dashboard");
    // Anonymous page-load counter — one increment ping per real page load,
    // nothing else: no document content, no filenames, no identifying
    // data, ever. Disclosed on the dashboard. Fails silently and never
    // blocks anything if the counting service is unreachable — this is
    // the ONLY network call this app ever makes to somewhere that isn't
    // its own local backend.
    fetch("https://countapi.mileshilliard.com/api/v1/hit/ecocode-casemap-pageviews").catch(() => {});
    // No visible badge for this — kept as a quiet console check only, so a
    // degraded backend is still discoverable while debugging without
    // putting a permanent technical status light in front of the user.
    try {
      const r = await fetch(API.health);
      const j = await r.json();
      if (j.ml_layer !== "active") console.warn("CaseMap backend is in degraded mode (regex-only).");
    } catch {
      console.warn("CaseMap backend unreachable at " + API.health);
    }
  },

  /* ---------- dashboard ---------- */
  renderDashboard() {
    const cases = Store.all();
    const grid = document.getElementById("caseGrid");
    const empty = document.getElementById("emptyState");
    grid.innerHTML = "";
    if (!cases.length) { empty.classList.remove("hidden"); return; }
    empty.classList.add("hidden");
    for (const c of cases) {
      const card = document.createElement("div");
      card.className = "case-card";
      card.onclick = () => Router.go("case", c.id);
      const docs = c.graph.documents?.length || 0;
      const nodes = c.graph.nodes?.length || 0;
      card.innerHTML = `
        <button class="del" title="Delete this case">Delete</button>
        <div class="title">${esc(c.name)}</div>
        <div class="meta">
          <span>${docs} document${docs === 1 ? "" : "s"}</span>
          <span>${nodes} facts extracted</span>
          <span>${new Date(c.createdAt).toLocaleDateString()}</span>
        </div>`;
      card.querySelector(".del").onclick = (ev) => {
        ev.stopPropagation();
        if (confirm(`Delete "${c.name}"? This only removes it from this browser.`)) {
          Store.remove(c.id);
          HandleStore.remove(c.id);
          this.renderDashboard();
        }
      };
      grid.appendChild(card);
    }
  },

  /* ---------- upload ---------- */
  pendingHandles: null,

  resetUpload() {
    this.pendingFiles = [];
    this.pendingHandles = null;
    document.getElementById("fileList").innerHTML = "";
    document.getElementById("caseNameRow").classList.add("hidden");
    document.getElementById("processBtn").classList.add("hidden");
    document.getElementById("progressWrap").classList.remove("show");
    document.getElementById("errorBox").classList.remove("show");
    document.getElementById("caseNameInput").value = "";
  },

  wireDropzone() {
    const dz = document.getElementById("dropzone");
    const input = document.getElementById("fileInput");
    dz.onclick = async () => {
      if (HandleStore.supported) {
        // Prefer the picker that hands back a re-readable handle — that's
        // what makes Reprocess possible later. Drag-and-drop below can't
        // give this (the drag-and-drop file-handle API is far less
        // consistently supported), so those files won't offer Reprocess.
        try {
          const handles = await window.showOpenFilePicker({
            multiple: true,
            excludeAcceptAllOption: false,
            types: [{ description: "Case documents",
              accept: {
                "application/pdf": [".pdf"],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                "text/plain": [".txt"],
              } }],
          });
          const files = await Promise.all(handles.map(h => h.getFile()));
          this.pendingHandles = handles;
          this.addFiles(files);
          return;
        } catch (e) {
          if (e.name === "AbortError") return; // user cancelled the picker
          // any other failure (e.g. permission API glitch) — fall through
          // to the plain input below rather than leaving upload stuck
        }
      }
      input.click();
    };
    input.onchange = () => { this.pendingHandles = null; this.addFiles([...input.files]); };
    ["dragenter", "dragover"].forEach(ev =>
      dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("drag"); }));
    ["dragleave", "drop"].forEach(ev =>
      dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove("drag"); }));
    dz.addEventListener("drop", e => {
      this.pendingHandles = null;
      this.addFiles([...e.dataTransfer.files]);
    });
  },

  addFiles(files) {
    const ok = /\.(pdf|docx?|txt)$/i;
    for (const f of files) if (ok.test(f.name)) this.pendingFiles.push(f);
    this.renderFileList();
  },

  renderFileList() {
    const list = document.getElementById("fileList");
    list.innerHTML = "";
    this.pendingFiles.forEach((f, i) => {
      const ext = f.name.split(".").pop().toUpperCase();
      const row = document.createElement("div");
      row.className = "file-row";
      row.innerHTML = `<span class="ext">${ext}</span><span>${esc(f.name)}</span>
        <button class="rm">✕</button>`;
      row.querySelector(".rm").onclick = () => {
        this.pendingFiles.splice(i, 1);
        this.renderFileList();
      };
      list.appendChild(row);
    });
    const has = this.pendingFiles.length > 0;
    document.getElementById("caseNameRow").classList.toggle("hidden", !has);
    document.getElementById("lookupProvisionsRow").classList.toggle("hidden", !has);
    document.getElementById("processBtn").classList.toggle("hidden", !has);
    if (has && !document.getElementById("caseNameInput").value) {
      document.getElementById("caseNameInput").value =
        this.pendingFiles[0].name.replace(/\.[^.]+$/, "");
    }
  },

  async processFiles() {
    const name = document.getElementById("caseNameInput").value.trim() || "Untitled case";
    const btn = document.getElementById("processBtn");
    const err = document.getElementById("errorBox");
    err.classList.remove("show");
    btn.disabled = true;
    document.getElementById("progressWrap").classList.add("show");
    document.getElementById("progressText").textContent =
      `Processing ${this.pendingFiles.length} document(s) — this can take a minute or two…`;

    const lookupProvisions = document.getElementById("lookupProvisionsInput").checked;
    const fd = new FormData();
    for (const f of this.pendingFiles) fd.append("files", f, f.name);
    fd.append("lookup_provisions", lookupProvisions ? "true" : "false");

    try {
      const r = await fetch(API.process, { method: "POST", body: fd });
      const graph = await r.json();
      if (!r.ok) throw new Error(graph.error || `Backend error (${r.status})`);
      const caseObj = {
        id: "case_" + Date.now().toString(36),
        name, createdAt: Date.now(), graph, lookupProvisions,
      };
      Store.add(caseObj);
      if (this.pendingHandles) await HandleStore.save(caseObj.id, this.pendingHandles);
      Router.go("case", caseObj.id);
    } catch (e) {
      err.textContent = "Couldn't process this case: " + e.message +
        ". The backend may not be running — start it with: uvicorn server.app:app --port 8756";
      err.classList.add("show");
    } finally {
      btn.disabled = false;
      document.getElementById("progressWrap").classList.remove("show");
    }
  },

  async reprocessCase() {
    const c = this.activeCase;
    if (!c) return;
    const handles = await HandleStore.get(c.id);
    if (!handles || !handles.length) return; // button is hidden in this case anyway

    const btn = document.getElementById("reprocessBtn");
    const originalLabel = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Reprocessing…";
    try {
      const files = [];
      for (const h of handles) {
        // Re-grants access to the SAME file the browser remembered — the
        // browser re-reads it fresh from disk itself; this code never
        // sees or stores a path, only ever the handle object.
        const perm = await h.requestPermission({ mode: "read" });
        if (perm !== "granted") throw new Error(`Permission to re-read "${h.name}" was denied.`);
        files.push(await h.getFile());
      }
      const fd = new FormData();
      for (const f of files) fd.append("files", f, f.name);
      fd.append("lookup_provisions", c.lookupProvisions ? "true" : "false");
      const r = await fetch(API.process, { method: "POST", body: fd });
      const graph = await r.json();
      if (!r.ok) throw new Error(graph.error || `Backend error (${r.status})`);

      c.graph = graph;
      c.createdAt = Date.now();
      const list = Store.all();
      const idx = list.findIndex(x => x.id === c.id);
      if (idx !== -1) { list[idx] = c; Store.save(list); }
      this.renderCase(c.id);
    } catch (e) {
      alert("Reprocess failed: " + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = originalLabel;
    }
  },

  /* ---------- case view ---------- */
  renderCase(id) {
    const c = Store.get(id);
    if (!c) { Router.go("dashboard"); return; }
    this.activeCase = c;
    document.getElementById("caseTitle").textContent = c.name;
    document.title = `${c.name} — CaseMap`;
    HandleStore.get(id).then(handles => {
      document.getElementById("reprocessBtn").hidden = !(handles && handles.length);
    });

    const g = c.graph;
    const nodes = g.nodes || [];
    const dated = nodes.filter(n => n.data.date).length;
    const docs = g.documents || [];
    const stats = document.getElementById("caseStats");
    stats.innerHTML = [
      [docs.length, "documents"],
      [nodes.length, "facts extracted"],
      [dated, "dated events"],
      [(g.provisions || []).length, "provisions cited"],
      [g.runtime_s != null ? g.runtime_s + "s" : "—", "processing time"],
    ].map(([n, l]) => `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");

    this.renderTimeline(g);
    this.renderTree(g);
    this.renderProvisions(g);
    this.renderParties(g);
    this.renderConflicts(g);
    this.switchTab("timeline");
  },

  switchTab(tab) {
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
    document.querySelectorAll(".tabpanel").forEach(p => p.classList.toggle("active", p.id === "tab-" + tab));
  },

  // Timeline is chronology only — every dated fact across every document in
  // this case, in date order. Undated facts (most sentences in a legal
  // argument genuinely don't name a calendar date — that's correct, not
  // missing data) live in Documents insights instead, grouped by heading,
  // not duplicated here.
  renderTimeline(g) {
    const body = document.getElementById("timelineBody");
    body.innerHTML = "";
    const isProvisionNode = n => PROVISION_HEADING_RE.test(n.data.sources[0]?.section || "");
    let dated = (g.nodes || []).filter(n =>
      n.data.date && n.type !== "fallback_party_block" && !isProvisionNode(n));
    dated = dedupeByDateSimilarity(dated);

    if (!dated.length) {
      body.innerHTML = `<p class="muted">No dated events found across these documents yet.
        Everything extracted is still there — see Documents insights for the full,
        heading-organized breakdown of each document.</p>`;
      return;
    }

    dated.sort((a, b) => a.data.date.localeCompare(b.data.date));
    const tl = document.createElement("div");
    tl.className = "timeline";
    for (const n of dated) {
      const s = n.data.sources[0] || {};
      const item = document.createElement("div");
      item.className = "tl-item";
      item.innerHTML = `<div class="tl-dot"></div>
        <div class="tl-card">
          <div class="top"><span class="type">${esc(friendlyType(n.type))}</span>
            <span class="date">${n.data.date}</span></div>
          <div class="txt">${esc(previewText(n, 220))}</div>
          <div class="loc">${esc(shortDocName(s.document || ""))} · p.${s.page ?? "?"}${s.paragraph ? " · ¶" + s.paragraph : ""}</div>
        </div>`;
      item.querySelector(".tl-card").onclick = () => this.openDrawer(n);
      tl.appendChild(item);
    }
    body.appendChild(tl);
  },

  renderTree(g) {
    const body = document.getElementById("treeBody");
    body.innerHTML = "";
    const byDoc = groupBy(g.nodes || [], n => n.data.sources[0]?.document || "Unknown");
    for (const [docName, items] of byDoc) {
      const meta = (g.documents || []).find(d => d.name === docName) || {};
      const rows = items.slice().sort((a, b) => {
        const sa = a.data.sources[0], sb = b.data.sources[0];
        return (sa.page - sb.page) || ((sa.paragraph || 0) - (sb.paragraph || 0)) || (sa.char_start - sb.char_start);
      });
      const headings = new Set(rows.map(r => r.data.sources[0]?.section).filter(Boolean));

      const det = document.createElement("details");
      det.open = true;
      det.innerHTML = `<summary>${esc(shortDocName(docName))} <span class="mono muted">${rows.length} facts</span></summary>`;

      // Real insight, not just a row dump: what kind of document this is,
      // how confidently it was parsed, and its shape at a glance — before
      // the reader scrolls through every extracted line.
      const insight = document.createElement("div");
      insight.className = "doc-insight";
      insight.innerHTML = `
        <div class="insight-stat"><div class="n">${meta.pages ?? "—"}</div><div class="l">pages</div></div>
        <div class="insight-stat"><div class="n">${headings.size}</div><div class="l">headings found</div></div>
        <div class="insight-stat"><div class="n">${(meta.sections_cited || []).length}</div><div class="l">citations (raw)</div></div>
        <div class="insight-stat"><div class="n">${(meta.amounts || []).length}</div><div class="l">amounts</div></div>
        <div class="insight-stat"><div class="n">${(meta.parties || []).length}</div><div class="l">parties</div></div>
        <div class="insight-stat"><div class="n">${esc(friendlyTier(meta.structure_tier))}</div><div class="l">parsing quality</div></div>`;
      det.appendChild(insight);

      // Same structure as the Provisions tab — grouped by heading, not one
      // long undifferentiated list — so a document's real shape (INDEX,
      // SYNOPSIS, GROUNDS, PRAYER, ...) reads at a glance here too. `rows`
      // is already sorted in document order, so grouping consecutively
      // preserves reading order (groupBy keeps first-seen key order).
      const byHeading = groupBy(rows, r => r.data.sources[0]?.section || "Untitled");
      for (const [heading, headingRows] of byHeading) {
        const hgroup = document.createElement("details");
        hgroup.className = "crowd-group heading-group";
        hgroup.open = true;
        hgroup.innerHTML = `<summary>${esc(heading)} <span class="n">${headingRows.length}</span></summary>
          <div class="crowd-body"></div>`;
        const hbody = hgroup.querySelector(".crowd-body");
        headingRows.forEach(n => {
          const s = n.data.sources[0];
          const row = document.createElement("div");
          row.className = "tree-row";
          row.innerHTML = `<span class="p">p.${s.page ?? "?"}</span>
            <span class="p">${s.paragraph ? "¶" + s.paragraph : ""}</span>
            <span>${esc(previewText(n, 170))}</span>`;
          row.onclick = () => this.openDrawer(n);
          hbody.appendChild(row);
        });
        det.appendChild(hgroup);
      }
      body.appendChild(det);
    }
  },

  renderProvisions(g) {
    const body = document.getElementById("provisionsBody");
    body.innerHTML = "";

    // Cross-referenced statute provisions (Section X of the Y Act) — grouped
    // with the Act, when one was actually named near the citation; when not,
    // shown plainly rather than guessed.
    if ((g.provisions || []).length) {
      const wrap = document.createElement("details");
      wrap.className = "crowd-group";
      wrap.open = true;
      wrap.innerHTML = `<summary>Provisions cited <span class="n">${g.provisions.length}</span></summary>
        <div class="crowd-body"><div class="prov-row">
          ${g.provisions.map(p => `<span class="prov-chip" title="${esc(p.documents.join(", "))}">
              <span class="prov-top">
                <span class="prov-sec">${esc(p.section)}</span>
                ${p.act ? `<span class="prov-act">${esc(p.act)}</span>`
                        : `<span class="prov-act unnamed">Act not named nearby</span>`}
                <span class="prov-count">×${p.count}</span>
              </span>
              ${p.statute_lookup ? `<div class="statute-lookup">
                  <p>${esc(p.statute_lookup.snippet)}</p>
                  <a href="${esc(p.statute_lookup.source_url)}" target="_blank" rel="noopener">Source: IndianKanoon — ${esc(p.statute_lookup.title)}</a>
                </div>` : ""}
            </span>`).join("")}
        </div></div>`;
      body.appendChild(wrap);
    }

    // GROUNDS/PRAYER/QUESTIONS OF LAW used to also be listed here, grouped
    // by heading — moved out. They now live in Documents insights (grouped
    // by heading there too, per-document, alongside everything else about
    // that document) so they're not duplicated in two tabs. This tab is
    // statute citations only.
    if (!body.children.length) body.innerHTML = `<p class="muted">No cited provisions detected in this document set.</p>`;
  },

  renderParties(g) {
    const body = document.getElementById("partiesBody");
    body.innerHTML = "";
    for (const d of g.documents || []) {
      if (d.error) continue;
      const unstable = d.party_tier === "ml_role_unstable";
      const det = document.createElement("details");
      det.className = "crowd-group";
      det.open = true;
      const parties = (d.parties || []).map(p =>
        `<span class="chip${unstable ? " chip-warn" : ""}">${esc(p.name)} <span class="muted">· ${esc(p.role)}</span></span>`).join("") ||
        `<span class="muted">No parties parsed — cause-title shown as fallback fact.</span>`;
      const warning = unstable
        ? `<div class="party-warning">⚠ Low-confidence extraction on this document — the role
             classifier flagged its own output as unstable. Expect some of these to be section
             headings or stray phrases picked up as if they were party names, not just the real
             parties. Verify against the document before relying on this list.</div>`
        : "";
      det.innerHTML = `<summary>${esc(shortDocName(d.name))}
          <span class="n">${unstable ? "⚠ unstable" : (d.party_tier || "")}</span></summary>
        <div class="crowd-body">${warning}<div class="chip-row">${parties}</div></div>`;
      body.appendChild(det);
    }
  },

  // POTENTIAL_CONFLICT is a real signal the backend computes (two facts
  // that already scored as related, where one plainly asserts something
  // and the other denies it — see server/app.py's polarity reclassification
  // for how false positives from context bleed were found and fixed) but
  // was never shown anywhere in the UI until now. Framed the same way the
  // original pipeline's own report always framed it: a review flag, not a
  // proven contradiction — a human still has to look at both excerpts and
  // judge whether they actually conflict.
  renderConflicts(g) {
    const body = document.getElementById("conflictsBody");
    const badge = document.getElementById("conflictBadge");
    body.innerHTML = "";
    const byId = new Map((g.nodes || []).map(n => [n.id, n]));
    const conflicts = (g.edges || []).filter(e => e.label === "POTENTIAL_CONFLICT");

    badge.textContent = String(conflicts.length);
    badge.classList.toggle("hidden", conflicts.length === 0);

    if (!conflicts.length) {
      body.innerHTML = `<p class="muted">No conflicts flagged across these documents.
        This only catches facts that plainly assert vs. deny the same underlying claim —
        it is not a substitute for a full read.</p>`;
      return;
    }

    const banner = document.createElement("div");
    banner.className = "party-warning";
    banner.innerHTML = `⚠ These are automatically flagged for review, not confirmed
      contradictions. Each pair below shares an entity/date/amount and uses opposite
      assert/deny language — read both excerpts yourself before treating this as a real conflict.`;
    body.appendChild(banner);

    conflicts.forEach(edge => {
      const a = byId.get(edge.source), b = byId.get(edge.target);
      if (!a || !b) return;
      const sa = a.data.sources[0], sb = b.data.sources[0];
      const card = document.createElement("div");
      card.className = "conflict-card";
      card.innerHTML = `
        <div class="conflict-side">
          <div class="conflict-doc">${esc(shortDocName(sa.document))} · p.${sa.page ?? "?"}</div>
          <div class="conflict-text">${esc(previewText(a, 220))}</div>
        </div>
        <div class="conflict-vs">⚡ conflicts with</div>
        <div class="conflict-side">
          <div class="conflict-doc">${esc(shortDocName(sb.document))} · p.${sb.page ?? "?"}</div>
          <div class="conflict-text">${esc(previewText(b, 220))}</div>
        </div>`;
      card.querySelectorAll(".conflict-side").forEach((el, i) =>
        el.onclick = () => this.openDrawer(i === 0 ? a : b));
      body.appendChild(card);
    });
  },

  /* ---------- evidence drawer ---------- */
  openDrawer(node) {
    const s = node.data.sources[0] || {};
    document.getElementById("drawerType").textContent = friendlyType(node.type);
    document.getElementById("drawerTitle").textContent = previewText(node, 140);

    const ctx = s.context || s.text || "";
    const highlighted = s.text ? highlightSpan(ctx, s.text, s.char_start, s.char_end, s.context_start) : esc(ctx);

    document.getElementById("drawerBody").innerHTML = `
      <div class="dgrid">
        <div class="dfield"><div class="k">Document</div><div class="v">${esc(shortDocName(s.document || ""))}</div></div>
        <div class="dfield"><div class="k">Page</div><div class="v">${s.page ?? "—"}</div></div>
        ${s.paragraph ? `<div class="dfield"><div class="k">Paragraph</div><div class="v">¶${s.paragraph}</div></div>` : ""}
        <div class="dfield"><div class="k">Section</div><div class="v">${esc(s.section || "—")}</div></div>
        <div class="dfield"><div class="k">Date</div><div class="v">${node.data.date || "—"}</div></div>
        <div class="dfield"><div class="k">Confidence</div><div class="v">${esc(node.data.confidence || "—")}</div></div>
        ${s.rhetorical_role ? `<div class="dfield"><div class="k">Argument role</div>
          <div class="v">${esc(friendlyRole(s.rhetorical_role))}${
            s.rhetorical_confidence === "carried_forward" ? ` <span class="muted">(inferred from section)</span>` : ""}</div></div>` : ""}
      </div>
      <div class="dfield">
        <div class="k">Verbatim text</div>
        <div class="evidence-text">${highlighted || "<em>No source text captured.</em>"}</div>
      </div>`;
    document.getElementById("drawer").classList.add("show");
    document.getElementById("drawerBackdrop").classList.add("show");
  },
  closeDrawer() {
    document.getElementById("drawer").classList.remove("show");
    document.getElementById("drawerBackdrop").classList.remove("show");
  },

  /* ---------- counsel report ---------- */
  downloadReport() {
    const c = this.activeCase;
    if (!c) return;
    const g = c.graph;
    const byDoc = groupBy(g.nodes || [], n => n.data.sources[0]?.document || "Unknown");
    const fullText = n => n.data.sources[0]?.text || n.data.label;
    const loc = n => {
      const s = n.data.sources[0];
      return `p.${s.page ?? "?"}${s.paragraph ? `, ¶${s.paragraph}` : ""}`;
    };

    let sections = "";
    for (const [docName, items] of byDoc) {
      const meta = (g.documents || []).find(d => d.name === docName) || {};
      const isProvisionNode = n => PROVISION_HEADING_RE.test(n.data.sources[0]?.section || "");
      const keyPoints = items.filter(n => n.type === "IMPORTANT_LINE" && !isProvisionNode(n));
      const dated = dedupeByDateSimilarity(items.filter(n => n.data.date))
        .sort((a, b) => a.data.date.localeCompare(b.data.date));
      const headingGroups = groupBy(
        items.filter(isProvisionNode),
        n => n.data.sources[0].section);

      const unstable = meta.party_tier === "ml_role_unstable";
      const parties = (meta.parties || []).map(p =>
        `<span class="pchip${unstable ? " pchip-warn" : ""}">${esc(p.name)} — ${esc(p.role)}</span>`).join(" ");

      const provisionsList = (meta.provisions_detail || []).length
        ? [...new Map((meta.provisions_detail || []).map(p => [p.raw + "|" + (p.act || ""), p])).values()]
        : null;

      sections += `<div class="doc-section">
        <h2>${esc(shortDocName(docName))}</h2>
        <p class="docmeta">${meta.pages ?? "?"} page(s) · parsing quality: ${esc(friendlyTier(meta.structure_tier))}
          · ${(meta.sections || 0)} section(s) detected</p>

        ${parties ? `<h3>Parties</h3>
          ${unstable ? `<p class="warn">⚠ Low-confidence extraction on this document — verify these against the source before relying on them.</p>` : ""}
          <p class="chiprow">${parties}</p>` : ""}

        ${provisionsList ? `<h3>Provisions cited</h3>
          <ul class="plain">${provisionsList.map(p => {
            const sl = p.statute_lookup;
            return `<li><b>${esc(p.raw)}</b>${p.act ? ` — ${esc(p.act)}` : ` <i>(act not named nearby)</i>`}
              ${sl ? `<div class="statute-lookup">
                  <p>${esc(sl.snippet)}</p>
                  <a href="${esc(sl.source_url)}" target="_blank" rel="noopener">Source: IndianKanoon — ${esc(sl.title)}</a>
                </div>` : ""}</li>`;
          }).join("")}</ul>` : ""}

        ${dated.length ? `<h3>Chronology</h3><ul class="plain">${dated.map(n =>
          `<li><b>${n.data.date}</b> — ${esc(fullText(n))} <span class="src">(${loc(n)})</span></li>`).join("")}</ul>` : ""}

        ${keyPoints.length ? `<h3>Key points</h3><ol>${keyPoints.map(n =>
          `<li>${esc(fullText(n))} <span class="src">(${loc(n)})</span></li>`).join("")}</ol>` : ""}

        ${[...headingGroups].map(([heading, nodes]) => `
          <h3>${esc(heading)}</h3>
          ${nodes.map(n => `<p class="quoted">${esc(fullText(n))} <span class="src">(${loc(n)})</span></p>`).join("")}
        `).join("")}
      </div>`;
    }

    const html = `<!doctype html><html><head><meta charset="utf-8">
      <title>${esc(c.name)} — Case Report</title>
      <style>
        @page { size: A4; margin: 20mm 18mm; }
        * { box-sizing: border-box; }
        body{font-family:Georgia,'Times New Roman',serif;max-width:760px;margin:32px auto;
          color:#1c2521;line-height:1.6;padding:0 20px;font-size:12.5pt;
          text-align:justify;hyphens:auto}
        h1,h2,h3,.docmeta,.meta,.src{text-align:left}
        h1{font-size:22pt;border-bottom:2px solid #8a5a2b;padding-bottom:10px;margin-bottom:6px}
        h2{font-size:15pt;margin-top:30px;color:#5f3c17;border-bottom:1px solid #d8cfb8;
          padding-bottom:4px;page-break-after:avoid}
        h3{font-size:10.5pt;text-transform:uppercase;letter-spacing:.05em;color:#6b5a3c;
          margin-top:16px;margin-bottom:6px;page-break-after:avoid}
        .docmeta{color:#7a7469;font-size:10pt;margin-top:-2px}
        .src{color:#8a8a8a;font-size:9.5pt;font-family:'Courier New',monospace}
        .meta{color:#54615b;font-size:10.5pt}
        .warn{background:#fbeecb;color:#8a5a12;padding:6px 10px;border-radius:4px;font-size:10pt}
        .chiprow{line-height:2.2}
        .pchip{display:inline-block;background:#f1e4d0;color:#5f3c17;border-radius:10px;
          padding:2px 9px;margin:0 4px 4px 0;font-size:10pt}
        .pchip-warn{background:#fbeecb;color:#8a5a12}
        ul.plain{list-style:disc;padding-left:20px}
        ol{padding-left:20px}
        li{margin-bottom:7px;page-break-inside:avoid}
        p.quoted{margin:0 0 10px;padding-left:12px;border-left:2px solid #d8cfb8;page-break-inside:avoid}
        .doc-section{page-break-inside:avoid-page}
        .reportfoot{margin-top:36px;padding-top:14px;border-top:1px solid #d8cfb8;
          text-align:center;font-size:9.5pt;color:#8a8a8a}
        .reportfoot a{color:#8a8a8a}
      </style></head><body>
      <h1>${esc(c.name)}</h1>
      <p class="meta">Prepared by CaseMap — verbatim extraction with page/paragraph references, for counsel review.
      Generated ${new Date().toLocaleString()}. Every statement below is a direct excerpt from the source
      document(s); nothing is paraphrased or generated.</p>
      ${sections}
      <p class="reportfoot">Built by <a href="https://www.ecocodes.in">EcoCode Solutions</a></p>
      </body></html>`;

    // A real PDF, not an HTML file: write the report into a fresh window and
    // hand off to the browser's native print pipeline, which every browser
    // can save straight to a .pdf ("Save as PDF" destination) — no external
    // library, no risk of a CDN not loading, and better pagination/typography
    // than a screenshot-based PDF generator would give.
    const win = window.open("", "_blank");
    if (!win) {
      alert("Your browser blocked the report window — allow pop-ups for this page and try again.");
      return;
    }
    win.document.write(html);
    win.document.close();
    // A SINGLE print() call. The previous version armed both win.onload
    // and a setTimeout fallback "just in case" — onload reliably fires for
    // a document.write()'d page, so both fired, opening two native print
    // dialogs back to back. On Windows some browsers make that dialog
    // application-modal (blocks every tab, not just this window) until
    // it's dismissed — which reads as "the browser won't even refresh."
    setTimeout(() => { try { win.focus(); win.print(); } catch (e) {} }, 250);
  },
};

/* ---------- helpers ---------- */
function esc(s) {
  // Escapes &<> AND both quote characters: esc() output is interpolated into
  // HTML attributes too (e.g. title="${esc(...)}"), so a " in a document/party
  // name would otherwise break out of the attribute. ' escaped as well for
  // single-quoted-attribute safety.
  return (s ?? "").toString()
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
// Marks the evidence span inside its wider context. Uses the backend's own
// char_start/char_end/context_start (casemap_service.py's _attach_context)
// to slice ctx directly — self-verified against ctx.slice(lo,hi) so a stale
// or unrelated offset (e.g. a fallback SECTION event, whose char_end spans
// the whole section while text is only its first ~400 chars) can never mark
// the wrong span. Falls back to the old literal-text search when the
// offsets don't line up, so nothing regresses. Plain string .replace() alone
// used to be the only strategy: it silently no-ops whenever text isn't an
// EXACT substring of ctx, and even a real match could be interpreted with
// "$"-replacement-pattern semantics — offsets avoid both.
function highlightSpan(ctx, text, charStart, charEnd, contextStart) {
  if (typeof charStart === "number" && typeof charEnd === "number" && typeof contextStart === "number") {
    const lo = charStart - contextStart, hi = charEnd - contextStart;
    if (lo >= 0 && hi <= ctx.length && hi > lo && ctx.slice(lo, hi) === text) {
      return esc(ctx.slice(0, lo)) + `<mark>${esc(text)}</mark>` + esc(ctx.slice(hi));
    }
  }
  const idx = ctx.indexOf(text);
  if (idx === -1) return esc(ctx);
  return esc(ctx.slice(0, idx)) + `<mark>${esc(text)}</mark>` + esc(ctx.slice(idx + text.length));
}

// Cutting a label at a fixed character count mid-word ("...resul...",
// "...charact...") reads as broken. Prefer stopping at the end of a real
// sentence within budget; only fall back to a word boundary (+ "…") if no
// sentence end is close enough, and never slice inside a word.
function smartTruncate(text, maxLen) {
  text = (text || "").trim();
  if (text.length <= maxLen) return text;
  const budget = text.slice(0, maxLen);
  let cut = -1;
  for (const m of budget.matchAll(/[.!?](?=\s|$)/g)) cut = m.index;
  if (cut > maxLen * 0.35) return budget.slice(0, cut + 1).trim();
  const lastSpace = budget.lastIndexOf(" ");
  const wordCut = lastSpace > maxLen * 0.35 ? budget.slice(0, lastSpace) : budget;
  return wordCut.trim() + "…";
}

// Prefer the full untruncated source sentence (sources[0].text) over
// data.label, which the backend may have already pre-cut at a fixed length
// with no regard for word/sentence boundaries — then apply smartTruncate
// on top so the displayed preview always ends cleanly.
function previewText(node, maxLen) {
  const full = node?.data?.sources?.[0]?.text || node?.data?.label || "";
  return smartTruncate(full, maxLen);
}
function shortDocName(n) { return (n || "").replace(/\.(pdf|txt|docx?)$/i, "").replace(/_/g, " "); }

// Structure tier is an internal pipeline label (layout_structure.py) meant
// for debugging, not for a lawyer reading the UI — translate the known
// values, and fall back to a readable version of anything unrecognized
// rather than ever printing a raw internal_snake_case_token.
const TIER_LABELS = {
  docling_layout: "Layout-detected",
  legacy_fallback_internal: "Standard",
  legacy_fallback_docling_error: "Standard",
  legacy_fallback_no_headings: "Standard",
  legacy_text_patterns: "Standard",
};
function friendlyTier(tier) {
  if (!tier) return "—";
  return TIER_LABELS[tier] || tier.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// Node "type" is an internal pipeline label too (EVENT_KEYWORDS category
// names, or this app's own IMPORTANT_LINE/SECTION/DATED_EVENT types) — a
// lawyer reading "IMPORTANT_LINE" has no idea what that means. Translate
// the ones this app actually produces; ALL-CAPS keyword categories
// (ORDER, NOTICE, ...) already read as real words, just Title-Case them.
const TYPE_LABELS = {
  IMPORTANT_LINE: "Key Fact",
  SECTION: "Document Section",
  DATED_EVENT: "Dated Event",
  fallback_party_block: "Case Parties",
};
function friendlyType(type) {
  if (!type) return "Fact";
  return TYPE_LABELS[type] ||
    type.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}
// Rhetorical role (rhetorical_roles.py) — where in a judgment/pleading's
// argument structure a fact sits. Internal SNAKE_CASE → what a lawyer reads.
const ROLE_LABELS = {
  FACTS: "Facts", ISSUES: "Issues", ANALYSIS: "Court's analysis",
  RULING: "Ruling", PRECEDENT: "Precedent cited",
  ARGUMENTS_PETITIONER: "Petitioner's argument",
  ARGUMENTS_RESPONDENT: "Respondent's argument",
};
function friendlyRole(role) {
  if (!role) return "";
  return ROLE_LABELS[role] ||
    role.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}
// A chronology should read as one line per real event, not one line per
// sentence that happens to mention the same date — a real report showed
// the same 24.09.2024 circular six times because six different paragraphs
// (SYNOPSIS, PRAYER, GROUNDS...) each mention it. Within each date, keep
// the fullest (longest) text per cluster of substantially-overlapping
// entries and drop the rest — real word-overlap, not exact-match, since
// these are different sentences describing the same event, not literal
// duplicates.
function dedupeByDateSimilarity(nodes) {
  const textOf = n => (n.data.sources[0]?.text || n.data.label || "").toLowerCase();
  const wordSet = text => new Set(text.split(/[^a-z0-9]+/).filter(w => w.length > 3));
  const overlapRatio = (a, b) => {
    if (!a.size || !b.size) return 0;
    let common = 0;
    for (const w of a) if (b.has(w)) common++;
    return common / Math.min(a.size, b.size);
  };
  // Pass 1: the SAME sentence can produce two DATED_EVENT nodes when its
  // text mentions two different dates (a real case: one table row naming
  // both 21.07.2026 and 25.08.2026 got a node anchored at each date,
  // both showing the identical row) — these never land in the same
  // per-date group below, so catch near-identical text globally first,
  // regardless of date, before the softer same-date pass.
  const seen = [];
  const exactDeduped = nodes.filter(n => {
    const t = textOf(n);
    if (seen.some(s => overlapRatio(wordSet(t), wordSet(s)) > 0.85)) return false;
    seen.push(t);
    return true;
  });

  const byDate = groupBy(exactDeduped, n => n.data.date);
  const out = [];
  for (const [, group] of byDate) {
    const sorted = group.slice().sort((a, b) => textOf(b).length - textOf(a).length);
    const kept = [];
    for (const n of sorted) {
      const words = wordSet(textOf(n));
      if (!kept.some(k => overlapRatio(words, wordSet(textOf(k))) > 0.5)) kept.push(n);
    }
    out.push(...kept);
  }
  return out;
}

function groupBy(arr, fn) {
  const m = new Map();
  for (const item of arr) {
    const k = fn(item);
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(item);
  }
  return m;
}

window.addEventListener("DOMContentLoaded", () => App.init());
