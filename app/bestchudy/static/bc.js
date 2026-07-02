/* BESTCHUDY — porównywarka. Wanilia, zero frameworków; CSP = zero inline (wszystko tutaj).
   Konwencja API jak w całej apce: {ok: bool, message?} (wzorzec api() z operator.js — kopia). */
(function () {
  "use strict";

  const LIMIT_TEKSTU = 20000; // lustra limitów z logika.py — serwer odrzuca, my ostrzegamy wcześniej
  const LIMIT_TAG = 2000;
  const KANAL_TRYBU = { odwrotny_wa: "WA", mail: "MAIL", ebay: "EBAY", forum: "FORUM" };

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

  // --- Tryb (selektor) + SESJA rolki dla trybów odwrotnych ----------------------------
  let tryb = "standard";
  $("bc-tryby").addEventListener("click", (ev) => {
    const guzik = ev.target.closest("[data-tryb]");
    if (!guzik) return;
    document.querySelectorAll("#bc-tryby .chip").forEach((c) => c.classList.remove("is-active"));
    guzik.classList.add("is-active");
    tryb = guzik.dataset.tryb;
    // Tryb odwrotny = moment dodania SESJI kanału (uwagi operatorki): pokazujemy okienko rolki.
    const odwrotny = tryb !== "standard";
    $("sesja-rolka").hidden = !odwrotny;
    if (odwrotny) $("rolka-kanal").textContent = KANAL_TRYBU[tryb] || "WA";
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

  async function doSchowka(tekst, gdzieOtworzyc) {
    try {
      await navigator.clipboard.writeText(tekst);
      return true;
    } catch (e) {
      if (gdzieOtworzyc) gdzieOtworzyc.open = true;
      return false;
    }
  }

  $("btn-kopiuj").addEventListener("click", async () => {
    if (!sklejka()) { $("wsad-status").textContent = "Pusty wsad — nie ma czego kopiować."; return; }
    const blad = zaDlugi();
    if (blad) { $("wsad-status").textContent = blad; return; }
    // W trybie odwrotnym wsad dla v11 niesie też blok ROLKA_START_[KANAL] (start w trybie kanału).
    const ok = await doSchowka(tekstDlaV11(), document.querySelector(".bc-podglad"));
    $("wsad-status").textContent = ok
      ? "Skopiowane — wklej w ramkę v11 (chudy dostaje to samo: sklejkę + rolkę)."
      : "Przeglądarka zablokowała schowek — skopiuj z podglądu sklejki.";
  });

  // --- ROLKA trybu odwrotnego: wzorzec (v11) + API (chudy, fallback wzorzec) ----------
  let rolkaZApi = null;   // null = nie pobierano/pusta → chudy dostaje rolkę-wzorzec
  let rolkaZApiZam = "";  // numer sprawy, dla której pobrano — inna sprawa unieważnia rolkę

  function efektywnaRolka() {
    if (tryb === "standard") return ""; // rolka NIE przecieka do trybu standard (uczciwość rekordu)
    if (rolkaZApi !== null && rolkaZApiZam !== nrzam(sklejka())) {
      rolkaZApi = null; // ręcznie podmieniona sprawa — rolka z API dotyczy poprzedniej
      $("rolka-api-podglad").hidden = true;
      $("rolka-status").textContent = "";
    }
    return rolkaZApi !== null ? rolkaZApi : $("rolka").value;
  }

  function tekstDlaV11() {
    const s = sklejka();
    if (tryb === "standard") return s;
    const wzorzec = $("rolka").value.trim();
    if (!wzorzec) return s;
    // Start w trybie kanału: v11 wymaga we wsadzie bloku ROLKA_START_[KANAL] (prompt L2652-2656);
    // komenda „SESJA WYNIK … – ROLKA_…" to odpowiedź W TRAKCIE sesji (§7.6.2), nie start.
    return s + "\n\nROLKA_START_" + (KANAL_TRYBU[tryb] || "WA") + "\n" + wzorzec;
  }

  $("btn-rolka-api").addEventListener("click", async () => {
    const guzik = $("btn-rolka-api");
    if (guzik.disabled) return;
    const zam = nrzam(sklejka());
    if (!zam) { $("rolka-status").textContent = "Najpierw wsad z numerem zamówienia."; return; }
    guzik.disabled = true;
    $("rolka-status").textContent = "Pobieram z archiwum…";
    try {
      const w = await api("/bestchudy/api/rolka?zam=" + encodeURIComponent(zam));
      if (!w.ok) {
        rolkaZApi = null;
        $("rolka-api-podglad").hidden = true;
        $("rolka-status").textContent = w.message || "Archiwum niedostępne.";
        return;
      }
      if (w.pusta) {
        rolkaZApi = null;
        $("rolka-api-podglad").hidden = true;
        $("rolka-status").textContent = "Archiwum nie zwróciło rozmowy (sprawa sprzed 'daty x', " +
          "numer spoza formatu archiwum albo starsza niż bufor) — chudy dostanie rolkę-wzorzec.";
        return;
      }
      rolkaZApi = w.rolka;
      rolkaZApiZam = zam;
      $("rolka-api-podglad").textContent = w.rolka;
      $("rolka-api-podglad").hidden = false;
      $("rolka-status").textContent = "API: " + w.liczba + " linii — chudy weźmie tę rolkę." +
        (w.przycieta ? " (długa rozmowa — przycięta od najstarszych)" : "");
    } finally {
      guzik.disabled = false;
    }
  });

  $("btn-kopiuj-rolke").addEventListener("click", async () => {
    const tresc = $("rolka").value.trim();
    if (!tresc) { $("rolka-status").textContent = "Pusta rolka-wzorzec — wklej rozmowę."; return; }
    const zam = nrzam(sklejka());
    if (!zam) { $("rolka-status").textContent = "Wsad bez numeru zamówienia — najpierw wsad."; return; }
    const kanal = KANAL_TRYBU[tryb] || "WA";
    // Komenda SESJI wg promptu v11 (L1723-1728): ROLKA_[KANAL] + treść MY/KLIENT.
    // To odpowiedź, gdy v11 POPROSI o rolkę W TRAKCIE sesji; na starcie ROLKA_START idzie we wsadzie.
    const komenda = "SESJA WYNIK " + zam + " – ROLKA_" + kanal + "\n" + tresc;
    const ok = await doSchowka(komenda, null);
    $("rolka-status").textContent = ok
      ? "Komenda SESJA skopiowana — wklej w ramkę v11, gdy poprosi o rolkę w trakcie sesji."
      : "Schowek zablokowany — zaznacz i skopiuj rolkę ręcznie.";
  });

  // --- FEED: sprawy z wieżowczyka ----------------------------------------------------
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
    rolkaZApi = null;
    $("rolka-api-podglad").hidden = true;
    $("rolka-status").textContent = "";
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
      " — teraz 🚀 ROZPOCZNIJ ANALIZĘ (obie strony dostaną ten sam wsad).";
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

  async function pobierzSprawy(zam, autoPierwszy) {
    const guziki = [$("btn-pierwszy"), $("btn-nastepne"), $("btn-po-numerze")];
    if (guziki[0].disabled) return; // blokada in-flight jak przy pozostałych przyciskach
    guziki.forEach((g) => { g.disabled = true; });
    $("feed-status").textContent = "Pobieram z wieżowczyka…";
    try {
      const limit = autoPierwszy ? 1 : 10;
      const w = await api("/bestchudy/api/sprawy?limit=" + limit +
        (zam ? "&zam=" + encodeURIComponent(zam) : ""));
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
      if (autoPierwszy || w.sprawy.length === 1) { uzyjSprawy(w.sprawy[0]); return; }
      pokazSprawy(w.sprawy);
      $("feed-status").textContent = "Wybierz sprawę z listy (najnowsze na górze).";
    } finally {
      guziki.forEach((g) => { g.disabled = false; });
    }
  }

  function poNumerze() {
    const zam = $("feed-zam").value.trim();
    if (!/^\d{4,9}$/.test(zam)) { $("feed-status").textContent = "Numer zamówienia to 4-9 cyfr."; return; }
    pobierzSprawy(zam, false);
  }
  $("btn-pierwszy").addEventListener("click", () => pobierzSprawy("", true));
  $("btn-nastepne").addEventListener("click", () => pobierzSprawy("", false));
  $("btn-po-numerze").addEventListener("click", poNumerze);
  $("feed-zam").addEventListener("keydown", (ev) => { if (ev.key === "Enter") poNumerze(); });

  // --- Chudy: rozmowa ------------------------------------------------------------
  let historia = [];        // [{role:"user"|"model", content}] — role jak w silniku skrzynki
  let ostatniPrompt = "";
  let snapshotWsadu = null; // wsad z chwili startu analizy — to on idzie do rekordu porównania
  let liczenie = false;     // blokada in-flight (start i dopisek dzielą jedną)

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
    $("btn-start").disabled = true;
    $("btn-dopisz").disabled = true;
    // Licznik czasu (uwaga operatorki: „chudy bardzo długo myśli") — operator widzi,
    // że liczenie trwa; wydajność silnika = zgłoszona koordynatorowi (COORDYNACJA).
    const start = Date.now();
    $("wsad-status").textContent = "Chudy liczy… 0 s";
    const tyk = setInterval(() => {
      $("wsad-status").textContent = "Chudy liczy… " + Math.round((Date.now() - start) / 1000) + " s";
    }, 1000);
    try {
      const w = await api("/bestchudy/api/policz", cialo);
      const sek = Math.round((Date.now() - start) / 1000);
      if (!w.ok) { $("wsad-status").textContent = w.message || "Silnik niedostępny."; return false; }
      if (odNowa) {                    // czyścimy dopiero PO sukcesie — błąd sieci nie gubi rozmowy
        historia = [];
        $("chudy-rozmowa").textContent = "";
        resetOceny();
        snapshotWsadu = { wsad: w.wejscie_bazowe || "", rolka: w.rolka || "",
                          wzorzec: (tryb !== "standard" ? $("rolka").value : "") };
      }
      historia.push({ role: "user", content: w.wejscie });
      historia.push({ role: "model", content: w.odpowiedz });
      ostatniPrompt = w.prompt || "";
      dodajDymek("user", w.wejscie);
      dodajDymek("model", w.odpowiedz);
      $("wsad-status").textContent = "Chudy odpowiedział po " + sek + " s (prompt: " +
        (w.prompt || "?") + ").";
      return true;
    } finally {
      clearInterval(tyk);
      liczenie = false;
      $("btn-start").disabled = false;
      $("btn-dopisz").disabled = false;
    }
  }

  // 🚀 ROZPOCZNIJ ANALIZĘ — obie strony NARAZ (uwagi operatorki): chudy startuje przez API,
  // wsad dla v11 ląduje w schowku (do wklejenia w ramkę; „ręka robota" wklei sama po
  // domknięciu cegły autologowania — rura /v11/ już działa).
  $("btn-start").addEventListener("click", async () => {
    if (liczenie) return;
    const s = sklejka();
    if (!s) { $("wsad-status").textContent = "Pusty wsad."; return; }
    const blad = zaDlugi();
    if (blad) { $("wsad-status").textContent = blad; return; }
    const schowekOk = await doSchowka(tekstDlaV11(), document.querySelector(".bc-podglad"));
    await policz({
      wsad_panel: $("wsad-panel").value, koperta: $("koperta").value,
      tag: $("tag").value, rolka: efektywnaRolka(),
    }, true);
    if (!schowekOk) {
      $("wsad-status").textContent += " ⚠️ Schowek zablokowany — wsad dla v11 weź z podglądu.";
    }
  });

  $("btn-dopisz").addEventListener("click", async () => {
    if (liczenie) return;
    const tekst = $("chudy-wiadomosc").value.trim();
    if (!tekst) return;
    if (!historia.length) { $("wsad-status").textContent = "Najpierw 🚀 ROZPOCZNIJ ANALIZĘ."; return; }
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
      $("zapis-status").textContent = "Najpierw 🚀 ROZPOCZNIJ ANALIZĘ — bez odpowiedzi chudego nie ma czego porównywać.";
      $("zapis-status").classList.remove("ok");
      return;
    }
    guzik.disabled = true;
    try {
      const w = await api("/bestchudy/api/porownanie", {
        tryb: tryb,
        // Wsad z chwili startu analizy (snapshot) — edycja pól PO starcie nie fałszuje rekordu.
        wsad: snapshotWsadu ? snapshotWsadu.wsad : sklejka(),
        rolka: snapshotWsadu ? snapshotWsadu.rolka : efektywnaRolka(),
        rolka_wzorzec: snapshotWsadu ? (snapshotWsadu.wzorzec || "") : "",
        chudy_odpowiedz: ostatnia.content,
        // CAŁA sesja chudego do rekordu (uwaga operatorki: odrzut ma nieść pełną rozmowę).
        chudy_rozmowa: historia,
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
  function dolaczPelnaSesje(kontener, rec) {
    const pre = (tytul, tresc) => {
      const naglowek = document.createElement("div");
      naglowek.className = "meta";
      naglowek.textContent = tytul;
      kontener.appendChild(naglowek);
      const blok = document.createElement("pre");
      blok.className = "codeblock bc-sesja-pelna";
      blok.textContent = tresc;
      kontener.appendChild(blok);
    };
    if (rec.wsad) pre("WSAD (obie strony):", rec.wsad);
    if (rec.rolka) pre("ROLKA (chudy):", rec.rolka);
    if (rec.rolka_wzorzec && rec.rolka_wzorzec !== rec.rolka) {
      pre("ROLKA-WZORZEC (v11):", rec.rolka_wzorzec);
    }
    const rozmowa = (rec.chudy_rozmowa || [])
      .map((m) => (m.role === "user" ? "MY: " : "CHUDY: ") + m.content).join("\n\n");
    pre("CAŁA SESJA CHUDEGO:", rozmowa || rec.chudy_odpowiedz || "(brak — rekord sprzed zmiany)");
  }

  function pozycja(rec) {
    const div = document.createElement("div");
    div.className = "bc-pozycja";
    const glowa = document.createElement("div");
    glowa.className = "bc-pozycja-glowa";
    const naglowek = document.createElement("span");
    naglowek.textContent = "NrZam " + (rec.nrzam || "—") + " · " + rec.tryb +
      " · v11: " + (rec.werdykt_v11 === "zielony" ? "🟢" : "🔴") +
      " · chudy: " + (rec.werdykt_chudy === "zielony" ? "🟢" : "🔴") +
      " · " + (rec.operator_label || rec.operator_pid || "");
    glowa.appendChild(naglowek);
    // Uwaga operatorki: odrzut ma nieść CAŁĄ sesję — dociągamy pełny rekord na kliknięcie.
    const guzik = document.createElement("button");
    guzik.type = "button";
    guzik.className = "btn btn--small";
    guzik.textContent = "Cała sesja";
    guzik.addEventListener("click", async () => {
      if (guzik.disabled) return;
      guzik.disabled = true;
      const w = await api("/bestchudy/api/porownanie?id=" + encodeURIComponent(rec.id));
      if (!w.ok) { guzik.disabled = false; guzik.textContent = w.message || "Błąd."; return; }
      guzik.remove();
      dolaczPelnaSesje(div, w.porownanie);
    });
    glowa.appendChild(guzik);
    div.appendChild(glowa);
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
