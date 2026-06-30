"""
Loader wsadów → sprawy. Operator-przełożony wkleja listę zamówień; tu zamieniamy ją na
sprawy w kolejce. Numer i grupę ustalamy deterministycznie (reguły), score z [SCORE=] lub domyślny.
"""
from __future__ import annotations

import re
import time
from typing import Dict

from .. import deps
from ..wspolne import model, reguly

_SCORE_RE = re.compile(r"\[SCORE\s*=\s*(\d{1,4})\]", re.IGNORECASE)


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _grupa_z_linii(linia: str) -> str:
    """
    Wykryj grupę po nazwie kraju (deterministycznie wg tablicy reguł).
    GRANICE SŁÓW — inaczej krótkie kody (de/at/ch) łapią się wewnątrz słów (np. 'de' w 'odeslac').
    Dłuższe nazwy sprawdzane najpierw (pełna nazwa wygrywa z kodem).
    """
    low = linia.lower()
    mapa = getattr(reguly, "KRAJ_DO_GRUPY", {})
    for kraj in sorted(mapa, key=lambda k: len(str(k)), reverse=True):
        if re.search(r"\b" + re.escape(str(kraj).lower()) + r"\b", low):
            return reguly.kraj_na_grupe(kraj)
    return model.Grupa.UKPL.value


def ingest_wsad(text: str, *, data_obrobki: str = "", default_score: int = 500) -> Dict:
    """Każda linia z rozpoznanym numerem → sprawa. Re-zapis numeru nadpisuje (idempotencja)."""
    data_obrobki = data_obrobki or _today()
    dodane, pominiete = 0, 0
    for i, linia in enumerate(text.splitlines()):
        linia = linia.strip()
        if not linia:
            continue
        numer = model.normalize_nrzam(linia)
        if not numer:
            pominiete += 1
            continue
        sc = _SCORE_RE.search(linia)
        score = int(sc.group(1)) if sc else default_score
        grupa = _grupa_z_linii(linia)
        deps.cases.upsert(model.Case(
            numer_zamowienia=numer, grupa=grupa, score=score,
            pelna_linia_szturchacza=linia, data_obrobki=data_obrobki, sort_order=i,
            priority_icon="🔴" if score > 800 else ("🟠" if score > 500 else "🟡"),
        ))
        dodane += 1
    return {"dodane": dodane, "pominiete": pominiete, "data_obrobki": data_obrobki}
