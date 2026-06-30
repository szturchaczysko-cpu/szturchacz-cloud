"""
WARSTWA STERUJĄCA (wyizolowana) — orkiestracja AI ⇄ reguły. TU poprawiasz zachowanie.

Wzorzec (decyzje właściciela):
- Kod LICZY fakty → wstrzykuje do promptu (przygotuj_fakty).
- AI proponuje WYJŚCIE JAKO JSON (kontrakt poniżej) → kod WALIDUJE/EGZEKWUJE (zwaliduj_wyjscie).
- Egzekucja: TWARDO na ryzyku (kasa, zakazane frazy, routing forum, przeskok PZ),
  reszta jako MIĘKKIE ostrzeżenia (samokontrola AI).
- Format: JSON od razu (koniec z kruchym wyławianiem regexami).

Reguły deterministyczne żyją w reguly.py; tu jest tylko spinanie + egzekucja.
Kolejność wdrażania (uzgodniona): 1 zakazane frazy ✓, 2 kwoty ✓, 3 routing ✓,
4 kurierzy, 5 terminy, 6 snapshot/koperta, 7 maszyna PZ, 8 bumpy/K1-K5.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import koperta as kop
from . import reguly
from .forum import FORUM_THREADS  # whitelista celów (routing — krok 3)
from .model import Case, PZ_MAX, PZ_MIN, parse_pz

# Zbiór dozwolonych celów forum (routing) — z jednego źródła.
DOZWOLONE_CELE = set(FORUM_THREADS.keys())


# ── Kontrakt wyjścia AI (JSON) ────────────────────────────────────────────────
# Kształt, którego żądamy od AI w chudym prompcie. Pola opcjonalne — AI wypełnia,
# co dotyczy danego ruchu. Kod czyta rubryki wprost (bez regexów po prozie).
KONTRAKT_WYJSCIA = {
    "wiadomosc_do_klienta": "str | '' — gotowy tekst do skopiowania (albo pusty gdy nie wysyłamy)",
    "krok_teraz": "str — jedno zdanie: co operator ma teraz zrobić",
    "koperta": {"pz": "int 0-12 | null", "ustalenia": "obiekt {klucz: wartosc}"},
    "kwota": "int | null — należność (jeśli dotyczy)",
    "ruchy_forum": [{"cel": "jeden z DOZWOLONE_CELE", "user_do": "str", "tresc": "str"}],
    "tag": "str — TAG C# (jeśli krok domyka etap), albo ''",
}


def instrukcja_json() -> str:
    """Blok doklejany na końcu promptu: wymuś wyjście jako JSON o powyższym kształcie."""
    return (
        "\n# FORMAT WYJŚCIA (🟥 OBOWIĄZKOWY)\n"
        "Na końcu odpowiedzi zwróć JEDEN blok ```json z polami: "
        "wiadomosc_do_klienta, krok_teraz, koperta{pz,ustalenia}, kwota, "
        "ruchy_forum[{cel,user_do,tresc}], tag. "
        "Pole 'cel' WYŁĄCZNIE z listy: " + ", ".join(sorted(DOZWOLONE_CELE)) + ". "
        "Kwot NIE licz samodzielnie — użyj wartości [KWOTA] z faktów, jeśli podana. "
        "Kuriera i termin odbioru bierz z faktów ([KURIER], [TERMIN_ODBIORU]) jeśli podane — nie wybieraj wbrew nim. "
        "Tekst dla człowieka możesz napisać przed blokiem; blok json jest źródłem prawdy dla aplikacji.\n"
    )


_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_JSON_BARE = re.compile(r"(\{(?:[^{}]|\{[^{}]*\})*\})", re.DOTALL)


def parsuj_wyjscie(ai_text: str) -> Optional[dict]:
    """Wyciągnij JSON z odpowiedzi AI: najpierw blok ```json, potem ostatni obiekt {...}. None gdy brak."""
    if not ai_text:
        return None
    m = _JSON_BLOCK.search(ai_text)
    candidates = [m.group(1)] if m else [g for g in _JSON_BARE.findall(ai_text)][-1:]
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            continue
    return None


# ── Fakty do wstrzyknięcia (kod liczy, AI dostaje gotowe) ─────────────────────
_DATA_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _dni_od_dostawy(case: Case) -> Optional[int]:
    """Best-effort: data dostawy (RRRR-MM-DD) z wsadu → dni do dziś. None gdy nie da się ustalić."""
    import datetime
    m = _DATA_RE.search(case.pelna_linia_szturchacza or "")
    if not m:
        return None
    try:
        d = datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def przygotuj_fakty(case: Case) -> Dict[str, Any]:
    """
    Fakty deterministyczne do wstrzyknięcia do promptu (krok 2: kwota/waluta).
    Zwraca tylko to, co kod policzył pewnie — reszta zostaje przy AI.
    """
    fakty: Dict[str, Any] = {}
    low = (case.pelna_linia_szturchacza or "").lower()
    waluta = "PLN" if re.search(r"\b(pl|poland|polska)\b", low) else "EUR"
    dni = _dni_od_dostawy(case)
    if dni is not None:
        fakty["dni_od_dostawy"] = dni
        fakty["kwota"] = reguly.kwota_naliczona(dni, waluta)
        fakty["waluta"] = waluta

    # KROK 4: kurier zwrotny — kod sugeruje, gdy da się ustalić z danych.
    index = (case.index_handlowy or "").strip()
    if "kolektor" in low or reguly._czy_kolektor(index):
        towar_typ = "KOLEKTOR"
    elif "skrzyn" in low:
        towar_typ = "SKRZYNIA"
    else:
        towar_typ = ""
    m_sk = re.search(r"(\d+)\s*skrzyn", low)
    liczba = int(m_sk.group(1)) if m_sk else (1 if towar_typ == "SKRZYNIA" else 0)
    if towar_typ or index:
        dec = reguly.wybor_kuriera(towar_typ=towar_typ, liczba_skrzyn=liczba,
                                   kurier_pierwotny=None, index_handlowy=index or None)
        if dec.get("kurier"):
            fakty["kurier"] = dec["kurier"]
            fakty["kurier_powod"] = dec["powod"]

    # KROK 5: najwcześniejszy realny termin odbioru (kalendarz z weekendem).
    fakty["termin_odbioru"] = reguly.termin_odbioru().isoformat()

    # KROK 8: następny krok sekwencji bumpów z poprzedniego snapshotu (kod liczy licznik).
    prior = kop.parsuj_snapshot("\n".join(
        m.get("content", "") for m in (case.autopilot_messages or [])
        if isinstance(m, dict) and m.get("role") == "model"))
    pola = prior.get("pola", {})
    if any(str(k).upper().startswith("FORUM_") for k in pola):
        bump = int(pola["bump"]) if str(pola.get("bump", "")).strip().isdigit() else 0
        ea = int(pola["ea"]) if str(pola.get("ea", "")).strip().isdigit() else 0
        zablok = "zablokowana" in (prior.get("ustalenia", "") or "").lower()
        fakty["nastepny_ruch_forum"] = reguly.nastepny_bump(bump, ea, zablok)["akcja"]
    return fakty


def fakty_do_promptu(fakty: Dict[str, Any]) -> str:
    """Sformatuj policzone fakty jako blok wstrzykiwany do promptu."""
    if not fakty:
        return ""
    linie = [f"{k}={v}" for k, v in fakty.items()]
    return "\n# FAKTY (policzone przez aplikację — użyj ich, nie licz sam)\n" + "\n".join(linie) + "\n"


# ── Walidacja / egzekucja wyjścia AI ──────────────────────────────────────────
@dataclass
class Wynik:
    ok: bool = True
    wiadomosc: str = ""
    krok_teraz: str = ""
    pz: Optional[int] = None
    kwota: Optional[int] = None
    ruchy_forum: List[dict] = field(default_factory=list)
    tag: str = ""
    naruszenia: List[str] = field(default_factory=list)    # TWARDE — blokują/poprawiają
    ostrzezenia: List[str] = field(default_factory=list)    # MIĘKKIE — tylko sygnał
    poprawki: Dict[str, Any] = field(default_factory=dict)  # co kod poprawił


def zwaliduj_wyjscie(ai_json: dict, case: Case, fakty: Optional[dict] = None) -> Wynik:
    """
    Sprawdź wyjście AI względem reguł. TWARDO na ryzyku, miękko poza tym.
    Zwraca Wynik z (ewentualnie poprawioną) treścią i listą naruszeń/ostrzeżeń.
    """
    fakty = fakty or {}
    w = Wynik()
    w.wiadomosc = str(ai_json.get("wiadomosc_do_klienta", "") or "")
    w.krok_teraz = str(ai_json.get("krok_teraz", "") or "")
    w.tag = str(ai_json.get("tag", "") or "")
    # AI bywa niekonsekwentne — koperta/ruchy mogą przyjść jako napis/None. Guardy typów,
    # żeby walidator (warstwa bezpieczeństwa) NIGDY nie padł na dziwnym wyjściu AI.
    koperta = ai_json.get("koperta")
    if not isinstance(koperta, dict):
        koperta = {}
    w.pz = parse_pz(koperta.get("pz"))
    w.kwota = ai_json.get("kwota")
    rf = ai_json.get("ruchy_forum")
    w.ruchy_forum = [r for r in rf if isinstance(r, dict)] if isinstance(rf, list) else []

    # KROK 1 (TWARDO): zakazane frazy w wiadomości do klienta → blokada.
    zakazane = reguly.znajdz_zakazane(w.wiadomosc)
    if zakazane:
        w.ok = False
        w.naruszenia.append("zakazane_frazy: " + ", ".join(zakazane))

    # KROK 2 (TWARDO): kwota — kod liczy, AI nie wolno jej podmienić.
    if fakty.get("kwota") is not None and w.kwota is not None:
        try:
            if int(w.kwota) != int(fakty["kwota"]):
                w.poprawki["kwota"] = {"ai": w.kwota, "poprawione": fakty["kwota"]}
                w.kwota = fakty["kwota"]
                w.naruszenia.append(
                    f"kwota: AI podała {w.poprawki['kwota']['ai']}, poprawiono na {fakty['kwota']} {fakty.get('waluta','')}")
                w.ok = False
        except (TypeError, ValueError):
            w.poprawki["kwota"] = {"ai": w.kwota, "poprawione": fakty["kwota"]}
            w.kwota = fakty["kwota"]
    elif fakty.get("kwota") is not None and w.kwota is None:
        w.kwota = fakty["kwota"]  # AI nie podała — wstaw policzoną

    # KROK 3 (TWARDO): routing forum — cel musi być z whitelisty; user_do nie może być pusty.
    for ruch in w.ruchy_forum:
        cel = str(ruch.get("cel", ""))
        if cel and cel not in DOZWOLONE_CELE:
            w.ok = False
            w.naruszenia.append(f"routing: nieznany cel forum '{cel}' (poza whitelistą)")
        if cel and not str(ruch.get("user_do", "")).strip():
            w.ok = False
            w.naruszenia.append(f"routing: brak user_do dla celu '{cel}'")

    # KROK 6 (TWARDO): koperta/USTALENIA — parsuj string v1_9 + sanityzacja (zakaz " ' , +).
    raw_ust = koperta.get("ustalenia")
    if isinstance(raw_ust, dict):
        ust = {str(k).upper(): v for k, v in raw_ust.items()}
    elif isinstance(raw_ust, str):
        ust = {str(k).upper(): v for k, v in kop.parsuj_ustalenia(raw_ust).items()}
        for n in kop.sanityzuj_ustalenia(raw_ust):
            w.naruszenia.append("ustalenia: " + n)
            w.ok = False
    else:
        ust = {}

    # KROK 4 (TWARDO): kurier — kod liczy; AI nie wybiera wbrew regule (kolektor → UPS).
    ai_kurier = str(ust.get("KURIER_PRZEWOZNIK", "") or ust.get("KURIER", "")
                    or ai_json.get("kurier_zwrotny", "")).strip().upper()
    fakt_kurier = str(fakty.get("kurier", "")).strip().upper()
    if ai_kurier and fakt_kurier and ai_kurier != fakt_kurier:
        w.poprawki["kurier"] = {"ai": ai_kurier, "poprawione": fakt_kurier}
        w.naruszenia.append(
            f"kurier: AI podała {ai_kurier}, reguła wskazuje {fakt_kurier} ({fakty.get('kurier_powod','')})")
        w.ok = False

    # KROK 7 (PZ): drabina postępu. Poprzedni PZ z OSTATNIEGO snapshotu (COP#-FIRST).
    prior_text = "\n".join(
        m.get("content", "") for m in (case.autopilot_messages or [])
        if isinstance(m, dict) and m.get("role") == "model")
    prior_snap = kop.parsuj_snapshot(prior_text)
    prior_pz = prior_snap["pz"]
    if prior_pz is None:
        prior_pz = case.result_pz
    # UWAGA: realni operatorzy SKACZĄ i COFAJĄ PZ wg nowych informacji (potwierdzone na TagsHistory:
    # pz2→pz10, pz9→pz2). Dlatego monotoniczność NIE jest twardą regułą — tylko miękki sygnał.
    if w.pz is not None:
        if not (PZ_MIN <= w.pz <= PZ_MAX):
            w.naruszenia.append(f"PZ poza zakresem 0-12: {w.pz}")
            w.ok = False
        elif prior_pz is not None and w.pz != prior_pz:
            delta = w.pz - prior_pz
            if delta < 0:
                w.ostrzezenia.append(f"PZ cofnięte {prior_pz}→{w.pz} — sprawdź dowód/marker.")
            elif delta > 1:
                w.ostrzezenia.append(f"PZ skok {prior_pz}→{w.pz} (o {delta}) — sprawdź dowód.")

    # KROK 8 (TWARDO): sekwencja forum — JEDEN ruch forumowy na przebieg + anty-dubel EA.
    if len(w.ruchy_forum) > 1:
        w.naruszenia.append(
            f"forum: {len(w.ruchy_forum)} ruchy forumowe w jednym przebiegu — dozwolony 1 (§0.1.1.2)")
        w.ok = False
    prior_ea = 0
    _ea_raw = str(prior_snap.get("pola", {}).get("ea", "")).strip()
    if _ea_raw.isdigit():
        prior_ea = int(_ea_raw)
    for r in w.ruchy_forum:
        if str(r.get("user_do", "")).strip().upper() == "EA" and prior_ea >= 1:
            w.naruszenia.append("forum: ponowna eskalacja EA w tym samym cyklu — anty-dubel (§0.1.1.2)")
            w.ok = False

    return w


if __name__ == "__main__":
    # Testy sanity warstwy sterującej (krok 1-3).
    c = Case(numer_zamowienia="111", grupa="DE", pelna_linia_szturchacza="DE 2026-05-01 zwrot")

    # parsuj_wyjscie z bloku ```json
    txt = 'Tekst dla człowieka.\n```json\n{"wiadomosc_do_klienta":"ok","kwota":900}\n```'
    assert parsuj_wyjscie(txt) == {"wiadomosc_do_klienta": "ok", "kwota": 900}

    # KROK 1: zakazana fraza → naruszenie
    w1 = zwaliduj_wyjscie({"wiadomosc_do_klienta": "Zapłać albo wezwiemy komornika."}, c)
    assert not w1.ok and any("zakazane" in n for n in w1.naruszenia), w1.naruszenia

    # KROK 2: kwota AI != policzona → poprawka twarda
    w2 = zwaliduj_wyjscie({"wiadomosc_do_klienta": "Należność.", "kwota": 900}, c, {"kwota": 600, "waluta": "EUR"})
    assert not w2.ok and w2.kwota == 600 and "kwota" in w2.poprawki, (w2.kwota, w2.poprawki)

    # KROK 3: zły cel forum → naruszenie; dobry → brak
    w3 = zwaliduj_wyjscie({"ruchy_forum": [{"cel": "NIE_ISTNIEJE", "user_do": "X", "tresc": "t"}]}, c)
    assert not w3.ok and any("routing" in n for n in w3.naruszenia)
    w3b = zwaliduj_wyjscie({"ruchy_forum": [{"cel": "AUTOS_KURIERZY", "user_do": "TEAM_ATOMOWKI", "tresc": "t"}]}, c)
    assert w3b.ok, w3b.naruszenia

    # przygotuj_fakty liczy kwotę z daty dostawy w wsadzie (best-effort)
    f = przygotuj_fakty(Case(numer_zamowienia="1", pelna_linia_szturchacza="DE 2026-01-01 zwrot"))
    assert "kwota" in f and f["waluta"] == "EUR" and "termin_odbioru" in f, f

    # KROK 4: kolektor → UPS; AI proponuje FEDEX → naruszenie + poprawka
    ck = Case(numer_zamowienia="222", grupa="DE",
              pelna_linia_szturchacza="DE kolektor zwrot", index_handlowy="ORG123")
    fk = przygotuj_fakty(ck)
    assert fk.get("kurier") == "UPS", fk
    w4 = zwaliduj_wyjscie({"koperta": {"ustalenia": {"kurier": "FEDEX"}}}, ck, fk)
    assert not w4.ok and "kurier" in w4.poprawki, (w4.naruszenia, w4.poprawki)
    w4b = zwaliduj_wyjscie({"koperta": {"ustalenia": {"kurier": "UPS"}}}, ck, fk)
    assert w4b.ok, w4b.naruszenia

    # KROK 6: USTALENIA jako STRING v1_9 — kurier wyłuskany i egzekwowany
    w6 = zwaliduj_wyjscie({"koperta": {"ustalenia": "PZ6.KURIER_PRZEWOZNIK=FEDEX.TOWAR_TYP=KOLEKTOR"}}, ck, fk)
    assert not w6.ok and "kurier" in w6.poprawki, (w6.naruszenia, w6.poprawki)
    w6b = zwaliduj_wyjscie({"koperta": {"ustalenia": "PZ6.KURIER_PRZEWOZNIK=UPS"}}, ck, fk)
    assert w6b.ok, w6b.naruszenia
    # sanityzacja: zakazany znak '+' w wartości → naruszenie
    w6c = zwaliduj_wyjscie({"koperta": {"ustalenia": "KURIER_PRZEWOZNIK=UPS+FEDEX"}}, c)
    assert not w6c.ok and any("ustalenia" in n for n in w6c.naruszenia), w6c.naruszenia

    # REGRESJA: dziwne kształty z AI nie mogą wywalić walidatora
    assert zwaliduj_wyjscie({"koperta": "wstrzymana", "ruchy_forum": "brak"}, c).ok
    assert zwaliduj_wyjscie({"koperta": None, "ruchy_forum": [{"cel": "AUTOS_KURIERZY", "user_do": "T"}, "smiec"]}, c).ok

    # KROK 7: PZ to MIĘKKI sygnał (operatorzy realnie skaczą/cofają — TagsHistory) — NIE blokuje
    cpz = Case(numer_zamowienia="333", grupa="DE", autopilot_messages=[
        {"role": "model", "content": "COP# PZ: PZ6\nCOP# USTALENIA: KURIER_PRZEWOZNIK=UPS"}])
    w7 = zwaliduj_wyjscie({"koperta": {"pz": "PZ2"}}, cpz)   # cofnięcie 6→2
    assert w7.ok and any("cofni" in o for o in w7.ostrzezenia), (w7.naruszenia, w7.ostrzezenia)
    w7s = zwaliduj_wyjscie({"koperta": {"pz": "PZ10"}}, cpz)  # skok 6→10
    assert w7s.ok and any("skok" in o for o in w7s.ostrzezenia), (w7s.naruszenia, w7s.ostrzezenia)

    # KROK 8: dwa ruchy forumowe w jednym przebiegu → naruszenie
    w8 = zwaliduj_wyjscie({"ruchy_forum": [
        {"cel": "AUTOS_KURIERZY", "user_do": "TEAM_ATOMOWKI"},
        {"cel": "SPEDYCJA_REKLAMACJE", "user_do": "SPEDYCJA_REKLAMACJE"}]}, c)
    assert not w8.ok and any("forum:" in n for n in w8.naruszenia), w8.naruszenia
    # KROK 8: anty-dubel EA — prior ea=1, AI znów próbuje EA → naruszenie
    cea = Case(numer_zamowienia="444", grupa="DE", autopilot_messages=[
        {"role": "model", "content": "COP# USTALENIA: FORUM_REKL=czekam_mozna_szturchac; bump=2; ea=1"}])
    w8b = zwaliduj_wyjscie({"ruchy_forum": [{"cel": "CZATOSZTUR_REKLAMACJE", "user_do": "EA"}]}, cea)
    assert not w8b.ok and any("anty-dubel" in n for n in w8b.naruszenia), w8b.naruszenia

    print("sterowanie.py: wszystkie testy sanity OK")
