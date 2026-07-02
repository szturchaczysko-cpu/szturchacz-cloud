"use strict";
const $ = (id) => document.getElementById(id);

async function api(path, body) {
  const opt = { method: body ? "POST" : "GET", headers: {} };
  if (body) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const r = await fetch(path, opt);
  return r.json().catch(() => ({ ok: false, message: "Błąd sieci." }));
}

/* --- Nawigacja: menu kafelków ↔ sekcje na pełnym ekranie --- */
function pokazEkran(id) {
  $("menu").hidden = !!id;
  document.querySelectorAll(".koord-ekran").forEach((s) => { s.hidden = (s.id !== id); });
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

/* --- Wieżowczyk: podajnik surowego wsadu (zakres dat / odwrotny zam) --- */
async function loadWiezowczyk() {
  const p = new URLSearchParams();
  if ($("wz-od").value) p.set("od", $("wz-od").value);
  if ($("wz-do").value) p.set("do", $("wz-do").value);
  if ($("wz-zam").value.trim()) p.set("zam", $("wz-zam").value.trim());
  $("wz-msg").textContent = "Pobieram…";
  const r = await api("/api/koord/wiezowczyk?" + p.toString());
  const box = $("wz-lista");
  box.innerHTML = "";
  if (!r.ok) { $("wz-msg").textContent = r.message || "Błąd."; return; }
  $("wz-msg").textContent = "Spraw: " + (r.liczba || 0);
  (r.sprawy || []).forEach((s) => {
    const d = document.createElement("details");
    d.className = "gotowiec";
    const sum = document.createElement("summary");
    const flagi = [s.ReklFlag ? "REKL" : "", s.KurFlag ? "KURIER" : "", s.Zoltek ? "ŻÓŁTEK" : ""]
      .filter(Boolean).join(" ");
    sum.textContent = `${s.zknzamnr} · ${s.data_zama} · ${s.kraj || s.kaCountry || "?"} · ${s.rodzaj_zama || "?"}`
      + (flagi ? " · " + flagi : "") + (s.czy_austauch_zakonczony ? " · ZAKOŃCZONA" : "");
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = (s.klient_nazwa || "") + (s.kakMail ? " · " + s.kakMail : "") + (s.ktTelNr ? " · " + s.ktTelNr : "");
    const pre = document.createElement("pre");
    pre.className = "codeblock";
    const koperta = (s.koperta || []).map((k) => `[${k.kiedy}] ${k.kto}: ${k.tresc}`).join("\n");
    pre.textContent = (s.wsad_panel || s.suchy_wsad)
      + (koperta ? "\n\n— KOPERTA (Comment):\n" + koperta : "");
    d.appendChild(sum); d.appendChild(meta); d.appendChild(pre);
    box.appendChild(d);
  });
  if (!box.children.length) box.innerHTML = '<p class="empty">Brak spraw w tym zakresie.</p>';
}

/* --- Rozmowy: archiwum WEM. Poziom 1 = zamówienie (klucz domeny), poziom 2 = klient. --- */
const arch = { tryb: "zam", kanal: "" };

function czasRozmowy(ts) {
  return ts ? new Date(ts * 1000).toLocaleString("pl-PL") : "—";
}

function liniaWiadomosci(m) {
  const p = document.createElement("p");
  p.className = "rozmowa-linia"
    + (m.kierunek === "out" ? " rozmowa-linia--out" : "")
    + (m.duplikat ? " rozmowa-linia--dup" : "");
  const kto = m.kierunek === "out" ? "MY" : "KLIENT";
  const kanal = m.channel ? " · " + m.channel : "";
  p.textContent = `[${czasRozmowy(m.ts)}${kanal}] ${kto}${m.duplikat ? " (duplikat)" : ""}: ${m.text || "(pusta treść)"}`;
  return p;
}

function pozycjaArchiwum(naglowek, meta, urlOsi) {
  const d = document.createElement("details");
  d.className = "gotowiec";
  const s = document.createElement("summary");
  s.textContent = naglowek;
  const m = document.createElement("div");
  m.className = "meta"; m.textContent = meta;
  const body = document.createElement("div");
  d.appendChild(s); d.appendChild(m); d.appendChild(body);
  d.addEventListener("toggle", async () => {
    if (!d.open || body.dataset.loaded) return;
    body.dataset.loaded = "1";
    const t = await api(urlOsi);
    body.innerHTML = "";
    (t.wiadomosci || []).forEach((w) => body.appendChild(liniaWiadomosci(w)));
    if (!body.children.length) body.innerHTML = '<p class="empty">Pusto.</p>';
  });
  return d;
}

function archParams() {
  const p = new URLSearchParams();
  if (arch.kanal) p.set("channel", arch.kanal);
  p.set("limit", $("arch-limit").value || "100");
  if ($("arch-od").value) p.set("od", $("arch-od").value);
  if ($("arch-do").value) p.set("do", $("arch-do").value);
  return "?" + p.toString();
}

async function szukajArchiwum() {
  const q = $("arch-szukaj").value.trim();
  if (!q) return;
  const box = $("rozmowy");
  box.innerHTML = '<p class="empty">Szukam…</p>';
  const r = await api("/api/koord/rozmowy/szukaj?q=" + encodeURIComponent(q));
  box.innerHTML = "";
  if (!r.ok) { $("arch-msg").textContent = r.message || "Błąd."; return; }
  $("arch-msg").textContent = `Szukano (${r.typ}): ${r.q} — wątków: ${(r.watki || []).length}`;
  (r.watki || []).forEach((w) => {
    const zam = (w.order_refs || []).length ? " · zam " + w.order_refs.join(", ") : "";
    const naglowek = `${w.channel} · ${w.klient} · ${w.liczba} wiad. (klient ${w.in} / my ${w.out})${zam}`;
    const meta = "ostatnia: " + czasRozmowy(w.ostatnia_ts) + " · " + (w.ostatnia || "");
    box.appendChild(pozycjaArchiwum(naglowek, meta, "/api/koord/rozmowy/watek?id=" + encodeURIComponent(w.thread_id)));
  });
  if (!box.children.length) box.innerHTML = '<p class="empty">Brak trafień.</p>';
}

async function pobierzHistorie() {
  const od = $("hist-od").value, doo = $("hist-do").value;
  if (!od || !doo) { $("arch-msg").textContent = "Podaj zakres dat (≤31 dni)."; return; }
  $("btn-hist").disabled = true;
  $("arch-msg").textContent = "Pobieram historię z bramy…";
  const r = await api("/api/koord/wem/historia", { kanal: $("hist-kanal").value, od, do: doo });
  $("btn-hist").disabled = false;
  $("arch-msg").textContent = r.ok
    ? `Historia ${r.kanal} ${r.od}–${r.do}: pobrano ${r.pobrano}, zapisano ${r.zapisano}, duplikatów ${r.pominieto_duplikaty}.`
    : (r.message || "Błąd.");
  if (r.ok && r.zapisano) loadRozmowy();
}

async function loadRozmowy() {
  const box = $("rozmowy");
  $("arch-msg").textContent = "";
  box.innerHTML = '<p class="empty">Ładuję…</p>';
  const q = archParams();
  if (arch.tryb === "zam") {
    const r = await api("/api/koord/rozmowy/zamowienia" + q);
    box.innerHTML = "";
    (r.zamowienia || []).forEach((z) => {
      const naglowek = `${z.etykieta} · ${z.liczba} wiad. (klient ${z.in} / my ${z.out}) · ${z.kanaly.join("+")}`;
      const meta = "klienci: " + (z.klienci.join(", ") || "—") + " · ostatnia: "
        + czasRozmowy(z.ostatnia_ts) + " · " + (z.ostatnia || "");
      const url = z.zam
        ? "/api/koord/rozmowy/zamowienie?zam=" + encodeURIComponent(z.zam)
        : "/api/koord/rozmowy/watek?id=" + encodeURIComponent(z.etykieta.replace("bez numeru · ", ""));
      box.appendChild(pozycjaArchiwum(naglowek, meta, url));
    });
    if (!box.children.length) box.innerHTML = '<p class="empty">Brak rozmów w tym widoku.</p>';
  } else {
    const r = await api("/api/koord/rozmowy" + q);
    box.innerHTML = "";
    (r.watki || []).forEach((w) => {
      const zam = (w.order_refs || []).length ? " · zam " + w.order_refs.join(", ") : "";
      const naglowek = `${w.channel} · ${w.klient} · ${w.liczba} wiad. (klient ${w.in} / my ${w.out})${zam}`;
      const meta = "ostatnia: " + czasRozmowy(w.ostatnia_ts) + " · " + (w.ostatnia || "");
      box.appendChild(pozycjaArchiwum(naglowek, meta, "/api/koord/rozmowy/watek?id=" + encodeURIComponent(w.thread_id)));
    });
    if (!box.children.length) box.innerHTML = '<p class="empty">Brak rozmów w tym widoku.</p>';
  }
}

function wireChips(containerId, attr, onPick) {
  const box = $(containerId);
  box.querySelectorAll(".chip").forEach((ch) => {
    ch.addEventListener("click", () => {
      box.querySelectorAll(".chip").forEach((x) => x.classList.remove("chip--on"));
      ch.classList.add("chip--on");
      onPick(ch.dataset[attr] || "");
    });
  });
}

window.addEventListener("DOMContentLoaded", () => {
  // menu kafelków ↔ pełnoekranowe sekcje
  document.querySelectorAll(".kafelek").forEach((k) => {
    k.addEventListener("click", () => {
      pokazEkran(k.dataset.cel);
      if (k.dataset.cel === "sek-rozmowy" && !$("rozmowy").children.length) loadRozmowy();
    });
  });
  document.querySelectorAll(".btn-wroc").forEach((b) => b.addEventListener("click", () => pokazEkran("")));

  $("btn-ingest").addEventListener("click", ingest);
  $("btn-save-config").addEventListener("click", saveConfig);
  $("btn-add-op").addEventListener("click", addOperator);
  $("btn-save-prompt").addEventListener("click", savePrompt);
  $("prompt-list").addEventListener("change", (e) => { if (e.target.value) $("prompt-url").value = e.target.value; });
  $("btn-reload-rozmowy").addEventListener("click", loadRozmowy);
  $("btn-arch-szukaj").addEventListener("click", szukajArchiwum);
  $("btn-hist").addEventListener("click", pobierzHistorie);
  $("arch-szukaj").addEventListener("keydown", (e) => { if (e.key === "Enter") szukajArchiwum(); });
  ["arch-limit", "arch-od", "arch-do"].forEach((i) => $(i).addEventListener("change", loadRozmowy));
  $("btn-wiezowczyk").addEventListener("click", loadWiezowczyk);
  $("wz-zam").addEventListener("keydown", (e) => { if (e.key === "Enter") loadWiezowczyk(); });
  wireChips("arch-tryb", "tryb", (v) => { arch.tryb = v || "zam"; loadRozmowy(); });
  wireChips("arch-kanaly", "kanal", (v) => { arch.kanal = v; loadRozmowy(); });

  load();
  loadPrompts();
});
