"""
Szturchacz — kafelek Pulpitu. main.py trzyma TYLKO trasy i montaż (chude).
Brama tożsamości operatora = sso.read_operator() (kontrakt z Pulpitem). Panel koordynatora
za rolą 'koordynator' (z Pulpitu) lub lokalnym logowaniem KOORD_PASSWORD (gdy SSO wyłączone).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.concurrency import run_in_threadpool

from . import config, deps, security_panel, sso
from .bestchudy.router import router as bestchudy_router  # gniazdo modułu Sylwii (pas: bestchudy)
from .cases_loader import autopilot as autopilot_mod
from .koordynator import panel
from .operator import flow

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

_ksession = URLSafeTimedSerializer(config.SECRET_KEY, salt="szt-koord")
KSESSION_MAX_AGE = 8 * 60 * 60


@asynccontextmanager
async def lifespan(app: FastAPI):
    deps.seed_dev()
    yield


app = FastAPI(title="Szturchacz", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.include_router(bestchudy_router)  # JEDYNE wpięcie pasa bestchudy we wspólny kod


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; "
        "script-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    response.headers["Cache-Control"] = "no-cache" if request.url.path.startswith("/static/") else "no-store"
    if config.COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# --- Pomocnicze ----------------------------------------------------------------
def _same_origin(request: Request) -> bool:
    sfs = request.headers.get("sec-fetch-site")
    if sfs is not None:
        return sfs == "same-origin"
    origin = request.headers.get("origin")
    if origin is not None:
        return urlparse(origin).netloc == (request.headers.get("host") or "")
    return True


async def _json(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def operator_of(request: Request) -> Optional[dict]:
    return sso.read_operator(request)


def koordynator_of(request: Request) -> Optional[dict]:
    op = sso.read_operator(request)
    if op and "koordynator" in op.get("roles", []):
        return op
    tok = request.cookies.get("ksession")
    if tok:
        try:
            _ksession.loads(tok, max_age=KSESSION_MAX_AGE)
            return {"pid": "koord-lokalny", "label": "Koordynator (lokalnie)", "roles": ["koordynator"]}
        except BadSignature:
            return None
    return None


def _csrf_guard(request: Request) -> Optional[JSONResponse]:
    if not _same_origin(request):
        return JSONResponse({"ok": False, "message": "Nieprawidłowe pochodzenie żądania."}, status_code=403)
    return None


# --- Ekran operatora -----------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    operator = operator_of(request)
    if not operator:
        return RedirectResponse(config.PULPIT_URL, status_code=303)
    active = await run_in_threadpool(flow.aktywna_sprawa, operator)
    return templates.TemplateResponse("operator.html", {
        "request": request, "operator": operator, "case": active.to_dict() if active else None,
    })


@app.get("/api/operator/state")
async def operator_state(request: Request):
    operator = operator_of(request)
    if not operator:
        return JSONResponse({"ok": False}, status_code=401)
    active = await run_in_threadpool(flow.aktywna_sprawa, operator)
    grupa = await run_in_threadpool(flow._grupa, operator)
    return {
        "ok": True,
        "operator": {"label": operator.get("label"), "grupa": grupa},
        "case": active.to_dict() if active else None,
        "messages": active.autopilot_messages if active else [],
        "wolne": await run_in_threadpool(deps.cases.wolne_count, grupa),
        "diamenty_dzis": await run_in_threadpool(deps.stats.diamenty_dzis, operator["pid"]),
    }


@app.post("/api/operator/next")
async def operator_next(request: Request):
    err = _csrf_guard(request)
    if err:
        return err
    operator = operator_of(request)
    if not operator:
        return JSONResponse({"ok": False, "message": "Zaloguj się przez Pulpit."}, status_code=401)
    case = await run_in_threadpool(flow.pobierz_sprawe, operator)
    if not case:
        return {"ok": True, "case": None, "message": "Brak gotowych spraw. Spróbuj później."}
    turn = await run_in_threadpool(flow.rozpocznij_rozmowe, case, operator)
    return {"ok": True, "case": case.to_dict(), "turn": turn}


@app.post("/api/operator/message")
async def operator_message(request: Request):
    err = _csrf_guard(request)
    if err:
        return err
    operator = operator_of(request)
    if not operator:
        return JSONResponse({"ok": False}, status_code=401)
    active = await run_in_threadpool(flow.aktywna_sprawa, operator)
    if not active:
        return JSONResponse({"ok": False, "message": "Brak aktywnej sprawy."}, status_code=400)
    text = str((await _json(request)).get("text", "")).strip()
    if not text:
        return JSONResponse({"ok": False, "message": "Pusta wiadomość."}, status_code=400)
    turn = await run_in_threadpool(flow.wyslij_wiadomosc, active, operator, text)
    return {"ok": True, "turn": turn}


@app.post("/api/operator/complete")
async def operator_complete(request: Request):
    err = _csrf_guard(request)
    if err:
        return err
    operator = operator_of(request)
    if not operator:
        return JSONResponse({"ok": False}, status_code=401)
    active = await run_in_threadpool(flow.aktywna_sprawa, operator)
    if not active:
        return JSONResponse({"ok": False, "message": "Brak aktywnej sprawy."}, status_code=400)
    # TAG bierzemy z ostatniej odpowiedzi AI (źródło prawdy decyzji).
    last_model = next((m["content"] for m in reversed(active.autopilot_messages or [])
                       if m.get("role") == "model"), "")
    tag, pz = flow.detect_tag(last_model)
    ok, msg = await run_in_threadpool(flow.domknij, active, operator, tag, pz)
    return {"ok": ok, "message": msg, "tag": tag, "pz": pz}


@app.post("/api/operator/skip")
async def operator_skip(request: Request):
    err = _csrf_guard(request)
    if err:
        return err
    operator = operator_of(request)
    if not operator:
        return JSONResponse({"ok": False}, status_code=401)
    active = await run_in_threadpool(flow.aktywna_sprawa, operator)
    if not active:
        return JSONResponse({"ok": False, "message": "Brak aktywnej sprawy."}, status_code=400)
    powod = str((await _json(request)).get("powod", "")).strip()
    ok, msg = await run_in_threadpool(flow.pomin, active, operator, powod)
    return {"ok": ok, "message": msg}


# --- Panel koordynatora --------------------------------------------------------
@app.get("/koordynator", response_class=HTMLResponse)
async def koord_page(request: Request):
    if not koordynator_of(request):
        return templates.TemplateResponse("koord_login.html", {"request": request})
    return templates.TemplateResponse("koordynator.html", {"request": request})


@app.post("/api/koord/login")
async def koord_login(request: Request):
    if not config.KOORD_PASSWORD:
        return JSONResponse({"ok": False, "message": "Logowanie lokalne wyłączone (brak KOORD_PASSWORD)."},
                            status_code=503)
    password = str((await _json(request)).get("password", ""))
    if not security_panel.constant_time_equals(password, config.KOORD_PASSWORD):
        return JSONResponse({"ok": False, "message": "Błędne hasło."}, status_code=401)
    resp = JSONResponse({"ok": True})
    resp.set_cookie("ksession", _ksession.dumps({"k": 1}), max_age=KSESSION_MAX_AGE,
                    httponly=True, secure=config.COOKIE_SECURE, samesite="strict")
    return resp


def _koord_guard(request: Request):
    if _csrf_guard(request):
        return None, _csrf_guard(request)
    person = koordynator_of(request)
    if not person:
        return None, JSONResponse({"ok": False, "message": "Tylko koordynator."}, status_code=403)
    return person, None


@app.get("/api/koord/overview")
async def koord_overview(request: Request):
    if not koordynator_of(request):
        return JSONResponse({"ok": False}, status_code=403)
    return {"ok": True, **await run_in_threadpool(panel.overview)}


@app.post("/api/koord/ingest")
async def koord_ingest(request: Request):
    _, err = _koord_guard(request)
    if err:
        return err
    payload = await _json(request)
    res = await run_in_threadpool(panel.ingest, str(payload.get("text", "")), str(payload.get("data_obrobki", "")))
    return {"ok": True, **res}


@app.post("/api/koord/config")
async def koord_config(request: Request):
    _, err = _koord_guard(request)
    if err:
        return err
    payload = await _json(request)
    return await run_in_threadpool(panel.set_config, str(payload.get("key", "")), payload.get("value"))


@app.post("/api/koord/operator")
async def koord_operator(request: Request):
    _, err = _koord_guard(request)
    if err:
        return err
    p = await _json(request)
    return await run_in_threadpool(
        panel.upsert_operator, str(p.get("pid", "")).strip(), str(p.get("label", "")).strip(),
        str(p.get("grupa", "")).strip(), bool(p.get("tel")), list(p.get("jezyki") or []),
        str(p.get("forum_nick", "")).strip())


@app.post("/api/koord/operator/delete")
async def koord_operator_delete(request: Request):
    _, err = _koord_guard(request)
    if err:
        return err
    return await run_in_threadpool(panel.remove_operator, str((await _json(request)).get("pid", "")))


@app.post("/api/koord/autopilot/run")
async def koord_autopilot_run(request: Request):
    _, err = _koord_guard(request)
    if err:
        return err
    return await run_in_threadpool(panel.run_autopilot)


@app.get("/api/koord/diamenty")
async def koord_diamenty(request: Request):
    if not koordynator_of(request):
        return JSONResponse({"ok": False}, status_code=403)
    return {"ok": True, **await run_in_threadpool(panel.raport_diamenty, request.query_params.get("data", ""))}


# --- Brama ATA: odbiór WhatsApp ------------------------------------------------
@app.api_route("/api/brama/wa/{token}", methods=["GET", "POST"])
async def brama_wa_webhook(request: Request, token: str):
    """Publiczny odbiór pusha WA z bramy ATA. Uwierzytelnienie = token-przepustka w URL
    (subskrypcja bramy ma tylko endpointURL, bez nagłówków). Pusty token w configu = 503."""
    expected = config.BRAMA_WA_WEBHOOK_TOKEN
    if not expected:
        return JSONResponse({"ok": False, "message": "wyłączone"}, status_code=503)
    if not security_panel.constant_time_equals(token, expected):
        return JSONResponse({"ok": False}, status_code=404)  # nie zdradzaj istnienia endpointu
    if request.method == "GET":
        # Handshake weryfikacyjny — odbij challenge, jeśli brama go wysyła przy subskrypcji.
        ch = request.query_params.get("challenge") or request.query_params.get("hub.challenge")
        return Response(ch, media_type="text/plain") if ch else JSONResponse({"ok": True})
    raw = await _json(request)
    try:
        rec = await run_in_threadpool(deps.wa_inbox.add, raw, dict(request.headers))
    except Exception:  # noqa: BLE001 — odbiór NIGDY nie może zgubić wiadomości po cichu
        from .wspolne import deadletter
        zapisano = await run_in_threadpool(deadletter.zapisz, raw, dict(request.headers), "wa_inbox.add padło")
        log.error("[brama_wa] trwały zapis padł → dead-letter=%s (surowiec zachowany)", zapisano)
        # 200 świadomie: brama jest (prawdopodobnie) at-most-once i nie ponawia → 5xx = pewna utrata,
        # a surowiec mamy już w dead-letter. Semantykę retry bramy potwierdza Krzysiek (pyt. 4).
        return JSONResponse({"ok": True, "deadletter": True})
    log.info("[brama_wa] push id=%s sender=%s dł.tekstu=%d", rec.get("id"), rec.get("sender"), len(rec.get("text") or ""))
    return {"ok": True, "id": rec["id"]}


@app.get("/api/koord/wa")
async def koord_wa(request: Request):
    """Podgląd odebranych rozmów WA (koordynator) — materiał do szlifowania chudego."""
    if not koordynator_of(request):
        return JSONResponse({"ok": False}, status_code=403)
    try:
        limit = int(request.query_params.get("limit", "50"))
    except ValueError:
        limit = 50
    items = await run_in_threadpool(deps.wa_inbox.recent, limit)
    count = await run_in_threadpool(deps.wa_inbox.count)
    return {"ok": True, "count": count, "items": items}


@app.get("/api/koord/rozmowy")
async def koord_rozmowy(request: Request):
    """Archiwum: lista wątków (ruch z bramy WEM sklejony po kliencie). Stare rekordy bez pól
    spinających doliczane w locie z treści — zero migracji."""
    if not koordynator_of(request):
        return JSONResponse({"ok": False}, status_code=403)
    from .wspolne import archiwum
    msgs = await run_in_threadpool(deps.wa_inbox.recent, 500)
    return {"ok": True, "watki": archiwum.zbuduj_watki(msgs)}


@app.get("/api/koord/rozmowy/watek")
async def koord_rozmowa(request: Request):
    """Archiwum: oś czasu jednego wątku (in+out chronologicznie, duplikaty oflagowane)."""
    if not koordynator_of(request):
        return JSONResponse({"ok": False}, status_code=403)
    tid = (request.query_params.get("id") or "").strip()
    if not tid:
        return JSONResponse({"ok": False, "message": "Brak id wątku."}, status_code=400)
    from .wspolne import archiwum
    msgs = await run_in_threadpool(deps.wa_inbox.recent, 500)
    return {"ok": True, "thread_id": tid, "wiadomosci": archiwum.zloz_rozmowe(msgs, tid)}


@app.get("/api/koord/gotowce")
async def koord_gotowce(request: Request):
    if not koordynator_of(request):
        return JSONResponse({"ok": False}, status_code=403)
    return {"ok": True, **await run_in_threadpool(panel.gotowce)}


@app.get("/api/koord/prompts")
async def koord_prompts(request: Request):
    if not koordynator_of(request):
        return JSONResponse({"ok": False}, status_code=403)
    return {"ok": True, **await run_in_threadpool(panel.list_prompts)}


@app.post("/api/koord/prompt")
async def koord_set_prompt(request: Request):
    _, err = _koord_guard(request)
    if err:
        return err
    url = str((await _json(request)).get("url", "")).strip()
    return await run_in_threadpool(panel.set_prompt, url)


@app.post("/api/koord/eval")
async def koord_eval(request: Request):
    """Ewaluacja A/B (bez zapisu): przepuść wsad przez wybrany prompt. Koord-only."""
    if not koordynator_of(request):
        return JSONResponse({"ok": False}, status_code=403)
    p = await _json(request)
    return await run_in_threadpool(
        panel.eval_case, str(p.get("wsad", "")), str(p.get("grupa", "DE")), str(p.get("prompt", "v1_9")))


# --- Wyzwalacz autopilota z harmonogramu (Cloud Scheduler) ---------------------
@app.post("/api/autopilot/run")
async def autopilot_run(request: Request):
    """Autoryzacja tokenem (nie sesją) — wołane przez harmonogram."""
    if not config.AUTOPILOT_TOKEN:
        return JSONResponse({"ok": False, "message": "Wyzwalacz wyłączony (brak AUTOPILOT_TOKEN)."},
                            status_code=503)
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth[:7].lower() == "bearer " else ""
    if not token or not security_panel.constant_time_equals(token, config.AUTOPILOT_TOKEN):
        return JSONResponse({"ok": False}, status_code=401)
    return await run_in_threadpool(autopilot_mod.run)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
