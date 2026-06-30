"""Drobne narzędzia bezpieczeństwa panelu (porównania stałoczasowe)."""
from __future__ import annotations

import hmac


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest((a or "").encode("utf-8"), (b or "").encode("utf-8"))
