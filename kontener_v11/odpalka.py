"""
ODPAŁKA kontenera v11 — jedyny NASZ kod w tym katalogu.

Pliki silnika (app_vertex_ew.py, forum_module.py, szturchacz_vnext_v1_11.txt, requirements.txt)
to kopie 1:1 z repo szturchacz-test — decyzja właściciela 2026-07-02: AS-IS, NIE DOTYKAĆ.
Wolno zmieniać wyłącznie ten plik, Dockerfile i constraints.txt (start/port/sekrety/pinowanie).

Co robi:
1. Buduje .streamlit/secrets.toml ze zmiennych środowiskowych — silnik czyta st.secrets,
   a sekretów nie wolno wpiekać w obraz (przychodzą z Secret Managera, pas koordynatora).
   Puste zmienne NIE trafiają do pliku — brak klucza uruchamia w silniku jego własne
   bramki konfiguracyjne (KeyError → komunikat), zamiast wybuchać później w środku pracy.
2. Startuje streamlit na $PORT (Cloud Run ustawia sam; lokalnie 8501).

Zmienne środowiskowe:
  FIREBASE_CREDS     — pełny JSON konta serwisowego (Firestore + Vertex, jak w starym st.secrets)
  GCP_PROJECT_IDS    — ID projektów po przecinku (decyzja właściciela: JEDEN projekt)
  GCP_LOCATION       — region Vertex AI
  FORUM_BEARER_TOKEN — token API forum F15
  PORT               — port nasłuchu (Cloud Run poda; lokalnie domyślnie 8501)
"""
from __future__ import annotations

import json
import os
import sys


def _toml_str(s: str) -> str:
    # Bezpieczny string TOML: escapowanie JSON-owe jest podzbiorem basic string TOML
    # (potwierdzone round-tripem pełnego JSON-a konta serwisowego z kluczem prywatnym).
    return json.dumps(s, ensure_ascii=False)


def main() -> None:
    # Streamlit szuka secrets w CWD/.streamlit — przypinamy CWD do katalogu odpałki,
    # żeby lokalny start z innego katalogu nie rozjechał zapisu i odczytu.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    linie = ["# Wygenerowane przez odpalka.py przy starcie kontenera — NIE commitować."]
    for nazwa in ("FIREBASE_CREDS", "GCP_LOCATION", "FORUM_BEARER_TOKEN"):
        wartosc = os.environ.get(nazwa, "")
        if wartosc.strip():
            linie.append(f"{nazwa} = {_toml_str(wartosc)}")
        else:
            print(f"[odpalka] UWAGA: brak {nazwa} — klucz pominięty; silnik pokaże swój "
                  f"komunikat konfiguracyjny przy pierwszym użyciu.", file=sys.stderr, flush=True)
    projekty = [p.strip() for p in os.environ.get("GCP_PROJECT_IDS", "").split(",") if p.strip()]
    if projekty:
        linie.append("GCP_PROJECT_IDS = [" + ", ".join(_toml_str(p) for p in projekty) + "]")
    else:
        # Pustej listy NIE zapisujemy: przeszłaby try/except silnika (liczony na KeyError)
        # i wybuchła dopiero po zalogowaniu operatora (IndexError na GCP_PROJECTS[0]).
        print("[odpalka] UWAGA: brak GCP_PROJECT_IDS — klucz pominięty (bramka silnika zadziała).",
              file=sys.stderr, flush=True)
    linie.append("")

    os.makedirs(".streamlit", exist_ok=True)
    sciezka = os.path.join(".streamlit", "secrets.toml")
    with open(sciezka, "w", encoding="utf-8") as f:
        f.write("\n".join(linie))
    os.chmod(sciezka, 0o600)
    print(f"[odpalka] secrets.toml gotowy (kluczy: {len(linie) - 2}, projekty: {len(projekty)}).",
          flush=True)

    port = os.environ.get("PORT") or "8501"
    os.execvp("streamlit", [
        "streamlit", "run", "app_vertex_ew.py",
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])


if __name__ == "__main__":
    main()
