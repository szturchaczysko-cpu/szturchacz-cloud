"""
POBIERACZ HISTORII z bramy WEM — zaciąganie STARYCH maili/eBay przez okno odpytywania
(`GET /api/v1/messages/receive`, parametry Channels/FromDate/ToDate). Etap 2 planu właściciela:
na skrzynkach leżą dziesiątki tysięcy wiadomości sprzed wpięcia webhooka — dociągamy je porcjami
(zakres dat ≤ 31 dni na strzał), wszystko przechodzi przez ISTNIEJĄCY magazyn (sklejanie po
kliencie przy zapisie) z odsiewem duplikatów przy wstawianiu.

WhatsApp celowo NIEOBSŁUGIWANY — Meta nie ma historii (push-only), brama jej nie gromadzi.
Kształt odpowiedzi /receive NIE jest opisany w Swaggerze bramy → parsujemy TOLERANCYJNIE
(parsuj_wa; pełny surowiec zawsze w `raw`). Auth jak klient wysyłkowy (token JWT, cache).
"""
from __future__ import annotations

import logging
import re
import time
from typing import List

from .. import config, deps
from . import archiwum

log = logging.getLogger("wem_pobieracz")

_DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$", re.ASCII)
_MAKS_DNI = 31          # jedna porcja = maks. miesiąc (brama może oddać tysiące na strzał)
_MAKS_WIADOMOSCI = 2000  # bezpiecznik na porcję


def _ts(d: str) -> int:
    return int(time.mktime(time.strptime(d, "%Y-%m-%d")))


def _z_bramy(channel: str, od: str, do: str) -> List[dict]:
    """Surowe elementy z okna odpytywania bramy. Osobna funkcja = łatwa atrapa w testach."""
    import requests
    from . import brama_wem_klient
    r = requests.get(config.WEM_URL.rstrip("/") + "/api/v1/messages/receive",
                     params={"Channels": channel, "FromDate": od, "ToDate": do},
                     headers={"Authorization": "Bearer " + brama_wem_klient._token()},
                     timeout=120)
    r.raise_for_status()
    d = r.json()
    if isinstance(d, list):
        return d
    if isinstance(d, dict):  # tolerancja na opakowanie {messages:[...]} / {items:[...]}
        for k in ("messages", "items", "data", "wiadomosci"):
            if isinstance(d.get(k), list):
                return d[k]
    return []


def pobierz_historie(channel: str, od: str, do: str) -> dict:
    """Jedna porcja historii: kanał (email/ebay) + zakres dat (≤31 dni). Zapis przez magazyn
    (thread_id/order_refs/dedup przy zapisie); duplikaty względem już zapisanych POMIJANE
    (po kluczu dedup — z prawdziwym id żelazne, bez id best-effort)."""
    channel = (channel or "").strip().lower()
    if channel not in ("email", "ebay"):
        return {"ok": False, "message": "Historia tylko dla email/ebay (WhatsApp nie ma historii — Meta)."}
    if not (_DATA_RE.match(od or "") and _DATA_RE.match(do or "")):
        return {"ok": False, "message": "Daty w formacie RRRR-MM-DD."}
    try:
        dni = (_ts(do) - _ts(od)) / 86400
    except (ValueError, OverflowError):
        return {"ok": False, "message": "Nieprawidłowe daty."}
    if dni < 0 or dni > _MAKS_DNI:
        return {"ok": False, "message": f"Zakres 0–{_MAKS_DNI} dni na porcję (masz {dni:.0f})."}
    try:
        elementy = _z_bramy(channel, od, do)
    except Exception as e:  # noqa: BLE001 — brama w przebudowie nie może wywalać zaplecza
        return {"ok": False, "message": f"Brama WEM nie odpowiada ({type(e).__name__}) — "
                                        "spróbuj później (u Krzyśka trwa przebudowa)."}
    elementy = elementy[:_MAKS_WIADOMOSCI]
    # Odsiew duplikatów wobec świeżo zapisanych (pushe z ostatnich dni) i wewnątrz porcji.
    widziane = {m.get("klucz_dedup") for m in deps.wa_inbox.recent(1000) if m.get("klucz_dedup")}
    zapisano = pominieto = 0
    for el in elementy:
        raw = {"channel": channel, "type": "message", "zrodlo": "historia",
               "data": el if isinstance(el, dict) else {"body": str(el)}}
        from .brama_wa import parsuj_wa
        probny = parsuj_wa(raw)
        klucz = archiwum.klucz_dedup(probny)
        if klucz in widziane:
            pominieto += 1
            continue
        widziane.add(klucz)
        deps.wa_inbox.add(raw)
        zapisano += 1
    log.info("[wem_pobieracz] %s %s..%s: pobrano=%d zapisano=%d duplikaty=%d",
             channel, od, do, len(elementy), zapisano, pominieto)
    return {"ok": True, "kanal": channel, "od": od, "do": do,
            "pobrano": len(elementy), "zapisano": zapisano, "pominieto_duplikaty": pominieto}
