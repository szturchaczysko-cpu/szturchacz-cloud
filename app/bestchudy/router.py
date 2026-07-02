"""
BESTCHUDY — gniazdo modułu (postawione przez koordynatora, 2026-07-02).

PAS SYLWII. Cały moduł porównywarki (v11 ‖ chudy) żyje w `app/bestchudy/` + własne kolekcje
bazy z prefiksem `bc_`. Wspólnych plików NIE edytujemy — wpięcie w apkę (jedna linijka
w main.py) już istnieje i jest jedynym punktem styku z montażem.

Zakres, styki i twarde zasady: COORDYNACJA.md → „MAPA EKRANÓW I GRANICE" + rozpis 5 pkt
w sekcji PODZIAŁ. Czego moduł potrzebuje od reszty apki (sprawa/rolka/silnik/wysyłka) —
przez STYKI uzgodnione wpisem w COORDYNACJA, nigdy przez import z cudzych pasów.

Tożsamość operatora: app/sso.py::read_operator(request) — jedyny dozwolony wspólny import
(kontrakt SSO, patrz CLAUDE.md).
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/bestchudy", tags=["bestchudy"])


@router.get("")
async def bestchudy_status():
    """Placeholder gniazda — do zastąpienia ekranem porównywarki (pas Sylwii)."""
    return {"ok": True, "modul": "bestchudy", "stan": "gniazdo postawione — czeka na porównywarkę"}
