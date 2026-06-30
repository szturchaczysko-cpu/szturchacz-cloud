"use strict";

const $ = (id) => document.getElementById(id);

async function api(path, body) {
  const opt = { method: body ? "POST" : "GET", headers: {} };
  if (body) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const r = await fetch(path, opt);
  try { return await r.json(); } catch (e) { return { ok: false, message: "Błąd sieci." }; }
}

// Wyłuskaj z odpowiedzi AI: krok „tu i teraz", draft do klienta, TAG.
function parseAi(text) {
  const out = { krok: "", draft: "", tag: "", raw: text || "" };
  if (!text) return out;
  const tag = text.match(/C#\s*:\s*\d{1,2}\.\d{1,2}[^\n]*/i);
  if (tag) out.tag = tag[0].trim();
  const krok = text.match(/Krok teraz\s*:\s*(.+)/i);
  if (krok) out.krok = krok[1].trim();
  const d = text.match(/Draft do klienta\s*:\s*\n?([\s\S]*?)(?:\n\s*TAG:|\n\s*\[FORUM|$)/i);
  if (d) out.draft = d[1].trim();
  return out;
}

function bubble(role, content) {
  const div = document.createElement("div");
  div.className = "bubble bubble--" + (role === "user" ? "user" : "model");
  div.textContent = content;
  return div;
}

function renderMessages(messages) {
  const box = $("messages");
  box.innerHTML = "";
  (messages || []).forEach((m) => box.appendChild(bubble(m.role, m.content)));
  box.scrollTop = box.scrollHeight;
}

function renderTurn(turn) {
  if (!turn) return;
  const p = parseAi(turn.ai_text);
  if (p.krok) { $("step-text").textContent = p.krok; $("step-card").hidden = false; }
  if (p.draft) { $("draft-text").textContent = p.draft; $("draft-card").hidden = false; }
  else { $("draft-card").hidden = true; }
  if ((turn.zakazane || []).length) {
    const w = document.createElement("div");
    w.className = "bubble bubble--warn";
    w.textContent = "⚠ AI użyło zakazanych fraz: " + turn.zakazane.join(", ");
    $("messages").appendChild(w);
  }
}

function renderCase(state) {
  const has = !!state.case;
  $("case-empty").hidden = has;
  $("case-body").hidden = !has;
  $("btn-next").hidden = has;
  if (has) {
    const c = state.case;
    $("case-nr").textContent = c.numer_zamowienia;
    $("case-meta").textContent = c.pelna_linia_szturchacza || "";
    $("case-pz").textContent = "PZ" + (c.result_pz != null ? c.result_pz : "?");
    $("case-score").textContent = "score " + (c.score || 0);
    $("case-grupa").textContent = c.grupa || "";
  }
}

async function loadState() {
  const s = await api("/api/operator/state");
  if (!s.ok) { location.href = "/"; return; }
  $("op-grupa").textContent = (s.operator && s.operator.grupa) || "—";
  $("op-spraw").textContent = (s.wolne != null ? s.wolne : 0) + " wolnych";
  $("op-diamenty").textContent = "💎 " + (s.diamenty_dzis || 0);
  renderCase(s);
  renderMessages(s.messages);
  // pokaż ostatni krok/draft z historii
  const lastModel = [...(s.messages || [])].reverse().find((m) => m.role === "model");
  if (lastModel) renderTurn({ ai_text: lastModel.content });
}

async function next() {
  $("btn-next").disabled = true;
  const r = await api("/api/operator/next", {});
  $("btn-next").disabled = false;
  if (!r.ok) { alert(r.message || "Błąd."); return; }
  if (!r.case) { $("case-empty").textContent = r.message || "Brak gotowych spraw."; return; }
  await loadState();
  if (r.turn) renderTurn(r.turn);
}

async function send() {
  const inp = $("chat-input");
  const text = inp.value.trim();
  if (!text) return;
  inp.value = "";
  $("messages").appendChild(bubble("user", text));
  const r = await api("/api/operator/message", { text });
  if (!r.ok) { alert(r.message || "Błąd."); return; }
  await loadState();
  if (r.turn) renderTurn(r.turn);
}

async function complete() {
  const r = await api("/api/operator/complete", {});
  if (!r.ok) { $("case-msg").textContent = r.message || "Nie można zakończyć."; return; }
  $("case-msg").textContent = "";
  $("step-card").hidden = true; $("draft-card").hidden = true;
  await loadState();
}

async function skip() {
  const powod = prompt("Powód pominięcia sprawy:");
  if (powod == null) return;
  const r = await api("/api/operator/skip", { powod });
  if (!r.ok) { $("case-msg").textContent = r.message || "Nie można pominąć."; return; }
  $("step-card").hidden = true; $("draft-card").hidden = true;
  await loadState();
}

function copyDraft() {
  const t = $("draft-text").textContent;
  if (navigator.clipboard) navigator.clipboard.writeText(t);
  $("btn-copy").textContent = "Skopiowano";
  setTimeout(() => ($("btn-copy").textContent = "Kopiuj"), 1500);
}

window.addEventListener("DOMContentLoaded", () => {
  $("btn-next").addEventListener("click", next);
  $("btn-send").addEventListener("click", send);
  $("chat-input").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  $("btn-complete").addEventListener("click", complete);
  $("btn-skip").addEventListener("click", skip);
  $("btn-copy").addEventListener("click", copyDraft);
  loadState();
});
