"""
BC-STORE — własny magazyn pasa bestchudy (kolekcje z prefiksem bc_).

Wzorzec SKOPIOWANY (nie importowany!) z warstwy zapisu apki — reguła pasa: wspólne importy
to wyłącznie sso.read_operator + fasada styki (COORDYNACJA → rozpis pkt 2 i ŁĄCZNIKI).
Dwuwarstwowo jak cała apka: STORAGE=file (domyślnie; JSON w DATA_DIR) / firestore (prod).
Budowa LENIWA przy pierwszym użyciu (wzorzec ai.get_provider) — zła konfiguracja nie ubija
startu apki. Firestore: tylko równości w zapytaniach, sortowanie w Pythonie (indeksy złożone
tworzy koordynator — nie wymuszamy ich).
"""
from __future__ import annotations

import json
import os
import threading

_MAX_PLIK = 5000          # rotacja pliku lokalnego (najnowsze zostają)
_LIMIT_ODCZYTU = 500

_lock = threading.Lock()
_store = None


def _data_dir() -> str:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.environ.get("DATA_DIR", os.path.join(root, "data"))


class _JsonFile:
    """Plik JSON z blokadą i zapisem atomowym (tmp + os.replace) — kopia wzorca ze store.py."""

    def __init__(self, path: str):
        self._path = path
        self._lock = threading.RLock()

    def read(self) -> list:
        with self._lock:
            if not os.path.exists(self._path):
                return []
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    dane = json.load(f)
                return dane if isinstance(dane, list) else []
            except Exception:
                return []

    def write(self, dane: list) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dane, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self._path)


def _filtruj(recs, dzien: str, odrzuty: bool, limit: int) -> list:
    from . import logika
    wynik = []
    for r in recs:
        if dzien and r.get("dzien") != dzien:
            continue
        if odrzuty and not logika.czy_odrzut(r):
            continue
        wynik.append(r)
        if len(wynik) >= limit:
            break
    return wynik


class _FileStore:
    def __init__(self):
        dd = _data_dir()
        self._porownania = _JsonFile(os.path.join(dd, "bc_porownania.json"))
        self._oceny = _JsonFile(os.path.join(dd, "bc_oceny_sesji.json"))

    def dodaj_porownanie(self, rec: dict) -> None:
        dane = self._porownania.read()
        dane.insert(0, rec)                       # najnowsze na przodzie
        self._porownania.write(dane[:_MAX_PLIK])

    def porownania(self, dzien: str = "", odrzuty: bool = False, limit: int = 200) -> list:
        return _filtruj(self._porownania.read(), dzien, odrzuty, min(limit, _LIMIT_ODCZYTU))

    def porownanie(self, pid: str):
        for r in self._porownania.read():
            if r.get("id") == pid:
                return r
        return None

    def dodaj_ocene(self, rec: dict) -> None:
        dane = self._oceny.read()
        dane.insert(0, rec)
        self._oceny.write(dane[:_MAX_PLIK])

    def oceny(self, dzien: str = "", limit: int = 50) -> list:
        dane = [r for r in self._oceny.read() if not dzien or r.get("dzien") == dzien]
        return dane[:min(limit, _LIMIT_ODCZYTU)]


class _FirestoreStore:
    def __init__(self, project: str):
        from google.cloud import firestore  # leniwy import — lokalnie niepotrzebny
        self._db = firestore.Client(project=project or None)
        self._porownania = self._db.collection("bc_porownania")
        self._oceny = self._db.collection("bc_oceny_sesji")

    def dodaj_porownanie(self, rec: dict) -> None:
        self._porownania.document(rec["id"]).set(rec)

    def porownania(self, dzien: str = "", odrzuty: bool = False, limit: int = 200) -> list:
        from google.cloud import firestore
        q = self._porownania
        if dzien:
            q = q.where("dzien", "==", dzien)     # tylko równość — bez indeksów złożonych
        else:
            # Bez dnia: sort po JEDNYM polu (indeks automatyczny) — inaczej limit(500)
            # tnie po losowych ID dokumentów i gubi najnowsze rekordy.
            q = q.order_by("created_at", direction=firestore.Query.DESCENDING)
        recs = [d.to_dict() for d in q.limit(_LIMIT_ODCZYTU).stream()]
        recs.sort(key=lambda r: r.get("created_at", ""), reverse=True)  # sort w Pythonie
        return _filtruj(recs, "", odrzuty, min(limit, _LIMIT_ODCZYTU))

    def porownanie(self, pid: str):
        doc = self._porownania.document(pid).get()
        return doc.to_dict() if doc.exists else None

    def dodaj_ocene(self, rec: dict) -> None:
        self._oceny.document(rec["id"]).set(rec)

    def oceny(self, dzien: str = "", limit: int = 50) -> list:
        from google.cloud import firestore
        q = self._oceny
        if dzien:
            q = q.where("dzien", "==", dzien)
        else:
            q = q.order_by("created_at", direction=firestore.Query.DESCENDING)
        recs = [d.to_dict() for d in q.limit(_LIMIT_ODCZYTU).stream()]
        recs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return recs[:min(limit, _LIMIT_ODCZYTU)]


def get_store():
    """Leniwy singleton pod blokadą — wzorzec ai.get_provider (nie anty-wzorzec deps)."""
    global _store
    if _store is None:
        with _lock:
            if _store is None:
                if os.environ.get("STORAGE", "file").lower() == "firestore":
                    _store = _FirestoreStore(os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
                else:
                    _store = _FileStore()
    return _store
