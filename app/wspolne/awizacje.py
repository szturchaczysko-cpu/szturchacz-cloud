"""
AWIZACJE KURIERSKIE (faza 1) — sygnał Szturchacz/Wieżowiec → apka Eweliny.

Zamiast (albo obok, w trybie shadow) wpisu na forum do TEAM_ATOMOWKI, Szturchacz odkłada
USTRUKTURYZOWANĄ intencję zlecenia do kolekcji `awizacje_kurier` (kontrakt: ~Desktop/kontrakt_awizacje_kurier.md).

FAZA 1 — tylko UPS + SKRZYNIA + odbiór u klienta (upsOpt=1), adres = pierwotny (fromDb:true).
Wszystko inne (FedEx/Schenker/kolektor/Access Point) → `parsuj_zlecenie` zwraca None i sprawa idzie
na forum po staremu. Parser jest TOLERANCYJNY i NIGDY nie rzuca (dyscyplina jak walidator sterowania).

Kształt `zlecenie` jest 1:1 pod `CreateZwrotka` Krzyśka (woła ją apka Eweliny, nie Szturchacz).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

# Nagłówek wpisu na forum w trybie shadow — żeby atomówki NIE zamówiły podwójnie.
KURIER_TEST_HEADER = ("⚠️ UWAGA — TO IDZIE TESTOWYM SYSTEMEM AUTOMATYCZNYM — "
                      "nie zamawiaj — szczegóły u Sylwii")

# Skrzynia: domyślne wymiary (decyzja koordynatora; do potwierdzenia z Krzyśkiem, nie blokuje).
PACKAGE_SKRZYNIA = {"weight": 69.0, "length": 80, "width": 60, "height": 40}

_RE_NRZAM = re.compile(r"Zam[óo]wienie\s*[:=]\s*(\d{4,7})", re.I)
_RE_UPS = re.compile(r"\bUPS\b", re.I)
_RE_KURIER = re.compile(r"Kurier\s*[:=]\s*((?:DB[\s_]?)?[A-Za-zĄĆĘŁŃÓŚŹŻ]+)", re.I)
_RE_SKRZYNIA = re.compile(r"TOWAR_TYP\s*[:=]\s*SKRZYNIA|skrzyni", re.I)
_RE_KOLEKTOR = re.compile(r"TOWAR_TYP\s*[:=]\s*KOLEKTOR|kolektor", re.I)
# Access Point / etykieta-punkt = upsOpt=2 → poza fazą 1.
_RE_ACCESSPOINT = re.compile(r"ETYKIETA_PUNKT|ACCESS[_\s]?POINT|UPS_ETYKIETA|punkt\s+ups", re.I)
_RE_PZ = re.compile(r"\bpz\s*=?\s*(pz\d{1,2}[ab]?)", re.I)
_RE_DATE_ISO = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
# Data DD.MM[.YYYY] w pobliżu słowa „odbiór/termin/pickup".
_RE_DATE_DM = re.compile(
    r"(?:odbi[oó]r|termin|pickup)[^0-9]{0,14}(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](20\d{2}))?", re.I)


def _kurier_norm(s: str) -> str:
    return re.sub(r"[\s_]", "", str(s or "")).upper()


def _pickup_iso(tresc: str) -> Optional[str]:
    """Data odbioru → 'yyyy-MM-dd'. ISO wprost, albo DD.MM[.YYYY] przy słowie odbiór/termin."""
    m = _RE_DATE_ISO.search(tresc)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _RE_DATE_DM.search(tresc)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else datetime.now().year
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _fromdb():
    return {"value": None, "fromDb": True}


def parsuj_zlecenie(tresc, *, numer=None, kto=None, source="szturchacz", grupa=None) -> Optional[dict]:
    """Buduje dokument awizacji z treści zlecenia kuriera — TYLKO jeśli faza 1 (UPS+skrzynia+odbiór u klienta).
    Zwraca dict (bez id/created_at — te dokłada store) albo None gdy poza zakresem fazy 1. Nigdy nie rzuca."""
    if not isinstance(tresc, str) or not tresc.strip():
        return None
    # nrZam (z parametru albo z treści "Zamówienie: NNN")
    nr = numer
    if not nr:
        m = _RE_NRZAM.search(tresc)
        nr = m.group(1) if m else None
    digits = re.sub(r"\D", "", str(nr or ""))
    if not digits:
        return None
    nrZam = int(digits)

    # FAZA 1: UPS. Jawny inny kurier ("Kurier: FEDEX/SCHENKER") → poza zakresem.
    mk = _RE_KURIER.search(tresc)
    if mk and _kurier_norm(mk.group(1)) not in ("UPS",):
        return None
    if not _RE_UPS.search(tresc):
        return None
    # SKRZYNIA only; kolektor bez skrzyni → poza zakresem.
    if _RE_KOLEKTOR.search(tresc) and not _RE_SKRZYNIA.search(tresc):
        return None
    if not _RE_SKRZYNIA.search(tresc):
        return None
    # Access Point (upsOpt=2) → poza fazą 1.
    if _RE_ACCESSPOINT.search(tresc):
        return None

    mp = _RE_PZ.search(tresc)
    pz = mp.group(1).lower() if mp else None
    pickup = _pickup_iso(tresc)

    return {
        "status": "nowe",
        "dedup_key": str(nrZam),
        "source": source or "szturchacz",
        "sprawa": {
            "nrZam": nrZam, "pz": pz, "grupa": grupa,
            "kto": kto or "chatoszturek", "forum_post_id": 0,
        },
        "zlecenie": {
            "nrZam": nrZam,
            "kurierTyp": 1,          # UPS
            "upsOpt": 1,             # odbiór u klienta
            "pickupDate": pickup,    # może być None → apka Eweliny/operator uzupełnia
            "clientData": {k: _fromdb() for k in
                           ("fullName", "phone", "email", "address", "city", "postalCode", "country")},
            "package": dict(PACKAGE_SKRZYNIA),
            "additionalInfo": None,
        },
        "wynik": None,
    }


if __name__ == "__main__":
    # UPS skrzynia odbiór u klienta → awizacja
    t1 = "Zamówienie: 378663\nPZ=PZ6\nKurier: UPS\nTOWAR_TYP: SKRZYNIA\ntermin odbioru: 01.07.2026"
    z = parsuj_zlecenie(t1, kto="chatoszturek", source="wiezowiec", grupa="DE")
    assert z and z["zlecenie"]["kurierTyp"] == 1 and z["zlecenie"]["upsOpt"] == 1, z
    assert z["zlecenie"]["pickupDate"] == "2026-07-01", z["zlecenie"]["pickupDate"]
    assert z["dedup_key"] == "378663" and z["sprawa"]["pz"] == "pz6"
    assert z["zlecenie"]["clientData"]["address"] == {"value": None, "fromDb": True}
    # poza fazą 1: FedEx / kolektor / Access Point / brak skrzyni (numery 4-7 cyfr jak w realu)
    assert parsuj_zlecenie("Zamówienie: 100001\nKurier: FEDEX\nTOWAR_TYP: SKRZYNIA\nodbiór 01.07") is None
    assert parsuj_zlecenie("Zamówienie: 100002\nKurier: UPS\nTOWAR_TYP: KOLEKTOR\nodbiór 01.07") is None
    assert parsuj_zlecenie("Zamówienie: 100003\nKurier: UPS\nTOWAR_TYP: SKRZYNIA\nUPS_ETYKIETA_PUNKT") is None
    assert parsuj_zlecenie("Zamówienie: 100004\nKurier: UPS\nbrak typu\nodbiór 01.07") is None
    # data ISO + DD.MM bez roku
    assert parsuj_zlecenie("Zamówienie: 100005 UPS SKRZYNIA pickup 2026-08-15")["zlecenie"]["pickupDate"] == "2026-08-15"
    z6 = parsuj_zlecenie("Zamówienie: 100006 UPS skrzynia termin odbioru: 05.07")
    assert z6["zlecenie"]["pickupDate"].endswith("-07-05"), z6["zlecenie"]["pickupDate"]
    # numer z parametru (gdy w treści krótki/brak) — realny przepływ podaje numer=...
    assert parsuj_zlecenie("UPS skrzynia odbiór 01.07", numer="378663")["zlecenie"]["nrZam"] == 378663
    # nigdy nie rzuca
    assert parsuj_zlecenie(None) is None and parsuj_zlecenie("") is None and parsuj_zlecenie(123) is None
    print("awizacje.py: sanity OK")
