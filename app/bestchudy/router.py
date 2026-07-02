"""
BESTCHUDY — porównywarka v11 ‖ chudy (ekran PRACA; pas Sylwii).

Granice pasa (COORDYNACJA → rozpis pkt 2 + ŁĄCZNIKI): importy spoza tego katalogu WYŁĄCZNIE
`app.sso.read_operator` oraz fasada `app.wspolne.styki`; kolekcje `bc_*` przez własny bc_store;
wspólnych plików nie dotykamy — wpięcie w apkę to jedna linijka w main.py (już istnieje).

Ekran (decyzja właściciela 2026-07-02): split view w jednej karcie — lewa strona = kontener v11
w RAMCE (env `V11_URL`; CSP `frame-src` dokłada koordynator przy wpięciu), prawa = chudy przez
styki. „KOPIUJ WSAD" daje OBU stronom identyczną sklejkę (PLAN.md §4–§5). Każde wyjście chudego
przez zawór `styki.wyslij` (klik operatora; WEM_WYSYLKA domyślnie sucho).
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..sso import read_operator  # jedyny dozwolony wspólny import poza fasadą styki
from . import bc_store, logika

router = APIRouter(prefix="/bestchudy", tags=["bestchudy"])

_KATALOG = os.path.dirname(os.path.abspath(__file__))
_szablony = Jinja2Templates(directory=os.path.join(_KATALOG, "templates"))
# Whitelist plików statycznych serwowanych trasą (mountu /static nie ruszamy — wspólny)
_STATIC = {"bc.css": "text/css; charset=utf-8", "bc.js": "text/javascript; charset=utf-8"}


def _v11_url() -> str:
    url = os.environ.get("V11_URL", "").strip()
    if url and "embed=" not in url:
        url += ("&" if "?" in url else "?") + "embed=true"
    return url


def _same_origin(request: Request) -> bool:
    # Kopia bezpiecznika z main.py (importować nie wolno — main importuje ten moduł = cykl).
    sfs = request.headers.get("sec-fetch-site")
    if sfs is not None:
        return sfs == "same-origin"
    origin = request.headers.get("origin")
    if origin is not None:
        return urlparse(origin).netloc == (request.headers.get("host") or "")
    return True


async def _json(request: Request) -> dict:
    try:
        dane = await request.json()
        return dane if isinstance(dane, dict) else {}
    except Exception:
        return {}


def _brama_api(request: Request):
    """Bramka API: operator z SSO (każdy endpoint sam pilnuje!) + same-origin na POST."""
    op = read_operator(request)
    if not op:
        return None, JSONResponse({"ok": False, "message": "Zaloguj się przez Pulpit."}, status_code=401)
    if request.method == "POST" and not _same_origin(request):
        return None, JSONResponse({"ok": False, "message": "Nieprawidłowe pochodzenie żądania."},
                                  status_code=403)
    return op, None


# --- Ekran -----------------------------------------------------------------------
@router.get("", response_class=HTMLResponse)
async def ekran(request: Request):
    op = read_operator(request)
    if not op:
        return RedirectResponse(os.environ.get("PULPIT_URL", "/"), status_code=303)
    return _szablony.TemplateResponse("porownywarka.html", {
        "request": request,
        "operator": op,
        "v11_url": _v11_url(),
        "tryby": logika.TRYBY,
        "dzis": logika.dzis(),
    })


@router.get("/static/{plik}")
async def statyczne(plik: str):
    if plik not in _STATIC:
        return JSONResponse({"ok": False, "message": "Nie ma takiego pliku."}, status_code=404)
    return FileResponse(os.path.join(_KATALOG, "static", plik), media_type=_STATIC[plik])


# --- FEED (styk daj-sprawę; B3 — koniec ręcznego wklejania) --------------------------
@router.get("/api/sprawy")
async def sprawy(request: Request):
    op, blad = _brama_api(request)
    if blad:
        return blad
    q = request.query_params
    zam = str(q.get("zam") or "").strip()
    if zam and not logika.poprawny_zam(zam):
        return JSONResponse({"ok": False, "message": "Numer zamówienia to 4-9 cyfr."}, status_code=400)
    try:
        limit = int(q.get("limit") or 10)
    except ValueError:
        limit = 10
    limit = max(1, min(limit, 50))

    from ..wspolne import styki  # fasada
    try:
        wynik = styki.daj_sprawe(zam=zam, limit=limit)
    except Exception as e:  # noqa: BLE001 — pas bezpieczeństwa: nigdy surowy 500 bez JSON-a
        return JSONResponse({"ok": False, "message": "Awaria podajnika po stronie serwera "
                            f"({type(e).__name__}) — szczegóły w logach usługi (koordynator)."},
                            status_code=502)
    if not wynik.get("ok"):
        # wejścia zwalidowane wyżej → ok:False = źródło niedostępne (upstream)
        return JSONResponse(wynik, status_code=502)
    sprawy_ui = []
    for s in wynik.get("sprawy") or []:
        wsad_panel = str(s.get("wsad_panel") or "")
        sprawy_ui.append({
            "nrzam": str(s.get("zknzamnr") or ""),
            "data": str(s.get("data_zama") or ""),
            "kraj": str(s.get("kaCountry") or s.get("kraj") or ""),
            "opis": str(s.get("suchy_wsad") or ""),
            "wsad_panel": wsad_panel,
            # Tag siedzi JUŻ w wsad_panel (wzorce §5.1) — pole TAG w UI zostaje puste.
            "koperta_tekst": logika.zloz_koperte(s.get("koperta")),
            "ma_karte": bool(wsad_panel.strip()),
        })
    return {"ok": True, "sprawy": sprawy_ui, "liczba": len(sprawy_ui)}


# --- Chudy (prawa strona) ----------------------------------------------------------
@router.post("/api/policz")
async def policz(request: Request):
    op, blad = _brama_api(request)
    if blad:
        return blad
    d = await _json(request)
    historia = d.get("historia") or []
    if not isinstance(historia, list):
        return JSONResponse({"ok": False, "message": "Pole historia musi być listą."}, status_code=400)
    kontynuacja = logika.przytnij(d.get("kontynuacja"), 4000)
    if kontynuacja:
        blad_historii = logika.waliduj_historie(historia)
        if blad_historii:
            return JSONResponse({"ok": False, "message": blad_historii}, status_code=400)
        # Czyste dicty: zrzucamy nadmiarowe klucze, utrwalamy kontrakt ról (user/model).
        historia = [{"role": m["role"], "content": m["content"]} for m in historia]
        wejscie_bazowe, rolka = kontynuacja, ""
    else:
        za_dlugi = logika.wsad_za_dlugi(d.get("wsad_panel"), d.get("koperta"), d.get("tag"))
        if za_dlugi:
            return JSONResponse({"ok": False, "message": za_dlugi}, status_code=400)
        wejscie_bazowe = logika.sklej_wsad(d.get("wsad_panel"), d.get("koperta"), d.get("tag"))
        rolka = logika.oczysc(d.get("rolka"))
        if len(rolka) > logika.LIMIT_TEKSTU:
            return JSONResponse({"ok": False, "message": "Rolka za długa (maks. 20000 znaków)."},
                                status_code=400)
        historia = []
    if not wejscie_bazowe:
        return JSONResponse({"ok": False, "message": "Pusty wsad."}, status_code=400)

    from ..wspolne import styki  # fasada — leniwie, żeby import routera nie budował magazynów
    try:
        wynik = styki.policz_chudego(wejscie_bazowe, rolka, historia)
    except Exception as e:  # noqa: BLE001 — pas bezpieczeństwa: nigdy surowy 500 bez JSON-a
        return JSONResponse({"ok": False, "message": "Awaria silnika po stronie serwera "
                            f"({type(e).__name__}) — szczegóły w logach usługi (koordynator)."},
                            status_code=502)
    if not wynik.get("ok"):
        return JSONResponse(wynik, status_code=502)
    # Lustro budowy wejścia w styki.policz_chudego — klient trzyma wierną historię rozmowy.
    wejscie = wejscie_bazowe + ("\n\n[ROLKA Z KANAŁU]\n" + rolka if rolka else "")
    return {"ok": True, "odpowiedz": wynik["odpowiedz"], "prompt": wynik.get("prompt", ""),
            "wejscie": wejscie, "wejscie_bazowe": wejscie_bazowe, "rolka": rolka,
            "nrzam": logika.wyluskaj_nrzam(wejscie)}


# --- Werdykty / porównania ----------------------------------------------------------
@router.post("/api/porownanie")
async def zapisz_porownanie(request: Request):
    op, blad = _brama_api(request)
    if blad:
        return blad
    d = await _json(request)
    komunikat = logika.waliduj_werdykty(d.get("werdykt_v11"), d.get("werdykt_chudy"),
                                        d.get("komentarz"))
    if komunikat:
        return JSONResponse({"ok": False, "message": komunikat}, status_code=400)
    if len(logika.oczysc(d.get("wsad"))) > logika.LIMIT_SKLEJKI:
        return JSONResponse({"ok": False, "message": "Wsad za długi — porównanie odrzucone "
                            "(nie tniemy po cichu)."}, status_code=400)
    if len(logika.oczysc(d.get("rolka"))) > logika.LIMIT_TEKSTU:
        return JSONResponse({"ok": False, "message": "Rolka za długa (maks. 20000 znaków)."},
                            status_code=400)
    rec = logika.nowe_porownanie(d, op)
    if not rec["wsad"]:
        return JSONResponse({"ok": False, "message": "Puste porównanie — najpierw wsad."},
                            status_code=400)
    if not rec["chudy_odpowiedz"]:
        return JSONResponse({"ok": False, "message": "Brak odpowiedzi chudego — najpierw "
                            "POLICZ CHUDEGO."}, status_code=400)
    bc_store.get_store().dodaj_porownanie(rec)
    return {"ok": True, "id": rec["id"], "dzien": rec["dzien"], "odrzut": logika.czy_odrzut(rec)}


@router.get("/api/porownania")
async def porownania(request: Request):
    op, blad = _brama_api(request)
    if blad:
        return blad
    q = request.query_params
    dzien = str(q.get("dzien") or "")
    if dzien and not logika.poprawny_dzien(dzien):
        return JSONResponse({"ok": False, "message": "Dzień w formacie RRRR-MM-DD."}, status_code=400)
    odrzuty = str(q.get("odrzuty") or "") in ("1", "true", "tak")
    magazyn = bc_store.get_store()
    lst = magazyn.porownania(dzien=dzien, odrzuty=odrzuty, limit=200)
    # Liczby dnia z OSOBNEGO odczytu (pełen dzień, bez filtra odrzutów) — inaczej przy
    # odrzuty=1 „porównań" znaczyłoby „odrzutów", a bez dnia mieszałoby dni.
    liczby = logika.liczby_dnia(magazyn.porownania(dzien=dzien, limit=500)) if dzien else None
    return {"ok": True, "porownania": lst, "liczba": len(lst), "liczby": liczby}


# --- Ocena na końcu sesji ------------------------------------------------------------
@router.post("/api/ocena")
async def zapisz_ocene(request: Request):
    op, blad = _brama_api(request)
    if blad:
        return blad
    d = await _json(request)
    dzien = d.get("dzien") if logika.poprawny_dzien(d.get("dzien")) else logika.dzis()
    dnia = bc_store.get_store().porownania(dzien=dzien, limit=500)
    rec = logika.nowa_ocena({"dzien": dzien, "uwagi": d.get("uwagi")}, op, logika.liczby_dnia(dnia))
    bc_store.get_store().dodaj_ocene(rec)
    return {"ok": True, "id": rec["id"], "dzien": rec["dzien"], "liczby": rec["liczby"]}


@router.get("/api/oceny")
async def oceny(request: Request):
    op, blad = _brama_api(request)
    if blad:
        return blad
    dzien = str(request.query_params.get("dzien") or "")
    if dzien and not logika.poprawny_dzien(dzien):
        return JSONResponse({"ok": False, "message": "Dzień w formacie RRRR-MM-DD."}, status_code=400)
    return {"ok": True, "oceny": bc_store.get_store().oceny(dzien=dzien)}


# --- Wyjście chudego (zawór skrzynki) --------------------------------------------------
@router.post("/api/wyslij")
async def wyslij(request: Request):
    op, blad = _brama_api(request)
    if blad:
        return blad
    d = await _json(request)
    if d.get("zgoda") is not True:
        return JSONResponse({"ok": False, "message": "Bezpiecznik: brak zgody operatora (klik)."},
                            status_code=400)
    from ..wspolne import styki
    try:
        wynik = styki.wyslij(
            str(d.get("kanal") or ""), logika.przytnij(d.get("adresat"), 300),
            logika.przytnij(d.get("tresc"), 8000), operator_pid=op.get("pid", ""),
            zgoda=True, subject=logika.przytnij(d.get("subject"), 300),
        )
    except Exception as e:  # noqa: BLE001 — pas bezpieczeństwa: nigdy surowy 500 bez JSON-a
        return JSONResponse({"ok": False, "message": "Awaria zaworu po stronie serwera "
                            f"({type(e).__name__}) — szczegóły w logach usługi (koordynator)."},
                            status_code=502)
    # ok:false z kluczem tryb=live występuje wyłącznie przy awarii bramy WEM (upstream) → 502.
    kod = 200 if wynik.get("ok") else (502 if wynik.get("tryb") == "live" else 400)
    return JSONResponse(wynik, status_code=kod)
