"""
Konfiguracja środowiska — jedno miejsce na odczyt zmiennych z env (jak top main.py Pulpitu).
Importuj stąd, nie czytaj os.environ rozsianego po kodzie.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

# Wczytaj .env z katalogu projektu niezależnie od katalogu uruchomienia.
# Na Cloud Run zmienne idą z env/Secret Managera, a pliku .env tam nie ma.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Środowisko ----------------------------------------------------------------
ENV = os.environ.get("ENV", "dev").lower()
if ENV not in ("dev", "prod"):
    raise RuntimeError(f"ENV musi być 'dev' albo 'prod', a jest {ENV!r}.")
# Secure-by-default: ciasteczka bez Secure tylko w jawnym 'dev'.
COOKIE_SECURE = ENV != "dev"
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN") or None

# --- Dane ----------------------------------------------------------------------
# Cloud Run: /tmp jest writable, ale ULOTNY — trwałe dane trzymamy w Firestore.
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
STORAGE = os.environ.get("STORAGE", "file").lower()
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

# --- Tożsamość / SSO -----------------------------------------------------------
def _load_pem_env(name: str) -> str:
    """Klucz PEM z env: surowy PEM (zawiera 'BEGIN') albo base64 PEM (zalecane w env).
    Ta sama normalizacja co Pulpit app/security._load_pem — kontrakt klucza publicznego."""
    v = os.environ.get(name, "")
    if not v or "BEGIN" in v:
        return v
    try:
        import base64
        return base64.b64decode(v).decode("ascii")
    except Exception:  # noqa: BLE001
        return v


PULPIT_URL = os.environ.get("PULPIT_URL", "https://pulpit.aitossilniki.com/")
PULPIT_PUBLIC_KEY = _load_pem_env("PULPIT_PUBLIC_KEY")  # klucz publiczny sesji Pulpitu (EdDSA)
DEV_OPERATOR = os.environ.get("DEV_OPERATOR", "")  # tylko dev: atrapa tożsamości

# --- Panel koordynatora --------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
KOORD_PASSWORD = os.environ.get("KOORD_PASSWORD", "")

# --- Forum F15 -----------------------------------------------------------------
FORUM_API_BASE = os.environ.get("FORUM_API_BASE", "https://f15.pmgtechnik.com")
FORUM_BEARER_TOKEN = os.environ.get("FORUM_BEARER_TOKEN", "")
# 'sucho' = nie wysyłaj na forum, tylko loguj (testy). 'live' = realne wpisy.
FORUM_MODE = os.environ.get("FORUM_MODE", "sucho").lower()

# --- Awizacje kurierskie (sygnał Szturchacz → apka Eweliny) ---------------------
# off    = po staremu (tylko forum, bez awizacji)
# shadow = awizacja (test_mode:true) ORAZ wpis na forum z nagłówkiem „nie zamawiaj, u Sylwii"
# live   = awizacja (test_mode:false), wpis na forum POMINIĘTY (sam sygnał)
KURIER_AWIZACJE_MODE = os.environ.get("KURIER_AWIZACJE_MODE", "off").lower()

# --- Brama ATA: odbiór WhatsApp (webhook push) ---------------------------------
# Sekret-przepustka w URL-u webhooka (subskrypcja bramy ma TYLKO endpointURL, bez nagłówków).
# Pusty = endpoint odbioru WYŁĄCZONY (zwraca 503). Ustawiany jako env/Secret na Cloud Run.
BRAMA_WA_WEBHOOK_TOKEN = os.environ.get("BRAMA_WA_WEBHOOK_TOKEN", "")

# --- Brama WEM: WYSYŁKA (zawór na rurze — bezpiecznik POZA promptem) -------------
# off   = wysyłka wyłączona całkiem (odmowa)
# sucho = NIC nie wychodzi do bramy; zamiar zapisywany w archiwum (kierunek=out, tryb=sucho)
# live  = realna wysyłka przez POST /api/v1/messages/send (nadal WYŁĄCZNIE po kliku operatora)
WEM_WYSYLKA = os.environ.get("WEM_WYSYLKA", "sucho").lower()
WEM_URL = os.environ.get("WEM_URL", "https://ata.autossilniki.com")
WEM_JWT_LOGIN = os.environ.get("WEM_JWT_LOGIN", "")
WEM_JWT_PASSWORD = os.environ.get("WEM_JWT_PASSWORD", "")

# --- Kontener v11 (bestchudy: lewa strona porównywarki w ramce) -----------------
# Adres serwisu kontener-v11 na Cloud Run. Ustawiony → nasza CSP wpuszcza ramkę z tej
# domeny (frame-src), a ekran porównywarki osadza v11 w split view. Pusty = ramka wyłączona.
V11_URL = os.environ.get("V11_URL", "").strip()

# --- AI ------------------------------------------------------------------------
GCP_PROJECT_IDS = [p.strip() for p in os.environ.get("GCP_PROJECT_IDS", "").split(",") if p.strip()]
GCP_LOCATION = os.environ.get("GCP_LOCATION", "europe-west1")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
PROMPT_URL = os.environ.get("PROMPT_URL", "")

# --- Autopilot -----------------------------------------------------------------
# Globalny wyłącznik awaryjny. 'stop' = autopilot nic nie robi.
AUTOPILOT = os.environ.get("AUTOPILOT", "stop").lower()
AUTOPILOT_TOKEN = os.environ.get("AUTOPILOT_TOKEN", "")


def is_dev() -> bool:
    return ENV == "dev"
