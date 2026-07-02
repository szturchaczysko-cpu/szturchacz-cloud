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

# re.ASCII: bez tego \d łapie też cyfry Unicode (np. arabskie ٣٨١٨٧٩) → wartość przechodzi
# walidację, a wybucha dopiero w SQL. Zgłoszone przez stronę Sylwii (przegląd adwersarialny B3).
_DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$", re.ASCII)   # YYYY-MM-DD
_ZAM_RE = re.compile(r"^\d{4,9}$", re.ASCII)               # numer zamówienia = same cyfry
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
    # Widok PEŁNY (v_austachStatus, nie Prosty): ma kaCountry/lindexy/etapy/doręczenia/listy/eBay —
    # komplet pod WSAD PANEL wg wzorców produkcyjnych Sylwii (PLAN.md §5.1).
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
       p.zknzamnr, p.data_zama, p.zknusertw, p.klient_nazwa, p.kakMail, p.ktTelNr,
       p.kraj, p.kaCountry, p.rodzaj_zama, p.zamRekl,
       p.czy_austauch_zakonczony, p.ReklFlag, p.KurFlag, p.Zoltek,
       p.stage, p.active, p.date, p.dataZamKur, p.reklamacja,
       p.ua_ups_StatusDesc, p.ua_ups_StatusDate, p.lindexy,
       p.ua_ups_TrackingNr, p.zwneTrackingNumber, p.upsFirmaKurierska,
       p.EbayLogin, p.buyerNick, p.Data_wyslania_m,
       p.austauch_id, t.ContentTag
from dbo.v_austachStatus p
left join SZTURCHACZ.dbo.ItemsTag t on t.DokId = p.austauch_id and t.DokTyp = 7
{where}
order by p.data_zama desc, p.zknzamnr desc
"""


def _sql_koperty(ids: list) -> str:
    """Kopertki operatorów (bloki COP#) — SZTURCHACZ.dbo.Comment, most: austaush = austauch_id.
    `ids` to inty prosto z bazy (nie wejście użytkownika)."""
    lista = ",".join(str(int(i)) for i in ids)
    return f"""
select austaush, userName, [date], contentMsg
from SZTURCHACZ.dbo.Comment
where austaush in ({lista}) and deleteCom = 0
order by [date]
"""


# Słownik kurierów odczytany EMPIRYCZNIE z wzorców produkcyjnych (381879=1=UPS, 381865=5=FEDEX).
# Inne wartości → surowa liczba; mapę uzupełnia strona Sylwii/panel, gdy wypłynie nowy kurier.
_KURIERZY = {1: "UPS", 5: "FEDEX"}


def _data(v) -> str:
    """Data w formacie panelu RRRR-MM-DD; przyjmuje date/datetime/Timestamp/str ('20260624' też)."""
    if v is None:
        return ""
    s = str(v).strip()
    if re.fullmatch(r"\d{8}", s):  # yyyymmdd (ua_ups_StatusDate)
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return s[:10] if len(s) >= 10 else s


def wsad_panel(r: dict) -> str:
    """WSAD PANEL — DOKŁADNIE układ z wzorców produkcyjnych Sylwii (PLAN.md §5.1):
    nagłówek → [tag] → etapy/reklamacja/doręczenie → lindexy → kurier → list + eBay.
    v11 czyta wsad SEMANTYCZNIE, ale kolejność i sąsiedztwa (data przed Delivered,
    list+login+nick w ostatniej linii) odtwarzamy wiernie."""
    naglowek = (f"{r.get('zknzamnr')} \t{_data(r.get('data_zama'))} \t{r.get('zknusertw') or ''} "
                f"\t{r.get('klient_nazwa') or ''} \t{r.get('kakMail') or ''} \t{r.get('ktTelNr') or ''} "
                f"\t{r.get('kaCountry') or r.get('kraj') or ''} \t")
    czesci = [naglowek, ""]
    tag = str(r.get("ContentTag") or "").strip()
    if tag:
        czesci += [f"    {tag}", ""]
    biezacy = "Nie wysłano żadnego maila" if not r.get("Data_wyslania_m") \
        else f"Mail wysłany {_data(r.get('Data_wyslania_m'))}"
    kolejny = f"Etap {r.get('stage')} ({'Aktywny' if r.get('active') else 'Nieaktywny'})" \
        if r.get("stage") is not None else ""
    czesci.append(f"\t{biezacy} \t\t{kolejny} \t{_data(r.get('date'))} \t{_data(r.get('dataZamKur'))}"
                  f"\t{r.get('reklamacja') or 'brak'} \t{_data(r.get('ua_ups_StatusDate'))}")
    if r.get("ua_ups_StatusDesc"):
        czesci.append(str(r["ua_ups_StatusDesc"]))  # 'Delivered'/'DELIVERED' — wielkość liter jak w bazie
    czesci += ["\t", f"\t{r.get('lindexy') or ''} \t\t\t", ""]
    kurier = _KURIERZY.get(r.get("upsFirmaKurierska"),
                           str(r.get("upsFirmaKurierska") or "")) if r.get("upsFirmaKurierska") else ""
    czesci.append(f"\t{kurier}")
    listy = " ".join(x for x in (r.get("ua_ups_TrackingNr"), r.get("zwneTrackingNumber")) if x)
    ostatnia = listy
    if r.get("EbayLogin") or r.get("buyerNick"):
        ostatnia = f"{listy} \t{r.get('EbayLogin') or ''} \t{r.get('buyerNick') or ''}"
    czesci.append(ostatnia)
    return "\n".join(czesci)


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
    # Kopertki (COP#) jednym strzałem dla całej paczki spraw; błąd kopert nie wywala podajnika.
    koperty: dict = {}
    ids = [r.get("austauch_id") for r in wiersze if r.get("austauch_id")]
    if ids:
        try:
            for k in klient_baz.czytaj("STEEPC", _sql_koperty(ids), limit=2000):
                koperty.setdefault(k["austaush"], []).append(
                    {"kto": k.get("userName") or "", "kiedy": _data(k.get("date")),
                     "tresc": str(k.get("contentMsg") or "")})
        except Exception:  # noqa: BLE001
            pass
    sprawy = []
    for r in wiersze:
        r = dict(r)
        for k in ("data_zama", "date", "dataZamKur", "Data_wyslania_m"):
            r[k] = _data(r.get(k))
        r["koperta"] = koperty.get(r.get("austauch_id"), [])
        r["suchy_wsad"] = suchy_wsad(r)
        r["wsad_panel"] = wsad_panel(r)
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
