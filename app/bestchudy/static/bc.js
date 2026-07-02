/* BESTCHUDY — porównywarka. Wanilia, zero frameworków; CSP = zero inline (wszystko tutaj).
   Konwencja API jak w całej apce: {ok: bool, message?} (wzorzec api() z operator.js — kopia). */
(function () {
  "use strict";

  const LIMIT_TEKSTU = 20000; // lustra limitów z logika.py — serwer odrzuca, my ostrzegamy wcześniej
  const LIMIT_TAG = 2000;

  async function api(path, body) {
    // Rozróżniamy DWIE awarie (diagnoza z produkcji, 2026-07-03): zerwane połączenie
    // (restart instancji / timeout usługi) vs odpowiedź serwera bez JSON-a (surowy 500).
    // Ogólne „Błąd sieci." wysyłało ludzi w złą stronę.
    let r;
    try {
      r = await fetch(path, body ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      } : undefined);
    } catch (e) {
      return { ok: false, message: "Połączenie zerwane w trakcie — serwer nie dokończył " +
        "odpowiedzi (możliwy restart usługi albo timeout). Spróbuj ponownie; jeśli się " +
        "powtarza, zgłoś koordynatorowi." };
    }
    try {
      return await r.json();
    } catch (e) {
      return { ok: false, message: "Serwer odpowiedział awarią bez treści (HTTP " + r.status +
        ") — błąd po stronie serwera, nie sieci. Podaj koordynatorowi ten numer HTTP." };
    }
  }

  const $ = (id) => document.getElementById(id);

  // --- Zakładki -----------------------------------------------------------------
  const zakladki = $("bc-zakladki");
  zakladki.addEventListener("click", (ev) => {
    const guzik = ev.target.closest("[data-zakladka]");
    if (!guzik) return;
    zakladki.querySelectorAll(".chip").forEach((c) => c.classList.remove("is-active"));
    guzik.classList.add("is-active");
    document.querySelectorAll(".bc-ekran").forEach((s) => {
      s.hidden = s.dataset.ekran !== guzik.dataset.zakladka;
    });
    if (guzik.dataset.zakladka === "odrzuty") odswiezOdrzuty();
    if (guzik.dataset.zakladka === "kalendarz") { odswiezKalendarz(); odswiezOceny(); }
  });

  // --- Tryb (selektor) -----------------------------------------------------------
  let tryb = "standard";
  $("bc-tryby").addEventListener("click", (ev) => {
    const guzik = ev.target.closest("[data-tryb]");
    if (!guzik) return;
    document.querySelectorAll("#bc-tryby .chip").forEach((c) => c.classList.remove("is-active"));
    guzik.classList.add("is-active");
    tryb = guzik.dataset.tryb;
  });

  // --- Sklejka wsadu (ten sam algorytm co logika.sklej_wsad na serwerze) ------------
  function sklejka() {
    return [$("wsad-panel").value.trim(), $("koperta").value.trim(), $("tag").value.trim()]
      .filter(Boolean).join("\n\n");
  }
  function nrzam(tekst) {
    const m = String(tekst || "").match(/(?<!\d)(\d{5,7})(?!\d)/);
    return m ? m[1] : "";
  }
  function zaDlugi() {
    if ($("wsad-panel").value.trim().length > LIMIT_TEKSTU ||
        $("koperta").value.trim().length > LIMIT_TEKSTU) {
      return "Wsad za długi (panel/koperta maks. 20000 znaków) — skróć PRZED wklejeniem do v11, " +
             "inaczej porównanie będzie nieuczciwe.";
    }
    if ($("tag").value.trim().length > LIMIT_TAG) return "Tag za długi (maks. 2000 znaków).";
    return "";
  }
  function odswiezPodglad() {
    const s = sklejka();
    $("sklejka-podglad").textContent = s || "(pusto)";
    $("nrzam-znacznik").textContent = "NrZam: " + (nrzam(s) || "—");
  }
  ["wsad-panel", "koperta", "tag"].forEach((id) => $(id).addEventListener("input", odswiezPodglad));
  odswiezPodglad();

  $("btn-kopiuj").addEventListener("click", async () => {
    const s = sklejka();
    if (!s) { $("wsad-status").textContent = "Pusty wsad — nie ma czego kopiować."; return; }
    const blad = zaDlugi();
    if (blad) { $("wsad-status").textContent = blad; return; } // NIE kopiujemy — v11 nie może dostać więcej niż chudy
    try {
      await navigator.clipboard.writeText(s);
      $("wsad-status").textContent = "Skopiowane — wklej w ramkę v11 (ta sama sklejka idzie chudemu).";
    } catch (e) {
      $("wsad-status").textContent = "Przeglądarka zablokowała schowek — skopiuj z podglądu sklejki.";
      document.querySelector(".bc-podglad").open = true;
    }
  });

  // --- FEED: sprawy z wieżowczyka (B3) ----------------------------------------------
  function uzyjSprawy(s) {
    if (!s.ma_karte) {
      $("feed-status").textContent = "Podajnik nie zwrócił pełnej karty dla " + (s.nrzam || "?") +
        " — wsad uzupełnij ręcznie. Streszczenie: " + (s.opis || "(brak)");
      return;
    }
    $("wsad-panel").value = s.wsad_panel;
    $("koperta").value = s.koperta_tekst || "";
    $("tag").value = ""; // tag siedzi już w karcie — drugi raz by się zdublował
    $("rolka").value = ""; // rolka poprzedniej sprawy nie może skleić się z nową
    // NOWA sprawa = czysty stan chudego; bez tego „Zapisz" mógłby sparować werdykty nowej
    // sprawy z odpowiedzią chudego dla POPRZEDNIEJ (sfałszowany rekord badawczy).
    historia = [];
    snapshotWsadu = null;
    ostatniPrompt = "";
    $("chudy-rozmowa").textContent = "";
    resetOceny();
    odswiezPodglad();
    $("feed-lista").hidden = true;
    $("feed-status").textContent = "Wciągnięto sprawę " + (s.nrzam || "?") +
      " (tag jest w karcie; pole TAG zostaw puste). Teraz: KOPIUJ WSAD → v11, POLICZ → chudy.";
  }

  function pokazSprawy(sprawy) {
    const kontener = $("feed-lista");
    kontener.textContent = "";
    sprawy.forEach((s) => {
      const div = document.createElement("div");
      div.className = "bc-pozycja";
      const glowa = document.createElement("div");
      glowa.className = "bc-pozycja-glowa";
      const opis = document.createElement("span");
      opis.textContent = (s.nrzam || "?") + " · " + (s.data || "?") + " · " + (s.kraj || "?") +
        (s.ma_karte ? "" : " · (bez pełnej karty)");
      const guzik = document.createElement("button");
      guzik.type = "button";
      guzik.className = "btn btn--small";
      guzik.textContent = "Użyj";
      guzik.addEventListener("click", () => uzyjSprawy(s));
      glowa.appendChild(opis);
      glowa.appendChild(guzik);
      div.appendChild(glowa);
      const meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = s.opis || "";
      div.appendChild(meta);
      kontener.appendChild(div);
    });
    kontener.hidden = !sprawy.length;
  }

  async function pobierzSprawy(zam) {
    const guziki = [$("btn-nastepne"), $("btn-po-numerze")];
    if (guziki[0].disabled) return; // blokada in-flight jak przy pozostałych przyciskach
    guziki.forEach((g) => { g.disabled = true; });
    $("feed-status").textContent = "Pobieram z wieżowczyka…";
    try {
      const w = await api("/bestchudy/api/sprawy?limit=10" + (zam ? "&zam=" + encodeURIComponent(zam) : ""));
      if (!w.ok) {
        $("feed-lista").hidden = true;
        $("feed-status").textContent = w.message || "Podajnik niedostępny.";
        return;
      }
      if (!w.sprawy.length) {
        $("feed-lista").hidden = true;
        $("feed-status").textContent = zam ? "Nie znaleziono sprawy " + zam + "." : "Podajnik pusty.";
        return;
      }
      if (w.sprawy.length === 1) { uzyjSprawy(w.sprawy[0]); return; }
      pokazSprawy(w.sprawy);
      $("feed-status").textContent = "Wybierz sprawę z listy (najnowsze na górze).";
    } finally {
      guziki.forEach((g) => { g.disabled = false; });
    }
  }

  function poNumerze() {
    const zam = $("feed-zam").value.trim();
    if (!/^\d{4,9}$/.test(zam)) { $("feed-status").textContent = "Numer zamówienia to 4-9 cyfr."; return; }
    pobierzSprawy(zam);
  }
  $("btn-nastepne").addEventListener("click", () => pobierzSprawy(""));
  $("btn-po-numerze").addEventListener("click", poNumerze);
  $("feed-zam").addEventListener("keydown", (ev) => { if (ev.key === "Enter") poNumerze(); });

  // --- Chudy: rozmowa ------------------------------------------------------------
  let historia = [];        // [{role:"user"|"model", content}] — role jak w silniku skrzynki
  let ostatniPrompt = "";
  let snapshotWsadu = null; // wsad z chwili POLICZ — to on idzie do rekordu porównania
  let liczenie = false;     // blokada in-flight (POLICZ i dopisek dzielą jedną)

  function dodajDymek(rola, tresc) {
    const dymek = document.createElement("div");
    dymek.className = "msg" + (rola === "user" ? " msg--mine" : "");
    dymek.textContent = (rola === "user" ? "MY: " : "CHUDY: ") + tresc;
    $("chudy-rozmowa").appendChild(dymek);
    $("chudy-rozmowa").scrollTop = $("chudy-rozmowa").scrollHeight;
  }

  const werdykty = { v11: "", chudy: "" };
  function resetOceny() {
    werdykty.v11 = "";
    werdykty.chudy = "";
    document.querySelectorAll("#werdykt-v11 .chip, #werdykt-chudy .chip")
      .forEach((c) => c.classList.remove("is-active"));
    $("komentarz").value = "";
    $("zapis-status").textContent = "";
    $("zapis-status").classList.remove("ok");
  }

  async function policz(cialo, odNowa) {
    if (liczenie) return false;
    liczenie = true;
    $("btn-policz").disabled = true;
    $("btn-dopisz").disabled = true;
    $("wsad-status").textContent = "Chudy liczy…";
    try {
      const w = await api("/bestchudy/api/policz", cialo);
      if (!w.ok) { $("wsad-status").textContent = w.message || "Silnik niedostępny."; return false; }
      if (odNowa) {                    // czyścimy dopiero PO sukcesie — błąd sieci nie gubi rozmowy
        historia = [];
        $("chudy-rozmowa").textContent = "";
        resetOceny();
        snapshotWsadu = { wsad: w.wejscie_bazowe || "", rolka: w.rolka || "" };
      }
      historia.push({ role: "user", content: w.wejscie });
      historia.push({ role: "model", content: w.odpowiedz });
      ostatniPrompt = w.prompt || "";
      dodajDymek("user", w.wejscie);
      dodajDymek("model", w.odpowiedz);
      $("wsad-status").textContent = "Chudy odpowiedział (prompt: " + (w.prompt || "?") + ").";
      return true;
    } finally {
      liczenie = false;
      $("btn-policz").disabled = false;
      $("btn-dopisz").disabled = false;
    }
  }

  $("btn-policz").addEventListener("click", () => {
    if (liczenie) return;
    if (!sklejka()) { $("wsad-status").textContent = "Pusty wsad."; return; }
    const blad = zaDlugi();
    if (blad) { $("wsad-status").textContent = blad; return; }
    policz({
      wsad_panel: $("wsad-panel").value, koperta: $("koperta").value,
      tag: $("tag").value, rolka: $("rolka").value,
    }, true);
  });

  $("btn-dopisz").addEventListener("click", async () => {
    if (liczenie) return;
    const tekst = $("chudy-wiadomosc").value.trim();
    if (!tekst) return;
    if (!historia.length) { $("wsad-status").textContent = "Najpierw POLICZ CHUDEGO na wsadzie."; return; }
    const ok = await policz({ kontynuacja: tekst, historia: historia }, false);
    if (ok) $("chudy-wiadomosc").value = ""; // czyścimy tylko po sukcesie — błąd nie zjada tekstu
  });

  // --- Wyślij (zawór skrzynki) ----------------------------------------------------
  $("btn-wyslij").addEventListener("click", async () => {
    const guzik = $("btn-wyslij");
    if (guzik.disabled) return;
    guzik.disabled = true;
    try {
      const w = await api("/bestchudy/api/wyslij", {
        kanal: $("wyslij-kanal").value, adresat: $("wyslij-adresat").value.trim(),
        subject: $("wyslij-temat").value.trim(), tresc: $("wyslij-tresc").value.trim(),
        zgoda: true, // zgoda = TEN klik; fizyczny zawór (sucho/live) siedzi w skrzynce
      });
      $("wyslij-status").textContent = w.message ||
        (w.ok ? (w.wyslano ? "Wysłane (LIVE)." : "Zapisane na sucho — nic nie wyszło.") : "Odmowa.");
    } finally {
      guzik.disabled = false;
    }
  });

  // --- Werdykty -------------------------------------------------------------------
  ["werdykt-v11", "werdykt-chudy"].forEach((id) => {
    $(id).addEventListener("click", (ev) => {
      const guzik = ev.target.closest("[data-werdykt]");
      if (!guzik) return;
      $(id).querySelectorAll(".chip").forEach((c) => c.classList.remove("is-active"));
      guzik.classList.add("is-active");
      werdykty[$(id).dataset.strona] = guzik.dataset.werdykt;
      if (werdykty.v11 === "zielony" && werdykty.chudy === "zielony") {
        $("zapis-status").textContent = "🟢🟢 zabronione — wskaż, która strona była LEPSZA.";
        $("zapis-status").classList.remove("ok");
      } else {
        $("zapis-status").textContent = "";
      }
    });
  });

  $("btn-zapisz").addEventListener("click", async () => {
    const guzik = $("btn-zapisz");
    if (guzik.disabled) return;
    const ostatnia = historia.filter((m) => m.role === "model").slice(-1)[0];
    if (!ostatnia) {
      $("zapis-status").textContent = "Najpierw POLICZ CHUDEGO — bez jego odpowiedzi nie ma czego porównywać.";
      $("zapis-status").classList.remove("ok");
      return;
    }
    guzik.disabled = true;
    try {
      const w = await api("/bestchudy/api/porownanie", {
        tryb: tryb,
        // Wsad z chwili POLICZ (snapshot) — edycja pól PO policzeniu nie fałszuje rekordu.
        wsad: snapshotWsadu ? snapshotWsadu.wsad : sklejka(),
        rolka: snapshotWsadu ? snapshotWsadu.rolka : $("rolka").value,
        chudy_odpowiedz: ostatnia.content,
        chudy_prompt: ostatniPrompt,
        tury_chudego: historia.filter((m) => m.role === "model").length,
        werdykt_v11: werdykty.v11,
        werdykt_chudy: werdykty.chudy,
        komentarz: $("komentarz").value,
      });
      if (w.ok) {
        const komunikat = "Zapisane (" + w.dzien + (w.odrzut ? ", trafia do odrzutów" : "") +
          ") — werdykty wyzerowane pod następną sprawę.";
        resetOceny(); // czyści też zapis-status, więc komunikat ustawiamy PO resecie
        $("zapis-status").textContent = komunikat;
        $("zapis-status").classList.add("ok");
      } else {
        $("zapis-status").textContent = w.message || "Nie zapisano.";
        $("zapis-status").classList.remove("ok");
      }
    } finally {
      guzik.disabled = false;
    }
  });

  // --- Listy: odrzuty / kalendarz / oceny -------------------------------------------
  function pozycja(rec) {
    const div = document.createElement("div");
    div.className = "bc-pozycja";
    const naglowek = document.createElement("div");
    naglowek.textContent = "NrZam " + (rec.nrzam || "—") + " · " + rec.tryb +
      " · v11: " + (rec.werdykt_v11 === "zielony" ? "🟢" : "🔴") +
      " · chudy: " + (rec.werdykt_chudy === "zielony" ? "🟢" : "🔴") +
      " · " + (rec.operator_label || rec.operator_pid || "");
    div.appendChild(naglowek);
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = (rec.created_at || "").replace("T", " ").slice(0, 16) + " UTC";
    div.appendChild(meta);
    if (rec.komentarz) {
      const kom = document.createElement("pre");
      kom.textContent = "Komentarz: " + rec.komentarz;
      div.appendChild(kom);
    }
    return div;
  }

  function wypelnij(cel, recs, pusty) {
    const kontener = $(cel);
    kontener.textContent = "";
    if (!recs || !recs.length) {
      const brak = document.createElement("div");
      brak.className = "empty";
      brak.textContent = pusty;
      kontener.appendChild(brak);
      return;
    }
    recs.forEach((r) => kontener.appendChild(pozycja(r)));
  }

  async function odswiezOdrzuty() {
    const dzien = $("odrzuty-dzien").value;
    const w = await api("/bestchudy/api/porownania?odrzuty=1" + (dzien ? "&dzien=" + dzien : ""));
    wypelnij("odrzuty-lista", w.ok ? w.porownania : [], w.ok ? "Brak odrzutów. 🎉" : (w.message || "Błąd."));
  }
  $("btn-odrzuty").addEventListener("click", odswiezOdrzuty);

  async function odswiezKalendarz() {
    const dzien = $("kalendarz-dzien").value;
    const w = await api("/bestchudy/api/porownania" + (dzien ? "?dzien=" + dzien : ""));
    if (w.ok && w.liczby) {
      $("kalendarz-liczby").textContent = "porównań: " + w.liczby.porownania +
        " · 🟢 v11: " + w.liczby.v11_zielone + " · 🟢 chudy: " + w.liczby.chudy_zielone +
        " · odrzuty: " + w.liczby.odrzuty;
    } else {
      $("kalendarz-liczby").textContent = "";
    }
    wypelnij("kalendarz-lista", w.ok ? w.porownania : [], w.ok ? "Pusty dzień." : (w.message || "Błąd."));
  }
  $("btn-kalendarz").addEventListener("click", odswiezKalendarz);

  async function odswiezOceny() {
    const w = await api("/bestchudy/api/oceny");
    const kontener = $("oceny-lista");
    kontener.textContent = "";
    const lista = w.ok ? (w.oceny || []) : [];
    if (!lista.length) {
      const brak = document.createElement("div");
      brak.className = "empty";
      brak.textContent = w.ok ? "Brak ocen." : (w.message || "Błąd.");
      kontener.appendChild(brak);
      return;
    }
    lista.forEach((o) => {
      const div = document.createElement("div");
      div.className = "bc-pozycja";
      const l = o.liczby || {};
      div.textContent = o.dzien + " · porównań: " + (l.porownania || 0) +
        " · 🟢 v11: " + (l.v11_zielone || 0) + " · 🟢 chudy: " + (l.chudy_zielone || 0) +
        " — " + (o.operator_label || "");
      if (o.uwagi) {
        const pre = document.createElement("pre");
        pre.textContent = o.uwagi;
        div.appendChild(pre);
      }
      kontener.appendChild(div);
    });
  }

  $("btn-ocena").addEventListener("click", async () => {
    const guzik = $("btn-ocena");
    if (guzik.disabled) return;
    guzik.disabled = true;
    try {
      const w = await api("/bestchudy/api/ocena", {
        dzien: $("kalendarz-dzien").value, uwagi: $("ocena-uwagi").value,
      });
      $("ocena-status").textContent = w.ok
        ? "Ocena zapisana (" + w.dzien + ", porównań: " + w.liczby.porownania + ")."
        : (w.message || "Nie zapisano.");
      $("ocena-status").classList.toggle("ok", !!w.ok);
      if (w.ok) { $("ocena-uwagi").value = ""; odswiezOceny(); }
    } finally {
      guzik.disabled = false;
    }
  });
})();
