"""
Klient WYSYŁKOWY bramy WEM (ATA) — jedyna droga czegokolwiek DO klienta przez bramę.

Auth: JWT z POST /api/v1/auth/token {login,password}; token wygasa po 60 min → cache z zapasem.
Wysyłka: POST /api/v1/messages/send {channel, recipient, body} (+subject dla maila).
Sekrety: WEM_JWT_LOGIN/PASSWORD z env/Secret Managera — NIGDY w repo.

Ten moduł NIE decyduje, CZY wysłać (to robi zawór w styki.wyslij: tryb + klik operatora) —
on tylko umie fizycznie wysłać, gdy zawór jest otwarty.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from .. import config

log = logging.getLogger("brama_wem")

_TOKEN: dict = {"wartosc": "", "wygasa": 0}
_TOKEN_ZAPAS_S = 300  # odśwież 5 min przed wygaśnięciem (token żyje 60 min)


def _token() -> str:
    if _TOKEN["wartosc"] and time.time() < _TOKEN["wygasa"]:
        return _TOKEN["wartosc"]
    if not (config.WEM_JWT_LOGIN and config.WEM_JWT_PASSWORD):
        raise RuntimeError("Brak WEM_JWT_LOGIN/WEM_JWT_PASSWORD (env/Secret Manager).")
    r = requests.post(config.WEM_URL.rstrip("/") + "/api/v1/auth/token",
                      json={"login": config.WEM_JWT_LOGIN, "password": config.WEM_JWT_PASSWORD},
                      timeout=30)
    r.raise_for_status()
    tok = (r.json() or {}).get("access_token") or ""
    if not tok:
        raise RuntimeError("Brama WEM nie oddała access_token.")
    _TOKEN.update(wartosc=tok, wygasa=time.time() + 3600 - _TOKEN_ZAPAS_S)
    return tok


def wyslij(channel: str, recipient: str, body: str, subject: str = "",
           sender: str = "") -> dict:
    """Fizyczna wysyłka przez bramę. Zwraca {ok, status, odpowiedz}. Rzuca przy braku creds."""
    payload = {"channel": channel, "recipient": recipient, "body": body}
    if subject:
        payload["subject"] = subject
    if sender:
        payload["sender"] = sender
    r = requests.post(config.WEM_URL.rstrip("/") + "/api/v1/messages/send",
                      json=payload, headers={"Authorization": "Bearer " + _token()}, timeout=60)
    ok = 200 <= r.status_code < 300
    if not ok:
        log.error("[brama_wem] send %s → %s: %s", channel, r.status_code, r.text[:300])
    tresc: Optional[dict]
    try:
        tresc = r.json()
    except ValueError:
        tresc = {"raw": r.text[:300]}
    return {"ok": ok, "status": r.status_code, "odpowiedz": tresc}
