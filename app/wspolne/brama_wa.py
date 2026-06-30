"""
Brama ATA → odbiór WhatsApp. Normalizacja pusha webhooka bramy do jednego kształtu.

UWAGA: dokładny kształt pusha potwierdzi Krzysiek (pyt. 3 z pingu: pull vs push + format).
Do tego czasu parser jest CELOWO TOLERANCYJNY — ZAWSZE zapisujemy surowiec (`raw`),
a pola wyciągamy best-effort. Odbiór nigdy nie może paść przez nieznany kształt
(ta sama dyscyplina co walidator sterowania: „żeby NIGDY nie padło").

Rekord znormalizowany: sender, recipient, text, ts (epoch), kierunek, msg_id.
"""
from __future__ import annotations

import time
from typing import Any, Optional

# Klucze, pod którymi RÓŻNE bramki/formaty trzymają to samo pole (od najpewniejszych).
_KLUCZE = {
    "sender": ("sender", "from", "sender_phone", "senderPhone", "wa_id", "waId", "author", "phone", "msisdn"),
    "recipient": ("recipient", "to", "recipient_phone", "recipientPhone", "destination"),
    "text": ("text", "body", "message", "contentMsg", "content", "caption"),
    "ts": ("timestamp", "ts", "date", "createdAt", "created_at", "sentAt", "sent_at"),
    "msg_id": ("id", "messageId", "message_id", "msgId", "wamid", "wa_message_id"),
    "kierunek": ("direction", "kierunek", "type"),
}


def _szukaj(d: Any, klucze: tuple) -> Optional[Any]:
    """Pola skalarne: dopasowanie po kluczu tylko gdy wartość jest SKALAREM; gdy pod kluczem
    siedzi dict (np. {'message': {...}}) — schodzimy poziom niżej. Nie wywala się na nie-dict."""
    if not isinstance(d, dict):
        return None
    low = {str(k).lower(): v for k, v in d.items()}
    for k in klucze:
        v = low.get(k.lower())
        if v not in (None, "", []) and not isinstance(v, (dict, list)):
            return v
    for v in d.values():  # jeden poziom w głąb (kontenery typu 'message'/'data')
        if isinstance(v, dict):
            got = _szukaj(v, klucze)
            if got not in (None, "", []):
                return got
    return None


def _to_epoch(v: Any) -> int:
    if isinstance(v, (int, float)):
        n = int(v)
        return n // 1000 if n > 10_000_000_000 else n  # ms → s
    if isinstance(v, str):
        s = v.strip()
        if s.isdigit():
            n = int(s)
            return n // 1000 if n > 10_000_000_000 else n
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
            try:
                return int(time.mktime(time.strptime(s[:len(time.strftime(fmt))], fmt)))
            except (ValueError, OverflowError):
                continue
    return int(time.time())


def parsuj_wa(raw: Any) -> dict:
    """Best-effort normalizacja. Nigdy nie rzuca. `raw` może być dict/list/str/None."""
    src = raw
    if isinstance(raw, list) and raw:
        src = raw[0] if isinstance(raw[0], dict) else {"text": str(raw)}
    if not isinstance(src, dict):
        src = {"text": str(src) if src is not None else ""}
    sender = _szukaj(src, _KLUCZE["sender"])
    text = _szukaj(src, _KLUCZE["text"])
    ts_raw = _szukaj(src, _KLUCZE["ts"])
    return {
        "sender": str(sender)[:64] if sender is not None else "",
        "recipient": str(_szukaj(src, _KLUCZE["recipient"]) or "")[:64],
        "text": (str(text)[:4000] if text is not None else ""),
        "ts": _to_epoch(ts_raw) if ts_raw is not None else int(time.time()),
        "msg_id": str(_szukaj(src, _KLUCZE["msg_id"]) or "")[:128],
        "kierunek": str(_szukaj(src, _KLUCZE["kierunek"]) or "in")[:16],
    }


if __name__ == "__main__":
    # sanity — różne kształty nie wywalają parsera
    assert parsuj_wa({"from": "+49123", "body": "Hallo", "timestamp": 1700000000})["sender"] == "+49123"
    assert parsuj_wa({"message": {"text": "x", "sender": "49500"}})["text"] == "x"
    assert parsuj_wa([{"contentMsg": "y"}])["text"] == "y"
    assert parsuj_wa("surowy string")["text"] == "surowy string"
    assert parsuj_wa(None)["text"] == ""
    assert parsuj_wa({"timestamp": "1700000000000"})["ts"] == 1700000000  # ms→s
    print("brama_wa.py: sanity OK")
