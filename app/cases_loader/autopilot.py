"""
Nocny autopilot — worker (uruchamiany z harmonogramu, NIE z otwartej karty przeglądarki).

Decyzja właściciela: PEŁNA automatyka (sam pisze na żywe forum), więc obwarowana bezpiecznikami:
- GLOBALNY kill-switch: config.AUTOPILOT == 'stop' → nic nie robi.
- 'sucho': klient forum w trybie FORUM_MODE='sucho' nie wysyła realnie (testy na prod).
- IDEMPOTENCJA: sprawy już przeliczone (autopilot_status=calculated) są pomijane; klient forum
  dodatkowo nie dubluje zleceń kuriera (pamięć forum).

Buduje kolejkę z top X% spraw per grupa (score malejąco), przydziela round-robin do obsady,
i dla każdej: ładuje kontekst forum → odpytuje AI jako bot → wykonuje akcje forum → zapisuje
gotową rozmowę na sprawie. Rano operator zastaje 'gotowca'.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List

from .. import config, deps
from ..wspolne import ai as ai_engine
from ..wspolne import model, sterowanie

log = logging.getLogger("autopilot")
BOT = "chatoszturek"


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _kolejka(percent: int) -> Dict[str, List[model.Case]]:
    """Top X% wolnych spraw per grupa (score malejąco), pomijając woreczek i już przeliczone."""
    per_grupa: Dict[str, List[model.Case]] = {}
    for c in deps.cases.all():
        if c.status != model.Status.WOLNY.value:
            continue
        if c.telefon_do_wykonania:
            continue
        if c.autopilot_status == model.AutopilotStatus.CALCULATED.value:
            continue  # idempotencja: już przeliczona
        per_grupa.setdefault(c.grupa, []).append(c)
    out: Dict[str, List[model.Case]] = {}
    for grupa, lista in per_grupa.items():
        lista.sort(key=lambda c: (-int(c.score or 0), c.sort_order))
        ile = max(1, round(len(lista) * percent / 100)) if lista else 0
        out[grupa] = lista[:ile]
    return out


def _przelicz(case: model.Case, operator_pid: str) -> bool:
    """Jeden case: kontekst forum → AI(bot) → akcje forum → zapis gotowca. Zwraca True gdy ok."""
    try:
        fakty = sterowanie.przygotuj_fakty(case)
        system = (deps.active_prompt_text()
                  + ai_engine.build_start_params(operator=BOT, data=time.strftime("%d.%m"), grupa=case.grupa)
                  + sterowanie.fakty_do_promptu(fakty)
                  + sterowanie.instrukcja_json())
        kontekst = deps.forum.auto_load_context(case.numer_zamowienia)
        wsad = case.pelna_linia_szturchacza or ""
        if kontekst:
            wsad += "\n\n" + kontekst
        history = [{"role": "user", "content": wsad}]
        ai_text = deps.ai_provider.respond(system, history)
        # Warstwa sterująca: walidacja wyjścia (twardo na ryzyku) — log naruszeń (autopilot pisze sam).
        ai_json = sterowanie.parsuj_wyjscie(ai_text)
        if ai_json:
            wynik = sterowanie.zwaliduj_wyjscie(ai_json, case, fakty)
            if wynik.naruszenia:
                log.warning("Autopilot %s: naruszenia reguł: %s", case.numer_zamowienia, wynik.naruszenia)
        res = deps.forum.execute_actions(
            ai_text, user_od=case.grupa, ai_user=BOT, source_type="autoszturchacz")
        ai_text = res.get("text", ai_text)
        history.append({"role": "model", "content": ai_text})

        case.autopilot_messages = history
        case.autopilot_status = model.AutopilotStatus.CALCULATED.value
        case.autopilot_assigned_to = operator_pid
        case.autopilot_calculated_at = int(time.time())
        deps.cases.upsert(case)
        return True
    except Exception as e:  # noqa: BLE001 — nocą nie wywalamy całego przebiegu przez jedną sprawę
        log.error("Autopilot: sprawa %s nie przeliczona: %s", case.numer_zamowienia, e)
        return False


def run() -> Dict:
    """Pełny przebieg nocny. Zwraca podsumowanie (do porannego raportu/alertu)."""
    if config.AUTOPILOT == "stop":
        return {"ok": False, "msg": "AUTOPILOT=stop (kill-switch) — nic nie zrobiono."}

    cfg = deps.biz_config.all()
    percent = int(cfg.get("autopilot_percent", 30))
    obsada = list(cfg.get("autopilot_obsada") or [])
    if not obsada:
        obsada = [o["pid"] for o in deps.operators.list()] or [BOT]

    kolejka = _kolejka(percent)
    przeliczone, bledy, przydzial = 0, 0, 0
    raport: Dict[str, int] = {}
    for grupa, lista in kolejka.items():
        # obsada tej grupy (jeśli operator ma grupę), inaczej cała obsada
        ops = [o["pid"] for o in deps.operators.list() if o.get("grupa") == grupa] or obsada
        for i, case in enumerate(lista):
            op = ops[i % len(ops)]
            if _przelicz(case, op):
                przeliczone += 1
            else:
                bledy += 1
            przydzial += 1
        raport[grupa] = len(lista)

    summary = {
        "ok": True, "tryb_forum": config.FORUM_MODE, "percent": percent,
        "przeliczone": przeliczone, "bledy": bledy, "wziete": przydzial, "per_grupa": raport,
        "data": _today(),
    }
    log.info("Autopilot zakończony: %s", summary)
    return summary
