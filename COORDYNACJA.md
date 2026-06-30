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
- **Propozycja automatu ↔ bramka operatora:** ⬜ DO USTALENIA — gdzie automat zapisuje propozycje
  („chcę wysłać X", „chcę zamówić kuriera"), jaki schemat, jak bramka czyta/akceptuje(zielony)/
  odrzuca(czerwony). **Uzgodnić TU zanim ktokolwiek zacznie kodować którąś stronę.**
- **Odrzuty (czerwone):** panel + komentarz wdrażającego → „wyślij jednak" / „do poprawy"
  (patch na żywym przypadku). Schemat rekordu odrzutu ⬜ DO USTALENIA.

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

## WSKAŹNIKI
- `szturchacz/CLAUDE.md` — stos, struktura, bezpieczniki.
- Brief Sylwii (cel + tryb pracy) — w czacie / patcher.
- Referencja streamlitowa: repo `szturchacz-test` (prompt v1_11), `wiezowiec-test` (READ-ONLY).
