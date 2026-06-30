"""
Kontener zależności — buduje magazyny + klienta forum + dostawcę AI wg STORAGE
(jak gałąź STORAGE w main.py Pulpitu). Reszta apki bierze gotowe obiekty stąd.
"""
from __future__ import annotations

import logging
import os

from . import config
from .wspolne import ai
from .wspolne.forum import ForumClient

log = logging.getLogger("deps")

_DATA = config.DATA_DIR


def _file_stores():
    from .wspolne.store import (
        AwizacjeStore, CasesStore, ConfigStore, ForumMemoryStore, OperatorsStore, StatsStore, WaInboxStore,
    )
    return {
        "cases": CasesStore(os.path.join(_DATA, "cases.json")),
        "operators": OperatorsStore(os.path.join(_DATA, "operators.json")),
        "config": ConfigStore(os.path.join(_DATA, "config.json")),
        "stats": StatsStore(os.path.join(_DATA, "stats.json")),
        "memory": ForumMemoryStore(os.path.join(_DATA, "forum_memory.json")),
        "wa_inbox": WaInboxStore(os.path.join(_DATA, "wa_inbox.json")),
        "awizacje": AwizacjeStore(os.path.join(_DATA, "awizacje_kurier.json")),
    }


if config.STORAGE == "firestore":
    # Wersja produkcyjna — ten sam interfejs co pliki (TODO: firestore_store.py).
    try:
        from .firestore_store import firestore_stores  # type: ignore
        _stores = firestore_stores(config.GOOGLE_CLOUD_PROJECT)
        log.info("STORAGE=firestore")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "STORAGE=firestore, ale brak działającego firestore_store. "
            "Uruchom lokalnie z STORAGE=file albo dokończ firestore_store.py."
        ) from e
else:
    _stores = _file_stores()
    log.info("STORAGE=file (%s)", _DATA)

cases = _stores["cases"]
operators = _stores["operators"]
biz_config = _stores["config"]
stats = _stores["stats"]
forum_memory = _stores["memory"]
wa_inbox = _stores["wa_inbox"]
awizacje = _stores["awizacje"]


def _diament_logger(entry: dict) -> None:
    """Forum woła to przy zleceniu kuriera → zapis do jednego strumienia zdarzeń."""
    stats.log(
        "diament",
        operator_pid=entry.get("operator", ""),
        numer=entry.get("numer_zamowienia", ""),
        grupa=entry.get("grupa", ""),
        czy_diament=bool(entry.get("czy_diament")),
        typ_zlecenia=entry.get("typ_zlecenia", ""),
        kurier=entry.get("kurier", ""),
        kategoria=entry.get("kategoria_towaru", ""),
        forum_post_id=entry.get("forum_post_id", ""),
        anomalia=bool(entry.get("anomalia")),
    )


def _awizacja_emitter(doc: dict) -> dict:
    """Forum woła to przy zleceniu kuriera fazy 1 (UPS skrzynia) → zapis do `awizacje_kurier`
    (sygnał do apki Eweliny). Zwraca rekord (z ewentualnym skipped_idempotent)."""
    return awizacje.add(doc)


forum = ForumClient(forum_memory, diament_logger=_diament_logger, awizacja_emitter=_awizacja_emitter)
ai_provider = ai.get_provider()


def active_prompt_text() -> str:
    """Tekst aktywnego promptu: nadpisanie z panelu (URL) albo wbudowany v1_9 (domyślny)."""
    return ai.get_prompt((biz_config.get("prompt_url") or "").strip())


def active_prompt_label() -> str:
    """Etykieta aktywnego promptu do panelu."""
    return (biz_config.get("prompt_url") or "").strip() or "v1_9 (wbudowany)"


def seed_dev() -> None:
    """Lokalnie: zasiej kilka spraw i operatora, by ekran miał co pokazać (tylko dev, pusta baza)."""
    if not config.is_dev():
        return
    if not operators.list():
        operators.upsert("dev", "Operator testowy (DE)", "DE", tel=True,
                         jezyki=["DE"], forum_nick="chatek")
    if not cases.all():
        from .wspolne.model import Case
        przyklady = [
            ("374593", "DE", 980, "NrZam: 374593 | Germany | zwrot skrzyni biegów, klient nie odbiera"),
            ("357219", "DE", 720, "NrZam: 357219 | Austria | reklamacja kolektor, czeka na kuriera"),
            ("400112", "FR", 650, "NrZam: 400112 | France | zwrot, klient pyta o etykietę"),
        ]
        for i, (nr, grp, score, linia) in enumerate(przyklady):
            cases.upsert(Case(
                numer_zamowienia=nr, grupa=grp, score=score,
                pelna_linia_szturchacza=linia, data_obrobki=_today(), sort_order=i,
                priority_icon="🔴" if score > 800 else "🟠",
            ))
        log.info("[seed] dodano %d przykładowych spraw (dev).", len(przyklady))


def _today() -> str:
    import time
    return time.strftime("%Y-%m-%d")
