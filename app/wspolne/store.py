"""
Lokalna warstwa danych (STORAGE=file) — pliki JSON w DATA_DIR, atomowy zapis pod lockiem
(wzorzec jak store.py Pulpitu). Interfejs celowo wąski, by wersja Firestore (prod) weszła
za tym samym kształtem. UWAGA: dysk Cloud Run jest ULOTNY — na prod używamy Firestore.

Stores:
- CasesStore      — wspólna kolejka spraw (rezerwacja transakcyjna).
- OperatorsStore  — operatorzy (grupa, tel, języki, login forum) edytowalni w panelu.
- ConfigStore     — konfiguracja biznesowa (kwoty/terminy/progi/autopilot) edytowalna w panelu.
- StatsStore      — jeden strumień zdarzeń (ruch/telefon/diament) + agregaty.
- ForumMemoryStore— most numer_zamówienia ↔ wpisy forum.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from .model import Case, Status, TelefonStatus


class _JsonFile:
    """Trwałość jednego pliku JSON z lockiem i atomowym zapisem."""

    def __init__(self, path: str, default: Any):
        self._path = path
        self._lock = threading.RLock()
        self._default = default
        self._data = self._read()

    def _read(self) -> Any:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                return json.loads(json.dumps(self._default))
        return json.loads(json.dumps(self._default))

    def _write(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)


def _now() -> int:
    return int(time.time())


class CasesStore(_JsonFile):
    """Wspólna kolejka spraw. Klucz = doc_id (ew_<numer>)."""

    def __init__(self, path: str):
        super().__init__(path, {"cases": {}})

    # --- zapis/odczyt podstawowy ---
    def upsert(self, case: Case) -> str:
        with self._lock:
            self._data["cases"][case.doc_id] = case.to_dict()
            self._write()
            return case.doc_id

    def get(self, doc_id: str) -> Optional[Case]:
        with self._lock:
            d = self._data["cases"].get(doc_id)
            return Case.from_dict(d) if d else None

    def get_by_nrzam(self, numer: str) -> Optional[Case]:
        return self.get(Case(numer_zamowienia=numer).doc_id)

    def all(self) -> List[Case]:
        with self._lock:
            return [Case.from_dict(d) for d in self._data["cases"].values()]

    def _save_case(self, case: Case) -> None:
        self._data["cases"][case.doc_id] = case.to_dict()
        self._write()

    # --- kolejka: rezerwacja TRANSAKCYJNA (koniec z wyścigiem) ---
    def reserve_next(self, operator_pid: str, grupa: str) -> Optional[Case]:
        """
        Atomowo wybiera najpilniejszą wolną sprawę grupy i rezerwuje ją dla operatora.
        Priorytet: najpierw nocno-przeliczone przypisane temu operatorowi, potem po score.
        Pomija sprawy w woreczku telefonicznym (osobny tor).
        """
        with self._lock:
            kandydaci = [
                Case.from_dict(d) for d in self._data["cases"].values()
                if d.get("status") == Status.WOLNY.value
                and d.get("grupa") == grupa
                and not d.get("telefon_do_wykonania")
            ]
            if not kandydaci:
                return None

            def klucz(c: Case):
                mine = c.autopilot_assigned_to == operator_pid and bool(c.autopilot_messages)
                return (0 if mine else 1, -int(c.score or 0), c.sort_order)

            kandydaci.sort(key=klucz)
            wybrany = kandydaci[0]
            wybrany.status = Status.PRZYDZIELONY.value
            wybrany.assigned_to = operator_pid
            wybrany.assigned_at = _now()
            self._save_case(wybrany)
            return wybrany

    def start(self, doc_id: str, operator_pid: str) -> Optional[Case]:
        with self._lock:
            c = self.get(doc_id)
            if not c or c.assigned_to != operator_pid:
                return None
            c.status = Status.W_TOKU.value
            c.started_at = _now()
            self._save_case(c)
            return c

    def complete(self, doc_id: str, operator_pid: str, result_tag: str, result_pz: Optional[int]) -> bool:
        with self._lock:
            c = self.get(doc_id)
            if not c:
                return False
            c.status = Status.ZAKONCZONY.value
            c.completed_at = _now()
            c.result_tag = result_tag
            c.result_pz = result_pz
            c.last_action_source = "operator"
            self._save_case(c)
            return True

    def release(self, doc_id: str, operator_pid: str) -> bool:
        """Zwolnij rezerwację (wylogowanie/reset) — sprawa wraca do puli."""
        with self._lock:
            c = self.get(doc_id)
            if not c or c.assigned_to != operator_pid:
                return False
            if c.status in (Status.PRZYDZIELONY.value, Status.W_TOKU.value):
                c.status = Status.WOLNY.value
                c.assigned_to = ""
                self._save_case(c)
            return True

    def skip(self, doc_id: str, operator_pid: str, powod: str) -> bool:
        with self._lock:
            c = self.get(doc_id)
            if not c:
                return False
            c.status = Status.POMINIETY.value
            c.assigned_to = ""
            c.skip_reason = powod
            c.skipped_by = operator_pid
            c.skipped_at = _now()
            self._save_case(c)
            return True

    def restore_active(self, operator_pid: str) -> Optional[Case]:
        """Po przeładowaniu — odzyskaj sprawę operatora w toku (żeby nie zgubił pracy)."""
        with self._lock:
            for d in self._data["cases"].values():
                if d.get("assigned_to") == operator_pid and d.get("status") in (
                    Status.PRZYDZIELONY.value, Status.W_TOKU.value
                ):
                    return Case.from_dict(d)
        return None

    def save_chat(self, doc_id: str, messages: List[dict]) -> None:
        with self._lock:
            c = self.get(doc_id)
            if c:
                c.autopilot_messages = messages  # bieżąca rozmowa trzymana na sprawie
                self._save_case(c)

    # --- woreczek telefoniczny ---
    def woreczek(self, grupa: Optional[str] = None) -> List[Case]:
        with self._lock:
            out = [
                Case.from_dict(d) for d in self._data["cases"].values()
                if d.get("telefon_do_wykonania")
                and d.get("telefon_status") not in (TelefonStatus.ZROBIONY.value, TelefonStatus.USUNIETY.value)
            ]
        if grupa:
            out = [c for c in out if c.grupa == grupa]
        return out

    def set_telefon(self, doc_id: str, **pola) -> bool:
        with self._lock:
            c = self.get(doc_id)
            if not c:
                return False
            for k, v in pola.items():
                if hasattr(c, k):
                    setattr(c, k, v)
            self._save_case(c)
            return True

    # --- raport / kolejka koordynatora ---
    def counts_by_status(self, grupa: Optional[str] = None) -> Dict[str, int]:
        out: Dict[str, int] = {}
        with self._lock:
            for d in self._data["cases"].values():
                if grupa and d.get("grupa") != grupa:
                    continue
                s = d.get("status", "?")
                out[s] = out.get(s, 0) + 1
        return out

    def wolne_count(self, grupa: str) -> int:
        return self.counts_by_status(grupa).get(Status.WOLNY.value, 0)


class OperatorsStore(_JsonFile):
    """Operatorzy edytowalni w panelu (koniec z 5 słownikami w kodzie)."""

    def __init__(self, path: str):
        super().__init__(path, {"operators": {}})

    def list(self) -> List[dict]:
        with self._lock:
            return list(self._data["operators"].values())

    def get(self, pid: str) -> Optional[dict]:
        with self._lock:
            return self._data["operators"].get(pid)

    def upsert(self, pid: str, label: str, grupa: str, tel: bool = False,
               jezyki: Optional[List[str]] = None, forum_nick: str = "",
               inicjaly: str = "") -> str:
        with self._lock:
            self._data["operators"][pid] = {
                "pid": pid, "label": label, "grupa": grupa, "tel": bool(tel),
                "jezyki": jezyki or [], "forum_nick": forum_nick or pid, "inicjaly": inicjaly,
            }
            self._write()
            return pid

    def remove(self, pid: str) -> bool:
        with self._lock:
            existed = pid in self._data["operators"]
            self._data["operators"].pop(pid, None)
            if existed:
                self._write()
            return existed


class ConfigStore(_JsonFile):
    """Konfiguracja biznesowa edytowalna przez koordynatora (kwoty/terminy/progi/autopilot)."""

    DEFAULTS = {
        "autopilot_percent": 30,        # % spraw przeliczanych nocą
        "autopilot_obsada": [],         # lista pid operatorów na noc
        "woreczek_retry_h": 2,          # nieodebrane wracają po +2h
        "woreczek_pominiete_proby": 3,  # próg „pominięte"
        "prompt_url": "",               # wybrany prompt sterujący (puste → fallback PROMPT_URL z env)
    }

    def __init__(self, path: str):
        super().__init__(path, {"config": dict(self.DEFAULTS)})

    def all(self) -> dict:
        with self._lock:
            cfg = dict(self.DEFAULTS)
            cfg.update(self._data.get("config", {}))
            return cfg

    def get(self, key: str, default: Any = None) -> Any:
        return self.all().get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data.setdefault("config", {})[key] = value
            self._write()


class StatsStore(_JsonFile):
    """Jeden strumień zdarzeń (ruch/telefon/diament) — zamiast 5 kolekcji liczących to samo."""

    def __init__(self, path: str):
        super().__init__(path, {"events": []})

    def log(self, typ: str, operator_pid: str, numer: str, grupa: str, **extra) -> str:
        eid = uuid.uuid4().hex
        with self._lock:
            self._data["events"].append({
                "id": eid, "typ": typ, "operator": operator_pid, "numer": numer,
                "grupa": grupa, "ts": _now(), "data": time.strftime("%Y-%m-%d"), **extra,
            })
            self._write()
        return eid

    def events(self, data: Optional[str] = None, typ: Optional[str] = None) -> List[dict]:
        with self._lock:
            out = list(self._data["events"])
        if data:
            out = [e for e in out if e.get("data") == data]
        if typ:
            out = [e for e in out if e.get("typ") == typ]
        return out

    def diamenty_dzis(self, operator_pid: Optional[str] = None) -> int:
        today = time.strftime("%Y-%m-%d")
        evs = [e for e in self.events(data=today, typ="diament") if e.get("czy_diament")]
        if operator_pid:
            evs = [e for e in evs if e.get("operator") == operator_pid]
        return len(evs)


class ForumMemoryStore(_JsonFile):
    """Most numer_zamówienia ↔ wpisy forum (gdzie chatoszturek już pisał)."""

    def __init__(self, path: str):
        super().__init__(path, {"memory": {}})

    def load(self, numer: str) -> dict:
        with self._lock:
            return dict(self._data["memory"].get(numer, {}))

    def save(self, numer: str, cel: str, entry: dict) -> None:
        with self._lock:
            mem = self._data["memory"].setdefault(numer, {})
            # pierwszy wpis dla danego celu wygrywa (nie nadpisujemy)
            if cel not in mem:
                mem[cel] = entry
                self._write()


_NAGL_OK = ("user-agent", "content-type", "x-forwarded-for")  # tylko nie-wrażliwe nagłówki


class WaInboxStore(_JsonFile):
    """Odebrane wiadomości WhatsApp z bramy ATA (push webhook). Trzyma ostatnie MAX wpisów.
    Lokalnie = plik; na prod = Firestore (ten sam interfejs)."""

    MAX = 3000

    def __init__(self, path: str):
        super().__init__(path, {"items": []})

    def add(self, raw: Any, headers: Optional[dict] = None) -> dict:
        from .brama_wa import parsuj_wa
        rec = {
            "id": uuid.uuid4().hex,
            "received_at": _now(),
            **parsuj_wa(raw),
            "raw": raw if isinstance(raw, (dict, list)) else str(raw),
            "headers": {k: v for k, v in (headers or {}).items() if str(k).lower() in _NAGL_OK},
        }
        with self._lock:
            self._data["items"].append(rec)
            if len(self._data["items"]) > self.MAX:
                self._data["items"] = self._data["items"][-self.MAX:]
            self._write()
        return rec

    def recent(self, limit: int = 50) -> List[dict]:
        with self._lock:
            return list(reversed(self._data["items"]))[:max(1, min(limit, 500))]

    def count(self) -> int:
        with self._lock:
            return len(self._data["items"])


class AwizacjeStore(_JsonFile):
    """Awizacje kurierskie (faza 1) — sygnał Szturchacz→apka Eweliny (kolekcja `awizacje_kurier`).
    Idempotencja: aktywna awizacja dla danego nrZam (dedup_key) nie jest tworzona drugi raz."""

    MAX = 5000

    def __init__(self, path: str):
        super().__init__(path, {"items": []})

    def add(self, doc: Dict) -> dict:
        with self._lock:
            dk = str(doc.get("dedup_key") or "")
            if dk:
                for it in self._data["items"]:
                    if str(it.get("dedup_key")) == dk and it.get("status") != "anulowane":
                        return {**it, "skipped_idempotent": True}
            rec = {**doc}
            rec.setdefault("status", "nowe")
            rec["id"] = uuid.uuid4().hex
            rec["created_at"] = _now()
            self._data["items"].append(rec)
            if len(self._data["items"]) > self.MAX:
                self._data["items"] = self._data["items"][-self.MAX:]
            self._write()
            return rec

    def recent(self, limit: int = 50) -> List[dict]:
        with self._lock:
            return list(reversed(self._data["items"]))[:max(1, min(limit, 500))]

    def count(self) -> int:
        with self._lock:
            return len(self._data["items"])
