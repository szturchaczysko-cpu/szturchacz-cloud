"""
Logika panelu koordynatora: przegląd kolejki, konfiguracja biznesowa, operatorzy, raporty.
Cienka warstwa nad magazynami — trasy w main.py tylko ją wołają.
"""
from __future__ import annotations

import time
from typing import Dict, List

import requests

from .. import config, deps
from ..cases_loader import autopilot, loader
from ..wspolne import ai as ai_engine
from ..wspolne import model, sterowanie

_PROMPT_REPO = "szturchaczysko-cpu/szturchacz"


def overview() -> Dict:
    grupy = [g.value for g in model.Grupa]
    counts = {g: deps.cases.counts_by_status(g) for g in grupy}
    return {
        "counts": counts,
        "diamenty_dzis": deps.stats.diamenty_dzis(),
        "config": deps.biz_config.all(),
        "operatorzy": deps.operators.list(),
        "autopilot": config.AUTOPILOT,
        "forum_mode": config.FORUM_MODE,
        "data": time.strftime("%Y-%m-%d"),
    }


def ingest(text: str, data_obrobki: str = "") -> Dict:
    return loader.ingest_wsad(text, data_obrobki=data_obrobki)


def set_config(key: str, value) -> Dict:
    if key not in deps.biz_config.DEFAULTS:
        return {"ok": False, "message": f"Nieznany klucz konfiguracji: {key}"}
    deps.biz_config.set(key, value)
    return {"ok": True, "config": deps.biz_config.all()}


def upsert_operator(pid: str, label: str, grupa: str, tel: bool = False,
                    jezyki: List[str] = None, forum_nick: str = "") -> Dict:
    if grupa not in [g.value for g in model.Grupa]:
        return {"ok": False, "message": "Zła grupa (DE/FR/UKPL)."}
    deps.operators.upsert(pid, label, grupa, tel=tel, jezyki=jezyki or [], forum_nick=forum_nick)
    return {"ok": True, "operatorzy": deps.operators.list()}


def remove_operator(pid: str) -> Dict:
    return {"ok": deps.operators.remove(pid)}


def run_autopilot() -> Dict:
    return autopilot.run()


def list_prompts() -> Dict:
    """Lista promptów: wbudowane (v1_9/chudy) + ewentualnie .txt z repo + aktualnie wybrany."""
    # Wbudowane, wybieralne bez sieci — w tym CHUDY do A/B.
    prompts: List[dict] = [
        {"name": "v1_9 (pełny, wbudowany — domyślny)", "url": "v1_9"},
        {"name": "chudy (odchudzony, wbudowany)", "url": "chudy"},
    ]
    try:
        headers = {"Accept": "application/vnd.github+json"}
        if config.GITHUB_TOKEN:
            headers["Authorization"] = f"token {config.GITHUB_TOKEN}"
        r = requests.get(f"https://api.github.com/repos/{_PROMPT_REPO}/contents/", headers=headers, timeout=15)
        r.raise_for_status()
        for item in r.json():
            name = item.get("name", "")
            if name.endswith(".txt"):
                prompts.append({
                    "name": name,
                    "url": item.get("download_url")
                    or f"https://raw.githubusercontent.com/{_PROMPT_REPO}/refs/heads/main/{name}",
                })
    except Exception:
        pass  # repo prywatne / brak tokenu / brak sieci → ręczny URL
    return {"prompts": prompts, "current": deps.active_prompt_label()}


def set_prompt(url: str) -> Dict:
    deps.biz_config.set("prompt_url", url.strip())
    return {"ok": True, "current": deps.active_prompt_label()}


def gotowce() -> Dict:
    """Nocne 'gotowce' (sprawy przeliczone przez autopilota) z odpowiedzią AI — do przeglądu jakości."""
    out: List[dict] = []
    for c in deps.cases.all():
        if c.autopilot_status == model.AutopilotStatus.CALCULATED.value:
            last = next((m["content"] for m in reversed(c.autopilot_messages or [])
                         if m.get("role") == "model"), "")
            out.append({
                "nrzam": c.numer_zamowienia, "grupa": c.grupa, "score": c.score,
                "wsad": c.pelna_linia_szturchacza, "gotowiec": last,
            })
    out.sort(key=lambda g: -int(g.get("score") or 0))
    return {"gotowce": out}


def eval_case(wsad: str, grupa: str = "DE", prompt_name: str = "v1_9") -> Dict:
    """
    Ewaluacja A/B (BEZ zapisu do bazy): przepuść wsad przez wybrany prompt + warstwę sterującą.
    Zwraca strukturę wyjścia AI i werdykt walidatora — do porównania v1_9 vs chudy na §16.
    """
    case = model.Case(
        numer_zamowienia=model.normalize_nrzam(wsad) or "eval",
        grupa=grupa, pelna_linia_szturchacza=wsad)
    fakty = sterowanie.przygotuj_fakty(case)
    system = (ai_engine.get_prompt(prompt_name)
              + ai_engine.build_start_params(operator="EVAL", data=time.strftime("%d.%m"), grupa=grupa)
              + sterowanie.fakty_do_promptu(fakty)
              + sterowanie.instrukcja_json())
    try:
        ai_text = deps.ai_provider.respond(system, [{"role": "user", "content": wsad}])
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "blad": str(e)}
    j = sterowanie.parsuj_wyjscie(ai_text)
    w = sterowanie.zwaliduj_wyjscie(j, case, fakty) if j else None
    return {
        "ok": True,
        "prompt": prompt_name,
        "prompt_len": len(ai_engine.get_prompt(prompt_name)),
        "ma_json": bool(j),
        "kwota": (w.kwota if w else None),
        "pz": (w.pz if w else None),
        "ruchy_forum": (len(w.ruchy_forum) if w else 0),
        "krok": (j.get("krok_teraz", "")[:140] if j else ai_text[:140]),
        "naruszenia": (w.naruszenia if w else []),
        "ostrzezenia": (w.ostrzezenia if w else []),
    }


def raport_diamenty(data: str = "") -> Dict:
    data = data or time.strftime("%Y-%m-%d")
    evs = deps.stats.events(data=data, typ="diament")
    diamenty = [e for e in evs if e.get("czy_diament")]
    return {"data": data, "diamenty": len(diamenty), "wpisy": evs}
