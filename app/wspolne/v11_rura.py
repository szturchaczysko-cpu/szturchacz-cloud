"""
RURA do kontenera v11 — przelotka `/v11/…` → serwis kontener-v11 (pas ARTURA).

Po co (decyzja właściciela 2026-07-03): przyciski nad oknami porównywarki mają WSZCZEPIAĆ
operatora i wsad do okna v11 „jak ręka robota" — a przeglądarka pozwala sięgać do ramki
WYŁĄCZNIE w obrębie tej samej domeny. Rura serwuje kontener pod NASZĄ domeną (`/v11/`),
pliki v11 pozostają NIETKNIĘTE (zmienia się tylko adres, pod którym widzi go przeglądarka).

Mechanika: HTTP przepuszczane strumieniowo; kanał na żywo Streamlita (websocket
`_stcore/stream`) mostkowany dwukierunkowo. Origin do upstreamu ustawiamy na jego własny
(Streamlit odrzuca obce originy na WS). Aktywna tylko gdy env `V11_UPSTREAM` ustawione —
bez niego trasy zwracają 503 (bezpieczny default, jak BRAMA_WA_WEBHOOK_TOKEN).

Uwaga dostępowa: kontener i tak jest publiczny pod własnym adresem (as-is, ma stare
logowanie v11) — rura nie otwiera niczego nowego; dokument główny dodatkowo za SSO operatora.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, Response

from .. import config, sso

log = logging.getLogger("v11_rura")

router = APIRouter()

# Nagłówki transportowe — nie wolno ich przenosić między połączeniami (HTTP hop-by-hop).
_HOP = {"host", "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
        "te", "trailers", "transfer-encoding", "upgrade", "content-length", "accept-encoding"}


def _upstream() -> str:
    return config.V11_UPSTREAM


@router.api_route("/v11", methods=["GET"], include_in_schema=False)
async def v11_korzen(request: Request):
    # Bez ukośnika względne ścieżki zasobów Streamlita by się rozjechały.
    return RedirectResponse("/v11/", status_code=307)


@router.api_route("/v11/{sciezka:path}",
                  methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
                  include_in_schema=False)
async def v11_http(request: Request, sciezka: str):
    up = _upstream()
    if not up:
        return Response("Rura v11 wyłączona (brak V11_UPSTREAM).", status_code=503)
    # Dokument główny za SSO operatora (reszta zasobów leci wolno — kontener i tak publiczny).
    if sciezka in ("", "index.html") and not sso.read_operator(request):
        return RedirectResponse(config.PULPIT_URL, status_code=303)
    import httpx
    cel = f"{up}/{sciezka}"
    if request.url.query:
        cel += "?" + request.url.query
    naglowki = {k: v for k, v in request.headers.items() if k.lower() not in _HOP}
    tresc = await request.body()
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as klient:
        try:
            odp = await klient.request(request.method, cel, headers=naglowki, content=tresc)
        except httpx.HTTPError as e:
            log.error("[v11_rura] %s %s → %s", request.method, cel, type(e).__name__)
            return Response("Kontener v11 nieosiągalny przez rurę.", status_code=502)
    zwrot = {k: v for k, v in odp.headers.items()
             if k.lower() not in _HOP and k.lower() != "content-encoding"}
    return Response(odp.content, status_code=odp.status_code, headers=zwrot)


@router.websocket("/v11/{sciezka:path}")
async def v11_ws(ws: WebSocket, sciezka: str):
    up = _upstream()
    if not up:
        await ws.close(code=1013)
        return
    import websockets
    cel = up.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/" + sciezka
    if ws.url.query:
        cel += "?" + ws.url.query
    # Streamlit sprawdza Origin na WS — podajemy jego własny, subprotokoły przekazujemy 1:1.
    subproto = ws.headers.get("sec-websocket-protocol")
    try:
        polacz = websockets.connect(
            cel, origin=up, subprotocols=[s.strip() for s in subproto.split(",")] if subproto else None,
            max_size=32 * 1024 * 1024, open_timeout=20)
        upstream = await polacz
    except Exception as e:  # noqa: BLE001
        log.error("[v11_rura] WS connect %s → %s", cel, type(e).__name__)
        await ws.close(code=1013)
        return
    await ws.accept(subprotocol=getattr(upstream, "subprotocol", None))

    async def do_gory():
        try:
            while True:
                wiad = await ws.receive()
                if wiad.get("type") == "websocket.disconnect":
                    break
                if wiad.get("bytes") is not None:
                    await upstream.send(wiad["bytes"])
                elif wiad.get("text") is not None:
                    await upstream.send(wiad["text"])
        except (WebSocketDisconnect, Exception):  # noqa: BLE001
            pass

    async def w_dol():
        try:
            async for wiad in upstream:
                if isinstance(wiad, (bytes, bytearray)):
                    await ws.send_bytes(bytes(wiad))
                else:
                    await ws.send_text(wiad)
        except Exception:  # noqa: BLE001
            pass

    zadania = [asyncio.create_task(do_gory()), asyncio.create_task(w_dol())]
    try:
        await asyncio.wait(zadania, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for z in zadania:
            z.cancel()
        try:
            await upstream.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
