"""
Produkcyjna warstwa danych (STORAGE=firestore) — TEN SAM interfejs co store.py (pliki),
żeby reszta apki nie wiedziała, skąd dane. Dysk Cloud Run jest ulotny → tu trwałość.

Kolekcje (jeden tryb, bez prefiksu test_ — decyzja właściciela):
  cases, operators, events, forum_memory; config w jednym dokumencie config/biz.

Rezerwacja sprawy jest TRANSAKCYJNA (Firestore transaction) — eliminuje wyścig,
w którym dwóch operatorów/autopilot chwyta tę samą sprawę.
"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

from google.cloud import firestore  # type: ignore

from .wspolne.model import Case, Status, TelefonStatus
from .wspolne.store import ConfigStore as _ConfigDefaults


def _now() -> int:
    return int(time.time())


class FirestoreCasesStore:
    def __init__(self, db: firestore.Client):
        self.db = db
        self.col = db.collection("szt_cases")

    def upsert(self, case: Case) -> str:
        self.col.document(case.doc_id).set(case.to_dict())
        return case.doc_id

    def get(self, doc_id: str) -> Optional[Case]:
        snap = self.col.document(doc_id).get()
        return Case.from_dict(snap.to_dict()) if snap.exists else None

    def get_by_nrzam(self, numer: str) -> Optional[Case]:
        return self.get(Case(numer_zamowienia=numer).doc_id)

    def all(self) -> List[Case]:
        return [Case.from_dict(d.to_dict()) for d in self.col.stream()]

    def reserve_next(self, operator_pid: str, grupa: str) -> Optional[Case]:
        # Kandydaci: równość (bez indeksu złożonego); sortowanie i preferencja w Pythonie.
        q = self.col.where("status", "==", Status.WOLNY.value).where("grupa", "==", grupa)
        kandydaci = [Case.from_dict(d.to_dict()) for d in q.stream() if not d.to_dict().get("telefon_do_wykonania")]
        if not kandydaci:
            return None

        def klucz(c: Case):
            mine = c.autopilot_assigned_to == operator_pid and bool(c.autopilot_messages)
            return (0 if mine else 1, -int(c.score or 0), c.sort_order)

        kandydaci.sort(key=klucz)

        @firestore.transactional
        def _claim(txn, ref):
            snap = ref.get(transaction=txn)
            d = snap.to_dict()
            if not d or d.get("status") != Status.WOLNY.value:
                return None
            txn.update(ref, {"status": Status.PRZYDZIELONY.value,
                             "assigned_to": operator_pid, "assigned_at": _now()})
            d.update({"status": Status.PRZYDZIELONY.value,
                      "assigned_to": operator_pid, "assigned_at": _now()})
            return Case.from_dict(d)

        for c in kandydaci:
            got = _claim(self.db.transaction(), self.col.document(c.doc_id))
            if got:
                return got
        return None

    def _patch(self, doc_id: str, **pola) -> Optional[Case]:
        ref = self.col.document(doc_id)
        snap = ref.get()
        if not snap.exists:
            return None
        ref.update(pola)
        d = snap.to_dict()
        d.update(pola)
        return Case.from_dict(d)

    def start(self, doc_id: str, operator_pid: str) -> Optional[Case]:
        c = self.get(doc_id)
        if not c or c.assigned_to != operator_pid:
            return None
        return self._patch(doc_id, status=Status.W_TOKU.value, started_at=_now())

    def complete(self, doc_id: str, operator_pid: str, result_tag: str, result_pz) -> bool:
        return self._patch(doc_id, status=Status.ZAKONCZONY.value, completed_at=_now(),
                           result_tag=result_tag, result_pz=result_pz,
                           last_action_source="operator") is not None

    def release(self, doc_id: str, operator_pid: str) -> bool:
        c = self.get(doc_id)
        if not c or c.assigned_to != operator_pid:
            return False
        if c.status in (Status.PRZYDZIELONY.value, Status.W_TOKU.value):
            self._patch(doc_id, status=Status.WOLNY.value, assigned_to="")
        return True

    def skip(self, doc_id: str, operator_pid: str, powod: str) -> bool:
        return self._patch(doc_id, status=Status.POMINIETY.value, assigned_to="",
                           skip_reason=powod, skipped_by=operator_pid, skipped_at=_now()) is not None

    def restore_active(self, operator_pid: str) -> Optional[Case]:
        q = self.col.where("assigned_to", "==", operator_pid)
        for d in q.stream():
            data = d.to_dict()
            if data.get("status") in (Status.PRZYDZIELONY.value, Status.W_TOKU.value):
                return Case.from_dict(data)
        return None

    def save_chat(self, doc_id: str, messages: List[dict]) -> None:
        self.col.document(doc_id).update({"autopilot_messages": messages})

    def woreczek(self, grupa: Optional[str] = None) -> List[Case]:
        q = self.col.where("telefon_do_wykonania", "==", True)
        out = []
        for d in q.stream():
            data = d.to_dict()
            if data.get("telefon_status") in (TelefonStatus.ZROBIONY.value, TelefonStatus.USUNIETY.value):
                continue
            if grupa and data.get("grupa") != grupa:
                continue
            out.append(Case.from_dict(data))
        return out

    def set_telefon(self, doc_id: str, **pola) -> bool:
        return self._patch(doc_id, **pola) is not None

    def counts_by_status(self, grupa: Optional[str] = None) -> Dict[str, int]:
        q = self.col.where("grupa", "==", grupa) if grupa else self.col
        out: Dict[str, int] = {}
        for d in q.stream():
            s = d.to_dict().get("status", "?")
            out[s] = out.get(s, 0) + 1
        return out

    def wolne_count(self, grupa: str) -> int:
        return self.counts_by_status(grupa).get(Status.WOLNY.value, 0)


class FirestoreOperatorsStore:
    def __init__(self, db: firestore.Client):
        self.col = db.collection("szt_operators")

    def list(self) -> List[dict]:
        return [d.to_dict() for d in self.col.stream()]

    def get(self, pid: str) -> Optional[dict]:
        snap = self.col.document(pid).get()
        return snap.to_dict() if snap.exists else None

    def upsert(self, pid: str, label: str, grupa: str, tel: bool = False,
               jezyki: Optional[List[str]] = None, forum_nick: str = "", inicjaly: str = "") -> str:
        self.col.document(pid).set({
            "pid": pid, "label": label, "grupa": grupa, "tel": bool(tel),
            "jezyki": jezyki or [], "forum_nick": forum_nick or pid, "inicjaly": inicjaly,
        })
        return pid

    def remove(self, pid: str) -> bool:
        if not self.col.document(pid).get().exists:
            return False
        self.col.document(pid).delete()
        return True


class FirestoreConfigStore:
    DEFAULTS = _ConfigDefaults.DEFAULTS

    def __init__(self, db: firestore.Client):
        self.ref = db.collection("szt_config").document("biz")

    def all(self) -> dict:
        cfg = dict(self.DEFAULTS)
        snap = self.ref.get()
        if snap.exists:
            cfg.update(snap.to_dict() or {})
        return cfg

    def get(self, key: str, default=None):
        return self.all().get(key, default)

    def set(self, key: str, value) -> None:
        self.ref.set({key: value}, merge=True)


class FirestoreStatsStore:
    def __init__(self, db: firestore.Client):
        self.col = db.collection("szt_events")

    def log(self, typ: str, operator_pid: str, numer: str, grupa: str, **extra) -> str:
        eid = uuid.uuid4().hex
        self.col.document(eid).set({
            "id": eid, "typ": typ, "operator": operator_pid, "numer": numer, "grupa": grupa,
            "ts": _now(), "data": time.strftime("%Y-%m-%d"), **extra,
        })
        return eid

    def events(self, data: Optional[str] = None, typ: Optional[str] = None) -> List[dict]:
        q = self.col
        if data:
            q = q.where("data", "==", data)
        if typ:
            q = q.where("typ", "==", typ)
        return [d.to_dict() for d in q.stream()]

    def diamenty_dzis(self, operator_pid: Optional[str] = None) -> int:
        today = time.strftime("%Y-%m-%d")
        evs = [e for e in self.events(data=today, typ="diament") if e.get("czy_diament")]
        if operator_pid:
            evs = [e for e in evs if e.get("operator") == operator_pid]
        return len(evs)


class FirestoreForumMemoryStore:
    def __init__(self, db: firestore.Client):
        self.col = db.collection("szt_forum_memory")

    def load(self, numer: str) -> dict:
        snap = self.col.document(str(numer)).get()
        return (snap.to_dict() or {}) if snap.exists else {}

    def save(self, numer: str, cel: str, entry: dict) -> None:
        ref = self.col.document(str(numer))
        snap = ref.get()
        mem = (snap.to_dict() or {}) if snap.exists else {}
        if cel not in mem:  # pierwszy wpis dla celu wygrywa
            ref.set({cel: entry}, merge=True)


_NAGL_OK = ("user-agent", "content-type", "x-forwarded-for")


class FirestoreWaInboxStore:
    """Odebrane wiadomości WhatsApp z bramy ATA (push webhook). Ten sam interfejs co WaInboxStore."""

    def __init__(self, db: firestore.Client):
        self.col = db.collection("szt_wa_inbox")

    def _zapisz_z_ponawianiem(self, rec: dict, proby: int = 3) -> None:
        """Zapis z ponawianiem: chwilowy błąd Firestore (timeout/quota) nie musi gubić wiadomości.
        Po wyczerpaniu prób RZUCA — wyżej łapie to endpoint i kieruje surowiec do dead-letter."""
        ost: Optional[Exception] = None
        for i in range(max(1, proby)):
            try:
                self.col.document(rec["id"]).set(rec)
                return
            except Exception as e:  # noqa: BLE001
                ost = e
                time.sleep(0.2 * (i + 1))
        raise ost if ost else RuntimeError("zapis nieudany")

    def add(self, raw, headers: Optional[dict] = None) -> dict:
        from .wspolne.archiwum import wzbogac
        from .wspolne.brama_wa import parsuj_wa
        rec = {
            "id": uuid.uuid4().hex,
            "received_at": _now(),
            **parsuj_wa(raw),
            "raw": raw if isinstance(raw, (dict, list)) else str(raw),
            "headers": {k: v for k, v in (headers or {}).items() if str(k).lower() in _NAGL_OK},
        }
        rec.update(wzbogac(rec))  # sklejanie po kliencie PRZY ZAPISIE (thread_id/order_refs/dedup)
        self._zapisz_z_ponawianiem(rec)
        return rec

    def dodaj_wyslane(self, channel: str, recipient: str, body: str,
                      msg_id: str = "", sender: str = "") -> dict:
        """Zapisz wiadomość WYCHODZĄCĄ (kierunek=out) — druga strona dialogu w archiwum.
        Woła to klient wysyłki przez bramę po udanym /messages/send (następna cegła)."""
        from .wspolne.archiwum import wzbogac
        from .wspolne.brama_wa import rekord_wyslany
        rec = {
            "id": uuid.uuid4().hex,
            "received_at": _now(),
            **rekord_wyslany(channel, recipient, body, msg_id, sender),
            "raw": {"_outbound": True, "channel": channel, "recipient": recipient, "body": body},
            "headers": {},
        }
        rec.update(wzbogac(rec))
        self._zapisz_z_ponawianiem(rec)
        return rec

    def recent(self, limit: int = 50) -> List[dict]:
        q = self.col.order_by("received_at", direction=firestore.Query.DESCENDING).limit(max(1, min(limit, 500)))
        return [d.to_dict() for d in q.stream()]

    def count(self) -> int:
        return len(list(self.col.limit(5000).stream()))


class FirestoreAwizacjeStore:
    """Awizacje kurierskie (faza 1) — kolekcja `awizacje_kurier`. Ten sam interfejs co AwizacjeStore.
    Idempotencja per dedup_key (nrZam): nie tworzy drugiej aktywnej awizacji dla tego samego zama."""

    def __init__(self, db: firestore.Client):
        self.col = db.collection("awizacje_kurier")

    def add(self, doc: dict) -> dict:
        dk = str(doc.get("dedup_key") or "")
        if dk:
            for d in self.col.where("dedup_key", "==", dk).stream():
                e = d.to_dict() or {}
                if e.get("status") != "anulowane":
                    return {**e, "skipped_idempotent": True}
        rec = {**doc}
        rec.setdefault("status", "nowe")
        rec["id"] = uuid.uuid4().hex
        rec["created_at"] = _now()
        self.col.document(rec["id"]).set(rec)
        return rec

    def recent(self, limit: int = 50) -> List[dict]:
        q = self.col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(max(1, min(limit, 500)))
        return [d.to_dict() for d in q.stream()]

    def count(self) -> int:
        return len(list(self.col.limit(5000).stream()))


def firestore_stores(project: str) -> Dict:
    """Buduje wszystkie magazyny Firestore (wywoływane z deps.py przy STORAGE=firestore)."""
    db = firestore.Client(project=project or None)
    return {
        "cases": FirestoreCasesStore(db),
        "operators": FirestoreOperatorsStore(db),
        "config": FirestoreConfigStore(db),
        "stats": FirestoreStatsStore(db),
        "memory": FirestoreForumMemoryStore(db),
        "wa_inbox": FirestoreWaInboxStore(db),
        "awizacje": FirestoreAwizacjeStore(db),
    }
