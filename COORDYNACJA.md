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

## PODZIAŁ PASÓW
- **ARTUR** (ta sesja z Claude): BRAMA ATA (WA/mail/eBay — odbiór+wysyłka) + prompt **chudy**.
- **SYLWIA** (jej sesja z Claude): orkiestracja automatu (skrzynia IN-OUT) + **bramka akceptacji
  operatora** (zielony/czerwony) + **panel odrzutów**.
- Granica MIĘKKA — doprecyzowujemy TU. Cokolwiek na styku → zapisz w „STYKI/KONTRAKTY".

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

## DECYZJE (log — dopisuj nowe na górze)
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
- eBay OAuth — zablokowany (zły `state` w linkach Krzyśka → token pod śmieciowym kluczem; do poprawy).

## REGULAMIN WSPÓŁPRACY (dwie sesje, zero patchera Pulpitu — wszystko na Gicie)
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
- `CLAUDE.md` — stos, struktura, bezpieczniki.
- Referencja streamlitowa (READ-ONLY): repo `szturchacz-test` (prompt v1_11), `wiezowiec-test`.
- Brief startowy sesji = wklejany prompt (NIE plik w repo).
