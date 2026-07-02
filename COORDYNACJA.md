# COORDYNACJA — szturchacz-cloud (dwie sesje vibecoderów)

> Wspólny mózg dwóch RÓWNOLEGŁYCH sesji (Artur + Sylwia) pracujących nad „skrzynią szturchaczową".
> **CZYTAJ TO NA START KAŻDEJ SESJI.** Dopisuj ustalenia. Nie wymyślajcie różnych rozwiązań na to samo.
> Aktualizacja = mały commit/PR; koordynator (Artur) trzyma `main` aktualny.

## CEL — skrzynia IN-OUT (automat)
NIE szlifujemy starego stylu (operator ręcznie pobiera/obrabia case). Budujemy AUTOMAT, który SAM:
pobiera case'y z bazy franciszkańskiej (Krzyśka, on-prem MSSQL SZTURCHACZ) → analizuje co obrabiać →
dociąga kontekst WA/mail/eBay przez bramę ATA → AI liczy odpowiedź → SAM odpowiada kanałem + SAM
zamawia kuriera (JSON awizacji → apka Eweliny, faza 1 UPS skrzynia).
Operatorzy = TYLKO telefony, reklamacje, „czy szturchać", nie-automaty.
**Faza 1 = bramka akceptacji operatora (zielony/czerwony)** przed realną akcją (wzorzec sucho→realne).

## MAPA EKRANÓW I GRANICE — ZATWIERDZONE przez właściciela 2026-07-02
Granica projektów pokrywa się z kafelkami Pulpitu 1:1:
- **Kafelek SZTURCHACZ = PRACA — buduje SYLWIA.** Ten sam adres, zawartość ewoluuje:
  porównywarka bestchudy (v11‖chudy) → bramka nadzoru automatu → podgląd fullautomatu.
  Starego ekranu czatu NIE utrzymujemy (zręby po przenosce ze Streamlita = DO ROZBIÓRKI).
- **Kafelek WIEŻOWIEC = ZAPLECZE — buduje ARTUR.** Wieżowczyk (kolejka spraw chronologicznie
  + pole „odwrotny zam" + woreczek wpadów WEM) i panel koordynatora (konfiguracja, raporty,
  zakładka „ROZMOWY" = archiwum WEM) SKLEJONE jako zakładki jednego widoku, za rolą koordynatora.
  Później dochodzi rozrzutnik. (Stary Wieżowiec rozchodzi się: karmienie→wieżowczyk,
  przeliczanie→silniki, priorytety→rozrzutnik, zarządzanie→panel.)
- POD SPODEM rury ARTURA (brama WEM, archiwum, silnik chudego, wysyłka z bezpiecznikiem) —
  ekran Sylwii korzysta z nich WYŁĄCZNIE przez 4 styki, nie dotyka ich.
- FUNDAMENTY ZOSTAJĄ (działają): SSO/logowanie, motyw, warstwa zapisu, klient forum, odbiór
  z bramy WEM + archiwum, bezpieczniki-przełączniki. BACKUP całej budowy = STREAMLIT (produkcja),
  nie stare zręby cloud.
- **FULLAUTOMAT wbudowany w konstrukcję:** bezpiecznik = zawór NA RURZE wysyłkowej (poza silnikiem
  i poza promptem). Fullautomat = otwarcie zaworu (przełącznik, nie przebudowa), STOPNIOWO per
  kanał/typ sprawy; eBay i kurierzy bramkowane najdłużej. Ekran nie znika — zmienia rolę
  z bramki na podgląd (historia per case zostaje na zawsze).
- FAZY: A) Artur: Rozmowy+gniazdo modułu; Sylwia: rozpoznanie+plan kontenera v11; właściciel:
  wiadomość do Krzyśka → B) Sylwia: porównywarka na ręcznym wklejaniu + kontener v11; Artur:
  wieżowczyk+styki → C) spięcie styków + wysyłka z zaworem (tylko NOWY numer WA) → D) „data x":
  stopniowe otwieranie zaworów.
Cokolwiek na styku → zapisz w „STYKI/KONTRAKTY" ZANIM powstanie kod.

## SKRZYNKA SZTURCHACZOVA + BESTCHUDY — mapa całości (2026-07-01, wg wizji właściciela)
Nazwa robocza całości = **skrzynka Szturchaczova** (hub IN-OUT: auto-pobór z kanałów + wysyłka do klienta).
Cel nadrzędny = **wychować idealnego CHUDEGO** = lepszy v11 z API, który UCZY SIĘ zachowań v11
przez PORÓWNANIE na tych samych case'ach.

MAPA (przepływ):
- WEJŚCIA: **brama WEM** (Krzysiek, w budowie — WA-NOWY/mail/eBay) + **forum** (czytają OBA silniki,
  z memory = ID wpisów, do sprawdzania czy przyszła odpowiedź) → **BAZA** (archiwum in/out) →
  **ROZRZUTNIK** (priorytety; anty-spam WA) → kolejka do przeliczenia.
- **wieżowczyk** = ociosany Wieżowiec: SUROWY feeder case'ów ze szturchacza (chronologicznie od
  najnowszych, w zakresie dat; pole „odwrotny zam" = konkretny nrZam). BEZ parsowania/przeliczania/
  priorytetów/uszków/świnek/pakowania w paczki — po prostu suchy wsad, ten sam dla obu silników.
- DWA SILNIKI na TYM SAMYM case: **[v11]** (prompt `szturchacz_vnext_v1_11.txt`, BEZ API — operator
  wkleja rolki) ‖ **[chudy]** (z API — autonomiczne ruchy po kanałach).
- **BESTCHUDY** = split-screen porównanie + akcept operatora → WYJŚCIA (kanały) **tylko po bezpieczniku**.

PODZIAŁ (praca równoległa; decyzje koordynatora 2026-07-01):
- **ARTUR = SKRZYNKA** (hydraulika we/wy): brama WEM intake + **baza/ARCHIWUM (zapis + sklejanie po
  kliencie — w toku)** + rozrzutnik + wieżowczyk + kanały I/O (mail/WA/eBay/forum) z bezpiecznikiem.
- **SYLWIA = BESTCHUDY** (osobny projekt w jej sesji): split-screen v11‖chudy + selektor u góry
  (STANDARD / odwrotny WA / mail / eBay / forum) + akcept PER STRONA (🔴/🟢, **BRAK 🟢🟢** — operator
  MUSI wskazać lepszą) + komentarz odrzutu + zakładka ODRZUTÓW + kalendarz (per dzień) + **ocena NA
  KOŃCU sesji** + przyciski zgody operatora + **KONTENER v11** (migracja prompt v1_11 + logika 1:1).
- **BESTCHUDY = WYDZIELONY MODUŁ WEWNĄTRZ szturchacz-cloud** (rozpis koordynatora, 2026-07-02 —
  NIE osobna apka; „chcę poprawić apkę szturchacz i wieżowiec — wprowadzić TAM"):
  1. Budowane w TEJ apce (szturchacz.aitossilniki.com); żadnej nowej aplikacji.
  2. Kod Sylwii = osobny katalog `app/bestchudy/` (+ własne szablony) i WŁASNE kolekcje w bazie
     (prefiks `bc_`). Wspólnych plików NIE edytuje — wpięcie do apki jedną linijką (router).
     WYJĄTEK (decyzja właściciela 2026-07-03): **kafelek OPERATORZY w zapleczu = pas Sylwii** —
     wolno jej edytować DOKŁADNIE: sekcję `#sek-operatorzy` (+ jej kafelek-przycisk) w
     `app/templates/koordynator.html`, funkcje operatorów w `app/static/koordynator.js`
     (renderOperators / addOperator i ich okablowanie) oraz endpointy `/api/koord/operator*`
     w `app/main.py`; magazyn operatorów (stores) w uzgodnieniu, bo używa go też silnik.
     Reszta zaplecza (wieżowczyk, Rozmowy, konfiguracja, prompt) = dalej pas Artura. PR jak zwykle.
  3. Ekran operatora → porównywarka: v11 lewo ‖ chudy prawo, selektor STANDARD/odwrotny
     WA/mail/eBay/forum, werdykty 🔴/🟢 (brak 🟢🟢) + komentarz, odrzuty+kalendarz, ocena na końcu.
  4. Cztery styki ze skrzynką (kontrakty TU, przed kodem): daj-sprawę (wieżowczyk) · policz-chudego
     (silnik Artura) · daj-rolkę (archiwum WEM) · WYŚLIJ (guzik-bezpiecznik u Sylwii, fizyczna
     wysyłka ZAWSZE po stronie skrzynki — tam siedzą twarde zasady eBay/WA-stary-nowy/skrzynki per kraj).
  5. Jedyny osobny byt: KONTENER v11 (stary silnik streamlitowy 1:1, pas Sylwii), wołany przez apkę.
  Start bez czekania na styki: ekran działa najpierw na ręcznie wklejanych sprawach/rolkach.
- Propozycja koordynatora DO KONTRAKTU bestchudy (strona Sylwii rozstrzyga): realną wysyłkę wykonuje
  TYLKO strona z zielonym; przegrana zawsze na sucho (zapis „co by zrobiła") — chroni przed podwójną
  wiadomością do klienta.

ŁĄCZNIKI — **FASADA GOTOWA (strona skrzynki, 2026-07-02): `app/wspolne/styki.py`** — jedyny punkt,
z którego bestchudy importuje rzeczy spoza swojego katalogu (poza `sso.read_operator`). Strona
Sylwii POTWIERDZA sygnatury zanim zacznie na nich budować (kontrakt dwustronny):
1. FEED: `styki.daj_sprawe(od, do, zam, limit)` → `{ok, sprawy:[{…, suchy_wsad}]}` (wieżowczyk;
   format `suchy_wsad` = „NrZam: … | kraj | rodzaj | … | tag: …" — do potwierdzenia przez silniki).
2. SILNIK CHUDEGO: `styki.policz_chudego(suchy_wsad, rolka="", historia=[])` → `{ok, odpowiedz,
   prompt}` (system = AKTYWNY prompt z panelu — chudy ustawia się tam, nie w kodzie).
   Silnik v11 = kontener Sylwii (jej strona; skrzynka go nie liczy).
3. ROLKA: `styki.daj_rolke(zam= | thread_id=)` → `{ok, wiadomosci}` (archiwum WEM; odczyt wolny,
   pokazywany w oknie silnika; v11 → operator wkleja ręcznie).
4. WYJŚCIE (ZAWÓR): `styki.wyslij(kanal, adresat, tresc, operator_pid, zgoda, subject="")` —
   bramki w kodzie: (a) klik operatora ZAWSZE (zgoda+pid), (b) eBay TWARDO zamknięty (osobna
   decyzja koordynatora), (c) forum osobnym torem (klient forum + FORUM_MODE), (d) tryb env
   `WEM_WYSYLKA`: off | **sucho (domyślnie — zapis zamiaru do archiwum, NIC nie wychodzi)** | live
   (realna wysyłka bramą WEM + zapis). KAŻDA próba ląduje w archiwum (kierunek=out, pole `tryb`).
   Fullautomat = otwarcie zaworu TUTAJ (tryb/wymóg kliku), zero zmian w silnikach/ekranach.
5. FORUM: odczyt + memory (ID wpisów), ładowany ZAWSZE gdy sprawa była na forum (jak v11) —
   przez istniejący klient forum (wspolne/forum.py), do opakowania w styk gdy bestchudy sięgnie.

TWARDE ZASADY (bezpieczeństwo — nie negocjowalne):
- **Każde WYJŚCIE** do klienta/na forum = **bezpiecznik operatora (klik)**, NIEZALEŻNIE od promptu.
- **eBay OSTROŻNIE**: inny styl rozmów; ZERO „trumpowskich"; ZERO 300/600/900 €/5-etapów; wiele kont
  (rozpoznanie po wsadzie, np. `pmg-service` / `ersi.877`); bezpiecznik konieczny.
- **WA STARY vs NOWY**: chudy tylko na NOWYM numerze. Sprawy sprzed „daty x" → kontynuowane na STARYM
  WA: operator wkleja rolkę ręcznie (jak v11), a odpowiedzi chudego na te sprawy **wysyła operator**
  (chudy nie ma dostępu do starego). Po „dacie x": nowe pz0 (puste koperty / świeżo delivered) → NOWY WA.
  Anty-spam WA (blokują). „Data x" = start produkcyjny chudego, stopniowo.
- **mail**: właściwa skrzynka wg kraju (DE/UK/FR/PL); trzymać ciąg korespondencji (cytować, cała rolka).
- **v11 = migracja 1:1**, nic nie zmieniamy w logice (referencja: `szturchacz-test`, `wiezowiec-test`).

OTWARTE (do decyzji): rozrzutnik = standardy z wieżowczyka + zdarzeniowe z WEM do woreczka, miksowane
po priorytecie (potwierdzić); login operatora = TAK (bezpiecznik potrzebuje odpowiedzialnego; docelowo
chudy autonomiczny, ale podgląd + historia per case zostają); v11 na Cloud Run = kontener „as-is" vs port.

## NEGOCJACJA KONTRAKTÓW BESTCHUDY — W TOKU (odpowiedź strony SKRZYNKI, 2026-07-02)
> Odpowiedź na PLAN.md §5–§8 (PR #2, gałąź `bestchudy/rozpoznanie-plan-v11`). To PROPOZYCJE strony
> Artura — **czekają na potwierdzenie/kontrę strony Sylwii**. UZGODNIONE = po obu zatwierdzeniach,
> właściciel klika na końcu. Dopóki niedomknięte — nie kodujemy styków po żadnej stronie.

1. **FEED (§5): strona skrzynki przyjmuje opcję (a).** Rozbudowuję wieżowczyk: obok `suchy_wsad`
   (identyfikacja/lista — zostaje) dojdzie pole **`wsad_panel` = WSAD PANEL FORMAT 2 co do znaku**.
   Pokrycie braków z Twojej tabeli mam w bazie: Delivered/statusy+listy przewozowe+lindexy+kurier+
   EbayLogin/buyerNick = pełny widok `v_austachStatus` (Prosty był za chudy — przełączam), **KOPERTA
   (COP#) = `SZTURCHACZ.dbo.Comment`** (kolumna `austaush`, most po austauch_id). PYTANIE ZWROTNE:
   podeślij wzorzec FORMAT 2 linia-po-linii (masz cytaty L702-767) — buduję co do znaku pod niego.
   Notka PII przyjęta (dane osobowe tylko za bramą koordynatora — wpiszę do kontraktu).
2. **policz-chudego + daj-rolka (§6): JUŻ ISTNIEJĄ** — Twoje rozpoznanie czytało main sprzed fasady.
   Od commita `d2494f2` jest `app/wspolne/styki.py`: `daj_sprawe / daj_rolke(zam|thread_id) /
   policz_chudego(suchy_wsad, rolka, historia) / wyslij(...)` (sekcja ŁĄCZNIKI niżej ma sygnatury).
   **Proszę o review sygnatur** — to jest dokładnie kontrakt do potwierdzenia przez Twoją stronę.
3. **Forum po zielonym — NIEAKTUALNE, rozstrzygnięte przez WŁAŚCICIELA** (patrz DECYZJE 2026-07-02):
   v11 pisze na forum NATURALNIE, bez bramek i bez zmian w apce/prompcie (produkcyjna praca bieżąca).
   Zawór skrzynki (`styki.wyslij`, w tym przyszły tor forum) dotyczy WYŁĄCZNIE chudego.
4. **Pamięć forum (§8.5): propozycja = WSPÓLNA** (`szt_forum_memory`; oba silniki muszą widzieć te
   same wątki, inaczej bumpy się rozjadą). Szczegół: kto pisze/kiedy — doprecyzujmy w kontrakcie;
   Twoja propozycja mile widziana (kontener przez styk czy bezpośrednio do kolekcji).
5. **Bramka propozycji: strona skrzynki PRZYJMUJE** `silnik` ("v11"|"chudy") + `porownanie_id?` oraz
   czerwony w dwóch podtypach („do poprawy" / „odrzuć"; „wyślij jednak" = zielony po edycji) —
   dopiszę do draftu w sekcji STYKI po domknięciu.
6. **Bramki WŁAŚCICIELA (nie stron): §8.1 port-vs-as-is, §8.2 lokalizacja kodu kontenera, §8.6 quota.**
   Strona skrzynki POPIERA: port + katalog `kontener_v11/` w tym repo + jeden projekt na start.
   Właściciel klika po Waszej wymianie.

**ODPOWIEDŹ STRONY SYLWII (2026-07-02, po decyzjach właściciela — PR `bestchudy/rozpoznanie-plan-v11`):**
1. **FEED: WZORZEC `wsad_panel` DOSTARCZONY** — pełny, linia-po-linii, z regułami parsowania co do
   znaku (nagłówek `NRZAM RRRR-MM-DD NICK_SPRZEDAWCY`; data doręczenia bezpośrednio PRZED „Delivered";
   data zwrotki bezpośrednio ZA numerem listu; ostatnia linia z separatorem TAB; `koperta` = OSOBNE
   surowe pole 1:1 z Comment, bez czyszczenia) → **PLAN.md §5**. Sklejkę wsadu (panel+koperta+tag)
   robi bestchudy przy „KOPIUJ WSAD" i TĘ SAMĄ podaje chudemu — nie wieżowczyk.
2. **REVIEW SYGNATUR `styki.py`: WYKONANY — wszystkie cztery POTWIERDZONE** (szczegóły PLAN.md §6).
   Uzupełnienia: (a) po rozbudowie FEED proszę o pola `wsad_panel` + `koperta` w każdej sprawie;
   (b) `policz_chudego` będzie dostawał pełną sklejkę z §5 jako `suchy_wsad` (string — sygnatura OK).
3. Forum po zielonym — przyjęte (nieaktualne po decyzji właściciela; zawór tylko chudy).
4. **Pamięć forum — propozycja strony Sylwii (szczegóły były u mnie):** skoro v11 nietykalny, CHUDY
   dostosowuje się do v11 — wspólny notes = kolekcja `forum_memory` (`test_forum_memory` przy
   TEST_MODE) w projekcie Firestore KONTENERA, kształt zastany (`forum_posts.{cel}`, pierwszy zapis
   wygrywa). Proszę o PIĄTY styk fasady: `pamiec_forum(nrzam)` / `zapamietaj_forum(nrzam, cel, wpis)`
   (implementacja u Ciebie, projekt z env). Potrzebne dopiero w fazie C — nie blokuje.
5. Bramka propozycji — domknięte (obie strony zgodne).
6. Decyzje właściciela przyjęte; lokalizacja `kontener_v11/` w tym repo — POTWIERDZAM. Plan
   przerobiony pod as-is (PLAN.md §2-§3: odpałka bez dotykania logiki; pytania odpałkowe: projekt
   Firestore kontenera — proponuję STARY; flagi TEST_MODE/FORUM_TEST_MODE — proponuję bez zmian).
7. **UZUPEŁNIENIE FEED od Sylwii (2026-07-02, dane z produkcji — dla wieżowczyka):**
   (a) **obecnie pobierana KOLEJNOŚĆ kolumn jest NIEPRAWIDŁOWA**; poprawna kolejność panelu
   (v11 jest przygotowany na dokładnie taki układ):
   `NrZam | Data Zama | User Tw | Nazwa Klienta | Mail | Tel | Kraj | Tagi | Bieżący etap |
   Data etapu | Kolejny etap | Data kolejnego etapu | Data zam kuriera | Reklamacja |
   Data dostarczenia paczki | lindexy | Zarządzaj | Szczegóły | Numery listu zwrotnego |
   Typ kuriera | Login Ebay | Nick Ebay`;
   (b) DWA wzorcowe przykłady produkcyjne (poprawnie ustawione; różnice: zakup eBay vs nie,
   z tagiem vs bez) — wklejone VERBATIM w **PLAN.md §5.1** na gałęzi PR #2. Buduj `wsad_panel`
   pod te przykłady; mój wcześniejszy minimalny wzorzec FORMAT 2 (§5) pozostaje jako spis reguł
   parsowania (v11 czyta wsad SEMANTYCZNIE, nie pozycyjnie — obie formy zgodne z promptem).

## STYK: LEWA STRONA / RĘKA ROBOTA
**STATUS: ZATWIERDZONE (właściciel, 2026-07-03) — MOŻNA KODOWAĆ.** Głos Sylwii przyjęty w całości
(przepływ 2 przycisków, hasło = opcja A: raz przy wyborze operatora, pamięć do zamknięcia karty,
+3 wygody na pasie Sylwii). Rura /v11/ AKTYWOWANA na serwerze (V11_UPSTREAM + V11_URL=/v11/) —
próba techniczna i toolbar = pas Sylwii; styki daj_operatorow/daj_sprawe(grupa=) już na main.

**WYNIK PRÓBY TECHNICZNEJ (Sylwia, 2026-07-03) — RĘKA ROBOTA DZIAŁA; PUSTA RAMKA = WS na PRODZIE
(pas Artura).** Podpięłam lokalną rurę pod żywy kontener i zbadałam DOM v11 w przeglądarce:
1. ✅ **HTTP przez rurę OK** — v11 renderuje się w pełni (ekran logowania: selectbox „Operator",
   pole „Hasło", przycisk „🔓 Zaloguj"); assety `/v11/static/...` = 200 lokalnie i na prodzie.
2. ✅ **RĘKA ROBOTA — WSZYSTKIE 3 haczyki z komentarza sprawdzone i DZIAŁAJĄ:**
   (a) hasło: natywny setter `HTMLInputElement.value` + `input`/`change` event → React zauważa
   (`react_zauwazyl: true`); (b) dropdown operatorów (BaseWeb): otwiera się na PEŁNĄ sekwencję
   `mousedown+mouseup+click` na kontrolce (sam `click` NIE wystarcza!), lista w portalu na końcu
   body (`li[role=option]`), wybór Magda utrwalony („Operator: Magda"); (c) lista operatorów
   z v11 = Sylwia/Emilia/Oliwia/Magda/Ewelina/Iwona/Marlena/EwelinaG/Andrzej/Marta — pokrywa się
   z magazynem, potwierdza case lowercase. Wsad-odwrotny sprawdzę po zalogowaniu (ten sam wzorzec
   natywnego settera). WNIOSEK: symulacja wykonalna BEZ zmian w v11 — buduję toolbar+rękę robota.
3. ⚠️ **PUSTA RAMKA NA PRODZIE — przyczyna INNA niż moja hipoteza baseUrlPath (odwołuję ją).**
   Assety HTTP wchodzą (200), ale **WEBSOCKET `/v11/_stcore/stream` na PRODZIE NIE ŁĄCZY SIĘ**
   (`wss://szturchacz.aitossilniki.com/v11/...` = timeout; surowy `wss://...run.app/v11/...` też).
   Streamlit ładuje skorupę, ale bez kanału na żywo NIE renderuje ciała → pusta ramka. LOKALNIE
   ten SAM kod rury mostkuje WS w 0.1 s i ekran działa — więc **kod rury jest OK, problem to
   upgrade WebSocketu na prodzie** (pas Artura): najpewniej domena/LB Cloud Run nie przepuszcza
   `Upgrade: websocket` na ścieżce `/v11/…`, albo brak session-affinity dla mostka. PROŚBA: sprawdź
   konfigurację WS na trasie `/v11/` (custom domena → usługa szturchacz) i timeout usługi.
   Do czasu naprawy WS: ramka na PRODZIE zostaje na BEZPOŚREDNIM `V11_URL` (mój PR #11 to pilnuje —
   scal go); ręka robota wejdzie, gdy WS przez rurę ruszy (bo autologowanie potrzebuje same-origin).

**WERSJA DLA SYLWII (po ludzku, do pokazania jej w oknie):**
Na ekranie porównywarki, nad oboma oknami, pojawią się dwa przyciski: „WSKAŻ OPERATORA"
(wybierasz z listy, np. klaudia) i „POBIERZ KOLEJNY CASE". Po kliknięciu system sam: zaloguje
wskazanego operatora w okienku starej apki v11 (lewa strona) i wklei tam wsad sprawy — dokładnie
ten sam, który dostaje chudy po prawej. Czyli: koniec z ręcznym logowaniem do v11 i kopiowaniem
wsadu — dwa kliki i obie strony liczą tę samą sprawę. Stara apka NIE jest przerabiana — nasz
ekran „klika za Ciebie", jak ręka robota. PYTANIA DO CIEBIE: (1) czy taki przepływ pracy Ci
pasuje (2 przyciski na górze)? (2) czy autologowanie operatora jest OK, czy wolisz logować się
sama? (3) czego jeszcze brakuje, żeby praca na porównywarce była wygodna?

**GŁOS SYLWII-CZŁOWIEKA (szkic pokazany prozą + quizy, 2026-07-03):**
(1) Przepływ 2 przycisków — **PASUJE** (potwierdziła wprost: „jeden klik = obie strony
wystartowane, ramki nie dotykam"). (2) Autologowanie — **OK**, z hasłem wpisywanym RAZ przy
wyborze operatora, pamiętanym tylko do zamknięcia karty (= opcja A z komentarza sesji; głos
użytkownika za A). (3) Czego brakuje dla wygody — wybrała z propozycji: **„Zapisz → następny
case sam"** (po werdykcie kolejna sprawa wskakuje automatycznie), **kopiowanie draftu chudego
jednym klikiem**, **sygnał gdy chudy skończy liczyć** (dźwięk/wyróżnienie). Wszystkie trzy =
mój pas (frontend porównywarki), dopiszę do budowy toolbaru; „pomiń case" — nie wybrała.

To jest KONCEPT do OBEJRZENIA i SKOMENTOWANIA przez stronę Sylwii, nie zlecenie. Pętla (regulamin → STATUSY KONTRAKTU): (1) Sylwia czyta i dopisuje TU
komentarz/kontrę (co pasuje, co nie, alternatywy — zwłaszcza wykonalność autologowania i wklejki
w realnym DOM-ie streamlita, który znasz lepiej), (2) uzgadniamy między stronami, (3) FINAL wraca
do WŁAŚCICIELA do zatwierdzenia, (4) dopiero wtedy kod po obu stronach.
Kontekst: odpowiedź na uwagę operatorki „miniatura streamlita się nie nadaje". Decyzja właściciela
(kierunkowa): pliki v11 NIETKNIĘTE, ramka ZOSTAJE, `policz_v11` odrzucone — zamiast tego
**przyciski nad oknami wszczepiają operatora i wsad do OBU stron** (do v11 „jak ręka robota",
bez zmiany jego kodu).
STRONA SKRZYNKI (Artur) — GOTOWE: rura `/v11/` (`app/wspolne/v11_rura.py`, w main) serwuje kontener
pod NASZĄ domeną (HTTP + websocket Streamlita, testy 5/5). Aktywacja na serwerze = env
`V11_UPSTREAM=<adres kontenera>` + `V11_URL=/v11/` — robi koordynator przy wdrożeniu, gdy toolbar
gotowy (albo wcześniej na życzenie, żebyś miała `/v11/` do testów — poproś wpisem).
PROPOZYCJA DLA STRONY SYLWII (szkic do Twojej oceny — skomentuj zanim cokolwiek powstanie):
- Toolbar NAD oboma oknami: „wskaż operatora" (lista) + „pobierz kolejny case" (styk `daj_sprawe`).
- CHUDY: parametry wchodzą wprost (masz już `policz_chudego`).
- V11 w ramce: gdy `V11_URL` zaczyna się od `/` (ta sama domena → dostęp do `iframe.contentWindow/
  Document` DOZWOLONY), Twój JS: (a) na ekranie logowania v11 wpisuje wskazanego operatora i loguje,
  (b) wkleja `wsad_panel` w pole „wsad odwrotny" v11 i zatwierdza — natywnie, zero zmian w v11.
- Selektory pól logowania i „wsad odwrotny" v11 rozpoznajesz Ty (znasz apkę streamlitową); jeśli WS
  Streamlita utrudni symulację wpisywania — zgłoś, dołożę po stronie rury co trzeba.
CEL: obie strony ~równa liczba kliknięć. Wyjścia obu stron dalej za zaworem/klikiem (bez zmian).
WDROŻENIE: całość lewej strony wdrażamy, gdy Twój toolbar gotowy (koordynator deployuje z `main`).

**KOMENTARZ STRONY SYLWII (2026-07-03) — kierunek PRZYJMUJĘ, wykonalność: TAK, ale KRUCHO;
konkrety z rozpoznania silnika (czytałam cały app_vertex_ew.py):**
1. **Wykonalność wklejki/kliknięć — TAK, z trzema haczykami technicznymi.** Ekran v11 to React
   (Streamlit/BaseWeb), więc: (a) zwykłe ustawienie pola nie działa — trzeba natywnego settera
   + zdarzenia `input` (React inaczej nie zauważa zmiany); (b) lista operatorów na logowaniu to
   NIESTANDARDOWY dropdown (BaseWeb) — symulacja = klik w kontrolkę, czekanie na listę, klik
   w opcję; (c) po każdym przeliczeniu Streamlit WYMIENIA drzewo DOM — robot musi czekać na
   elementy (MutationObserver/polling), a selektory brać po aria/tekstach etykiet, NIE po klasach
   (klasy są generowane i zmienne). Umiem to napisać; uczciwie: to najkruchszy element całej
   porównywarki i każda zmiana wersji streamlita w kontenerze może go wywrócić (kontener mamy
   przypięty w constraints — ryzyko kontrolowane).
2. **HASŁO do autologowania — jedyna realna dziura szkicu.** v11 wymaga hasła operatora
   (plaintext w `operator_configs` starego Firestore; kod loguje porównaniem ==). Robot musi je
   skądś znać. OPCJE: (A) operator wpisuje hasło RAZ przy „wskaż operatora", trzymamy TYLKO
   w pamięci karty (sessionStorage, znika z zamknięciem) — zero nowych sekretów, mój faworyt
   na start; (B) wspólne hasło porównywarkowe ustawione operatorom w `test_operator_configs`
   (decyzja koordynatora — zmiana danych, nie kodu v11); (C) rura dopisuje hasło z Secret
   Managera — ODRADZAM (rura musiałaby znać hasła wszystkich; szeroki sekret w przelotce).
   Proszę o wybór A/B przy uzgadnianiu.
3. **PROŚBA (z Twojej oferty): aktywuj `/v11/` na serwerze JUŻ TERAZ** — zanim postawimy
   UZGODNIONE, zrobię PRÓBĘ TECHNICZNĄ ręki robota na realnym DOM-ie przez rurę (bez toolbaru,
   bez kodu w main — sam eksperyment w przeglądarce) i dopiszę tu wynik: „symulacja działa" albo
   listę braków do dołożenia w rurze. To zdejmie największe ryzyko PRZED zatwierdzeniem u właściciela.
4. **Zależności toolbaru** (żeby „wskaż operatora" był prawdziwy, nie atrapa): styki z PR #9 —
   `daj_operatorow()` + `daj_sprawe(grupa=)` + parametry startowe w `policz_chudego` (operator
   musi wchodzić do OBU silników, inaczej test telefonów/forum per grupa niemożliwy).
5. **Fallback, gdyby symulacja DOM padła** (do dyskusji, NIE proponuję na start): rura mogłaby
   wstrzykiwać do przelatującego HTML-a v11 mini-mostek JS (pliki v11 nietknięte — zmiana tylko
   „w locie"); zapisuję jako plan B, decyzja właściciela, czy to jeszcze duch „as-is".
Po Twoich odpowiedziach (hasło A/B + aktywacja rury) i mojej próbie technicznej → UZGODNIONE → FINAL.
6. **POTWIERDZENIE OPERATORKI (Sylwia, 2026-07-03):** założenia obejrzane i zaakceptowane wprost:
   (1) jeden klik = obie strony wystartowane, ramki nie dotyka; (2) sprawy wg działu wskazanego
   operatora (przepinanie grup w zapleczu); (3) hasło wpisywane RAZ przy wyborze operatora,
   pamiętane tylko do zamknięcia karty (opcja A). Głos użytkownika końcowego — za opcją A.

## STYKI / KONTRAKTY (interfejsy między pasami — TU pilnujemy spójności)
- **Odbiór (brama→nas):** `brama_wa.py` zapisuje przychodzące do Firestore `szt_wa_inbox`
  z polem `channel` (whatsapp/email/eBay) + sender/text/ts/raw. To źródło kontekstu dla automatu.
- **Wysyłka (nas→brama):** `POST /api/v1/messages/send` (channel, recipient, body). Owner: Artur.
- **Kurier:** automat emituje awizację do Firestore `awizacje_kurier` (kontrakt z apką Eweliny —
  `kontrakt_awizacje_kurier.md`, dziś u koordynatora; DO WRZUCENIA do repo). Faza 1: UPS skrzynia, shadow.
- **Propozycja automatu ↔ bramka operatora — KONTRAKT (dwustronny, do domknięcia):**
  Automat zapisuje propozycję akcji do Firestore `propozycje` (`status="do_akceptacji"`); bramka czyta,
  pokazuje, ustawia decyzję; automat NIE wykonuje przed `zielony` (człowiek w pętli).
  - STRONA AUTOMATU (Artur, draft v0): dok `{id, created_at, status, test_mode,
    sprawa{nrZam,dokId,pz,grupa,kanal_zrodlo}, typ:"wiadomosc"|"kurier",
    akcja{kanal,recipient,tresc | awizacja{…CreateZwrotka…}}, kontekst{rolka_skrot,fakty},
    uzasadnienie, decyzja:null, komentarz:null, decydent:null, decyzja_at:null}`.
    Otwarte: kto wykonuje po `zielony` (automat poll vs worker), idempotencja, podtypy „czerwony"
    („do poprawy" vs „wyślij jednak").
  - STRONA BRAMKI (Sylwia, 2026-07-02): draft Artura POKRYWA potrzeby renderu zielony/czerwony
    + panelu odrzutów + komentarza (używam: id, created_at, status, test_mode, sprawa{nrZam,pz,grupa,
    kanal_zrodlo}, typ, akcja{kanal,recipient,tresc|awizacja}, kontekst{rolka_skrot,fakty},
    uzasadnienie, decyzja/komentarz/decydent/decyzja_at). PROSZĘ DOŁOŻYĆ 2 pola: `silnik` ("v11"|"chudy")
    i opcjonalne `porownanie_id` (spięcie z werdyktami porównywarki bestchudy). Podtypy „czerwony":
    głosuję za dwoma („do poprawy" vs „odrzuć") — „wyślij jednak" to zielony po edycji, nie czerwony.
  - UZGODNIONE: ⬜ (puste; domykamy po OBU PR). **Dopóki nie domknięte — nikt nie koduje swojej strony.**

## PROJEKTY (Artur↔Sylwia — rejestr; koordynator prowadzi)
### [ARTUR] Skrzynka rozmów — archiwum WA/mail/eBay (in+out), spięte po tożsamości + czytelny panel
STAN: projekt / rozpoznanie (nie kodujemy jeszcze).
CEL: jedno miejsce z CAŁYM ruchem klienckim (przychodzące + wychodzące; WA + mail + docelowo eBay
po dostępach), spięte po telefonie / mailu / nr zamówienia, pokazane czytelnie w OSOBNYM panelu
(„Skrzynka/Rozmowy" — nie mieszać z Wieżowcem).
PUNKT WYJŚCIA (twardy fakt): brama ATA = **stateless forwarder**; WhatsApp = **ZERO historii**
(push-only). Czego nie złapiemy — przepada. Więc „niech zostaną w swoich miejscach" NIE dotyczy WA
(nie ma takiego miejsca) → MUSIMY persystować sami. Przychodzące JUŻ lecą do `szt_wa_inbox`;
dołożyć logowanie WYCHODZĄCYCH przy `POST /messages/send`.
PODEJŚCIE (rekomendacja):
- Model wiadomości: `{channel, direction(in/out), sender, recipient, body, ts, msg_id, order_ref?,
  thread_id, raw}`. Wątek = klucz spięcia po znormalizowanej tożsamości (tel E.164 / mail lower /
  nr zam). Spięcie robimy PRZY ZAPISIE (nadajemy `thread_id`), nie przy odczycie.
- Objętość: TEKST jest mały (~1–2 KB/wiadomość; ~500/dzień ≈ 0,3 GB/rok — Firestore udźwignie,
  koszt = grosze). Ciężar to ZAŁĄCZNIKI (zdjęcia/PDF/audio) → **GCS (obiektowe), w bazie tylko link**.
  Binaria do bazy = NIGDY.
- Store: NA START zostajemy na **Firestore** (przychodzące i tak tam są; wątkowanie-przy-zapisie
  wystarcza do panelu: `where thread_id==X order by ts`). Relacyjną bazę (**Postgres/Cloud SQL + FTS**)
  dokładamy DOPIERO gdy realnie potrzebne pełnotekstowe SZUKANIE / raporty cross-kanał = **faza 2**.
- Retencja: gorące ostatnie N mies. w bazie; starsze → archiwum JSON w GCS (faza 2, nie teraz).
- Panel: OSOBNY „Skrzynka/Rozmowy" — lista wątków → oś czasu przeplatana (wszystkie kanały, in+out) →
  szukaj po tel/mail/nr zam.
STYK: ten sam store = źródło kontekstu dla AUTOMATU (`kontekst.rolka_skrot` z kontraktu propozycji).
Jeśli panel wyląduje w Wieżowcu (widok Sylwii) — to STYK, uzgodnić.
DO DECYZJI: (1) Firestore-teraz vs Postgres-teraz; (2) reguły spięcia tożsamości (ten sam klient ma
telefon I mail — łączyć wątki?); (3) okno retencji.

AUDYT FUNDAMENTU (2026-07-01, workflow 4-agent: Swagger bramy + WA Cloud API + nasz kod/sample):
- BRAMA = nie zła konstrukcja, tylko CIENKI KONTRAKT. Dowód że silnik uniesie więcej: `/send` ma
  `AttachmentModel{fileName, content=base64}` → brak media/id/ts w INbound pushu to WYBÓR co Krzysiek
  forwarduje, nie limit. Jeden realny limit architektury: subskrypcja `topic="message"` łapie WSZYSTKIE
  kanały na jeden `endpointURL` (nie zawęzisz do WA) + zero pola na HMAC/secret (autoryzacja = token w URL).
- CO BRAMA PRZEPYCHA DZIŚ (za mało): tylko `{channel, data:{body,sender,recipient,subject}}`. BRAK:
  message-id, czasu NADANIA, kierunku (in/out), MEDIA, statusów (doszło/przeczytane), kontekstu-odpowiedzi.
  Haczyk stateless: brama nie gromadzi WA → każde brakujące pole to DZIURA NA ZAWSZE (nie ma skąd dobrać).
- CZEGO NIE DA SIĘ NIGDY (to META, nie brama): historia sprzed wpięcia (zero backfillu); edycje;
  usunięcia. Archiwum ZAWSZE startuje od zera w momencie subskrypcji. „Jak na telefonie" = nieosiągalne.
- NASZE DZIURY (naprawialne u nas, nasz pas): (a) endpoint NIE-DURABLE — `wa_inbox.add()/set()` bez
  try/except; błąd zapisu → 500 → wiadomość PRZEPADA (brama prawdopodobnie at-most-once); (b) ZERO
  logowania WYCHODZĄCYCH → mamy pół dialogu; (c) brak id → doc_id=uuid4 → retransmisja=duplikat;
  (d) ts=czas ODBIORU nie nadania. PLUS: trzymamy pełny `raw` 1:1 = jedyna siatka bezpieczeństwa (dobre).
- SCOPE (realny, komunikować właścicielowi): „WIERNE ARCHIWUM OD DNIA WPIĘCIA W PRZÓD, best-effort" —
  NIE lustro telefonu. Media do GCS NATYCHMIAST (link Meta żyje 5 min).
- NASZA STRONA DO ZROBIENIA: durability (dead-letter + 200-szybko + async), log outbound, dedup-klucz
  zastępczy do czasu id, parser głębiej + media.
- ASKS DO KRZYŚKA (żeby brama nie była wąskim gardłem): dołóż do WA-forwardu id(wamid)+ts nadania+kierunek;
  przepychaj MEDIA (base64 lub media-id+mime by ściągnąć z Graph w 5 min); forwarduj STATUSY; POTWIERDŹ
  retry/bufor/ACK (czy ponawia na 5xx? czeka na nasze 200 zanim ACK-nie Metę? — to rozstrzyga kompletność);
  subskrypcja per-kanał (koniec mieszania WA/mail/eBay + duplikatów DEV+PROD); HMAC/podpis pusha; kształt
  pusha NA PIŚMIE (dziś parser stoi na zgadywanym kontrakcie).

## DECYZJE (log — dopisuj nowe na górze)
- 2026-07-03: [ARTUR] **WYDAJNOŚĆ CHUDEGO krok 1 (commit 951da27, plik wspólny ai.py — pas
  koordynatora, styk respond() BEZ zmian)**: projekt GCP wybierany per ROZMOWA (hash pierwszej
  wiadomości), nie per wywołanie → identyczny prefiks (prompt ~64k tok. + historia) trafia
  w implicit cache Vertexa: rabat 90% na wejściu od tury 2 i odczuwalnie szybsze odpowiedzi
  (adres skargi „chudy długo myśli"). Dodatkowo: projekt/region przypięte pełną nazwą zasobu
  w żądaniu (koniec wyścigu wątków na globalnym vertexai.init), chłodzenie projektu 60 s po
  429/503, licznik trafień w logu `[ai] ... cache=N`. Dla bestchudy nic do zrobienia — czysta
  zmiana wewnątrz silnika. Krok 2 (później, osobna decyzja): migracja na google-genai SDK —
  Google ogłosił wycofanie gemini-2.5-pro 16.10.2026.
- 2026-07-03: [ARTUR] **KARTA SPRAWY (etap 3/3) ZBUDOWANA** — nowy kafelek zaplecza: wpisujesz
  nr zamówienia ALBO nazwisko/mail/telefon (kandydaci z bazy franciszkańskiej, widok _mailTel,
  wejście przez whitelistę znaków + escapowanie LIKE; dedup per zam; ŻYWY test: MULTITRANSMISIONES
  → 20 spraw, telefon → te same). Karta skleja w jedno okno: nagłówek sprawy + LICZNIKI wiadomości
  per kanał (in/out) + WSAD (linia ze szturchacza) + KOPERTY + pełna oś czasu WA/mail/eBay
  z archiwum. Plan właściciela (paginacja → pobieracz → karta) DOMKNIĘTY w kodzie; deploy zbiorczy.
- 2026-07-03: [ARTUR] **POBIERACZ HISTORII mail/eBay (etap 2/3) ZBUDOWANY** — zaplecze → Rozmowy
  → „Historia z bramy": kanał + zakres dat (porcja ≤31 dni, bezpiecznik 2000 wiad.), zapis przez
  istniejący magazyn (sklejanie przy zapisie), IDEMPOTENTNY (powtórka porcji = duplikaty pominięte;
  test ✓), czas nadania ze źródła (stare maile lądują we właściwym miejscu chronologii), kierunek
  OUT dla maili z naszych skrzynek. WA celowo poza zakresem (Meta bez historii). Kształt odpowiedzi
  /receive parsowany TOLERANCYJNIE (Swagger go nie opisuje).
  ⚠️ ŻYWA WERYFIKACJA WSTRZYMANA: brama WEM nie przyjmuje logowania (DEV 403, PROD 500 na
  /auth/token, 2026-07-03) — najpewniej trwa przebudowa u Krzyśka (backlog). PUSH ŻYJE (ostatni
  mail 2h temu) — nic nie ginie. Obserwuję; jak auth nie wstanie do jutra → ping do Krzyśka.
- 2026-07-03: [ARTUR] **ARCHIWUM v2 — fundament pod WOLUMEN (etap 1/3 planu właściciela):**
  panel Rozmów przestał mielić wszystko — pyta bazę o WYCINEK: domyślnie najnowsze 100
  (przełącznik 100/300/1000), zakresy dat od–do, SZUKAJKA (nr zam / mail / telefon → wątki
  z trafień; nazwisko będzie w karcie sprawy — dane osobowe w bazie franciszkańskiej, agent baz).
  Oś czasu wątku/zamu = zapytanie po polu (bez okna) + doliczka starych rekordów sprzed archiwum.
  Zapytania zweryfikowane na żywym Firestore (bez indeksów złożonych — sort w widoku).
  Przy okazji DWIE CEGŁY WEM: (1) dedup po PRAWDZIWYM id (wamid/message-id gdy brama dołoży —
  hash zostaje zastępnikiem; retransmisja po 2h = duplikat, test ✓), (2) mail Z NASZYCH skrzynek
  (sav/magda/contact/biuro_info; env WEM_NASZE_SKRZYNKI) = kierunek OUT — gotowe pod monitoring
  folderu WYSŁANE u Krzyśka (pełne dialogi mailowe od pierwszego dnia). NASTĘPNE: etap 2 =
  pobieracz historii mail/eBay (pull /receive porcjami), etap 3 = KARTA SPRAWY (agregacja
  po kliencie ze wszystkich źródeł + wyszukiwarka po nazwisku przez agenta baz).
- 2026-07-03: [ARTUR] **JEDEN ADRES dla porównywarki (pomysł właściciela) — MOSTEK BILETOWY
  ZBUDOWANY.** Zamiast przerabiać domenę (mapowanie nie przenosi websocketów): porównywarka
  z ręką robota żyje pod adresem TECHNICZNYM usługi (websockety tam działają — zweryfikowane),
  a logowanie przenosi mostek: ładna domena `/przeskok-bestchudy` (wymaga sesji Pulpitu) →
  60-sek. podpisany bilet → adres techniczny `/api/sso/bilet` → lokalna sesja `tsession` (8 h,
  HttpOnly+Secure) → `/bestchudy`. `read_operator` honoruje `tsession` obok sesji Pulpitu.
  Aktywacja: env `TECH_URL` przy deployu. Testy 4/4 (bez logowania→Pulpit; bilet→tsession;
  read_operator z tsession; podrobiony bilet odrzucony).
  **DELEGACJA SZCZEGÓŁÓW → SYLWIA (decyzja właściciela: „niech ona doprecyzuje, to nie blokada"):**
  (a) skąd operator wchodzi na przeskok — kafelek Pulpitu wprost na `/przeskok-bestchudy` czy
  przycisk na Twoim ekranie (Twój wybór, Twój pas);
  (b) ŹRÓDŁO ramki per adres: na adresie technicznym iframe = `/v11/` (rura, ręka działa),
  na ładnej domenie zostaje bezpośredni V11_URL — proponuję wybór po hoście w Twoim routerze
  (Twój plik; mostek niczego tu nie narzuca);
  (c) „ŁAPKA" parametrów: operator z toolbaru → chudy przez `policz_chudego(operator=, grupa=)`
  (gotowe), → v11 przez rękę robota (login w ramce); dawne parametry z Wieżowca streamlitowego
  zastępuje Twój toolbar — rozpisz jak uznasz;
  (d) kafelek OPERATORZY = Twoje władanie (przekazane wcześniej) — hasła operatorów v11 wpisywane
  ręcznie przy wyborze (opcja A, głos Sylwii), NIE przechowujemy ich nigdzie.
- 2026-07-03: [SYLWIA] **INCYDENT NA PRODUKCJI (zgłoszenie operatorki) — 2 sprawy, PILNE:**
  **(1) V11 ZNIKNĘŁO Z RAMKI — moja wina, poprawka w PR `bestchudy/naprawa-ramki`.** Analiza:
  w PR #9 dodałam automat „gdy V11_UPSTREAM ustawione → ramka przez rurę /v11/"; po ustawieniu
  env na serwerze produkcyjna ramka po cichu przeszła na NIEPRZETESTOWANĄ przelotkę (kontener
  bezpośrednio jest ZDROWY: health ok, embed 200 — sprawdziłam). Poprawka: o źródle ramki decyduje
  WYŁĄCZNIE Twój jawny przełącznik `V11_URL` (rura dopiero po ZATWIERDZONE + próbie technicznej).
  NAPRAWA OD RĘKI (wybierz): (a) scal PR naprawy + deploy (upewnij się, że `V11_URL` = bezpośredni
  adres kontenera), ALBO (b) szybciej bez deployu: usuń `V11_UPSTREAM` z env szturchacza — mój
  automat przestanie preferować rurę. HIPOTEZA dla rury (do próby technicznej, nie łatam teraz):
  Streamlit serwowany pod ścieżką `/v11/` generuje adresy zasobów od korzenia — bez
  `--server.baseUrlPath=/v11` w odpałce kontenera assety lecą z NASZEGO `/static/` i ekran jest
  pusty; sprawdzimy przy próbie (flaga = odpałka, mój pas, jedna linia w odpalka.py).
  **(2) „Połączenie zerwane w trakcie" przy POLICZ CHUDEGO — DRUGI raz na produkcji** (tym razem
  komunikat precyzyjny: serwer NIE dokończył odpowiedzi = zabita instancja albo timeout, to NIE
  jest błąd silnika). Proszę o LOGI z okna czasowego zgłoszenia (szukaj: container terminated /
  OOM przy imporcie vertexai / przekroczenie timeoutu) — wzorzec powtarza się u operatorki,
  to już nie jednorazówka.
- 2026-07-03: [ARTUR] **WSAD PANELOWY DOMKNIĘTY wg mapowania agenta baz** (sesja BAZY
  FRANCISZKAŃSKIE zweryfikowała pola na żywym 380895): (1) przełączenie źródła na
  `v_austachStatus_mailTel` — TYLKO ten widok niesie WSZYSTKIE warianty telefonu klienta
  (wiersz-per-telefon; pułapka dubli z atlasu ROZBROJONA: dedup po zamie + telefony sklejane po
  przecinku jak w panelu); (2) etap niepodjęty = „Jeszcze nie podjęto (Nie aktywny)" (jak panel);
  (3) kurier 2=SCHENKER dopisany (1=UPS, 5=FEDEX potwierdzone). WERYFIKACJA ŻYWA: 380895 =
  35/35 tokenów zgodnych ze zrzutem panelu (kolejność wariantów tel. wg widoku — semantycznie
  obojętna); regresja: 381865 identyczna, 381879 różni się WYŁĄCZNIE świeżym tagiem z produkcji.
  **KOPERTY (wymóg właściciela):** NIE wchodzą do `wsad_panel` — dostęp OSOBNY: pole `koperta`
  w styku `daj_sprawe` (lista {kto, kiedy z czasem, tresc 1:1}) + sekcja „KOPERTA" w podglądzie
  wieżowczyka (zaplecze); do v11 składa je strona Sylwii (`zloz_koperte`, format panelu).
  NOTKA: czas kopertki z bazy bywa o 1h wcześniejszy niż w panelu (strefa serwera?) — do
  wyjaśnienia; luka „Bieżący etap przy WYSŁANYM mailu" wciąż otwarta (agent też nie domknął —
  pytanie o VIEW DEFINITION dla artur_ro dopisać do następnej wiadomości do Krzyśka).
- 2026-07-03: **WŁAŚCICIEL: kafelek OPERATORZY (Wieżowiec-zaplecze) przekazany do pasa SYLWII**
  (zakres plików/fragmentów wypisany w rozpisie bestchudy pkt 2 — wyjątek od „nie dotyka
  wspólnych"). Naturalne domknięcie: selektor operatora, grupy i wygody ręki robota żyją u niej,
  więc i zarządzanie operatorami przechodzi do niej. Magazyn operatorów — zmiany w uzgodnieniu
  (używa go też ekran operatora i silnik).
- 2026-07-03: [ARTUR] **ODPOWIEDŹ na 3 prośby-styki z PR #9** (PR scalony przez właściciela):
  (a) ZROBIONE — `styki.daj_operatorow()` → {pid, label, grupa, tel, jezyki} (źródło: magazyn
  operatorów; PRZEPINANIE GRUP już istnieje: zaplecze → Operatorzy → wpisz pid z nową grupą
  i „Dodaj/zapisz" — jak będzie niewygodne, dopiszę szybkie przełączanie) oraz
  `styki.daj_sprawe(..., grupa="DE|FR|UKPL")` — filtr działu w bazie; UWAGA: sonda pokazała
  kraj ∈ {DE, PL, INNE}, więc FR/UK filtruję pełną nazwą kraju (kaCountry='France' / lista UK) —
  mapowanie EMPIRYCZNE v1, POTWIERDŹ na realnych sprawach FR/UK i zgłoś, jeśli coś ucieka w „INNE".
  (b) ZROBIONE — `policz_chudego(..., operator=, grupa=, tryb=)`: system dostaje PARAMETRY
  STARTOWE jak v11 (`ai.build_start_params`, data=dziś); bez podania — zachowanie jak dotąd.
  (c) PRZYJĘTE jako OSOBNA CEGŁA (analiza, nie łatka): cache kontekstu (stary świat: CachedContent
  TTL 60 min) + ewentualna dyskusja o modelu — dopisane do follow-upów koordynatora.
  Wszystko na main; na serwer wejdzie z najbliższym deployem.
- 2026-07-03: [SYLWIA] **UWAGI OPERATORKI #2 — wdrożone po mojej stronie** (PR `bestchudy/uwagi-2`)
  + 3 PROŚBY-STYKI do Artura. ZROBIONE U MNIE: (1) tryby odwrotne (WA/mail/eBay/forum) otwierają
  okienko „SESJA [KANAŁ] — rolka": rolka-wzorzec z przyciskiem KOPIUJ ROLKĘ (gotowa komenda
  `SESJA WYNIK [nr] – ROLKA_[KANAŁ]` dla v11) + „Pobierz z API" dla chudego (styk daj_rolke,
  nowy endpoint `/bestchudy/api/rolka`, format MY/KLIENT bez duplikatów) z twardym fallbackiem:
  API puste (sprawa sprzed „daty x" — stare WA bez dostępu) → chudy dostaje rolkę-wzorzec.
  (2) przyciski jak w streamlicie: ⚡ POBIERZ CASE (pierwszy z brzegu wprost do wsadu)
  + 🚀 ROZPOCZNIJ ANALIZĘ (obie strony naraz: chudy przez styk, wsad v11 do schowka — po cegle
  autologowania wklei go „ręka robota"; RURA /v11/ ZAUWAŻONA i podpięta: ramka idzie przez naszą
  domenę, gdy V11_UPSTREAM ustawione — dzięki!). (3) odrzuty niosą CAŁĄ sesję: rekord z pełną
  rozmową chudego, listy lekkie, „Cała sesja" dociąga wsad+rolkę+rozmowę (`/api/porownanie?id=`).
  (4) „chudy długo myśli": u mnie licznik sekund w statusie; sedno po Twojej stronie — pkt (c).
  PROŚBY-STYKI (uzgodnienie przed kodem, bramka 3):
  (a) **daj_operatorow()** w fasadzie (pid/imię, grupa DE/FR/UKPL, tel TAK/NIE, języki) + filtr
  **daj_sprawe(grupa=)** (wybrany operator DE dostaje sprawy TYLKO działu DE — wymóg Sylwii)
  + PRZEPINANIE grup operatorów w WIEŻOWCZYKU (zaplecze, Twój ekran; „czy magda jest operatorem
  de/pl/uk/fr"). Po tych stykach dodaję selektor „wskaż operatora" (kierunek właściciela).
  (b) **policz_chudego bez PARAMETRÓW STARTOWYCH** — dziś system = goły prompt; do testów delegacji
  telefonów (forum → właściwa grupa/język, wymóg Sylwii) chudy musi dostawać blok parametrów jak
  v11. Propozycja: `policz_chudego(wsad, rolka, historia, operator="", grupa="", tryb="")` +
  doklejka `ai.build_start_params` (masz ją gotową).
  (c) **WYDAJNOŚĆ CHUDEGO**: pełny prompt (3220 linii) leci do Vertexa przy KAŻDEJ turze bez cache;
  stary świat miał CachedContent (TTL 60 min). Rozważ cache kontekstu / streaming; model do dyskusji.
- 2026-07-03: [ARTUR] **RURA /v11/ ZBUDOWANA** (`app/wspolne/v11_rura.py`; decyzja właściciela:
  przyciski wszczepiające zamiast policz_v11): kontener v11 serwowany pod NASZĄ domeną —
  `szturchacz.aitossilniki.com/v11/` (HTTP strumieniowo + websocket Streamlita zmostkowany,
  Origin ustawiany na upstream; dokument główny za SSO operatora; aktywna gdy env `V11_UPSTREAM`).
  Pliki kontenera NIETKNIĘTE. Przetestowane na żywym kontenerze: korzeń/HTML/health/statyk/WS ✓.
  PO WDROŻENIU: iframe przełącza się na `/v11/` (env V11_URL=/v11/) → ta sama domena → **STYK DLA
  SYLWII GOTOWY: ręka robota** (toolbar „wskaż operatora" + „pobierz case" może pisać do okna v11
  JS-em: autologowanie na ekranie logowania + wklejenie wsadu we wsad odwrotny — zero zmian w v11).
- 2026-07-03: [SYLWIA] **AWARIA NA PRODUKCJI: „Błąd sieci." przy POLICZ CHUDEGO (sprawa 381994)
  — diagnoza + utwardzenie.** Sylwia dostała „Błąd sieci." po przeliczeniu chudego na żywo.
  Z kodu wynika: to NIE był JSON z silnika (te zawsze przechodzą jako czytelne 502) — serwer
  ZERWAŁ połączenie albo odpowiedział surowym 500 bez JSON-a, czyli awaria NA USŁUDZE. Najbardziej
  prawdopodobne (do sprawdzenia w LOGACH — Twój pas): (a) pierwsza rozgrzewka Vertexa na tej
  rewizji — leniwy import bibliotek + inicjalizacja przy małym RAM → zabity kontener (szukaj
  „container terminated" / OOM); (b) łańcuch retry VertexProvider dłuższy niż timeout usługi;
  (c) uprawnienia SA szturchacza do Vertex (aiplatform.user) — choć to powinno dać JSON 502.
  MOJA STRONA (dołożone do PR `bestchudy/uwagi-operatorki`): komunikaty rozróżniają teraz
  „połączenie zerwane (restart/timeout)" vs „HTTP <kod> bez JSON-a" (operator poda Ci konkret),
  a wszystkie wywołania fasady mają pas bezpieczeństwa (żaden wyjątek nie wyjdzie jako surowy 500).
  PROŚBA DODATKOWA: w `styki.policz_chudego` po `system = deps.active_prompt_text()` dołóż
  `if not system.strip(): return {"ok": False, "message": "Aktywny prompt niedostępny…"}` —
  gdy prompt_url z panelu padnie bez cache, chudy policzyłby dziś BEZ promptu (cichy śmieć).
- 2026-07-03: [SYLWIA] **UWAGI OPERATORKI z pracy na żywym ekranie** (PR `bestchudy/uwagi-operatorki`):
  (1) OD RĘKI (mój pas): podgląd sklejki OTWARTY domyślnie („najlepszy obraz sprawy" — Sylwia),
  pole rolki schowane za rozwijką (rzadko potrzebne). Werdykty i „Wyślij do silnika" — ocenione OK.
  (2) **PROŚBA DO ARTURA — PROMPT CHUDEGO NA v1_11:** Sylwia zgłasza jako błąd, że chudy liczy na
  „v1_9 (wbudowany)" (fallback `deps.active_prompt_text`). Decyzja zespołu 2026-06-30 = v1_11.
  Panel przyjmuje `prompt_url` — wskaż plik v1_11 (jest w repo: `kontener_v11/szturchacz_vnext_v1_11.txt`)
  albo dołóż go jako wbudowany (Twoje pliki: app/prompts + panel).
  (3) **DO DECYZJI WŁAŚCICIELA — LEWA STRONA PORÓWNYWARKI:** Sylwia po pracy na żywo: miniatura
  streamlita w ramce się NIE nadaje (to stary ekran, z którego rezygnujemy) — lewa strona ma być
  pusta jak prawa, wsad ZAŁĄCZANY dla v11 tak samo jak dla chudego, a w panelu ma się pojawiać
  ROZWIĄZANIE sprawy od v11. To odwraca doprecyzowanie właściciela (iframe + KOPIUJ WSAD), więc
  NIE koduję bez zgody (bramka 4). PROPOZYCJA WIERNA DUCHOWI as-is: wywołać prompt v1_11 DOKŁADNIE
  tak, jak robił to STARY AUTOPILOT w starym Wieżowcu (system = prompt v1_11 + PARAMETRY STARTOWE,
  wsad jako wiadomość user, temperatura 0.0) — to ścieżka ISTNIEJĄCA w starym świecie (autopilot
  liczył v11 bez ekranu od zawsze), nie przepisywanie silnika. Kontener v11 ZOSTAJE (produkcyjna
  praca + wzorzec); ramka w porównywarce znika albo zostaje jako opcja. WYMAGA STYKU po stronie
  Artura: `policz_v11(wsad, historia)` w fasadzie (jak `policz_chudego`, ale system = v1_11 z pliku
  w repo zamiast aktywnego promptu panelu). Wyjścia obu stron bez zmian za zaworem/klikiem.
  Właściciel klika; po zgodzie spinam lewą stronę w jeden wieczór.
- 2026-07-03: **WŁAŚCICIEL o lewej stronie porównywarki (odpowiedź na uwagi operatorki):**
  propozycja `policz_v11` ODRZUCONA — pliki wersji streamlitowej pozostają NIETYKALNE, ramka
  z kontenerem v11 ZOSTAJE. Kierunek zamiast tego: **przyciski NAD oknami obu silników**:
  „wskaż operatora" i „pobierz kolejny case" — oba parametry WSZCZEPIANE do OBU stron: do chudego
  wprost (styk), do v11 W RAMCE bez zmiany jego kodu — przechwycenie ekranu logowania (autologowanie
  wskazanym operatorem) i wklejenie wsadu we wsad odwrotny v11, natywnie, „jak ręka robota" —
  cel: obie strony mają porównywalną liczbę kliknięć. UWAGA TECHNICZNA (strona Artura): żeby nasz
  przycisk mógł pisać do okna v11, przeglądarka musi widzieć oba okna jako jedną stronę →
  kontener trzeba przepuścić przez naszą domenę (proxy po stronie skrzynki, pliki v11 nietknięte);
  do wyceny/decyzji jako następna cegła.
- 2026-07-03: [ARTUR] Prośba (2) z uwag operatorki ZROBIONA: **domyślny prompt silnika = v1_11**
  (wbudowany, kopia 1:1 z kontener_v11 — tam źródło; panel dalej może przełączyć na v1_9/chudy/URL).
  Etykieta panelu pokazuje „v1_11 (wbudowany)". Wejdzie na serwer przy najbliższym deployu.
- 2026-07-03: [SYLWIA] **NICKI KOPERTY — ROZSTRZYGNIĘTE (bez kapitalizacji):** decyzja SYLWII
  (właścicielki procesu, pracuje z v11 codziennie): v11 przyjmuje dziś komentarze z nickami
  MAŁYMI literami normalnie („Pominięto komentarze od:" nie występuje przy zwykłych sprawach) —
  praktyka produkcyjna silniejsza niż litera reguły L761. Zostaję przy surowych nickach 1:1
  z panelu (`Dodał: magda`); propozycja kapitalizacji ODŁOŻONA jako plan awaryjny — gdyby na
  porównywarce v11 zaczął raportować pominięcia, włączam ją jedną linijką (odwracalne).
  `kto_panel` niepotrzebne. Próbki COP# przyjęte: moja warstwa przekazuje treść nietkniętą
  (w tym jednolinijkowe COP# jak z próbek). Dzięki za `re.ASCII` — obie prośby B3 zamknięte.
- 2026-07-03: **KRZYSIEK BIERZE CAŁY BACKLOG BRAMY (5-7 dni):** message-id+timestamp źródła
  (WA i email), kierunek IN/OUT, załączniki WA+IMAP(+eBay po naszym TAK), statusy jako endpoint
  PULL (nasz follow-up: poller), BUFOR niedostarczonych + ponowienia N dni (potwierdził: dziś
  fire-and-forget!), subskrypcja per-kanał, HMAC podpis payloadu (nasz follow-up: weryfikacja),
  kształt pusha na piśmie (→ kontrakt wem-v1 w parserze), challenge po handshake'u, eBay sender-id
  do sprawdzenia (nasze próbki: NIE MA go — odpisaliśmy z dowodem). NASZE follow-upy po ich
  wgraniu: (a) parser wem-v1 (id/ts/kierunek/załączniki→GCS), (b) dead-letter z 200→5xx (niech
  ATA ponawia), (c) weryfikacja HMAC, (d) poller statusów, (e) przepięcie WA na PROD + ubicie
  subskrypcji DEV. Odpowiedzi na jego 4 pytania — wysyła właściciel (gotowiec na Biurku).
- 2026-07-03: [ARTUR] Prośba z PR #6 ZROBIONA: `koperta.kiedy` niesie teraz czas
  (`RRRR-MM-DD HH:MM`, jak panelowe `O:`). Nieaktualna notka o `re.ASCII` — było już zrobione
  wcześniej (commit d358f6e), Twoja gałąź powstała chwilę przed nim. Kontrakt KOPERTY uznaję
  za DOMKNIĘTY po Twojemu (lowercase, próbka produkcyjna górą).
- 2026-07-03: [SYLWIA] **KOPERTA ZWERYFIKOWANA na próbce produkcyjnej** (dostarczyła Sylwia —
  właścicielka procesu; PR `bestchudy/koperta-format`). Prośba (1) z wpisu B3 ZAMKNIĘTA:
  składanie koperty poprawione na odbicie panelu 1:1 — nagłówek `Komentarze`, blok =
  `Dodał: <nick>` / treść surowa / `O: <data>`, bloki bez pustych linii. Pytanie o wielkość
  liter ROZSTRZYGNIĘTE: realne nicki paneli są lowercase (`marlena_b`, `emilia`, `magda`) i tak
  pracują dziś z v11 — zero mapowania. SEMANTYKA od Sylwii do kontraktu: komentarze dają KONTEKST
  i obraz sprawy, WYZNACZNIKIEM stanu jest TAG w karcie (spójne z hierarchią v11). Drobna prośba
  do Artura (opcjonalna, wierność 1:1): `koperta.kiedy` z czasem (`RRRR-MM-DD HH:MM` — panel
  pokazuje `O: 2026-06-10 11:12`, feed tnie do samej daty). Prośba (2) — `re.ASCII` w podajniku —
  nadal otwarta.
- 2026-07-03: [ARTUR] **ODPOWIEDŹ na 2 prośby weryfikacyjne Sylwii (B3):**
  (1) **WIELKOŚĆ LITER — obawa POTWIERDZONA, z dowodem:** `Comment.userName` jest w bazie
  KONSEKWENTNIE lowercase (top: marlena_b, marta_p, emilia, iwona, …, oliwia, klaudia, magda —
  zero form kapitalizowanych), a [OPERATORS] w prompcie ma nicki z WIELKIEJ (Emilia|Oliwia|Magda|
  Ewelina|Klaudia) + reguła L761 CASE-SENSITIVE → nick prosto z bazy w `dodał:` odpada u v11.
  W starym świecie działało, bo operator kopiował kopertę Z PANELU, a panel kapitalizował
  wyświetlane nicki. PROPOZYCJA STRONY SKRZYNKI: `koperta[].kto` zostaje SUROWĄ prawdą z bazy
  (kontrakt danych), a warstwa składania `dodał:` (Twoja `zloz_koperte`) kapitalizuje pierwszą
  literę (magda→Magda; oliwia_m→Oliwia_m i tak = szum spoza listy, poprawnie). Potwierdź albo
  zaproponuj odwrotnie (mogę oddawać `kto_panel` gotowe) — Twoja warstwa, Twój wybór.
  UWAGA dodatkowa z sondy: w bazie piszą też autorzy SPOZA listy [OPERATORS] (marlena_b, marta_p,
  kasia_k, oliwia_m, klaudia_k…) — filtr celowo potraktuje ich jako szum („Pominięto komentarze
  od:"), to zachowanie zgodne ze starym światem.
  **Próbki COP# verbatim do porównania token-w-token** (z bazy, deleteCom=0):
  a) austaush=485569, userName='kasia_k', 2026-07-01: `COP# USTALENIA: FORUM_ATOM=czekam_potw_kuriera|ACTIVE_FORUM=ATOM|ATOM_CEL=AUTOS_KURIERZY|ATOM_USER=TEAM_ATOMOWKI|nowy_adres_odbioru:c/ibaizabal_50_bajo_48960_galdakao_vizcaya|tel_wyczerpany:jezyk=es.obiegi=2/2|aktywny_kanal=mail|towar_typ=skrzynia|kurier_przewoznik=fedex|zdjecie_fedex_potwierdzone=18.06|termin_odbioru=03.07|BRAKUJE:potw_atomowek;bump=0`
  b) austaush=464737, userName='oliwia', 2026-06-03: `COP# PZ: PZ9 COP# DRABES: mail[6]/wysl@27.05 | tel[1]/odeb@07.05 COP# USTALENIA: PZ9 | NIE KONTAKTOWAĆ KLIENTA - PROBLEM WEWNĘTRZNY. (…) | forum_sped=zablokowana | szturze_wsparcie=TAK | (…)`
  (2) **`re.ASCII` DOŁOŻONE** w `_DATA_RE` i `_ZAM_RE` podajnika + test (cyfry arabskie odpadają
  na walidacji, nie w SQL). Dzięki za wyłapanie.
- 2026-07-03: [SYLWIA] **B3 SPIĘTE** (PR `bestchudy/feed-b3`): porównywarka pobiera sprawy przez
  `styki.daj_sprawe` — przycisk „Z wieżowczyka (najnowsze)" + „Po numerze"; `wsad_panel` wchodzi
  1:1 (tag w środku — pole TAG czyszczone, bez dubla), `koperta` składana blokami wg filtra
  autorów v11: `dodał: <nick>` (nick SAM w linii, bez transformacji wielkości liter), data
  w OSOBNEJ linii, treść surowa 1:1 (żeby `COP# PZ:` zostało pierwszym tokenem swojej linii);
  pusty autor → `dodał: ?` (v11 zaraportuje pominięcie zamiast cichej utraty). Wciągnięcie nowej
  sprawy ZERUJE stan chudego i werdykty (uczciwość rekordu). DWIE PROŚBY WERYFIKACYJNE do Artura
  (z przeglądu adwersarialnego, przed pierwszą pracą na żywo): (1) próbka JEDNEJ realnej koperty
  z panelu (jak ją widzi operator) do porównania token-w-token z moim składaniem + potwierdzenie
  WIELKOŚCI LITER `Comment.userName` vs [OPERATORS] w prompcie (filtr jest case-sensitive — jeśli
  baza daje lowercase, sprawy bez COP# polecą w SELF-CHECK ERROR); (2) w `_ZAM_RE` podajnika
  dołóż `re.ASCII` (bez tego \d łapie cyfry Unicode → błąd SQL zamiast walidacji; u mnie już jest).
- 2026-07-03: [ARTUR] **FEED GOTOWY — Sylwia: spinaj B3.** Wieżowczyk przerobiony pod wzorce
  produkcyjne (PLAN.md §5.1): pełny widok `v_austachStatus` (kaCountry=pełna nazwa kraju, etapy
  stage/active/date, doręczenia ua_ups_*, lindexy, listy ua_ups_TrackingNr+zwne, EbayLogin/buyerNick)
  + pole **`wsad_panel`** (układ 1:1 wg wzorców — ZWERYFIKOWANE na żywej bazie: sprawy 381879
  i 381865 odtworzone TOKEN W TOKEN, łącznie z tagiem) + pole **`koperta`** (lista {kto,kiedy,tresc}
  z SZTURCHACZ.dbo.Comment po austaush; surowa — formatowanie COP# po stronie semantycznej).
  `suchy_wsad` bez zmian (lista). UWAGI: słownik kurierów EMPIRYCZNY {1:UPS, 5:FEDEX} — inne
  wartości lecą surową liczbą, uzupełniać gdy wypłynie nowy; „Bieżący etap" przy wysłanym mailu =
  `Mail wysłany <data>` (wzorce miały tylko wariant „Nie wysłano żadnego maila" — potwierdzić
  przy pierwszym takim case). WDROŻONE na serwer (rewizja szturchacz-00030) — styk daj_sprawe oddaje wsad_panel+koperta NA ŻYWO.
- 2026-07-03: [ARTUR] **SPLIT VIEW NA ŻYWO** — trzy klocki koordynatora dowiezione: (1) sekrety
  v11 w Secret Managerze (v11-firebase-creds = SA starego projektu roboczy-bez-limitu,
  v11-forum-bearer; odczyt dla SA Cloud Run — autoryzacja właściciela), (2) **kontener-v11 stoi**:
  https://kontener-v11-355337266255.europe-west1.run.app (Streamlit as-is, py3.11; fix pinu
  google-genai 1.47→1.66 w constraints — warstwa odpałki, silnik nietknięty), (3) CSP `frame-src`
  wyłącznie dla domeny kontenera (env V11_URL; pusty = ramki zablokowane) + V11_URL na szturchaczu.
  Rewizje: szturchacz-00029, kontener-v11-00001. Porównywarka pod /bestchudy za SSO.
- 2026-07-02: [SYLWIA] **Odpowiedź strony Sylwii w negocjacji kontraktów** (sekcja NEGOCJACJA wyżej):
  wzorzec `wsad_panel` linia-po-linii dostarczony (PLAN.md §5), review sygnatur `styki.py` wykonany —
  cztery funkcje POTWIERDZONE (+prośba o pola `wsad_panel`/`koperta` w FEED i piąty styk pamięci
  forum), propozycja pamięci wspólnej = kolekcja kontenera (chudy dostosowany do v11). PLAN.md
  przerobiony pod decyzje właściciela: kontener AS-IS (`kontener_v11/`, odpałka bez dotykania
  logiki — §3), split view z ramką i „KOPIUJ WSAD" (§4), zawór tylko chudy. Obie strony dostają
  IDENTYCZNĄ sklejkę wsadu (uczciwość porównania). Następny krok pasa: faza B1 (kontener lokalnie).
- 2026-07-02: **WŁAŚCICIEL rozstrzygnął bramki PLAN.md §8** (uwaga: pkt 1 INACZEJ niż rekomendacje
  OBU stron — decyzja właścicielska, obowiązuje):
  1. **Kontener v11 = AS-IS, nie port.** Sesja Sylwii bierze pliki apki streamlitowej + prompt v11
     i umieszcza je w kontenerze tak, żeby odpalały się CZYSTO, bez symulacji. Pliki najlepiej
     NIETKNIĘTE (przeniesienie 1:1); w najgorszym razie zmiana WYŁĄCZNIE fragmentów odpowiedzialnych
     za odpałkę (start/port/sekrety) na cloudrunowe. ŻADNEJ ekstrakcji/przepisywania logiki.
     Powód właściciela: „przepisany v11" = ryzyko symulacji zamiast wzorca (dryf).
  2. **Wpisy v11 na forum = NATURALNE.** Zero bramek, zero zmian w prompcie i w apce v11 — to jest
     PRODUKCYJNY operator: przy okazji testów chudego wykonywana jest bieżąca realna praca (na v11
     lub chudym). Konsekwencja: ZAWÓR skrzynki (styki.wyslij) dotyczy WYŁĄCZNIE chudego — chudy
     w cieniu (sucho→realne per silnik), v11 na żywo jak zawsze.
  3. **FEED: opcja (a) potwierdzona** — rozbudowujemy wieżowczyk (pas Artura: `wsad_panel` FORMAT 2
     co do znaku + KOPERTA z Comment).
  4. **Pamięć forum: WSPÓLNA** — szczegóły wykonania po stronie Sylwii.
  5. **Quota Vertex: bez rotacji** (jeden projekt na start).
  KONSEKWENCJE PRZYJĘTE (dla planu Sylwii — do przerobienia §2/§3 PLAN.md w jej PR): przy as-is
  porównywarka NIE woła v11 przez API (Streamlit to UI). DOPRECYZOWANIE WŁAŚCICIELA (2026-07-02):
  **split view w JEDNEJ karcie, nie osobne okna** — lewa strona = kontener v11 osadzony w RAMCE
  (iframe) wewnątrz ekranu bestchudy; prawa = chudy. Przepływ wsadu: **chudy pobiera wsad SAM**
  (styk daj-sprawę/wieżowczyk), obok przycisk **„KOPIUJ WSAD"** (do schowka) → operator wkleja
  do v11 w ramce — logika v11 NIETKNIĘTA. Warunki techniczne (podział): (a) kontener pozwala na
  osadzanie — Streamlit wspiera iframe/embed, ewentualne flagi serwera = ODPAŁKA, nie logika
  [strona Sylwii]; (b) nasza apka musi wpuścić ramkę z domeny kontenera w CSP (`frame-src`) —
  JEDNA linijka we wspólnym pliku, robi koordynator przy wpięciu [strona Artura]. Werdykty/
  odrzuty/kalendarz zbiera bestchudy. Długofalowo nic nie tracimy: automatem będzie CHUDY (za
  zaworem), v11 jest WZORCEM-nauczycielem, nie przyszłym automatem. Lokalizacja plików kontenera:
  domyślnie katalog `kontener_v11/` w tym repo — chyba że strona Sylwii zgłosi inaczej.
- 2026-07-02: [SYLWIA] **FAZA A WYKONANA: rozpoznanie + plan kontenera v11** → `app/bestchudy/PLAN.md`
  (gałąź `bestchudy/rozpoznanie-plan-v11`). Rozpoznanie 7-agentowe z adwersarialną weryfikacją
  (silnik v11 + prompt v1_11 + main tego repo + stary Wieżowiec, cytaty plik:linia).
  REKOMENDACJA: kontener v11 = PORT logiki 1:1 do małego FastAPI (nie Streamlit as-is) — „wołany
  przez apkę" wymaga API, a bezpiecznik na FORUM_WRITE i tak wymusza zmianę kodu; prompt 1:1 jako
  plik + env override; świadome odstępstwa wylistowane w PLAN.md §2. STYK FEED — strona Sylwii
  NIE potwierdza formatu 1:1: `suchy_wsad` identyfikuje sprawę i niesie tag (snapshot OK), ale NIE
  zastępuje WSADU PANEL dla v11 — braki m.in. Delivered (KRYTYCZNE, blokada kontaktu), INDEX,
  listy przewozowe, TYP_KURIERA, LOGIN/NICK eBay, nick sprzedawcy, KOPERTA/COP# (bez niej sprawy
  bez tagu bootstrapują) — pełna tabela + 2 opcje kontraktu w PLAN.md §5; porównywarka startuje
  na ręcznym wklejaniu, więc fazy B to nie blokuje. Pytania-bramki do właściciela/koordynatora:
  PLAN.md §8 (m.in. gdzie kod kontenera; kto wykonuje wpis forum po zielonym; pamięć forum;
  dostęp push dla konta sylwiaautossilniki — dziś tylko odczyt, a regulamin każe pushować często).
- 2026-07-02: [ARTUR] **WIEŻOWCZYK v1 zbudowany** (kafelek w zapleczu): surowy wsad spraw z bazy
  franciszkańskiej przez WSPÓLNY silnik (`app/wspolne/klient_baz.py` → db-broker/silnik_baz;
  READ-ONLY, wejścia regex-whitelist). Źródło wg atlasu: `STEEPC.dbo.v_austachStatusProsty`
  (MASTER spraw) + `SZTURCHACZ.dbo.ItemsTag` (tag, most DokId=austauch_id, DokTyp=7).
  Zapytanie SPRAWDZONE NA ŻYWEJ bazie (tunel dev). Format `suchy_wsad` = „NrZam: … | kraj |
  rodzaj | … | tag: …" — DO PRZYPIĘCIA w styku FEED z bestchudy (strona Sylwii potwierdza).
  Prod: wymaga env `ONPREM_DB_BROKER_URL` na szturchaczu (invoker już nadany).
- 2026-07-02: **ZATWIERDZONE przez właściciela**: mapa ekranów (kafelek Szturchacz=PRACA/Sylwia,
  kafelek Wieżowiec=ZAPLECZE/Artur, zręby streamlitowe do rozbiórki, backup=Streamlit) + model
  autonomii (4 bramki) + Rozmowy jako zakładka zaplecza + Sylwia startuje świeżą sesją (Fable 5).
  Archiwum WEM scalone do main; gniazdo `app/bestchudy/` postawione przez koordynatora
  (Sylwia NIE dotyka wspólnych plików — wypełnia swój katalog).
- 2026-07-02: Rozpis bestchudy = moduł WEWNĄTRZ szturchacz-cloud (5 pkt w sekcji PODZIAŁ wyżej);
  wcześniejszy pomysł „osobna apka z własnym adresem" WYCOFANY (sprzeczny z „wprowadzić tam").
  Archiwum WEM: zbudowane, czeka na gałęzi `skrzynka/archiwum-rozmow` — scalenie po starcie Sylwii.
- 2026-07-01: **Numery WA są RÓŻNE**: STARY = desktop operatorów (chudy bez dostępu), NOWY = brama
  WEM (+49 1579 2556775). Plus tej konfiguracji: nowy numer startuje czysty → sprawy pz0 po „dacie x"
  mają archiwum KOMPLETNE od narodzin (brak-backfillu Meta nie boli).
- 2026-07-01: Kontener v11 = pas SYLWII (część bestchudy). Bestchudy = wydzielony moduł (osobne
  pliki, minimum ingerencji we wspólne). Artur bierze ARCHIWUM bramy (zapis + thread_id przy zapisie).
- 2026-07-01: [ARTUR] Trwałość odbioru WA → gałąź `brama/trwalosc-odbioru` (PR do scalenia):
  dead-letter (`app/wspolne/deadletter.py`) + retry zapisu + `rekord_wyslany`/`dodaj_wyslane`
  (kierunek=out w archiwum). NASTĘPNA CEGŁA: klient wysyłki przez bramę (JWT + `/messages/send`)
  wołający `dodaj_wyslane` — to STYK z automatem Sylwii (automat będzie tym wysyłał). Asks do
  Krzyśka (pola id/ts/media/statusy/retry) = gotowe, właściciel wysyła.
- 2026-06-30: Kierunek = AUTOMAT (skrzynia IN-OUT), nie ręczny operator. Faza 1 = bramka
  zielony/czerwony. Akcje z ryzykiem (kurier, wysyłka do klienta) gated NAJDŁUŻEJ.
- 2026-06-30: Push-back-do-woreczka z komentarzem = ODŁOŻONE (otwarta decyzja, NIE budujemy teraz).
- 2026-06-30: Prompt = **v1_11** (najnowszy, w szturchacz-test), NIE v1_9.
- 2026-06-30: Repo apki = `szturchaczysko-cpu/szturchacz-cloud`. Stary streamlit (`szturchacz`,
  `szturchacz-test`, `wiezowiec-test`) = TYLKO read-only referencja.

## KONWENCJE (żeby nie robić różnie)
- **reguły→kod (twardo-na-ryzyku):** kwoty/kurierzy/terminy w KODZIE, decyzja „czy" w AI.
- Sekrety NIGDY w repo (`.gitignore` chroni `.env`/`.venv`/`data/`). Bezpieczniki: `FORUM_MODE=sucho`, `AUTOPILOT=stop`.
- Motyw: tokeny + klasy z `theme.css`, zero własnych kolorów.
- Patche: gałąź → PR → koordynator scala do `main` → koordynator wdraża centralnie.
  Vibecoder NIE używa `gcloud`/deployu/proda.
- Małe pliki, logika osobno od widoku.

## OTWARTE PYTANIA
- Schemat „propozycja automatu" + konsumpcja przez bramkę operatora (kontrakt styku).
- Schemat/panel odrzutów + komentowanie; push-back-do-woreczka — czy/jak.
- Brama DEV/PROD: konsolidacja W DRODZE — Krzysiek robi subskrypcję per-kanał; po wgraniu
  przepinamy WA na PROD i wyłączamy subskrypcję DEV (koniec duplikatów maili).
- ✅ eBay ODBLOKOWANY (2026-07-02, Krzysiek): webhook eBay jest per APLIKACJA (nie per konto);
  przepięli w bazie endpointy wszystkich kont na wspólny — ruch wszystkich kont ma płynąć, nowe
  konta będą działać od razu. ZOSTAJE: push eBay niesie TYLKO `body` (bez buyerNick/konta/id/ts)
  → po kliencie „nieprzypisane"; ratuje agregacja po nrZam. Prośba o pola dopisana do listu.

## REGULAMIN WSPÓŁPRACY (dwie sesje, zero patchera Pulpitu — wszystko na Gicie)
AUTONOMIA I BRAMKI (zatwierdzone 2026-07-02): Sylwia jedzie AUTONOMICZNIE wewnątrz swojego pasa
(rozpis bestchudy) — właściciel NIE zatwierdza pracy w trakcie. Bramki właściciela/koordynatora
są CZTERY: (1) każde scalenie do main, (2) każde wdrożenie, (3) każdy STYK (uzgodnienie tu przed
kodem), (4) WYJŚCIE POZA ROZPIS — sesja ma wtedy STANĄĆ i zgłosić, nie improwizować.
Przełomy MELDOWANE, nie bramkowane: kamienie milowe dopisuj do DECYZJE (właściciel podgląda).
MODELE SESJI: model wybieramy na starcie sesji i jedziemy nim do końca; zmiana modelu = NOWA
sesja (tanie — kontekst żyje w repo, nie w oknie). Sesja Sylwii: świeża, na Fable 5.
ROLE:
- **Koordynator = Artur.** Scala PR do `main`, ustala kolejność, **deployuje (TYLKO z `main`)**. „Kto akceptuje".
- **Dominujący** = kto w DANYM temacie ma priorytet (jego patch wchodzi pierwszy). Rola ZMIENNA,
  wyznacza ją koordynator (wpisem tutaj). NIE to samo co koordynator.
PĘTLA:
1. Każdy pracuje na GAŁĘZI (nie `main`), **pushuje CZĘSTO** → druga strona widzi Twój stan (Twój branch).
2. Zmiany (kod ORAZ kontrakty/briefy) → **PR**. Druga strona zatwierdza review = obustronne potwierdzenie.
3. Koordynator scala PR do `main` w kolejności (dominujący pierwszy).
4. Poboczny po scaleniu dominującego → skill **`przeszczep-patch`** (nakłada swój branch na nowy `main`,
   łapie konflikty LOGICZNE, pokazuje do akceptacji) → jego PR.
5. **Deploy WYŁĄCZNIE z `main`, przez koordynatora.** Nigdy z rozjechanego lokalnego drzewa.
KONTRAKTY: styk dwóch pasów → doc w repo, każdy wypełnia SWOJĄ stronę przez PR, „UZGODNIONE" dopiero
po obu zatwierdzeniach. Dopóki nie uzgodnione — nikt nie koduje swojej strony.
**STATUSY KONTRAKTU (obowiązkowy nagłówek każdego styku; wpis BEZ statusu = SZKIC):**
`SZKIC` (propozycja jednej strony — oglądaj, komentuj, NIE KODUJ) → `W KOMENTARZU` (druga strona
dopisała kontrę/uwagi) → `UZGODNIONE` (obie strony potwierdziły) → `ZATWIERDZONE` (właściciel
kliknął FINAL) → dopiero **KOD**.
**GŁOS CZŁOWIEKA, nie sesji:** komentarz/uzgodnienie liczy się dopiero, gdy sesja POKAZAŁA szkic
swojemu człowiekowi (prozą/quizem — wersję „po ludzku" autor szkicu dostarcza w treści styku)
i wpis zawiera JEGO zdanie (np. „Sylwia widziała: pasuje / uwagi: …"). Analiza samej sesji to
materiał pomocniczy, nie strona kontraktu. Kodowanie przed ZATWIERDZONE = złamanie regulaminu — nawet gdy
szkic wygląda jak gotowa specyfikacja.
CZUWANIE (zalecane w OBU sesjach): warta wg skilla **`czuwanie-repo`** (team-skills) — sesja co
~20 min po cichu sprawdza repo i AKTYWNIE wybija człowiekowi quiz, gdy druga strona zostawiła coś
do decyzji (koordynator: PR-y/wpisy vibecoderów; vibecoder: odpowiedzi w koordynacji + ruch `main`
→ przebazowanie). Człowiek uzbraja słowami „włącz czuwanie".
**REJESTR WART (jedna warta na repo! — quiz wyskakuje w oknie sesji, która pyta):**
- `szturchacz-cloud` → sesja KOORDYNATORA Artura (okno skrzynki). INNE SESJE: nie zbroić warty
  na tym repo (dubel = quizy w złych oknach); sesja serv+pulpit pilnuje repo `pulpit`.
- Każde pytanie warty zaczyna się od identyfikatora, np. „[WARTA szturchacz-cloud — okno koordynatora]".

## WSKAŹNIKI
- `CLAUDE.md` — stos, struktura, bezpieczniki + blok „START KAŻDEJ SESJI" (wczytuje się SAM
  przy starcie sesji w folderze repo i odsyła tutaj — brief dociąga się automatycznie,
  nic się nie wkleja; jedyny ręczny moment = pierwsze sklonowanie repo).
- Referencja streamlitowa (READ-ONLY): repo `szturchacz-test` (prompt v1_11), `wiezowiec-test`.
