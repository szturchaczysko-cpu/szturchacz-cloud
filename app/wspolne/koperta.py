"""
Parser SNAPSHOT/KOPERTY v1_9 (§12) — wyizolowany, czysty (stdlib).

Koperta to równoległy stan sprawy trzymany w tekście:
    COP# PZ: PZx
    COP# DRABES: WA[1]/wysl@12.06 | TEL[1]/zlec@13.06 | ...
    COP# USTALENIA: [kanał+wynik]; KURIER_PRZEWOZNIK=UPS; FORUM_ATOM=...; | ATOM_CEL=...
Reguła COP#-FIRST (§12 l.2460): OSTATNI blok COP# = źródło prawdy (gdy brak TAG-KOPERTA).
USTALENIA: tokeny KEY=VALUE, separatory ';' i '|'. Wartości: snake_case/uppercase,
ZAKAZ znaków " ' , + (§12 l.2533-2538) — bo łamią parser/forum (API 400).

Tu tylko ODCZYT + SANITYZACJA. Egzekucję skutków robi sterowanie.py.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .model import parse_pz

# Dozwolone wyjątki dla '>' (trend=N>N>N) — patrz §0.6. Reszta znaków specjalnych zakazana w wartościach.
_ZAKAZANE_ZNAKI_WARTOSCI = ('"', "'", ",", "+")


def parsuj_ustalenia(s: str) -> Dict[str, str]:
    """
    USTALENIA (string) → słownik KEY=VALUE. Tolerancyjny: separatory ';' i '|',
    a także '.' UŻYTE jako separator przed kolejnym KLUCZ= (AI bywa niekonsekwentne),
    NIE tnąc dat 'DD.MM' (kropka przed cyfrą zostaje).
    """
    if not s:
        return {}
    # '.' przed wzorcem KLUCZ= → traktuj jak separator (ale 'DD.MM' zostaje, bo po kropce cyfra).
    s = re.sub(r"\.(?=[A-Za-zĄĆĘŁŃÓŚŹŻ][A-Za-z0-9_]*\s*=)", ";", s)
    pola: Dict[str, str] = {}
    for chunk in re.split(r"[;|]", s):
        chunk = chunk.strip()
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            k = k.strip()
            if k:
                pola[k] = v.strip()
    return pola


def sanityzuj_ustalenia(s: str) -> List[str]:
    """
    Zwraca listę naruszeń zasad defensywnych USTALENIA (§12 l.2533-2538):
    zakaz " ' , + w WARTOŚCIACH tokenów KEY=VALUE. Pole 'klient: "..."' (z ':') nie jest
    tokenem KEY=VALUE, więc nie jest sprawdzane (cudzysłów tam dozwolony).
    """
    naruszenia: List[str] = []
    for k, v in parsuj_ustalenia(s).items():
        for ch in _ZAKAZANE_ZNAKI_WARTOSCI:
            if ch in v:
                naruszenia.append(f"{k}: niedozwolony znak '{ch}' w wartości")
    return naruszenia


def parsuj_snapshot(text: str) -> Dict:
    """
    Z tekstu (wsad/rozmowa) wyciągnij ostatni snapshot wg COP#-FIRST.
    Zwraca {pz, pz_raw, drabes, ustalenia, pola, zrodlo}. Puste gdy brak koperty.
    """
    if not text:
        return {"pz": None, "pz_raw": "", "drabes": "", "ustalenia": "", "pola": {}, "zrodlo": "brak"}

    # OSTATNI blok COP# (najniżej) = źródło prawdy.
    pz_raw = ""
    pz_matches = re.findall(r"COP#\s*PZ\s*:\s*(PZ[0-9]{1,2}[AB]?)", text, re.IGNORECASE)
    if pz_matches:
        pz_raw = pz_matches[-1]
    drabes_matches = re.findall(r"COP#\s*DRABES\s*:\s*([^\n]*)", text, re.IGNORECASE)
    ust_matches = re.findall(r"COP#\s*USTALENIA\s*:\s*([^\n]*)", text, re.IGNORECASE)
    ustalenia = ust_matches[-1].strip() if ust_matches else ""

    return {
        "pz": parse_pz(pz_raw),
        "pz_raw": pz_raw,
        "drabes": drabes_matches[-1].strip() if drabes_matches else "",
        "ustalenia": ustalenia,
        "pola": parsuj_ustalenia(ustalenia),
        "zrodlo": "cop#" if pz_matches or ust_matches else "brak",
    }


def kurier_z_ustalen(pola: Dict[str, str]) -> Optional[str]:
    """KURIER_PRZEWOZNIK z pól USTALENIA (uppercase), None gdy brak."""
    k = (pola.get("KURIER_PRZEWOZNIK") or pola.get("kurier") or "").strip().upper()
    return k or None


if __name__ == "__main__":
    # format v1_9 (separatory ; i |)
    s = 'WA+odp; klient: "ok"; KURIER_PRZEWOZNIK=UPS; FORUM_ATOM=czekam_potw_kuriera | ATOM_CEL=AUTOS_KURIERZY | ATOM_USER=TEAM_ATOMOWKI'
    p = parsuj_ustalenia(s)
    assert p["KURIER_PRZEWOZNIK"] == "UPS", p
    assert p["ATOM_CEL"] == "AUTOS_KURIERZY", p
    # 'klient: "ok"' nie jest tokenem = → cudzysłów nie zgłaszany
    assert sanityzuj_ustalenia(s) == [], sanityzuj_ustalenia(s)
    # zakazany znak w wartości
    assert any("niedozwolony" in n for n in sanityzuj_ustalenia("KURIER_PRZEWOZNIK=UPS+FEDEX"))
    # format „kropkowy" z AI + data DD.MM nietknięta
    s2 = "PZ6.TOWAR_TYP=KOLEKTOR.KURIER_PRZEWOZNIK=UPS.KOTWICA=12.06"
    p2 = parsuj_ustalenia(s2)
    assert p2["TOWAR_TYP"] == "KOLEKTOR" and p2["KURIER_PRZEWOZNIK"] == "UPS", p2
    assert p2["KOTWICA"] == "12.06", p2  # data nietknięta
    # snapshot COP#-FIRST: ostatni blok wygrywa
    txt = "COP# PZ: PZ2\nCOP# USTALENIA: KURIER_PRZEWOZNIK=FEDEX\n...\nCOP# PZ: PZ6\nCOP# USTALENIA: KURIER_PRZEWOZNIK=UPS"
    snap = parsuj_snapshot(txt)
    assert snap["pz"] == 6 and snap["pola"]["KURIER_PRZEWOZNIK"] == "UPS", snap
    print("koperta.py: testy sanity OK")
