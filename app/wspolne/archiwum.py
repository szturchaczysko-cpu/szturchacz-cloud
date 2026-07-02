"""
Archiwum rozmów (skrzynka Szturchaczova) — sklejanie ruchu z bramy WEM po KLIENCIE.

Spinamy PRZY ZAPISIE, nie przy odczycie: każda wiadomość (in i out) dostaje:
- `thread_id`   — kanał + znormalizowana tożsamość klienta (tel/mail/nick),
- `order_refs`  — kandydaci nrZam wyłuskani z treści (best-effort),
- `klucz_dedup` — ZASTĘPCZY klucz duplikatów (brama nie daje message-id; gdy Krzysiek dołoży
                  wamid, wpada w `msg_id` i przejmuje rolę klucza — pole zostaje),
- `kontrakt`    — stempel wersji kontraktu pusha; po wzbogaceniu pól przez bramę podbijamy
                  wersję, a STARE rekordy da się przeliczyć z `raw` (parsuj_wa → wzbogac).

Zasada twarda: archiwum ZAPISUJE WSZYSTKO (duplikaty też) — odsiew robi WIDOK po kluczu.
Funkcje widoku (zbuduj_watki / zloz_rozmowe) są czyste: dostają listę rekordów, niczego nie piszą.
"""
from __future__ import annotations

import hashlib
import re
import time
from typing import List

KONTRAKT = "wem-v0"  # cienki push bramy: {channel, data:{body,sender,recipient,subject}}

_NR_ZAM = re.compile(r"(?<!\d)(\d{6})(?!\d)")  # nrZam w domenie = 6 cyfr (374593, 400112…)
_DEDUP_OKNO_S = 600  # okno klucza zastępczego; łapie retransmisje i podwójny forward DEV+PROD.
# Świadomy kompromis: identyczna treść na granicy okien da DWA klucze (przepuszczony duplikat),
# a legalne powtórzenie („ok" dwa razy w 10 min) sklei się w jedno — best-effort do czasu wamid.


def normalizuj_telefon(v: str) -> str:
    """Cyfry bez ozdobników; '00' z przodu ścinamy (0048… == +48… == 48…)."""
    cyfry = re.sub(r"\D", "", str(v or ""))
    return cyfry[2:] if cyfry.startswith("00") else cyfry


def strona_klienta(rec: dict) -> str:
    """Tożsamość KLIENTA w rozmowie: in → nadawca, out → odbiorca. Mail małymi, telefon cyframi."""
    kto = rec.get("recipient") if rec.get("kierunek") == "out" else rec.get("sender")
    kto = str(kto or "").strip()
    if "@" in kto:
        return kto.lower()
    tel = normalizuj_telefon(kto)
    return tel if tel else kto.lower()


def thread_id(rec: dict) -> str:
    klient = strona_klienta(rec)
    return f'{rec.get("channel") or "?"}:{klient}' if klient else ""


def order_refs(text) -> List[str]:
    return list(dict.fromkeys(_NR_ZAM.findall(str(text or ""))))[:5]


def klucz_dedup(rec: dict) -> str:
    baza = f'{rec.get("channel")}|{strona_klienta(rec)}|{rec.get("kierunek")}|{str(rec.get("text") or "")[:500]}'
    okno = int(rec.get("ts") or time.time()) // _DEDUP_OKNO_S
    return hashlib.sha1(f"{baza}|{okno}".encode()).hexdigest()[:16]


def wzbogac(rec: dict) -> dict:
    """Pola spinające dla rekordu już sparsowanego (parsuj_wa / rekord_wyslany).
    Wołane przy zapisie; przeliczalne później z `raw` (migracja = re-parse, nie przebudowa)."""
    return {
        "kontrakt": KONTRAKT,
        "thread_id": thread_id(rec),
        "order_refs": order_refs(rec.get("text")),
        "klucz_dedup": klucz_dedup(rec),
    }


# --- Widok (czyste funkcje na liście rekordów; stare rekordy bez pól doliczamy w locie) ---------
def _tid(rec: dict) -> str:
    return rec.get("thread_id") or thread_id(rec)


def zbuduj_watki(wiadomosci: List[dict]) -> List[dict]:
    """Lista wątków z listy rekordów (recent() = od najnowszych). Rekordy bez tożsamości
    lądują w koszyku '<kanał>:nieprzypisane', żeby nic nie znikało z widoku."""
    grupy: dict = {}
    for m in wiadomosci:
        tid = _tid(m) or f'{m.get("channel") or "?"}:nieprzypisane'
        g = grupy.setdefault(tid, {
            "thread_id": tid, "channel": m.get("channel") or "?",
            "klient": tid.split(":", 1)[1] if ":" in tid else tid,
            "ostatnia": (m.get("text") or "")[:160],
            "ostatnia_ts": m.get("ts") or 0,
            "liczba": 0, "in": 0, "out": 0, "order_refs": [],
        })
        g["liczba"] += 1
        g["out" if m.get("kierunek") == "out" else "in"] += 1
        for r in (m.get("order_refs") or order_refs(m.get("text"))):
            if r not in g["order_refs"]:
                g["order_refs"].append(r)
    return sorted(grupy.values(), key=lambda g: -g["ostatnia_ts"])


def zloz_rozmowe(wiadomosci: List[dict], tid: str) -> List[dict]:
    """Oś czasu jednego wątku (rosnąco po ts). Duplikaty NIE są wycinane — dostają flagę
    `duplikat`, widok decyduje jak pokazać. Bez `raw`/`headers` (widok ma być lekki)."""
    # `wiadomosci` = recent() (od najnajnowszych) → odwracamy do kolejności WPŁYWU, żeby stabilne
    # sortowanie rozstrzygało remisy czasów (ts z dokładnością do sekundy) kolejnością zapisu.
    wybrane = [m for m in reversed(wiadomosci) if _tid(m) == tid]
    wybrane.sort(key=lambda m: (m.get("ts") or 0, m.get("received_at") or 0))
    widziane, out = set(), []
    for m in wybrane:
        k = m.get("klucz_dedup") or klucz_dedup(m)
        d = {kk: vv for kk, vv in m.items() if kk not in ("raw", "headers")}
        d["duplikat"] = k in widziane
        widziane.add(k)
        out.append(d)
    return out


if __name__ == "__main__":
    # sanity — sklejanie in/out po kliencie, niezależnie od zapisu numeru
    win = {"channel": "whatsapp", "sender": "+48 695 287 327", "recipient": "4915792556775",
           "text": "zwrot 374593 prosze o etykiete", "ts": 1700000000, "kierunek": "in"}
    wout = {"channel": "whatsapp", "sender": "4915792556775", "recipient": "0048695287327",
            "text": "etykieta w drodze", "ts": 1700000100, "kierunek": "out"}
    assert thread_id(win) == thread_id(wout) == "whatsapp:48695287327"
    assert order_refs(win["text"]) == ["374593"]
    assert order_refs("tel 4915792556775 i kwota 300") == []  # 11 cyfr i 3 cyfry ≠ nrZam
    m1 = {"channel": "email", "sender": "Kunde@Web.DE", "text": "Hallo", "ts": 1700000000, "kierunek": "in"}
    assert thread_id(m1) == "email:kunde@web.de"
    assert klucz_dedup(m1) == klucz_dedup(dict(m1, ts=1700000300))      # to samo okno → duplikat
    assert klucz_dedup(m1) != klucz_dedup(dict(m1, text="Hallo?"))      # inna treść → inny klucz
    w = zbuduj_watki([wout, win, m1])
    # sortowanie po czasie OSTATNIEJ wiadomości → WhatsApp (1700000100) przed mailem (1700000000)
    assert [x["thread_id"] for x in w] == ["whatsapp:48695287327", "email:kunde@web.de"]
    wa = next(x for x in w if x["channel"] == "whatsapp")
    assert wa["liczba"] == 2 and wa["in"] == 1 and wa["out"] == 1 and wa["order_refs"] == ["374593"]
    r = zloz_rozmowe([wout, win, dict(win)], "whatsapp:48695287327")
    assert [x["kierunek"] for x in r] == ["in", "in", "out"] and [x["duplikat"] for x in r] == [False, True, False]
    assert all("raw" not in x for x in r)
    print("archiwum.py: sanity OK")
