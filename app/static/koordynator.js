"use strict";
const $ = (id) => document.getElementById(id);

async function api(path, body) {
  const opt = { method: body ? "POST" : "GET", headers: {} };
  if (body) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const r = await fetch(path, opt);
  return r.json().catch(() => ({ ok: false, message: "Błąd sieci." }));
}

function renderCounts(counts) {
  const ul = $("counts");
  ul.innerHTML = "";
  Object.keys(counts || {}).forEach((grupa) => {
    const statuses = counts[grupa] || {};
    const total = Object.values(statuses).reduce((a, b) => a + b, 0);
    const li = document.createElement("li");
    const left = document.createElement("span");
    left.textContent = grupa;
    const right = document.createElement("span");
    right.className = "meta";
    right.textContent = "wolne " + (statuses.wolny || 0) + " · w toku " + (statuses.w_toku || 0)
      + " · zakończone " + (statuses.zakonczony || 0) + " · razem " + total;
    li.appendChild(left); li.appendChild(right);
    ul.appendChild(li);
  });
  if (!ul.children.length) ul.innerHTML = '<li class="empty">Brak spraw.</li>';
}

function renderOperators(ops) {
  const ul = $("operators");
  ul.innerHTML = "";
  (ops || []).forEach((o) => {
    const li = document.createElement("li");
    const left = document.createElement("span");
    left.textContent = o.label + " (" + o.pid + ")";
    const right = document.createElement("span");
    right.className = "meta";
    right.textContent = o.grupa + " · forum:" + (o.forum_nick || "—");
    const del = document.createElement("button");
    del.className = "btn btn--danger"; del.textContent = "Usuń";
    del.addEventListener("click", async () => {
      await api("/api/koord/operator/delete", { pid: o.pid }); load();
    });
    right.appendChild(document.createTextNode(" ")); right.appendChild(del);
    li.appendChild(left); li.appendChild(right);
    ul.appendChild(li);
  });
  if (!ul.children.length) ul.innerHTML = '<li class="empty">Brak operatorów.</li>';
}

async function load() {
  const s = await api("/api/koord/overview");
  if (!s.ok) { location.reload(); return; }
  $("kpi-diamenty").textContent = "💎 " + (s.diamenty_dzis || 0) + " dziś";
  $("kpi-forum").textContent = "forum: " + (s.forum_mode || "—");
  $("kpi-autopilot").textContent = "autopilot: " + (s.autopilot || "—");
  renderCounts(s.counts);
  renderOperators(s.operatorzy);
  $("cfg-percent").value = (s.config && s.config.autopilot_percent) || 0;
  $("cfg-retry").value = (s.config && s.config.woreczek_retry_h) || 2;
}

async function ingest() {
  const text = $("wsad").value;
  const r = await api("/api/koord/ingest", { text });
  $("ingest-msg").textContent = r.ok ? ("Dodano " + r.dodane + ", pominięto " + r.pominiete) : (r.message || "Błąd");
  if (r.ok) { $("wsad").value = ""; load(); }
}

async function saveConfig() {
  await api("/api/koord/config", { key: "autopilot_percent", value: parseInt($("cfg-percent").value, 10) || 0 });
  const r = await api("/api/koord/config", { key: "woreczek_retry_h", value: parseInt($("cfg-retry").value, 10) || 2 });
  $("config-msg").textContent = r.ok ? "Zapisano." : (r.message || "Błąd");
}

async function addOperator() {
  const r = await api("/api/koord/operator", {
    pid: $("op-pid").value.trim(), label: $("op-label").value.trim(),
    grupa: $("op-grupa").value.trim().toUpperCase(), forum_nick: $("op-nick").value.trim(),
  });
  $("op-msg").textContent = r.ok ? "Zapisano." : (r.message || "Błąd");
  if (r.ok) { ["op-pid", "op-label", "op-grupa", "op-nick"].forEach((i) => ($(i).value = "")); load(); }
}

async function loadPrompts() {
  const r = await api("/api/koord/prompts");
  if (!r.ok) return;
  const sel = $("prompt-list");
  sel.innerHTML = '<option value="">— wybierz z repo —</option>';
  (r.prompts || []).forEach((p) => {
    const o = document.createElement("option");
    o.value = p.url; o.textContent = p.name;
    sel.appendChild(o);
  });
  $("prompt-current").textContent = r.current || "(domyślny z env)";
}

async function savePrompt() {
  const url = $("prompt-url").value.trim() || $("prompt-list").value.trim();
  const r = await api("/api/koord/prompt", { url });
  $("prompt-msg").textContent = r.ok ? "Ustawiono." : (r.message || "Błąd");
  if (r.ok) { $("prompt-current").textContent = r.current || "(domyślny z env)"; $("prompt-url").value = ""; }
}

async function loadGotowce() {
  const r = await api("/api/koord/gotowce");
  const box = $("gotowce");
  box.innerHTML = "";
  if (!r.ok || !(r.gotowce || []).length) { box.innerHTML = '<p class="empty">Brak gotowców. Uruchom autopilot.</p>'; return; }
  r.gotowce.forEach((g) => {
    const d = document.createElement("details");
    d.className = "gotowiec";
    const s = document.createElement("summary");
    s.textContent = `${g.nrzam} · ${g.grupa} · score ${g.score}`;
    const meta = document.createElement("div");
    meta.className = "meta"; meta.textContent = g.wsad || "";
    const pre = document.createElement("pre");
    pre.className = "codeblock";
    pre.textContent = g.gotowiec || "(brak treści)";
    d.appendChild(s); d.appendChild(meta); d.appendChild(pre);
    box.appendChild(d);
  });
}

async function runAutopilot() {
  $("btn-run-autopilot").disabled = true;
  const r = await api("/api/koord/autopilot/run", {});
  $("btn-run-autopilot").disabled = false;
  const out = $("autopilot-out");
  out.hidden = false;
  out.textContent = JSON.stringify(r, null, 2);
  load();
  loadGotowce();
}

window.addEventListener("DOMContentLoaded", () => {
  $("btn-ingest").addEventListener("click", ingest);
  $("btn-save-config").addEventListener("click", saveConfig);
  $("btn-add-op").addEventListener("click", addOperator);
  $("btn-run-autopilot").addEventListener("click", runAutopilot);
  $("btn-save-prompt").addEventListener("click", savePrompt);
  $("prompt-list").addEventListener("change", (e) => { if (e.target.value) $("prompt-url").value = e.target.value; });
  $("btn-reload-gotowce").addEventListener("click", loadGotowce);
  load();
  loadPrompts();
  loadGotowce();
});
