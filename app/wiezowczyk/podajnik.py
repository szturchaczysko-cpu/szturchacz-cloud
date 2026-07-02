"""
WIEŻOWCZYK — podajnik spraw (pas ARTURA; ociosany spadkobierca starego Wieżowca).

GŁUPI z definicji (decyzja właściciela): podaje SUROWY wsad spraw austauschowych z bazy
franciszkańskiej — chronologicznie od najnowszych, w zakresie dat, albo konkretny numer
(„odwrotny zam"). BEZ parsowania, przeliczania AI, priorytetów, uszków/świnek, pakowania
w paczki. Przeliczanie = silniki (v11/chudy) w bestchudy; priorytety = rozrzutnik (później).

Źródło (atlas baz on-prem):
- STEEPC.dbo.v_austachStatusProsty  — MASTER spraw austauschowych (nrZam, data, kraj, klient…),
- SZTURCHACZ.dbo.ItemsTag           — aktualny tag sprawy (ContentTag DSL), most: DokId=austauch_id, DokTyp=7.
Dostęp WYŁĄCZNIE przez wspólny silnik (app/wspolne/klient_baz.py → db-broker / lokalny silnik_baz).
READ-ONLY. Wejścia twardo walidowane (regex-whitelist) — do SQL nie wchodzi nic spoza wzorca.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

_DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")   # YYYY-MM-DD
_ZAM_RE = re.compile(r"^\d{4,9}$")               # numer zamówienia = same cyfry
_LIMIT_MAX = 200


def _waliduj(od: str, do: str, zam: str, limit: int) -> Tuple[str, str, str, int, Optional[str]]:
    od, do, zam = (od or "").strip(), (do or "").strip(), (zam or "").strip()
    if od and not _DATA_RE.match(od):
        return "", "", "", 0, "Data OD musi być w formacie RRRR-MM-DD."
    if do and not _DATA_RE.match(do):
        return "", "", "", 0, "Data DO musi być w formacie RRRR-MM-DD."
    if zam and not _ZAM_RE.match(zam):
        return "", "", "", 0, "Numer zamówienia to same cyfry."
    return od, do, zam, max(1, min(int(limit or 50), _LIMIT_MAX)), None


def _sql(od: str, do: str, zam: str, limit: int) -> str:
    # Wartości przeszły regex-whitelist (same cyfry/format daty) — wstawienie jest bezpieczne.
    warunki = []
    if zam:
        warunki.append(f"p.zknzamnr = {zam}")
    if od:
        warunki.append(f"p.data_zama >= '{od}'")
    if do:
        warunki.append(f"p.data_zama <= '{do}'")
    where = ("where " + " and ".join(warunki)) if warunki else ""
    return f"""
select top {limit}
       p.zknzamnr, p.data_zama, p.kraj, p.kaCountry, p.rodzaj_zama, p.zamRekl,
       p.czy_austauch_zakonczony, p.ReklFlag, p.KurFlag, p.Zoltek,
       p.klient_nazwa, p.kakMail, p.ktTelNr, p.austauch_id, t.ContentTag
from dbo.v_austachStatusProsty p
left join SZTURCHACZ.dbo.ItemsTag t on t.DokId = p.austauch_id and t.DokTyp = 7
{where}
order by p.data_zama desc, p.zknzamnr desc
"""


def suchy_wsad(r: dict) -> str:
    """Jedna linia SUROWEGO wsadu — ten sam kształt dla obu silników (format do przypięcia
    w styku FEED z bestchudy; trzymamy się stylu starego wsadu „NrZam: … | kraj | …")."""
    czesci = [f"NrZam: {r.get('zknzamnr')}", str(r.get("kraj") or r.get("kaCountry") or "?"),
              str(r.get("rodzaj_zama") or "?")]
    if r.get("ReklFlag"):
        czesci.append("REKLAMACJA")
    if r.get("zamRekl"):
        czesci.append(str(r["zamRekl"]))
    czesci.append(f"z dnia {r.get('data_zama')}")
    if r.get("klient_nazwa"):
        czesci.append(f"klient: {r['klient_nazwa']}")
    tag = str(r.get("ContentTag") or "").strip()
    czesci.append(f"tag: {tag if tag else '—'}")
    return " | ".join(czesci)


def pobierz(od: str = "", do: str = "", zam: str = "", limit: int = 50) -> dict:
    """Suchy wsad spraw: najnowsze w zakresie dat albo konkretny nrZam (odwrotny zam).
    Zwraca {ok, sprawy:[{...pola, suchy_wsad}]} albo {ok:False, message} gdy źródło niedostępne."""
    od, do, zam, limit, blad = _waliduj(od, do, zam, limit)
    if blad:
        return {"ok": False, "message": blad}
    from ..wspolne import klient_baz
    try:
        wiersze: List[dict] = klient_baz.czytaj("STEEPC", _sql(od, do, zam, limit), limit=limit)
    except Exception as e:  # noqa: BLE001 — brak brokera/tunelu nie może wywalać zaplecza
        return {"ok": False, "message": f"Źródło spraw niedostępne ({type(e).__name__}). "
                                        "Sprawdź ONPREM_DB_BROKER_URL (prod) / tunel (dev)."}
    sprawy = []
    for r in wiersze:
        r = dict(r)
        r["data_zama"] = str(r.get("data_zama") or "")[:10]
        r["suchy_wsad"] = suchy_wsad(r)
        sprawy.append(r)
    return {"ok": True, "sprawy": sprawy, "liczba": len(sprawy)}


if __name__ == "__main__":
    # sanity — walidacja i format wsadu (bez dotykania bazy)
    assert _waliduj("2026-07-01", "", "", 50)[4] is None
    assert _waliduj("1.07.2026", "", "", 50)[4] is not None       # zły format daty
    assert _waliduj("", "", "382576; drop", 50)[4] is not None    # nie-cyfry w zam → odrzut
    assert _waliduj("", "", "", 9999)[3] == _LIMIT_MAX            # limit przycięty
    w = suchy_wsad({"zknzamnr": 382576, "kraj": "DE", "rodzaj_zama": "KOLEKTORY",
                    "ReklFlag": True, "data_zama": "2026-07-01", "klient_nazwa": "Firma X",
                    "ContentTag": "c#:01.07;pz=pz2"})
    assert w == "NrZam: 382576 | DE | KOLEKTORY | REKLAMACJA | z dnia 2026-07-01 | klient: Firma X | tag: c#:01.07;pz=pz2", w
    assert "tag: —" in suchy_wsad({"zknzamnr": 1, "kraj": "DE", "rodzaj_zama": "SKRZYNIE", "data_zama": "2026-01-01"})
    assert "select top 50" in _sql("", "", "", 50) and "where" not in _sql("", "", "", 50)
    assert "p.zknzamnr = 382576" in _sql("", "", "382576", 50)
    print("podajnik.py: sanity OK")
