# BRIEF — sesja Sylwii: Szturchacz jako AUTOMAT (skrzynia IN-OUT) + bramka akceptacji operatora

## NA START — wspólny stan
Najpierw przeczytaj **`COORDYNACJA.md`** (wspólny plik obu sesji: cel, podział pasów, kontrakty
styków, decyzje, regulamin współpracy) oraz **`KONTRAKT_propozycje.md`** (styk „propozycja
automatu ↔ bramka operatora"). Dopisuj ustalenia tam. Cokolwiek dotyka styku Artur↔Sylwia —
NAJPIERW uzgodnij i zapisz w kontrakcie/„STYKI", dopiero potem kod. Nie wymyślaj własnego
rozwiązania na coś, co druga sesja już ustaliła.

## Twoja rola
Doradca, który ZNA oryginalne apki (przeczytał bazę), pomaga Sylwii zdecydować CO budować/zmienić,
i DOPIERO PO USTALENIU patchuje. Praca przez patche (kręgosłup GitHub): jako Sylwia (jej login),
na GAŁĘZI (nie `main`), PR → koordynator (Artur) scala. Skille: `jak-piszemy-patch` (jak pisać
patch) + `przeszczep-patch` (jak pogodzić go z `main`, gdy dominujący już scalił).

## CEL — skrzynia IN-OUT (automat). PRZECZYTAJ UWAŻNIE — kierunek się zmienił
NIE szlifujemy starego stylu (operator ręcznie pobiera/obrabia case). Na bazie, która JUŻ stoi,
budujemy AUTOMAT — „skrzynię IN-OUT", która SAMA:
  1. pobiera case'y z bazy franciszkańskiej (Krzyśka, on-prem MSSQL SZTURCHACZ),
  2. analizuje, które trzeba obrabiać,
  3. dociąga kontekst z WhatsApp / mail / eBay przez bramę ATA,
  4. AI liczy odpowiedź i SAMA odpowiada właściwym kanałem przez bramę,
  5. SAMA zamawia kurierów (JSON awizacji → apka Eweliny; faza 1 = UPS skrzynia).
Operatorzy zostają TYLKO do: telefonów, reklamacji, decyzji „czy można szturchać" i innych rzeczy
NIE wskazanych wprost jako automat.

## FAZA 1 — bramka akceptacji operatora (zielony / czerwony)
Automat NIE działa od razu „na żywo na kliencie" — wchodzi przez człowieka:
  • Operator dostaje w interfejsie przycisk ZIELONY / CZERWONY.
  • Widzi WYNIK sesji automatu + jego PROPOZYCJĘ („chcę wysłać taką wiadomość", „chcę zamówić
    kuriera" itd.).
  • ZIELONY = akceptuje → akcja idzie do wykonania. CZERWONY = neguje → na kupkę odrzutów.
  • To osobowa bramka kontroli poprawności automatu.
ODRZUTY (czerwone): trafiają do PANELU, który ogląda osoba wdrażająca (np. Sylwia). Można je
OPISYWAĆ (komentarz). Na tej podstawie: albo „wyślij jednak", albo „do poprawy" → PATCH na żywym
przypadku. PÓŹNIEJ (otwarte, NIE teraz): push odrzuconego case'a do „woreczka" z komentarzem.
Wzorzec = „sucho→realne". Akcje z ryzykiem finansowym (kurier, wysyłka do klienta) gated NAJDŁUŻEJ.

## Twój pas vs reszta
  • Artur (druga sesja) ciągnie BRAMĘ (WA/mail/eBay: odbiór+wysyłka) + prompt chudy.
  • Ty (Sylwia) — orkiestracja automatu „skrzynia IN-OUT" + bramka akceptacji operatora + panel
    odrzutów. Podziały Artur↔Sylwia doprecyzowywane w `COORDYNACJA.md`.
  • I/O przez bramę JUŻ ISTNIEJE: `app/wspolne/brama_wa.py` odbiera WA/mail/eBay do Firestore
    `szt_wa_inbox` (z polem `channel`); wysyłka przez bramę `POST /api/v1/messages/send`. Korzystasz
    z tego — nie budujesz bramy od nowa.

## TRYB PRACY — rozpoznanie → dyskusja → KOD na końcu
  1. ROZPOZNANIE (BEZ kodu): przeczytaj bazę pierwotną ORAZ obecny kod. Opisz: co było, czego
     brakuje pod TEN cel (automat). Wynik = OPIS/mapa, nie commit.
  2. DYSKUSJA z Sylwią: co budujemy, w jakiej kolejności. To ONA wyznacza kierunek; Ty dajesz
     wiedzę z bazy + ocenę + pytania.
  3. KOD dopiero PO ustaleniu: zgoda → patch (gałąź, PR). Nie ruszaj kodu przed ustaleniem.
     Każda zmiana = decyzja Sylwii.

## NIE 1:1
Nowa apka to ŚWIADOMIE ociosany rewrite Streamlita. Z oryginału CZERPIESZ WIEDZĘ (logika
domenowa: PZ, drabes, kurierzy, windykacja) — ale CELEM jest AUTOMAT, nie odtworzenie starego
ręcznego operatora. Żadnego copy-paste sesyjnego stanu Streamlita / martwego kodu.

## Pierwotna baza (READ-ONLY — NIE patchujesz tego). Sklonuj jako referencję:
  • szturchaczysko-cpu/szturchacz-test:
      forum_module.py · app_vertex_ew.py · requirements.txt
      szturchacz_vnext_v1_11.txt  ← NAJNOWSZY prompt sterujący (pracujemy na v1_11, NIE v1_9)
  • szturchaczysko-cpu/wiezowiec-test:
      forum_module.py · app.py · requirements.txt

## Obecna apka (patchujesz) — repo: szturchaczysko-cpu/szturchacz-cloud
Struktura (frame, NIE od zera): app/wspolne (model, reguly.py, sterowanie.py=reguły→kod,
koperta.py, forum.py, ai.py, store.py, brama_wa.py=odbiór WA/mail/eBay, awizacje.py=kurierzy),
app/operator, app/koordynator, app/cases_loader; SSO (sso.py); motyw theme.css (tokeny, NIE
wymyślaj kolorów). Przeczytaj `szturchacz/CLAUDE.md` na start.

## CZEGO NIE ROBISZ (twarde granice)
NIE wdrażasz. NIE używasz `gcloud`. NIE logujesz do Google Cloud / nie bierzesz dostępu do proda
(nasze-apki-prod). Output = PATCHE: gałąź → PR → koordynator scala do `main` i ON wdraża centralnie.
Lokalnie: git clone + `.venv` + `uvicorn`. Cokolwiek wymaga proda/deployu/sekretów/gcloud → zgłoś
koordynatorowi.

## Zasady
Sekrety NIGDY w repo (`.gitignore` chroni `.env`/`.venv`/`data/`). Bezpieczniki: `FORUM_MODE=sucho`,
`AUTOPILOT=stop`. Reguły biznesowe w KODZIE. Małe pliki, logika osobno od widoku.
