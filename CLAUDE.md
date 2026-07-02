# Szturchacz — kafelek Pulpitu (zwroty/reklamacje)

Apka-kafelek ekosystemu Pulpit. Jeden serwis FastAPI, jedna wspólna kolejka spraw,
dwa widoki nad nią: **operator** (dzień) i **koordynator + autopilot** (noc).

## START KAŻDEJ SESJI (obowiązkowo, zanim cokolwiek zrobisz)
Przeczytaj **`COORDYNACJA.md`** — wspólny mózg sesji Artura i Sylwii: cel, podział pasów,
styki-kontrakty, decyzje, regulamin. Nie wymyślaj rozwiązań na coś, co tam już ustalone.
**Sesja BESTCHUDY (Sylwia):** twój zakres = COORDYNACJA sekcja „PODZIAŁ" (rozpis 5 pkt) —
pracujesz WYŁĄCZNIE w `app/bestchudy/` + kolekcje `bc_*` + kontener v11; wspólnych plików nie
edytujesz; czego potrzebujesz od reszty → styk uzgodniony wpisem w COORDYNACJA, potem kod.
Referencja (READ-ONLY): repo `szturchacz-test` (prompt `szturchacz_vnext_v1_11.txt` — v1_11,
NIE v1_9) i `wiezowiec-test`. Faza 1 = ROZPOZNANIE bez kodu → dyskusja → dopiero patch.
Praca: gałąź (nie `main`) → PR → koordynator (Artur) scala i TYLKO on wdraża.
ZERO `gcloud` / logowania do Google Cloud / dostępu do proda. Lokalnie: `.venv` + `uvicorn`.

## Stos i struktura
- Python + FastAPI + Jinja2 + Firestore (prod) / pliki JSON (lokalnie), wzorzec jak w Pulpicie.
- `app/wspolne/` — model sprawy, reguły domenowe, klient forum, silnik AI, repozytoria.
- `app/cases_loader/` — wsady → sprawy, priorytetyzacja, autopilot (worker).
- `app/operator/` — dzienny ekran pracy operatora (kolejka, czat, TAG, woreczek, tryby odwrotne).
- `app/koordynator/` — panel: wsady, konfiguracja biznesowa, raporty/Diamentoza.
- Małe pliki, jedna sprawa na plik. Logika osobno od widoku.

## Wygląd
Używamy `app/static/theme.css` (tokeny + komponenty), NIE wymyślamy własnych kolorów.
Motyw jest WSPÓLNY dla całego ekosystemu (źródło: team-skills `plugins/pulpit-ekosystem/skills/
motyw-wizualny/assets/theme.css` — aktualizacja: `git pull` w team-skills → kopiuj theme.css).
`theme.css` dołączany PRZED `app/static/app.css`; własny CSS apki = TYLKO layout, na tokenach.
Stylując UI ZAWSZE używaj zmiennych (var(--accent), var(--card)…) i klas bazowych
(.btn, .card/.panel, .text-input, .topbar, .section-title, .status-pill, .chip, .codeblock, .list, .badge).
Zasada: monochrom + JEDEN delikatny akcent (tint/obwódka, NIGDY jaskrawe wypełnienie),
bez podkreślonych przycisków.

## Tożsamość operatora (SSO z Pulpitu)
`app/sso.py::read_operator(request)` → `{pid, label, roles} | None`. To JEDYNY punkt styku.
Weryfikacja JWT (EdDSA) ciasteczka `session` kluczem publicznym Pulpitu dostarczana po stronie
Pulpitu (patrz plan SSO asymetryczny). Lokalnie: `DEV_OPERATOR` w `.env` daje atrapę.
Ekran operatora wchodzi na PROD dopiero, gdy Pulpit przekazuje tożsamość; do tego czasu
autopilot + panel koordynatora mogą działać za bramą Pulpitu.

## Twarde wymagania Cloud Run
Nasłuch na `$PORT`; non-root; dane piszemy do `/tmp` (DATA_DIR), trwałe → Firestore;
sekrety z env/Secret Manager; `.env`/`.venv` wykluczone w `.dockerignore` ORAZ `.gcloudignore`.
Region z własną domeną: `europe-west1`. Do uptime używaj `/`, nie `/healthz`.

## Local-first
```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # ustaw DEV_OPERATOR i sekrety lokalne
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080
```

## Bezpieczniki rdzenia (decyzje właściciela)
- Autopilot = pełna automatyka na żywe forum, ale: idempotencja zleceń, globalny `AUTOPILOT=stop`,
  `FORUM_MODE=sucho` (log zamiast forum) do testów.
- Reguły biznesowe (kwoty/terminy/routing/kurierzy) w KODZIE, edytowalne w panelu koordynatora.
  Decyzję „czy windykować/kasować" podejmuje AI; KWOTĘ liczy kod. Twardy filtr zakazanych fraz.
