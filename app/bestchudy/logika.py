"""
Logika porównywarki BESTCHUDY — czysta (bez FastAPI i bez widoku).

Twarde reguły rozpisu (COORDYNACJA → PODZIAŁ):
- werdykt PER STRONA 🔴/🟢, ale 🟢🟢 ZABRONIONE — operator musi wskazać lepszą stronę;
- czerwony werdykt wymaga komentarza odrzutu;
- sklejka wsadu (panel+koperta+tag) jest JEDNA i ta sama dla v11 i chudego (PLAN.md §4-§5) —
  dlatego za długie pola ODRZUCAMY (400), nigdy nie tniemy po cichu (cichy nóż = nieuczciwe
  porównanie, którego nikt nie widzi).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

TRYBY = ("standard", "odwrotny_wa", "mail", "ebay", "forum")
WERDYKTY = ("zielony", "czerwony")

# Lookaround jak w archiwum (wzorzec domeny) — nie wyłuskuj 7 cyfr ze środka dłuższego ciągu.
_NRZAM = re.compile(r"(?<!\d)(\d{5,7})(?!\d)")
_DZIEN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Cięcie krawędziowe zgodne z JS String.trim() (obejmuje BOM/U+FEFF, którego str.strip() nie tnie).
_KRAWEDZIE = re.compile(r"^[\s﻿]+|[\s﻿]+$")

LIMIT_TEKSTU = 20000   # panel / koperta / rolka
LIMIT_TAG = 2000
LIMIT_SKLEJKI = 45000  # rekord porównania: pełna sklejka (20k+20k+2k + separatory) musi się zmieścić


def oczysc(tekst) -> str:
    """Trim krawędziowy 1:1 z JS .trim() (razem z BOM) — lustra muszą ciąć tak samo."""
    return _KRAWEDZIE.sub("", str(tekst or ""))


def przytnij(tekst, limit: int = LIMIT_TEKSTU) -> str:
    return oczysc(tekst)[:limit]


def wyluskaj_nrzam(tekst) -> str:
    m = _NRZAM.search(str(tekst or ""))
    return m.group(1) if m else ""


def sklej_wsad(wsad_panel, koperta="", tag="") -> str:
    """Sklejka „KOPIUJ WSAD" (kontrakt PLAN.md §5): panel + koperta + tag, puste części pomijane.
    BEZ limitów — długość waliduje wsad_za_dlugi() i odrzuca, zamiast ciąć po cichu."""
    czesci = [oczysc(wsad_panel), oczysc(koperta), oczysc(tag)]
    return "\n\n".join([c for c in czesci if c])


def wsad_za_dlugi(wsad_panel, koperta="", tag="") -> str:
    """Komunikat błędu, gdy pola przekraczają limity (pusty string = OK)."""
    if len(oczysc(wsad_panel)) > LIMIT_TEKSTU or len(oczysc(koperta)) > LIMIT_TEKSTU:
        return ("Wsad za długi (panel i koperta maks. 20000 znaków każde) — porównanie wymaga "
                "PEŁNEJ, identycznej sklejki dla obu stron, więc nie tniemy po cichu.")
    if len(oczysc(tag)) > LIMIT_TAG:
        return "Tag za długi (maks. 2000 znaków)."
    return ""


def poprawny_dzien(dzien) -> bool:
    return bool(_DZIEN.match(str(dzien or "")))


def dzis() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def waliduj_werdykty(w_v11, w_chudy, komentarz="") -> str:
    """Zwraca komunikat błędu albo pusty string, gdy werdykty są poprawne."""
    for w in (w_v11, w_chudy):
        if w not in WERDYKTY:
            return "Werdykt OBU stron musi być ustawiony: zielony albo czerwony."
    if w_v11 == "zielony" and w_chudy == "zielony":
        return "Podwójny zielony zabroniony — wskaż, która strona była LEPSZA (rozpis koordynatora)."
    if "czerwony" in (w_v11, w_chudy) and not str(komentarz or "").strip():
        return "Czerwony werdykt wymaga komentarza odrzutu."
    return ""


def _bezpieczny_int(wartosc) -> int:
    try:
        return max(0, int(wartosc))
    except (TypeError, ValueError):
        return 0


def nowe_porownanie(d: dict, operator: dict) -> dict:
    # Router waliduje długości i odrzuca 400 — przytnij niżej to tylko pas bezpieczeństwa.
    wsad = przytnij(d.get("wsad"), LIMIT_SKLEJKI)
    teraz = datetime.now(timezone.utc)
    tryb = d.get("tryb")
    return {
        "id": uuid4().hex,
        "nrzam": wyluskaj_nrzam(wsad),
        "tryb": tryb if tryb in TRYBY else "standard",
        "wsad": wsad,
        "rolka": przytnij(d.get("rolka")),
        # Przy trybie odwrotnym v11 widzi wzorzec, a chudy rolkę z API — rekord niesie OBIE,
        # inaczej werdyktu v11 nie da się potem odtworzyć.
        "rolka_wzorzec": przytnij(d.get("rolka_wzorzec")),
        "chudy_odpowiedz": przytnij(d.get("chudy_odpowiedz"), 40000),
        "chudy_rozmowa": pelna_rozmowa(d.get("chudy_rozmowa")),
        "chudy_prompt": przytnij(d.get("chudy_prompt"), 200),
        "tury_chudego": _bezpieczny_int(d.get("tury_chudego")),
        "werdykt_v11": d.get("werdykt_v11"),
        "werdykt_chudy": d.get("werdykt_chudy"),
        "komentarz": przytnij(d.get("komentarz"), 4000),
        "operator_pid": operator.get("pid", ""),
        "operator_label": operator.get("label") or "",
        "created_at": teraz.isoformat(),
        "dzien": teraz.strftime("%Y-%m-%d"),
    }


def czy_odrzut(rec: dict) -> bool:
    return "czerwony" in (rec.get("werdykt_v11"), rec.get("werdykt_chudy"))


def liczby_dnia(recs) -> dict:
    """Podsumowanie dnia do oceny na końcu sesji."""
    return {
        "porownania": len(recs),
        "v11_zielone": sum(1 for r in recs if r.get("werdykt_v11") == "zielony"),
        "chudy_zielone": sum(1 for r in recs if r.get("werdykt_chudy") == "zielony"),
        "odrzuty": sum(1 for r in recs if czy_odrzut(r)),
    }


def waliduj_historie(historia) -> str:
    """Historia rozmowy z chudym: maks 40 wpisów {role: user|model, content: str ≤65000}."""
    if len(historia) > 40:
        return "Historia za długa (maks. 40 wpisów)."
    for m in historia:
        if not (isinstance(m, dict) and m.get("role") in ("user", "model")
                and isinstance(m.get("content"), str) and len(m["content"]) <= 65000):
            return "Nieprawidłowy wpis w historii (role: user/model, content: tekst do 65000 znaków)."
    return ""


def zloz_koperte(wpisy) -> str:
    """Koperta z FEED (lista {kto, kiedy, tresc}) → tekst 1:1 jak sekcja „Komentarze" w panelu.
    Wzorzec = PRÓBKA PRODUKCYJNA od Sylwii (2026-07-03): nagłówek `Komentarze`, blok =
    `Dodał: <nick>` / treść surowa / `O: <data>`; bloki bez pustych linii między sobą.
    Nick BEZ transformacji (filtr autorów v11 jest case-sensitive; realne nicki paneli są
    lowercase — `marlena_b`, `emilia` — i w tej formie zna je [OPERATORS], skoro operatorki
    tak dziś pracują). Treść nietknięta co do znaku (linie C#/COP# muszą zostać rozpoznawalne).
    Semantyka (wskazówka właścicielki procesu): komentarze dają KONTEKST I OBRAZ sprawy,
    wyznacznikiem stanu jest TAG w karcie (hierarchia v11: TAG-KOPERTA > COP# > bootstrap)."""
    if not isinstance(wpisy, list):
        return ""
    bloki = []
    for w in wpisy:
        if not isinstance(w, dict):
            continue
        tresc = oczysc(w.get("tresc"))
        if not tresc:
            continue
        # Pusty autor: „?" nie jest w [OPERATORS], więc v11 JAWNIE zaraportuje pominięcie
        # („Pominięto komentarze od: ?") zamiast cichej utraty treści.
        kto = oczysc(w.get("kto")) or "?"
        kiedy = oczysc(w.get("kiedy"))
        blok = "Dodał: " + kto + "\n" + tresc
        if kiedy:
            blok += "\nO: " + kiedy
        bloki.append(blok)
    return ("Komentarze\n" + "\n".join(bloki)) if bloki else ""


# Lustro walidacji podajnika; re.ASCII — bez niego \d łapie cyfry Unicode (np. arabskie),
# które przechodzą do SQL i kończą się mylącym 502.
_ZAM_FEED = re.compile(r"^\d{4,9}$", re.ASCII)
_ID_REC = re.compile(r"^[0-9a-f]{32}$", re.ASCII)


def poprawny_zam(zam) -> bool:
    return bool(_ZAM_FEED.match(str(zam or "").strip()))


def poprawny_id(pid) -> bool:
    return bool(_ID_REC.match(str(pid or "").strip()))


def zloz_rolke(wiadomosci) -> str:
    """Rolka ze styku daj-rolkę (archiwum WEM) → tekst MY/KLIENT, jak wkleja się do v11.
    Duplikaty (flaga archiwum) pomijane; kolejność chronologiczna jak z archiwum.
    UWAGA (uwaga operatorki): sprawy sprzed „daty x" nie istnieją w archiwum (stare WA
    bez dostępu) — wtedy chudy dostaje rolkę-wzorzec wklejoną ręcznie (fallback w UI)."""
    if not isinstance(wiadomosci, list):
        return ""
    linie = []
    for w in wiadomosci:
        if not isinstance(w, dict) or w.get("duplikat"):
            continue
        tekst = oczysc(w.get("text"))
        if not tekst:
            continue
        kto = "MY" if w.get("kierunek") == "out" else "KLIENT"
        linie.append(kto + ": " + tekst)
    return "\n".join(linie)


def pelna_rozmowa(historia) -> list:
    """Pełna sesja chudego do rekordu porównania (uwaga operatorki: odrzut ma nieść CAŁĄ
    rozmowę — „czemu zostało odrzucone", nie samo krótkie info).
    Budżet ŁĄCZNY 250000 znaków (bezpiecznik: dokument Firestore ma twardy limit ~1 MiB;
    bez budżetu 40×20000 + wsad + odpowiedź przekracza go przy polskich znakach i zapis
    przepada). Tniemy od NAJSTARSZYCH — finał sesji (to, czego dotyczy werdykt) zawsze zostaje."""
    if not isinstance(historia, list):
        return []
    czysta = []
    for m in historia[-40:]:  # od KOŃCA — najnowsza wymiana nie może wypaść
        if (isinstance(m, dict) and m.get("role") in ("user", "model")
                and isinstance(m.get("content"), str)):
            czysta.append({"role": m["role"], "content": m["content"][:20000]})
    budzet = 250000
    wynik = []
    for m in reversed(czysta):
        budzet -= len(m["content"])
        if budzet < 0:
            break
        wynik.append(m)
    return list(reversed(wynik))


def nowa_ocena(d: dict, operator: dict, liczby: dict) -> dict:
    teraz = datetime.now(timezone.utc)
    dzien = d.get("dzien") if poprawny_dzien(d.get("dzien")) else teraz.strftime("%Y-%m-%d")
    return {
        "id": uuid4().hex,
        "dzien": dzien,
        "uwagi": przytnij(d.get("uwagi"), 8000),
        "liczby": liczby,
        "operator_pid": operator.get("pid", ""),
        "operator_label": operator.get("label") or "",
        "created_at": teraz.isoformat(),
    }
