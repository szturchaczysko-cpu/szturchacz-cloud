"""
Wspólny model SPRAWY (case) — jedno źródło prawdy dla obu widoków (operator/koordynator).

Sprawa = jeden zwrot/reklamacja, identyfikowana numerem zamówienia. Wieżowiec (noc) ją
TWORZY i przelicza; operator (dzień) ją POBIERA, prowadzi i DOMYKA. W starym kodzie statusy
były „gołymi napisami" rozsianymi po obu apkach — tu są jednym Enumem.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class Status(str, Enum):
    """Cykl życia sprawy w kolejce."""
    WOLNY = "wolny"              # gotowa do pobrania
    PRZYDZIELONY = "przydzielony"  # zarezerwowana przez operatora (jeszcze nie zaczęta)
    W_TOKU = "w_toku"           # operator pracuje
    ZAKONCZONY = "zakonczony"
    ODROCZONY = "odroczony"     # czeka na zasób zewnętrzny / przyszłą datę (NEXT)
    POMINIETY = "pominiety"     # zwolniona z powodem, wraca do puli


class Grupa(str, Enum):
    """Grupa językowa/krajowa, do której trafia sprawa i operator."""
    DE = "DE"
    FR = "FR"
    UKPL = "UKPL"


class AutopilotStatus(str, Enum):
    """Ślad nocnego autopilota na sprawie."""
    NONE = ""
    CALCULATED = "calculated"      # autopilot przygotował gotową rozmowę
    FORUM_ACTION = "forum_action"  # autopilot wykonał ruch na forum
    BUMPED = "bumped"              # autopilot podbił wątek


class TelefonStatus(str, Enum):
    """Stan sprawy w 'woreczku telefonicznym'."""
    BRAK = ""
    CZEKA = "czeka"
    ODROCZONY = "odroczony"          # nieodebrane → wraca po +2h
    ZROBIONY = "zrobiony"
    USUNIETY = "usuniety"
    ODPOWIEDZ_TELEFONISTY = "odpowiedz_telefonisty"


# --- Drabina PZ (postęp zwrotu) ------------------------------------------------
# PZ to maszyna stanów postępu sprawy. PZ wolno podnieść TYLKO przy jednoznacznym
# dowodzie, że krok faktycznie nastąpił (reguła z Kartoteki) — egzekwuje to kod.
PZ_LABELS: Dict[int, str] = {
    0: "Brak kontaktu",
    1: "Pierwszy kontakt",
    2: "Rozmowa w toku",
    3: "Ustalenia z klientem",
    4: "Dane do zwrotu zebrane",
    5: "Logistyka ustalona",
    6: "Zamówiony kurier",          # DIAMENT
    7: "Zlecenie potwierdzone",
    8: "Klient poinformowany",
    9: "Etykieta/odbiór w toku",
    10: "Zwrot w drodze",
    11: "Zwrot dostarczony do magazynu",
    12: "Rozliczone",
}
PZ_MIN, PZ_MAX = 0, 12
DIAMENT_PZ = 6  # osiągnięcie PZ6 = zamówiony kurier (miara sukcesu); decyzja diamentu z TREŚCI posta


def parse_pz(value: Any) -> Optional[int]:
    """Wyciąga numer etapu z 'PZ6' / 'pz6' / 6. Zwraca None gdy się nie da."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if PZ_MIN <= value <= PZ_MAX else None
    m = re.search(r"pz\s*(\d{1,2})", str(value), re.IGNORECASE)
    if not m:
        m = re.fullmatch(r"\s*(\d{1,2})\s*", str(value))
    if not m:
        return None
    n = int(m.group(1))
    return n if PZ_MIN <= n <= PZ_MAX else None


def pz_glowny(pz_list: List[int]) -> Optional[int]:
    """PZ główny sprawy = NAJNIŻSZY numerycznie ze wszystkich nóg transportu (reguła z Kartoteki)."""
    nums = [n for n in pz_list if n is not None]
    return min(nums) if nums else None


# --- Numer zamówienia ----------------------------------------------------------
def normalize_nrzam(text: str) -> Optional[str]:
    """
    Jedna funkcja wyciągania numeru zamówienia (w starym kodzie powtórzona 3x).
    Akceptuje 'NrZam: 374593', 'ZN374593', albo goły 5-7 cyfrowy ciąg.
    """
    if not text:
        return None
    s = str(text)
    m = re.search(r"(?:NrZam|ZN|ZW)[:\s]*([0-9]{5,7})", s, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\b([0-9]{5,7})\b", s)
    return m.group(1) if m else None


def case_doc_id(numer: str) -> str:
    """
    Deterministyczne ID dokumentu sprawy. Firestore traktuje '/' jako separator ścieżki,
    więc sanityzujemy. Re-zapis tego samego numeru NADPISUJE (idempotencja wsadu).
    """
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(numer))
    return f"ew_{safe}"


# --- Encja sprawy --------------------------------------------------------------
@dataclass
class Case:
    numer_zamowienia: str
    grupa: str = Grupa.UKPL.value
    status: str = Status.WOLNY.value
    score: int = 0
    priority_icon: str = ""
    priority_label: str = ""
    naglowek_priorytetowy: str = ""
    index_handlowy: str = ""
    pelna_linia_szturchacza: str = ""   # surowy wsad = wejście dla AI
    data_obrobki: str = ""              # dzień planu YYYY-MM-DD
    batch_id: str = ""
    sort_order: int = 0
    # przydział / przebieg
    assigned_to: str = ""
    assigned_at: int = 0
    started_at: int = 0
    completed_at: int = 0
    result_tag: str = ""
    result_pz: Optional[int] = None
    last_action_source: str = ""
    # ślad autopilota (noc)
    autopilot_status: str = AutopilotStatus.NONE.value
    autopilot_assigned_to: str = ""
    autopilot_calculated_at: int = 0
    autopilot_messages: List[dict] = field(default_factory=list)
    # woreczek telefoniczny
    telefon_do_wykonania: bool = False
    telefon_status: str = TelefonStatus.BRAK.value
    telefon_pz: Optional[int] = None
    telefon_jezyk: str = ""
    telefon_proby: int = 0
    telefon_retry_at: int = 0
    telefon_zlecil: str = ""
    telefon_wsad: str = ""
    telefon_last_op: str = ""
    # powód pominięcia
    skip_reason: str = ""
    skipped_by: str = ""
    skipped_at: int = 0

    @property
    def doc_id(self) -> str:
        return case_doc_id(self.numer_zamowienia)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Case":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
