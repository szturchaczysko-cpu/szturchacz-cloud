# BESTCHUDY — rozpoznanie (faza A) + plan kontenera v11

> Pas Sylwii. Wynik fazy A z COORDYNACJA („rozpoznanie + plan kontenera v11 → dyskusja → dopiero patch").
> Rozpoznanie zrobione 2026-07-02 workflow'em 7-agentowym (4 czytelników + 3 weryfikatorów adwersarialnych,
> każde nośne twierdzenie potwierdzone cytatem plik:linia). Referencje czytane READ-ONLY:
> `~/szturchacz-test` (żywe pliki: `app_vertex_ew.py`, `forum_module.py`, `szturchacz_vnext_v1_11.txt`),
> `~/wiezowiec-test` (`app.py`), oraz `main` tego repo (stan po Wieżowczyku v1).

## 1. Co NAPRAWDĘ jest silnikiem v11 (sedno rozpoznania)

**v11 = prompt + cienki klej.** Cała logika biznesowa (kwoty 300/600/900, terminy, kurierzy,
etapy K1–K5, routing forum, checklisty telefoniczne) żyje W PROMPCIE (3220 linii). Kod silnika to:

- **Pobranie promptu HTTP-em z URL-a** trzymanego w starym Firestore (kaskada: override per operator →
  default admina → fallback; `app_vertex_ew.py:113-156`, `get_remote_prompt` :1393-1401, cache 1 h).
  Kod NIGDZIE nie ma nazwy pliku promptu. Decyzja zespołu 2026-06-30: obowiązuje **v1_11**
  (uwaga: nagłówek w pliku mówi „v1.5.3" — zamrożony, realna wersja = nazwa pliku).
- **Doklejenie 7 parametrów startowych** na końcu promptu (f-string :1521-1530): `domyslny_operator`,
  `domyslna_data` (DD.MM), `Grupa_Operatorska`, `domyslny_tryb`, `notag`, `analizbior`, `operator_dzwoniacy`.
- **Wsad = JEDNA wiadomość user** (nie jest sklejany z promptem). Kod wymaga od wsadu tylko NrZam
  (regex `(\d{5,7})`); cała struktura wsadu to kontrakt z PROMPTEM (WSAD PANEL FORMAT 1/2, koperta COP#,
  TAG-KOPERTA, `[FORUM_CONTEXT]`, `[TELEFON_WORECZEK]`, komendy `SESJA OK/STOP/WYNIK [NUMER]`).
- **Wywołanie: Vertex AI (Gemini)**, `temperature=0.0` (jedyny parametr!), bez streamingu, bez natywnego
  tool-use. Modele: `gemini-2.5-pro` + łańcuch fallback (:1167-1172), retry przy 429/quota/503/unavailable
  (5 prób/model, backoff 5-10 s). Auth: JSON konta serwisowego (`FIREBASE_CREDS`) + `GCP_LOCATION`
  + rotacja projektów `GCP_PROJECT_IDS` per operator (rozkładanie quoty).
- **Wyjście = wolny tekst z markerami** parsowanymi regexami: TAG `C#...` (warunek zamknięcia sprawy),
  `[FORUM_WRITE|cel=...|user_do=...|tresc=...]` / `[FORUM_READ|...]` (wykonywane przez `forum_module`,
  marker podmieniany na status), `TEL_DZWON=`/`TEL_WYNIK=`, `PZ=`/`bump=`/`KURIER_PRZEWOZNIK=`/`TOWAR_TYP=`
  (diamenty). Zero JSON-a — wszystko konwencja tekstowa prompt↔regex.
- **Pętla agentowa przez `st.rerun()`**: FORUM_READ dokleja treść forum jako nową wiadomość user
  i przelicza — BEZ limitu iteracji (autopilot w starym Wieżowcu miał limit 3).
- **forum_module.py** (1304 linie, WSPÓŁDZIELONY ze starym Wieżowcem): klient REST forum F15
  (`https://f15.pmgtechnik.com`, stały bearer), mapa wątków z zaszytymi post_id, pamięć wpisów per
  zamówienie w Firestore `forum_memory/{nrzam}`, log diamentów. Streamlit przecieka do niego
  TRANZYTYWNIE (logger `_flog`, `_get_bearer`→`st.secrets`, cache korzeni, ukryte wejście
  `st.session_state.chat_nrzam` w `execute_forum_actions` :731!) — do portu trzeba wstrzyknąć:
  token, logger, nrzam, cache korzeni.
- **Rdzeń silnika NIE istnieje jako funkcje** — to ~265 linii inline w bloku `else:` renderowania
  czatu (:1500-1764), przeplecione `st.spinner/toast/markdown/rerun`. Trzeba go WYEKSTRAHOWAĆ,
  nie „zaimportować".
- **Stan**: historia czatu tylko w `st.session_state` (restart = utrata rozmowy); trwałe rzeczy
  w starym Firestore (`ew_cases`, statystyki, woreczek, `forum_memory`, diamenty).

## 2. DECYZJA DO DYSKUSJI: kontener „as-is" vs port — rekomendacja: PORT logiki 1:1

Rozpis mówi: „jedyny osobny byt: KONTENER v11 (stary silnik streamlitowy 1:1), wołany przez apkę".
Otwarte pytanie brzmiało: opakować Streamlita w kontener „as-is" czy przenieść logikę.

**Rekomendacja: mały serwis FastAPI z logiką przeniesioną 1:1 (port), NIE Streamlit w kontenerze.**

Uzasadnienie:
1. **„Wołany przez apkę" wymaga API.** Streamlit nie wystawia API — to UI. Porównywarka nie ma jak
   „zawołać" Streamlita o policzenie case'a; sterowanie cudzym UI to proteza. (Osadzenie w iframe
   też odpada: nasz middleware daje `X-Frame-Options: DENY`.)
2. **Bezpiecznik na wyjściach i tak wymusza zmianę kodu.** Twarda zasada zespołu: każde WYJŚCIE
   (w tym wpis na forum) za kliknięciem operatora, bezpiecznik POZA promptem. Stary silnik wykonuje
   `FORUM_WRITE` automatycznie w środku pętli czatu — żeby wstawić bramkę, trzeba zmienić kod.
   Czyli „as-is" i tak przestaje być as-is; skoro tak — porządny port.
3. **1:1 dotyczy LOGIKI, a ta żyje w prompcie.** Prompt przenosimy CO DO ZNAKU (plik w repo kontenera).
   Klej portujemy wiernie: te same parametry startowe, temperatura 0.0, ten sam łańcuch modeli i retry,
   te same regexy parsujące, ten sam forum_module (z wstrzykniętymi zależnościami zamiast `st.*`).
4. **„As-is" ciągnie stary świat:** logowanie hasłami plaintext z Firestore, sekrety w `st.secrets`,
   sidebar, woreczek, licznik diamentów — nic z tego nie jest silnikiem; UI zastępuje porównywarka.
5. **Ryzyko dryfu jest kontrolowalne:** case'y regresyjne §16 promptu (16.1–16.66) + tryb „sucho"
   dają gotowy materiał na testy porównawcze port vs oryginał.

**Świadome odstępstwa od 1:1 (do zatwierdzenia, każde z powodem):**
- `FORUM_WRITE` NIE wykonuje się automatycznie → wraca jako „propozycja wpisu" i czeka na zielony
  operatora (twarda zasada zespołu; łącznik 4).
- Pętla FORUM_READ dostaje limit iteracji (proponuję 3, jak autopilot w starym Wieżowcu :2525) —
  stary ekran operatora nie miał ŻADNEGO limitu (ryzyko zapętlenia).
- Historia czatu sesji v11 zapisywana w `bc_v11_sesje` (restart nie gubi rozmowy — stary tracił).
- Poprawka ukrytego wejścia: `chat_nrzam` jako jawny parametr (w oryginale filtr forum cicho
  przestaje działać, gdy brak session_state — ryzyko wycieku cudzych zamówień do kontekstu).
- NIE przenosimy: logowania hasłem (SSO/pulpit załatwia tożsamość), woreczka/diamentozy (zostają
  w starym świecie do czasu decyzji), rotacji `GCP_PROJECT_IDS` per operator (do decyzji koordynatora
  — quota; na start jeden projekt).

**Pułapka z oryginału (uwaga przy testach):** stara apka testowa ma `TEST_MODE=True` (kolekcje `test_*`),
ale `FORUM_TEST_MODE=False` — czyli „testowa" pisze na PRODUKCYJNE wątki forum. Kontener dostaje
JEDEN wspólny przełącznik trybu suchego (wzorzec `FORUM_MODE=sucho` z CLAUDE.md) obejmujący też forum.

## 3. Kształt kontenera v11 (propozycja)

- **Gdzie kod:** propozycja A (preferowana): katalog `kontener_v11/` w TYM repo (osobny Dockerfile,
  osobny serwis Cloud Run) — jeden PR-flow, wspólna koordynacja. Propozycja B: osobne repo.
  → decyzja koordynatora.
- **API (szkic, do domknięcia przy budowie):**
  - `POST /v11/sesja` — `{wsad, parametry:{operator, data, grupa, tryb, notag, analizbior, operator_dzwoniacy}}`
    → `{sesja_id, odpowiedz, propozycje_wyjsc:[{typ:"forum_write", cel, user_do, tresc}...], tag?}`
  - `POST /v11/sesja/{id}/odpowiedz` — `{tresc}` (komendy SESJA... wstrzykiwane przez porównywarkę)
  - `POST /v11/sesja/{id}/wykonaj-wyjscie` — wykonanie POJEDYNCZEJ propozycji po zielonym operatora
    (przejściowo, dopóki fizyczna wysyłka nie przejdzie na skrzynkę — patrz styk WYŚLIJ).
  - `GET /v11/sesja/{id}` — stan (messages, markery, tag) do renderu lewej strony porównywarki.
- **Prompt:** plik `szturchacz_vnext_v1_11.txt` skopiowany 1:1 do repo kontenera + env `V11_PROMPT_URL`
  jako override (zachowuje możliwość podmiany bez builda, jak stara kaskada, ale bez zależności
  od starego Firestore).
- **Stan:** `bc_v11_sesje` (wzorzec dwuwarstwowy file/Firestore skopiowany z apki, budowany LENIWIE).
- **Sekrety (prowizjonuje koordynator, ja tylko wymieniam):** dostęp do Vertex (docelowo ADC konta
  serwisowego Cloud Run zamiast JSON-a w env — jak reszta naszych apek), `GCP_LOCATION`,
  `FORUM_BEARER_TOKEN`; opcjonalnie `V11_PROMPT_URL`.
- **Pamięć forum (`forum_memory/{nrzam}`)**: potrzebna do bumpów. W starym świecie żyje w starym
  Firestore; w naszej apce Artur ma `szt_forum_memory`. Trzy opcje: własna kopia `bc_`, wspólna
  przez styk, odczyt starej. → pytanie do styku z Arturem (łącznik 5), NIE decyduję sama.
- **Fazy budowy (B):**
  1. **B1**: szkielet FastAPI + wyekstrahowana pętla LLM (bez forum) + zaślepka AI lokalnie;
     testy na case'ach §16 w trybie suchym.
  2. **B2**: port forum_module z wstrzykniętymi zależnościami; FORUM_READ 1:1 (z limitem),
     FORUM_WRITE jako propozycja za bramką.
  3. **B3**: spięcie z porównywarką; porównanie odpowiedzi port vs oryginał na tych samych wsadach.

## 4. Porównywarka (ekran PRACA) — plan zgodny z rozpisem 5 pkt

Start NA RĘCZNYM WKLEJANIU (bez czekania na styki): operator wkleja wsad (i rolkę), lewa strona = v11
przez kontener, prawa strona = chudy — do czasu styku „policz-chudego" zaślepka z jasnym komunikatem.

- **Układ:** split-screen v11 ‖ chudy; selektor u góry (STANDARD / odwrotny WA / mail / eBay / forum —
  mapuje się na `domyslny_tryb` i nagłówki `ROLKA_START_*`); werdykt PER STRONA 🔴/🟢 z twardą blokadą
  🟢🟢 (operator MUSI wskazać lepszą); komentarz przy odrzucie; zakładka ODRZUTÓW; kalendarz per dzień;
  ocena NA KOŃCU sesji; przyciski zgody operatora (bezpiecznik WYŚLIJ).
- **Kolekcje `bc_`:** `bc_v11_sesje` (przebiegi v11), `bc_porownania` (case + wyniki obu stron + werdykty
  + komentarz), `bc_odrzuty`, `bc_oceny_sesji`. Doc-id deterministyczne (wzorzec `case_doc_id`).
- **Technika (potwierdzone weryfikacją):** wszystko w `app/bestchudy/` — własny `bc_store.py`
  (kopia wzorca `_JsonFile` + własny `firestore.Client`, budowa leniwa jak `ai.get_provider()`),
  własny katalog `templates/` (własna instancja Jinja2Templates; własny base albo lista katalogów
  z dziedziczeniem `base.html` read-only — do drobnego uzgodnienia), własne JS/CSS serwowane trasą
  routera (`FileResponse`) — bez dotykania mountu `/static`; motyw przez linki do `/static/theme.css`
  i klasy bazowe (uwaga z weryfikacji: `.chip--on` jest w `app.css`, nie w motywie; `.badge--muted`
  nie istnieje). KAŻDY endpoint sam woła `sso.read_operator` (nie ma globalnej bramki; placeholder
  jest dziś publiczny) + kopia ~8 linii `_same_origin` na POST-y. CSP: zero inline JS/CSS.
  Odpowiedzi API: `{ok: bool, ...}`. Python 3.9-kompatybilnie.

## 5. STYK FEED (daj-sprawę) — strona Sylwii: NIE potwierdzam formatu 1:1, zgłaszam braki

Weryfikator porównał pole-po-polu `suchy_wsad` wieżowczyka z tym, czego v11 wymaga we WSADZIE PANEL
(prompt L702-767). **`suchy_wsad` świetnie identyfikuje sprawę i niesie snapshot (tag = TAG-KOPERTA,
nadrzędne źródło stanu), ale NIE zastępuje WSADU PANEL.** Braki:

| Brak | Dlaczego to boli |
|---|---|
| STATUS_DOSTARCZENIA / Delivered | **KRYTYCZNE**: bez Delivered v11 ma blokadę kontaktu (L707); `czy_austauch_zakonczony` to co innego |
| INDEX_HANDLOWY (lindexy) | linia 2 FORMATU 2; decyduje m.in. o kurierze (kolektor vs skrzynia) |
| NUMER_LISTU_PRZEWOZOWEGO (pierwotny) | wymagany w ostatniej linii FORMATU 2 |
| TYP_KURIERA (UPS/FEDEX) | `KurFlag` to flaga, nie typ; bez tego v11 dopytuje `KURIER_PIERWOTNY` = stop w automacie |
| NUMER_LISTU_ZWROTNEGO + data | rozpoznanie zwrotu w drodze |
| LOGIN_EBAY + NICK_EBAY | twarda zasada: rozpoznanie konta eBay PO WSADZIE (`pmg-service`/`ersi.877`) |
| nick SPRZEDAWCY (3. element nagłówka) | delegacje na forum (user_do = nick sprzedawcy) |
| KOPERTA (bloki COP#) | sprawa bez tagu i bez koperty → SESJA BOOTSTRAP = stop bez operatora |
| układ nagłówka `numer RRRR-MM-DD nick` | v11 czyta datę „bezpośrednio po numerze"; w suchym wsadzie między nimi stoi kraj/rodzaj, data ma prefiks „z dnia" |
| tel/mail w LINII (są w JSON) | potrzebne do WA / inicjału maila |

**Propozycja kontraktu (do decyzji Artura):**
- **(a) preferowana:** rozszerzyć SELECT wieżowczyka o pola panelu i dodać drugie pole `wsad_panel`
  (FORMAT 2 co do znaku) obok `suchy_wsad` (lista/identyfikacja zostaje jak jest); albo
- **(b)** zapisać jawnie, że FEED podaje TYLKO wskaźnik sprawy + tag, a WSAD PANEL bierzemy z innego
  źródła (jakiego? — wtedy to trzeba wskazać).
- Niezależnie: skąd KOPERTA (komentarze COP#)? Bez niej sprawy bez tagu zawsze bootstrapują.
- Uwaga poboczna: `kakMail`/`ktTelNr`/`klient_nazwa` w JSON endpointu to dane osobowe — jest za bramką
  koordynatora, odnotować w kontrakcie.

Porównywarka STARTUJE na ręcznym wklejaniu, więc to NIE blokuje fazy B — ale kontrakt FEED trzeba
domknąć przed spinaniem (faza C).

## 6. Pozostałe styki (status mojej strony)

- **policz-chudego:** czekam na kontrakt strony Artura; do tego czasu prawa strona = zaślepka.
- **daj-rolkę:** technicznie rolka siedzi za `deps.wa_inbox` (import zakazany) — potrzebny styk
  (endpoint lub uzgodniony odczyt `szt_wa_inbox`); do tego czasu rolki ręcznie.
- **WYŚLIJ:** propozycja koordynatora (wysyła TYLKO strona z zielonym, przegrana na sucho z zapisem
  „co by zrobiła") — **strona Sylwii: POPIERAM**, chroni przed podwójną wiadomością. Doprecyzowania
  wymaga: kto fizycznie wykonuje wpis na FORUM po zielonym dla v11 (przejściowo kontener przez
  forum_module, docelowo skrzynka?) — patrz §3.
- **BRAMKA propozycji (strona Sylwii — wypełniam TODO):** do renderu zielony/czerwony + panelu odrzutów
  potrzebuję pól: `id`, `created_at`, `status`, `test_mode`, `sprawa{nrZam, pz, grupa, kanal_zrodlo}`,
  `typ`, `akcja{kanal, recipient, tresc | awizacja}`, `kontekst{rolka_skrot, fakty}`, `uzasadnienie` —
  czyli draft Artura POKRYWA potrzeby; dodałabym tylko `silnik` ("v11"|"chudy") i `porownanie_id?`
  (spięcie z werdyktami porównywarki). Decyzja/komentarz/decydent/decyzja_at — jak w drafcie.

## 7. Główne ryzyka (pełna lista 15 w wynikach rozpoznania)

1. Dwie flagi test/prod w dwóch plikach starego świata (test pisze na PROD forum) → jeden przełącznik.
2. Detekcja tagów wrażliwa na wielkość liter zależnie od modelu (znany przypadek Gemini 2.5).
3. Pamięć forum: bez niej bumpy zakładają nowe wątki zamiast podbijać (dryf z historią).
4. Polskie znaki są ładunkiem funkcjonalnym (nazwy grup/wątków forum, `CZATOSZTUR_UK/PL` z ukośnikiem)
   — kontener musi mieć UTF-8 (+ locale pl_PL), inaczej 400 z API forum.
5. Rozjazd portu z oryginałem → mitygacja: case'y regresyjne §16 + porównanie na tych samych wsadach.

## 8. Pytania do dyskusji (właściciel/koordynator) — bramki

1. **Port vs as-is** (§2) — akceptacja rekomendacji + listy świadomych odstępstw.
2. **Gdzie kod kontenera** (§3): katalog w tym repo vs osobne repo.
3. **Styk FEED** (§5): opcja (a) czy (b) + skąd KOPERTA.
4. **Forum po zielonym** (§6): kto wykonuje wpis (kontener przejściowo vs skrzynka od razu).
5. **Pamięć forum** (§3): własna `bc_` vs wspólna vs odczyt starej.
6. **Quota Vertex**: jeden projekt na start czy przenosimy rotację `GCP_PROJECT_IDS`.
7. **Dostęp do repo:** konto `sylwiaautossilniki` ma dziś TYLKO odczyt (push 403) — regulamin każe
   „pushować często"; proszę o write na gałęzie albo decyzję „pracujemy przez fork".
