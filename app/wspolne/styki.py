"""
STYKI — fasada skrzynki dla modułu BESTCHUDY (kontrakt: COORDYNACJA.md → ŁĄCZNIKI).

To JEDYNY punkt, z którego `app/bestchudy/` bierze rzeczy spoza swojego katalogu
(poza sso.read_operator). Cztery funkcje = cztery łączniki:

1. daj_sprawe(...)      — surowy wsad z wieżowczyka (zakres dat / odwrotny zam),
2. daj_rolke(...)       — rozmowa z archiwum WEM (po nrZam albo po wątku klienta),
3. policz_chudego(...)  — silnik chudego na suchym wsadzie (+opcjonalna rolka/historia),
4. wyslij(...)          — JEDYNA droga do klienta/kanałów; ZAWÓR NA RURZE:
                          wymaga KLIKU operatora (zgoda=True, pid) NIEZALEŻNIE od trybu,
                          tryb z env WEM_WYSYLKA: off | sucho (domyślnie; zapis zamiaru,
                          nic nie wychodzi) | live (realna wysyłka przez bramę WEM).
                          eBay: zawór twardo ZAMKNIĘTY do osobnej decyzji koordynatora.

Fullautomat (decyzja właściciela): otwarcie zaworu = zmiana trybu/wymogu kliku TUTAJ,
w JEDNYM miejscu — silników i ekranów się nie dotyka.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from .. import config, deps

log = logging.getLogger("styki")

KANALY = ("whatsapp", "email", "ebay", "forum")


# --- 1. FEED -------------------------------------------------------------------
def daj_sprawe(od: str = "", do: str = "", zam: str = "", limit: int = 50, grupa: str = "") -> dict:
    """Surowy wsad spraw (wieżowczyk). `grupa` (DE/FR/UKPL) = tylko sprawy działu operatora
    (prośba-styk Sylwii, PR #9). Zwraca {ok, sprawy:[{..., suchy_wsad, wsad_panel, koperta}]}."""
    from ..wiezowczyk import podajnik
    return podajnik.pobierz(od, do, zam, limit, grupa=grupa)


# --- 2. ROLKA ------------------------------------------------------------------
def daj_rolke(zam: str = "", thread_id: str = "", limit: int = 500) -> dict:
    """Rozmowa z archiwum WEM: po numerze zamówienia (wszystkie kanały) albo po wątku
    klienta. Odczyt wolny (bez bezpiecznika) — pokazuj rolkę w oknie silnika."""
    from . import archiwum
    if not (zam or thread_id):
        return {"ok": False, "message": "Podaj zam albo thread_id."}
    msgs = deps.wa_inbox.recent(limit)
    wiadomosci = archiwum.zloz_zamowienie(msgs, zam) if zam else archiwum.zloz_rozmowe(msgs, thread_id)
    return {"ok": True, "wiadomosci": wiadomosci, "liczba": len(wiadomosci)}


# --- 3. SILNIK CHUDEGO -----------------------------------------------------------
def policz_chudego(suchy_wsad: str, rolka: str = "",
                   historia: Optional[List[dict]] = None,
                   operator: str = "", grupa: str = "", tryb: str = "") -> dict:
    """Policz chudego na sprawie: system = aktywny prompt (panel) + PARAMETRY STARTOWE jak u v11
    (prośba-styk Sylwii, PR #9: delegacje telefonów wymagają operatora/grupy/trybu w systemie).
    Bez operatora/grupy — parametry pomijane (zachowanie jak dotąd). `historia` = [{role, content}]."""
    if not str(suchy_wsad or "").strip():
        return {"ok": False, "message": "Pusty wsad."}
    from . import ai
    system = deps.active_prompt_text()
    if operator or grupa or tryb:
        import time as _t
        system += ai.build_start_params(operator=operator or "operator",
                                        data=_t.strftime("%d.%m"),
                                        grupa=grupa or "DE",
                                        tryb=tryb or "standard")
    wejscie = str(suchy_wsad).strip()
    if rolka:
        wejscie += "\n\n[ROLKA Z KANAŁU]\n" + str(rolka).strip()
    msgs = list(historia or []) + [{"role": "user", "content": wejscie}]
    try:
        odpowiedz = deps.ai_provider.respond(system, msgs)
    except Exception as e:  # noqa: BLE001 — silnik nie może wywalać ekranu
        return {"ok": False, "message": f"Silnik chudego niedostępny ({type(e).__name__})."}
    return {"ok": True, "odpowiedz": odpowiedz, "prompt": deps.active_prompt_label()}


# --- 3a. OPERATORZY (prośba-styk Sylwii, PR #9) ----------------------------------
def daj_operatorow() -> dict:
    """Lista operatorów do selektora (pid, imię/label, grupa DE/FR/UKPL, tel, języki).
    Źródło = magazyn operatorów (edycja: zaplecze → Operatorzy; tam też przepinanie grup)."""
    try:
        osoby = deps.operators.list()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"Magazyn operatorów niedostępny ({type(e).__name__})."}
    return {"ok": True, "operatorzy": [
        {"pid": o.get("pid"), "label": o.get("label") or o.get("pid"),
         "grupa": o.get("grupa") or "", "tel": bool(o.get("tel")),
         "jezyki": o.get("jezyki") or []} for o in osoby]}


# --- 4. WYJŚCIE (zawór) ----------------------------------------------------------
def wyslij(kanal: str, adresat: str, tresc: str, operator_pid: str,
           zgoda: bool = False, subject: str = "") -> dict:
    """JEDYNA droga do klienta. Twarde bramki, w kolejności:
    (a) klik operatora (zgoda=True + pid) — bezpiecznik POZA promptem, zawsze;
    (b) kanał znany; eBay twardo zamknięty (osobna decyzja koordynatora);
    (c) tryb WEM_WYSYLKA: off=odmowa · sucho=zapis zamiaru · live=brama WEM.
    KAŻDA próba (sucho i live) ląduje w archiwum jako kierunek=out z polem tryb."""
    kanal = str(kanal or "").strip().lower()
    if not (zgoda and str(operator_pid or "").strip()):
        return {"ok": False, "message": "Bezpiecznik: wysyłka wymaga kliknięcia operatora (zgoda + pid)."}
    if kanal not in KANALY:
        return {"ok": False, "message": f"Nieznany kanał: {kanal!r}."}
    if not (str(adresat or "").strip() and str(tresc or "").strip()):
        return {"ok": False, "message": "Brak adresata albo treści."}
    if kanal == "ebay":
        return {"ok": False, "message": "eBay: zawór twardo zamknięty (decyzja koordynatora osobno)."}
    if kanal == "forum":
        return {"ok": False, "message": "Forum idzie osobnym torem (klient forum + FORUM_MODE), nie przez bramę WEM."}
    tryb = config.WEM_WYSYLKA
    if tryb == "off":
        return {"ok": False, "message": "Wysyłka wyłączona (WEM_WYSYLKA=off)."}
    if tryb == "sucho":
        rec = deps.wa_inbox.dodaj_wyslane(kanal, adresat, tresc, sender=operator_pid, tryb="sucho")
        log.info("[styki.wyslij] SUCHO %s → %s (operator=%s, id=%s)", kanal, adresat, operator_pid, rec["id"])
        return {"ok": True, "tryb": "sucho", "wyslano": False, "rekord_id": rec["id"],
                "message": "Zawór zamknięty (sucho): zamiar zapisany w archiwum, NIC nie wyszło."}
    # live — realna wysyłka przez bramę WEM
    from . import brama_wem_klient
    wynik = brama_wem_klient.wyslij(kanal, adresat, tresc, subject=subject)
    if not wynik["ok"]:
        return {"ok": False, "tryb": "live", "wyslano": False,
                "message": f"Brama WEM odmówiła (HTTP {wynik['status']}).", "odpowiedz": wynik["odpowiedz"]}
    rec = deps.wa_inbox.dodaj_wyslane(kanal, adresat, tresc, sender=operator_pid, tryb="live")
    log.info("[styki.wyslij] LIVE %s → %s (operator=%s, id=%s)", kanal, adresat, operator_pid, rec["id"])
    return {"ok": True, "tryb": "live", "wyslano": True, "rekord_id": rec["id"],
            "odpowiedz": wynik["odpowiedz"]}
