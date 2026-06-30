"""
JEDYNY punkt styku z logowaniem Pulpitu.

`read_operator(request)` zwraca tożsamość zalogowanego operatora `{pid, label, roles}`
albo `None` (→ wywołujący przekierowuje na bramę Pulpitu, PULPIT_URL).

Źródłem prawdy jest podpisane ciasteczko `session`, które Pulpit wystawia po PIN-ie.
Docelowo: JWT podpisany kluczem PRYWATNYM Pulpitu, weryfikowany tu kluczem PUBLICZNYM
(EdDSA, PULPIT_PUBLIC_KEY) — kafelek NIE MOŻE podrobić sesji. Ciało weryfikacji dostarcza
Pulpit (plan SSO asymetryczny); tu zostaje punkt wpięcia, żeby reszta apki była gotowa.

Lokalnie (bez Pulpitu): ustaw DEV_OPERATOR w .env, wtedy read_operator() zwraca atrapę.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from . import config


def _parse_dev_operator(raw: str) -> Optional[Dict]:
    """Format: 'pid|Etykieta|rola1,rola2'. Tylko dev — atrapa tożsamości."""
    if not raw:
        return None
    parts = raw.split("|")
    pid = (parts[0] if parts else "").strip() or "dev"
    label = (parts[1].strip() if len(parts) > 1 else "Operator testowy")
    roles = [r.strip() for r in (parts[2].split(",") if len(parts) > 2 else ["operator"]) if r.strip()]
    return {"pid": pid, "label": label, "roles": roles or ["operator"]}


def read_operator(request) -> Optional[Dict]:
    """
    Zwraca {pid, label, roles} zalogowanego operatora albo None.

    Kolejność:
    1) DEV_OPERATOR (tylko ENV=dev) → atrapa, żeby ekran operatora działał bez Pulpitu.
    2) ciasteczko `session` z Pulpitu → weryfikacja JWT kluczem publicznym (dostarczy Pulpit).
    """
    if config.is_dev() and config.DEV_OPERATOR:
        return _parse_dev_operator(config.DEV_OPERATOR)

    token = request.cookies.get("session")
    if not token or not config.PULPIT_PUBLIC_KEY:
        # Brak ciasteczka albo brak klucza publicznego (SSO nieskonfigurowane) → brak tożsamości.
        return None

    # Weryfikacja sesji OSOBY: JWT podpisany kluczem PRYWATNYM Pulpitu, sprawdzany TU
    # kluczem PUBLICZNYM (EdDSA) → kafelek NIE MOŻE podrobić sesji. Kontrakt claimów
    # (Pulpit app/security.make_session): {pid, roles, label, iat, exp}; exp pilnuje PyJWT.
    try:
        import jwt
        claims = jwt.decode(token, config.PULPIT_PUBLIC_KEY, algorithms=["EdDSA"])
    except Exception:  # noqa: BLE001 — zła sygnatura / wygasłe / uszkodzone → brak tożsamości
        return None
    pid = claims.get("pid")
    if not pid:
        return None
    return {"pid": str(pid), "label": claims.get("label"),
            "roles": [str(r) for r in (claims.get("roles") or [])]}


def operator_group(operator: Optional[Dict]) -> Optional[str]:
    """Grupa językowa operatora (DE/FR/UKPL) z jego ról, jeśli zakodowana jako 'grupa:DE'."""
    if not operator:
        return None
    for r in operator.get("roles", []):
        if r.startswith("grupa:"):
            return r.split(":", 1)[1].upper() or None
    return None
