# Kontener v11 — odpałka (AS-IS)

Stary silnik streamlitowy Szturchacza w pudełku pod Cloud Run — **decyzja właściciela 2026-07-02:
pliki W CAŁOŚCI, nietknięte** (obawa: przepisany silnik = symulacja wzorca zamiast wzorca).

## Co jest czym

| Plik | Pochodzenie | Wolno zmieniać? |
|---|---|---|
| `app_vertex_ew.py` | kopia 1:1 z `szturchacz-test` (sha1 `81c0463…`) | **NIE** |
| `forum_module.py` | kopia 1:1 (sha1 `edfaf71…`) | **NIE** |
| `szturchacz_vnext_v1_11.txt` | kopia 1:1 (sha1 `5668100…`) | **NIE** |
| `requirements.txt` | kopia 1:1 (sha1 `c089b58…`) | **NIE** |
| `constraints.txt` | nasz — pinowanie wersji z przetestowanego środowiska | tak (aktualizacja pinów = decyzja przy buildzie, po teście) |
| `odpalka.py`, `Dockerfile` | nasze (pas Sylwii) | tak — ale TYLKO start/port/sekrety |

Aktualizacja silnika = ponowna kopia 1:1 z `szturchacz-test` (nigdy ręczna edycja).

## Sekrety (pas koordynatora — Secret Manager)

`odpalka.py` przy starcie generuje `.streamlit/secrets.toml` (silnik czyta `st.secrets`;
do obrazu sekrety NIE są wpiekane — patrz `.dockerignore`):

- `FIREBASE_CREDS` — pełny JSON konta serwisowego (Firestore + Vertex, jeden klucz jak dotąd)
- `GCP_PROJECT_IDS` — projekty po przecinku; decyzja właściciela: **jeden projekt** (bez rotacji)
- `GCP_LOCATION` — region Vertex AI
- `FORUM_BEARER_TOKEN` — token API forum F15

## Uruchomienie lokalne

```
docker build -t kontener-v11 .
docker run --rm -p 8501:8501 --env-file sekrety.env kontener-v11
```

Sekrety podawać przez `--env-file` (plik np. `sekrety.env`, jest w `.gitignore`) — NIE przez
`-e` w linii poleceń, bo zostają w historii terminala.

Bez Dockera: `pip install -r requirements.txt -c constraints.txt`, ustawić zmienne,
`python odpalka.py`. Bez prawdziwych sekretów silnik wstanie, a w oknie pokaże swój komunikat
konfiguracyjny — to oczekiwane; mechanikę pudełka (port, secrets.toml, ramka) sprawdza się
na atrapach (test 2026-07-02: health „ok", `/` i `/?embed=true` odpowiadają 200).

## Osadzanie w ramce (porównywarka bestchudy)

Lewa strona ekranu PRACA = ten kontener w iframe: `https://<adres-kontenera>/?embed=true`.
Streamlit wspiera osadzanie; gdyby ramka nie działała przez politykę przeglądarki, kandydaci
na flagi odpałki (dopisać w `odpalka.py`, NIE w silniku): `--server.enableCORS=false`,
`--server.enableXsrfProtection=false` — decyzja przy wpięciu, razem z koordynatorem.
Po stronie apki-matki: CSP `frame-src <adres-kontenera>` — jedna linijka, robi koordynator.

## Świadomie zachowane AS-IS (uwaga przy testach!)

- `TEST_MODE=True` w `app_vertex_ew.py` (kolekcje `test_*`) **oraz** `FORUM_TEST_MODE=False`
  w `forum_module.py` → wpisy forum idą na **PRODUKCYJNE** wątki F15. Tak dziś pracują operatorzy;
  zmiana którejkolwiek flagi = decyzja koordynatora, nie odpałki.
- Logowanie po staremu: lista operatorów + hasło z `test_operator_configs` (w ramce, bez SSO).
- Prompt: silnik sam pobiera go z URL-a wskazanego w Firestore (`test_admin_config/default_prompt`),
  cache 1 h — zarządzanie promptem bez zmian (admin).

## Wymagania deployu (Streamlit trzyma sesję W PAMIĘCI — inaczej operator będzie wylatywał)

`st.session_state` (w tym LOGIN operatora i cała rozmowa z AI) żyje w pamięci procesu i na
websockecie. Na Cloud Run to oznacza twarde wymagania:
- `--timeout=3600` (domyślne 300 s zetnie websocket = wylogowanie co ~5 min),
- `--session-affinity` oraz `--max-instances=1` (druga instancja = rozerwane sesje),
- rozważyć `--min-instances=1` (zimny start gubi sesje) i pamięć ≥1 GiB.
Restart instancji = utrata trwającej rozmowy (case wraca z bazy, rozmowa nie) — tak samo
działał stary streamlit; odnotowane, nie naprawiamy (as-is).

## Monitoring — uwaga

Uptime na `/` jest ŚLEPY na zepsuty silnik: streamlit serwuje 200 nawet bez sekretów
(błąd widać dopiero w sesji przeglądarki). Po wdrożeniu zrobić jednorazowy test ręczny
(zalogowanie + wklejka wsadu), nie polegać na samym uptime.

## Pytania odpałkowe do koordynatora (przy wdrożeniu; nie blokują)

1. **Projekt Firestore** dla `FIREBASE_CREDS`: propozycja = STARY projekt (loginy operatorów,
   konfiguracja promptu, pamięć forum i statystyki działają dalej bez zasiewania).
2. Flagi ramki (CORS/XSRF) — tylko jeśli osadzanie tego wymaga (patrz wyżej).
3. Deploy: WYŁĄCZNIE koordynator, z `main`, region `europe-west1`, uptime na `/`
   (z zastrzeżeniem z sekcji „Monitoring") + flagi z sekcji „Wymagania deployu".
