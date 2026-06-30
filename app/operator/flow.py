"""
Przepływ pracy operatora (dzień): pobierz sprawę → rozmowa z AI (1 ruch) → TAG → domknij.

Sercem jest `_ai_turn`: woła dostawcę AI, wykonuje akcje forum z odpowiedzi (w trybie 'sucho'
nic nie idzie na forum), sprawdza zakazane frazy (guardrail prawny) i wykrywa TAG/PZ.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from .. import config, deps
from ..wspolne import ai as ai_engine
from ..wspolne import model, reguly, sterowanie

log = logging.getLogger("operator")

# TAG kończący ruch: C#:DD.MM;PZ=PZx;DRABES=... (3 warianty wielkości liter jak w oryginale)
_TAG_RE = re.compile(r"(C#\s*:\s*\d{1,2}\.\d{1,2}[^\n]*)", re.IGNORECASE)
_PZ_IN_TAG = re.compile(r"PZ\s*=\s*PZ?\s*(\d{1,2})", re.IGNORECASE)


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _grupa(operator: dict) -> str:
    rec = deps.operators.get(operator["pid"])
    if rec and rec.get("grupa"):
        return rec["grupa"]
    for r in operator.get("roles", []):
        if r.startswith("grupa:"):
            return r.split(":", 1)[1].upper()
    return model.Grupa.UKPL.value


def _forum_nick(operator: dict) -> str:
    rec = deps.operators.get(operator["pid"])
    return (rec or {}).get("forum_nick") or operator["pid"]


def detect_tag(text: str) -> Tuple[Optional[str], Optional[int]]:
    """Zwraca (tag, pz) z odpowiedzi AI albo (None, None)."""
    m = _TAG_RE.search(text or "")
    if not m:
        return None, None
    tag = m.group(1).strip()
    pz_m = _PZ_IN_TAG.search(tag)
    pz = int(pz_m.group(1)) if pz_m else None
    return tag, (pz if pz is not None and model.PZ_MIN <= pz <= model.PZ_MAX else None)


def _system_prompt(case: model.Case, operator: dict, grupa: str) -> str:
    base = deps.active_prompt_text()
    params = ai_engine.build_start_params(
        operator=operator.get("label") or operator["pid"],
        data=time.strftime("%d.%m"), grupa=grupa)
    # Warstwa sterująca: wstrzyknij policzone fakty + wymuś wyjście JSON.
    fakty = sterowanie.fakty_do_promptu(sterowanie.przygotuj_fakty(case))
    return base + params + fakty + sterowanie.instrukcja_json()


def _ai_turn(case: model.Case, operator: dict, history: List[dict]) -> Dict:
    """Jeden obrót AI + akcje forum + guardrail. Zwraca {ai_text, tag, pz, forum, zakazane}."""
    grupa = _grupa(operator)
    system = _system_prompt(case, operator, grupa)
    forum_total = {"reads": [], "writes": []}

    ai_text = deps.ai_provider.respond(system, history)
    # Wykonaj akcje forum z odpowiedzi (max 2 obroty: write → read wraca do AI).
    for _ in range(2):
        res = deps.forum.execute_actions(
            ai_text, user_od=grupa, ai_user=_forum_nick(operator), source_type="operator")
        ai_text = res.get("text", ai_text)
        forum_total["reads"] += res.get("reads", [])
        forum_total["writes"] += res.get("writes", [])
        if not res.get("reads"):
            break
        # wynik czytania forum wraca do AI jako kolejny wsad
        history = history + [
            {"role": "model", "content": ai_text},
            {"role": "user", "content": "[FORUM_CONTEXT]\n" + "\n".join(
                str(r) for r in res["reads"])},
        ]
        ai_text = deps.ai_provider.respond(system, history)

    tag, pz = detect_tag(ai_text)
    zakazane = reguly.znajdz_zakazane(ai_text)
    if zakazane:
        log.warning("Sprawa %s: AI użyło zakazanych fraz: %s", case.numer_zamowienia, zakazane)

    # Warstwa sterująca: jeśli AI zwróciło JSON — zwaliduj/egzekwuj (twardo na ryzyku).
    ster: Optional[dict] = None
    ai_json = sterowanie.parsuj_wyjscie(ai_text)
    if ai_json:
        wynik = sterowanie.zwaliduj_wyjscie(ai_json, case, sterowanie.przygotuj_fakty(case))
        ster = {"naruszenia": wynik.naruszenia, "ostrzezenia": wynik.ostrzezenia,
                "poprawki": wynik.poprawki, "kwota": wynik.kwota, "pz": wynik.pz}
        if wynik.naruszenia:
            log.warning("Sprawa %s: naruszenia reguł: %s", case.numer_zamowienia, wynik.naruszenia)
        if wynik.pz is not None:
            pz = wynik.pz  # JSON jest źródłem prawdy dla PZ

    return {"ai_text": ai_text, "tag": tag, "pz": pz, "forum": forum_total,
            "zakazane": zakazane, "sterowanie": ster}


# --- API przepływu (woła main.py) ---------------------------------------------
def pobierz_sprawe(operator: dict) -> Optional[model.Case]:
    """Pobierz najpilniejszą sprawę grupy operatora i zarezerwuj transakcyjnie."""
    grupa = _grupa(operator)
    case = deps.cases.reserve_next(operator["pid"], grupa)
    if case:
        deps.cases.start(case.doc_id, operator["pid"])
        deps.stats.log("pobranie", operator_pid=operator["pid"], numer=case.numer_zamowienia, grupa=grupa)
    return case

def aktywna_sprawa(operator: dict) -> Optional[model.Case]:
    return deps.cases.restore_active(operator["pid"])


def rozpocznij_rozmowe(case: model.Case, operator: dict) -> Dict:
    """Pierwszy obrót: wstrzyknij wsad (+ kontekst forum) i odpytaj AI."""
    kontekst = deps.forum.auto_load_context(case.numer_zamowienia)
    wsad = case.pelna_linia_szturchacza or ""
    if kontekst:
        wsad = wsad + "\n\n" + kontekst
    history = [{"role": "user", "content": wsad}]
    out = _ai_turn(case, operator, history)
    history.append({"role": "model", "content": out["ai_text"]})
    deps.cases.save_chat(case.doc_id, history)
    return out


def wyslij_wiadomosc(case: model.Case, operator: dict, text: str) -> Dict:
    history = list(case.autopilot_messages or [])
    if not history:
        return rozpocznij_rozmowe(case, operator)
    history.append({"role": "user", "content": text})
    out = _ai_turn(case, operator, history)
    history.append({"role": "model", "content": out["ai_text"]})
    deps.cases.save_chat(case.doc_id, history)
    return out


def domknij(case: model.Case, operator: dict, tag: str, pz: Optional[int]) -> Tuple[bool, str]:
    if not tag:
        return False, "Brak TAG-u w odpowiedzi AI — nie można zakończyć."
    ok = deps.cases.complete(case.doc_id, operator["pid"], tag, pz)
    if ok:
        deps.stats.log("ruch", operator_pid=operator["pid"], numer=case.numer_zamowienia,
                       grupa=_grupa(operator), pz=pz,
                       diament=bool(pz == model.DIAMENT_PZ))
    return ok, "" if ok else "Nie udało się domknąć sprawy."


def pomin(case: model.Case, operator: dict, powod: str) -> Tuple[bool, str]:
    if not powod.strip():
        return False, "Podaj powód pominięcia."
    ok = deps.cases.skip(case.doc_id, operator["pid"], powod.strip())
    if ok:
        deps.stats.log("pominiecie", operator_pid=operator["pid"], numer=case.numer_zamowienia,
                       grupa=_grupa(operator), powod=powod.strip())
    return ok, "" if ok else "Nie udało się pominąć."
