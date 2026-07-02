# BESTCHUDY — rozpoznanie (faza A) + plan kontenera v11 i porównywarki

> Pas Sylwii. Wynik fazy A z COORDYNACJA, PRZEROBIONY po decyzjach właściciela z 2026-07-02
> (kontener AS-IS, split view w ramce, forum v11 naturalne — patrz DECYZJE w COORDYNACJA.md).
> Rozpoznanie zrobione 2026-07-02 workflow'em 7-agentowym (4 czytelników + 3 weryfikatorów
> adwersarialnych, każde nośne twierdzenie potwierdzone cytatem plik:linia). Referencje READ-ONLY:
> `~/szturchacz-test` (żywe pliki: `app_vertex_ew.py`, `forum_module.py`, `szturchacz_vnext_v1_11.txt`),
> `~/wiezowiec-test` (`app.py`), oraz `main` tego repo.

## 1. Co NAPRAWDĘ jest silnikiem v11 (sedno rozpoznania — bez zmian)

**v11 = prompt + cienki klej.** Cała logika biznesowa (kwoty 300/600/900, terminy, kurierzy,
etapy K1–K5, routing forum, checklisty telefoniczne) żyje W PROMPCIE (3220 linii). Kod silnika to:

- **Pobranie promptu HTTP-em z URL-a** trzymanego w Firestore (kaskada: override per operator →
  default admina → fallback; `app_vertex_ew.py:113-156`, `get_remote_prompt` :1393-1401, cache 1 h).
  Kod NIGDZIE nie ma nazwy pliku promptu — wiązanie przez URL w Firestore (zarządza admin w Wieżowcu).
  Decyzja zespołu 2026-06-30: obowiązuje **v1_11** (nagłówek w pliku mówi „v1.5.3" — zamrożony,
  realna wersja = nazwa pliku).
- **Doklejenie 7 parametrów startowych** na końcu promptu (:1521-1530): `domyslny_operator`,
  `domyslna_data` (DD.MM), `Grupa_Operatorska`, `domyslny_tryb`, `notag`, `analizbior`, `operator_dzwoniacy`.
- **Wsad = JEDNA wiadomość user.** Kod wymaga od wsadu tylko NrZam (regex `(\d{5,7})`); cała struktura
  wsadu to kontrakt z PROMPTEM (WSAD PANEL FORMAT 1/2, koperta COP#, TAG-KOPERTA, `[FORUM_CONTEXT]`,
  `[TELEFON_WORECZEK]`, komendy `SESJA OK/STOP/WYNIK [NUMER]`).
- **Wywołanie: Vertex AI (Gemini)**, `temperature=0.0`, bez streamingu, bez natywnego tool-use;
  modele `gemini-2.5-pro` + fallback (:1167-1172); retry przy 429/quota/503/unavailable.
  Auth: JSON konta serwisowego (`FIREBASE_CREDS` w `st.secrets`) + `GCP_LOCATION` + rotacja
  `GCP_PROJECT_IDS` per operator.
- **Wyjście = wolny tekst z markerami** parsowanymi regexami: TAG `C#...`, `[FORUM_WRITE|...]` /
  `[FORUM_READ|...]` (wykonywane przez `forum_module`), `TEL_DZWON=`/`TEL_WYNIK=`, `PZ=`/`bump=` itd.
- **forum_module.py** (1304 linie): klient REST forum F15, mapa wątków z zaszytymi post_id, pamięć
  wpisów per zamówienie w Firestore `forum_memory/{nrzam}`, log diamentów.
- **Stan**: historia czatu w `st.session_state` (ulotna); trwałe w Firestore (`ew_cases`,
  `operator_configs` z logowaniem, statystyki, woreczek, `forum_memory`, diamenty) — przy
  `TEST_MODE=True` (:24) wszystkie kolekcje z prefiksem `test_`; UWAGA: `FORUM_TEST_MODE=False`
  (forum_module.py:807) niezależnie od tego kieruje wpisy na PRODUKCYJNE wątki forum.

## 2. DECYZJA WŁAŚCICIELA (2026-07-02): kontener v11 = AS-IS — obowiązuje

Faza A rekomendowała port; **właściciel rozstrzygnął INACZEJ i to zamyka temat**: pliki apki
streamlitowej + prompt idą do kontenera **W CAŁOŚCI, nietknięte**. Powód właściciela: przepisany
v11 = ryzyko symulacji zamiast wzorca (dryf). Konsekwencje przyjęte przez pas bestchudy:

- Zmiany w plikach TYLKO jeśli niezbędne do ODPAŁKI (start/port/sekrety) — zero dotykania logiki.
- v11 **pisze na forum NATURALNIE** (bez bramek, bez zmian promptu) — to produkcyjny operator
  wykonujący bieżącą realną pracę. Zawór (`styki.wyslij`) dotyczy WYŁĄCZNIE chudego.
- Porównywarka NIE woła v11 przez API: v11 żyje w RAMCE (iframe) po lewej stronie ekranu,
  wsad przenosi operator przyciskiem „KOPIUJ WSAD" (schowek → wklejka do v11).
- Ustalenia rozpoznania pozostają wartościowe jako mapa terenu (sekrety, kolekcje, pułapki)
  — wykorzystujemy je do odpałki i do budowy chudego, nie do przepisywania v11.

## 3. Kontener v11 AS-IS — plan odpałki

**Lokalizacja:** katalog `kontener_v11/` w tym repo (domyślna właściciela — potwierdzam).
Zawartość: `app_vertex_ew.py` + `forum_module.py` + `szturchacz_vnext_v1_11.txt` skopiowane 1:1
z `szturchacz-test`, plus WYŁĄCZNIE pliki odpałkowe: `Dockerfile`, `requirements.txt` (kopia),
skrypt startowy, README odpałki.

**Odpałka (wszystko poza plikami silnika):**
1. **Start:** `streamlit run app_vertex_ew.py --server.port=$PORT --server.address=0.0.0.0
   --server.headless=true` — nasłuch na `$PORT` (twardy wymóg Cloud Run), non-root, obraz z UTF-8
   i locale `pl_PL.UTF-8` (polskie znaki w nazwach wątków forum to ładunek funkcjonalny; kod robi
   `locale.setlocale` w try/except :31).
2. **Sekrety:** skrypt startowy generuje `.streamlit/secrets.toml` ze zmiennych środowiskowych
   (Secret Manager po stronie koordynatora): `FIREBASE_CREDS`, `GCP_PROJECT_IDS`, `GCP_LOCATION`,
   `FORUM_BEARER_TOKEN`. `st.secrets` czyta plik — zero zmian w kodzie.
3. **Prompt:** bez zmian w mechanice — apka sama pobiera prompt z URL-a wskazanego w Firestore
   (dokument `*_admin_config/default_prompt`). To dane konfiguracyjne, nie kod.
4. **Osadzanie w ramce:** Streamlit wspiera iframe (URL z `?embed=true`); jeśli okażą się potrzebne
   flagi serwera — to odpałka (parametry startu), nie logika. Po stronie apki-matki CSP `frame-src`
   dokłada koordynator (jedna linijka, wspólny plik — poza moim pasem).
5. **Logowanie:** as-is — operator loguje się w ramce po staremu (lista operatorów + hasło
   z `*_operator_configs`). SSO Pulpitu chroni EKRAN porównywarki; ramka ma swój stary zamek.

**Pytania odpałkowe (drobne, do rozstrzygnięcia z koordynatorem przy budowie — nie blokują startu):**
- **Projekt Firestore kontenera** (`FIREBASE_CREDS`): proponuję STARY projekt (prawdziwe as-is —
  loginy operatorów, konfiguracja promptu, `forum_memory`, statystyki po prostu DZIAŁAJĄ dalej).
  Wskazanie nowego projektu = pusta baza = trzeba by ją zasiewać (więcej ruchów, więcej ryzyka).
- **Flagi `TEST_MODE=True` / `FORUM_TEST_MODE=False` zostają jak są** (as-is; operatorzy dziś tak
  pracują — kolekcje `test_*`, forum produkcyjne). Zmiana którejkolwiek = decyzja koordynatora.
- Quota: **bez rotacji** (decyzja właściciela) — `GCP_PROJECT_IDS` dostaje jeden projekt (lista
  1-elementowa; mechanizm w kodzie nietknięty).

## 4. Porównywarka (ekran PRACA) — plan zgodny z rozpisem i doprecyzowaniem właściciela

Split view w JEDNEJ karcie:
- **Lewa strona = v11 w ramce** (iframe kontenera, `?embed=true`). Operator pracuje w niej po staremu.
- **Prawa strona = chudy** przez styki: `daj_sprawe` (wsad sam), `policz_chudego`, `daj_rolke`;
  wysyłka WYŁĄCZNIE `styki.wyslij` po kliku (zawór, domyślnie sucho).
- **Przycisk „KOPIUJ WSAD"** przy sprawie: kopiuje do schowka DOKŁADNIE to, co ma dostać v11
  (wsad_panel + koperta + tag — patrz §5), operator wkleja w ramkę. **Obie strony dostają TEN SAM
  wsad** (chudemu podajemy ten sam sklejony tekst jako `suchy_wsad` w `policz_chudego`) — inaczej
  porównanie byłoby nieuczciwe.
- Selektor u góry (STANDARD / odwrotny WA / mail / eBay / forum), werdykt PER STRONA 🔴/🟢
  z twardą blokadą 🟢🟢, komentarz przy odrzucie, zakładka ODRZUTÓW, kalendarz per dzień,
  ocena NA KOŃCU sesji. Werdykty/odrzuty/kalendarz zbiera bestchudy (kolekcje `bc_`).
- **Kolekcje `bc_`:** `bc_porownania` (case + wynik chudego + werdykty + komentarze; strona v11
  dokumentowana wklejką/skrótem — v11 as-is nie raportuje do nas), `bc_odrzuty`, `bc_oceny_sesji`.
- **Technika (potwierdzona weryfikacją):** własny `bc_store.py` (kopia wzorca `_JsonFile` + własny
  `firestore.Client`, budowa leniwa jak `ai.get_provider()`), własny katalog `templates/`,
  JS/CSS serwowane trasą routera; motyw przez `/static/theme.css` (uwaga: `.chip--on` jest w
  `app.css`, `.badge--muted` nie istnieje). KAŻDY endpoint sam woła `sso.read_operator` + kopia
  `_same_origin` na POST-y. CSP: zero inline JS/CSS. Odpowiedzi `{ok: bool, ...}`. Python 3.9.

## 5. STYK FEED — rozstrzygnięty (opcja a); WZORZEC `wsad_panel` DLA ARTURA (co do znaku)

Właściciel potwierdził opcję (a): wieżowczyk obok `suchy_wsad` (zostaje — identyfikacja/lista)
poda **`wsad_panel` = WSAD PANEL FORMAT 2** + **`koperta`** (surowe komentarze z `Comment`).
Poniżej wzorzec linia-po-linii, o który prosił Artur (źródło: prompt v1_11, L702-767 — FORMAT 2,
semantyka nagłówka L716, reguły Delivered/DATA_DOSTAWY L740-751):

```
<NRZAM> <RRRR-MM-DD> <NICK_SPRZEDAWCY>
<STATUS_DOSTARCZENIA>
<INDEX_HANDLOWY>
<NUMER_LISTU_ZWROTNEGO> <RRRR-MM-DD>
<DATA_ZWROTU>
<TYP_KURIERA>
<NUMER_LISTU_PRZEWOZOWEGO>	<LOGIN_EBAY>	<NICK_EBAY>
```

Reguły co do znaku (tak parsuje v11):
1. **Nagłówek**: numer zamówienia, potem data ZAMÓWIENIA wzorcem `RRRR-MM-DD` **bezpośrednio po
   numerze**, potem nick sprzedawcy (forum) — dokładnie ta kolejność (przykład z promptu:
   `358279 2025-11-13 kasia_k`). Nick = do delegacji TEL i wpisów forum.
2. **STATUS_DOSTARCZENIA**: słowo `Delivered` (case-insensitive) = paczka PIERWOTNA dostarczona;
   cokolwiek innego/brak = `Delivered=NIE` → v11 ma blokadę kontaktu. Jeśli znana jest DATA
   doręczenia: `RRRR-MM-DD` **bezpośrednio przed** słowem Delivered (ta sama linia albo linia nad) —
   z tego v11 liczy `dni_od_dostawy` (kwoty 5. etapu); bez daty przy potrzebie dopyta operatora.
3. **INDEX_HANDLOWY**: np. `236222GRUP2,OLEJ_TITAN_75W_36` (SYMBOL = od początku do pierwszego
   przecinka/spacji — używany w formatkach; nie przycinać).
4. **Linia listu zwrotnego (OPCJONALNA)**: numer listu + `RRRR-MM-DD` **bezpośrednio ZA numerem**
   (= data zamówienia kuriera zwrotnego; po TYM v11 poznaje, że to list ZWROTNY, a nie pierwotny).
5. **DATA_ZWROTU (OPCJONALNA)**: pole informacyjne; NIE jest dowodem doręczenia.
6. **TYP_KURIERA**: `UPS` / `FEDEX` (kurier pierwotny).
7. **Ostatnia linia**: list przewozowy PIERWOTNY + login eBay + nick eBay, **separator TAB**
   (fallback: spacje); UPS poznawany po prefiksie `1Z`. Token1=list, token2=login, reszta=nick.
8. Parser ignoruje puste linie i `-`; jeśli po INDEX od razu TYP_KURIERA → v11 uznaje brak listu
   zwrotnego. Pola nieznane → linia z `-` (nie wycinać linii, kolejność jest znacząca).
9. **`koperta` = OSOBNE pole, surowe 1:1** (niczego nie czyścić!): jeśli zawiera blok `COP#` —
   v11 bierze OSTATNI blok; jeśli nie — bloki muszą mieć `dodał: <nick>` (autorzy spoza [OPERATORS]
   = odfiltrowany szum; brak `dodał:` w ogóle = SELF-CHECK ERROR, więc przekazywać jak jest w bazie).
10. **Tag** (`ContentTag`, jest już w `suchy_wsad`): przy sklejaniu wsadu dla silników dokładamy go
    jako ostatnią linię — TAG-KOPERTA to nadrzędne źródło snapshotu stanu sprawy.

**Sklejka „KOPIUJ WSAD" (robi bestchudy, nie wieżowczyk):** `wsad_panel` + pusta linia + `koperta`
+ pusta linia + linia tagu. To samo idzie do chudego.

Notka PII przyjęta przez Artura — do zapisania w kontrakcie (dane osobowe tylko za bramą).

## 6. Pozostałe styki — PRZEGLĄD SYGNATUR WYKONANY (strona Sylwii)

Przejrzałam `app/wspolne/styki.py` z `main` (commit `d2494f2`). Werdykt:

- **`daj_sprawe(od, do, zam, limit)`** → `{ok, sprawy:[...]}` — **POTWIERDZAM**. Po rozbudowie
  (pkt 5) proszę o pola `wsad_panel` (string) i `koperta` (string, surowa) w każdej sprawie;
  `suchy_wsad` zostaje do listy/identyfikacji.
- **`daj_rolke(zam= | thread_id=, limit)`** → `{ok, wiadomosci, liczba}` — **POTWIERDZAM**
  (odczyt wolny, pokazywany w oknie; wystarcza prawej stronie).
- **`policz_chudego(suchy_wsad, rolka="", historia=[])`** → `{ok, odpowiedz, prompt}` —
  **POTWIERDZAM**; doprecyzowanie: porównywarka poda w argumencie `suchy_wsad` PEŁNĄ sklejkę
  z §5 (tę samą, którą operator wkleja do v11) — sygnatura to umożliwia (string), sens porównania
  tego wymaga.
- **`wyslij(kanal, adresat, tresc, operator_pid, zgoda, subject)`** — **POTWIERDZAM zawór**:
  klik zawsze, `WEM_WYSYLKA` off/sucho/live (sucho domyślnie), eBay twardo zamknięty, forum osobnym
  torem. Zgodnie z decyzją właściciela zawór dotyczy WYŁĄCZNIE chudego (v11 w ramce działa po staremu).
- **Prośba o PIĄTY styk (pamięć forum)** — patrz §7.

## 7. Pamięć forum WSPÓLNA — propozycja wykonania (szczegóły były po stronie Sylwii)

Skoro v11 jest nietykalny, **chudy dostosowuje się do v11**: wspólny „notes forum" = kolekcja
`forum_memory` (przy `TEST_MODE=True`: `test_forum_memory`) w projekcie Firestore KONTENERA
(dokument per nrZam, mapa `forum_posts.{cel} = {id, data, co, new_subthread}` — kształt zastany).
Propozycja: nowa funkcja fasady `styki.pamiec_forum(nrzam)` / `styki.zapamietaj_forum(nrzam, cel, wpis)`
(implementacja u Artura — klient Firestore wskazany env-em na projekt kontenera; zapis „pierwszy
wygrywa", jak w oryginale `save_forum_memory`). Chudy czyta/pisze WYŁĄCZNIE przez ten styk.
Do domknięcia przy budowie fazy C — dla fazy B (ręczne wklejanie) niepotrzebne.

## 8. Bramki — stan po decyzjach właściciela (2026-07-02)

| # | Pytanie z fazy A | Rozstrzygnięcie |
|---|---|---|
| 1 | port vs as-is | **AS-IS** (właściciel; obowiązuje) |
| 2 | gdzie kod kontenera | `kontener_v11/` w tym repo (potwierdzam) |
| 3 | styk FEED | **opcja (a)**: `wsad_panel` + `koperta` (wzorzec: §5) |
| 4 | forum po zielonym | **nieaktualne** — v11 naturalnie; zawór tylko chudy |
| 5 | pamięć forum | **wspólna**; wykonanie: §7 (nowy styk, chudy dostosowany do v11) |
| 6 | quota Vertex | **bez rotacji** (jeden projekt) |
| 7 | dostęp push | **załatwione** (konto ma push od 2026-07-02) |

**Otwarte drobiazgi odpałkowe (koordynator, przy budowie):** projekt Firestore kontenera
(propozycja: stary — §3), flagi TEST_MODE/FORUM_TEST_MODE (propozycja: bez zmian — §3),
CSP `frame-src` w apce-matce (jedna linijka, strona Artura).

## 9. Główne ryzyka (aktualne po decyzji as-is)

1. **Dwie flagi test/prod w dwóch plikach** (test_* w bazie, forum PRODUKCYJNE) — as-is je zachowuje;
   każdy, kto testuje kontener, musi wiedzieć, że wpisy forum idą NA ŻYWO.
2. **Iframe**: do sprawdzenia na początku fazy B, że kontener daje się osadzić (embed=true) i że
   logowanie w ramce działa; jeśli potrzebne flagi — odpałka.
3. **Prompt przez URL**: kontener zależy od dostępności URL-a promptu (cache 1 h w apce) — bez zmian
   względem dzisiejszej pracy operatorów; odnotowane.
4. **Nierówny wsad = nieuczciwe porównanie** — dlatego twarda zasada §4: obie strony dostają
   identyczną sklejkę.
5. Polskie znaki/UTF-8 w kontenerze (nazwy wątków forum) — pilnowane w odpałce (§3 pkt 1).

## 10. Fazy budowy (B) — po tym PR

1. **B1**: katalog `kontener_v11/` (pliki 1:1 + Dockerfile + skrypt sekretów) + lokalny test odpałki
   (docker run, logowanie, wklejka wsadu, iframe embed) — BEZ deployu (deploy = koordynator).
2. **B2**: ekran porównywarki w `app/bestchudy/` (split view: ramka + chudy przez styki, KOPIUJ WSAD,
   werdykty 🔴/🟢 bez 🟢🟢, odrzuty, kalendarz, ocena sesji) na ręcznym wklejaniu.
3. **B3**: spięcie z rozbudowanym FEED (`wsad_panel`) gdy Artur dowiezie; styk pamięci forum (faza C).
