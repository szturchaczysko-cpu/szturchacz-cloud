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

ŁĄCZNIKI (kontrakt skrzynka↔bestchudy — DOPIĄĆ PRZED kodem, dwustronnie):
1. FEED: bestchudy prosi skrzynkę o „następny case" (wieżowczyk) albo „case po nrZam".
2. SILNIKI: „policz v11 na case" / „policz chudy na case" → wynik każdej strony (ten sam suchy wsad).
3. KANAŁ (chudy): chudy żąda sprawdzenia kanału → skrzynka zwraca rolkę (ODCZYT autonomiczny OK,
   pokazany w oknie); v11 tego nie umie → operator wkleja ręcznie.
4. WYJŚCIE: każda wysyłka (WA/mail/eBay/forum) → skrzynka wykonuje **TYLKO po kliknięciu operatora
   „pozwalam wysłać"** (bezpiecznik POZA promptem); v11 → pokazać treść + do kogo przed publikacją, też bezpiecznik.
5. FORUM: odczyt + memory (ID wpisów), ładowany ZAWSZE gdy sprawa była na forum (jak v11).

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
  - STRONA BRAMKI (Sylwia): ⬜ TODO — jakich pól potrzebuje do renderu zielony/czerwony + panel
    odrzutów + komentarz.
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
- Brama DEV/PROD: WhatsApp leci przez DEV, mail przez PROD — konsolidacja (czeka na Magdę/Krzyśka).
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

## WSKAŹNIKI
- `CLAUDE.md` — stos, struktura, bezpieczniki + blok „START KAŻDEJ SESJI" (wczytuje się SAM
  przy starcie sesji w folderze repo i odsyła tutaj — brief dociąga się automatycznie,
  nic się nie wkleja; jedyny ręczny moment = pierwsze sklonowanie repo).
- Referencja streamlitowa (READ-ONLY): repo `szturchacz-test` (prompt v1_11), `wiezowiec-test`.
