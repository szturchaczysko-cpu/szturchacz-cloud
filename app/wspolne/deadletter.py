"""
Siatka bezpieczeństwa odbioru z bramy ATA: gdy trwały zapis (Firestore/plik) padnie MIMO
ponawiania, NIE gubimy wiadomości po cichu — dopisujemy surowiec do `wa_deadletter.jsonl`.
Sam moduł nigdy nie rzuca (błąd zapisu dead-letter → tylko log ERROR; Cloud Logging jest trwałe).

UWAGA: DATA_DIR na Cloud Run = /tmp (ULOTNY) → to OSTATNIA linia obrony, nie magazyn.
Drenaż/replay = zadanie operacyjne (TODO: podgląd/replay w panelu koordynatora).
Powód istnienia: brama jest (prawdopodobnie) at-most-once i nie ponawia, więc błąd zapisu u nas
= trwała luka w archiwum. Dead-letter zamienia „utrata" na „do odzyskania".
"""
from __future__ import annotations

import json
import logging
import os
import time

from .. import config

log = logging.getLogger("deadletter")

PLIK = "wa_deadletter.jsonl"


def zapisz(raw, headers=None, powod: str = "") -> bool:
    """Dopisz surowiec pusha do pliku JSONL (best-effort). Zwraca True gdy się udało. Nigdy nie rzuca."""
    try:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        rec = {
            "ts": int(time.time()),
            "powod": str(powod)[:300],
            "raw": raw if isinstance(raw, (dict, list)) else str(raw),
            "headers": headers or {},
        }
        with open(os.path.join(config.DATA_DIR, PLIK), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception:  # noqa: BLE001
        log.exception("[deadletter] zapis do pliku padł — surowiec tylko w tym logu: %r", raw)
        return False
