"use strict";
const $ = (id) => document.getElementById(id);

async function login() {
  const password = $("koord-pass").value;
  const r = await fetch("/api/koord/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const j = await r.json().catch(() => ({ ok: false }));
  if (j.ok) { location.reload(); }
  else { $("koord-login-msg").textContent = j.message || "Błędne hasło."; }
}

window.addEventListener("DOMContentLoaded", () => {
  $("btn-koord-login").addEventListener("click", login);
  $("koord-pass").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });
});
