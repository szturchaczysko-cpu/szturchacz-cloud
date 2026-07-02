"""
Silnik AI (Vertex/Gemini) za prostym interfejsem + ZAŚLEPKA do pracy lokalnej bez GCP.

- `get_provider()` zwraca dostawcę: VertexProvider gdy skonfigurowany (GCP_PROJECT_IDS i
  dostępny pakiet), inaczej StubProvider (lokalne testy całego przepływu bez chmury).
- `get_remote_prompt(url)` pobiera „Kartotekę Twardą" z repo (decyzja: prompt zostaje na GitHubie),
  ale UTWARDZONY: cache TTL + fallback do ostatniej dobrej wersji (awaria repo NIE blokuje operatora).
- Kontrakt dostawcy: `respond(system_prompt: str, messages: list[dict], *, temperature=0.0) -> str`.
  messages: [{"role": "user"|"model", "content": str}, ...].
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Dict, List, Optional

import requests

from .. import config

log = logging.getLogger("ai")

# Wbudowane prompty (wersjonowane z kodem). v1_11 = kanoniczny pełny (decyzja zespołu 2026-06-30,
# kopia 1:1 z kontener_v11 — tam źródło); v1_9 = poprzedni; chudy = odchudzony (warstwa AI).
_PROMPTS_DIR = os.path.join(config.BASE_DIR, "prompts")
BUNDLED_PROMPTY = {
    "v1_11": "szturchacz_vnext_v1_11.txt",
    "v1_9": "szturchacz_v1_9.txt",
    "chudy": "szturchacz_chudy.txt",
}
_bundled_cache: Dict[str, str] = {}


def load_bundled_prompt(name: str = "v1_11") -> str:
    name = name if name in BUNDLED_PROMPTY else "v1_11"
    if name not in _bundled_cache:
        path = os.path.join(_PROMPTS_DIR, BUNDLED_PROMPTY[name])
        try:
            with open(path, "r", encoding="utf-8") as fh:
                _bundled_cache[name] = fh.read()
        except OSError as e:  # noqa: BLE001
            log.error("Brak wbudowanego promptu %s: %s", path, e)
            _bundled_cache[name] = ""
    return _bundled_cache[name]


def get_prompt(override: str = "") -> str:
    """
    Domyślnie wbudowany v1_11 (decyzja zespołu). Koordynator może wskazać w panelu:
    nazwę wbudowanego ('v1_11' / 'v1_9' / 'chudy') albo URL (pobierany, utwardzony cache+fallback).
    """
    o = (override or "").strip()
    if o.lower() in BUNDLED_PROMPTY:
        return load_bundled_prompt(o.lower())
    if o:
        return get_remote_prompt(o)  # traktuj jako URL
    return load_bundled_prompt("v1_9")

# --- Pobieranie promptu (utwardzone) -------------------------------------------
_PROMPT_TTL = 3600  # 1h
_prompt_cache: Dict[str, dict] = {}  # url -> {"text", "fetched": ts}
_prompt_lock = threading.Lock()


def get_remote_prompt(url: str) -> str:
    """
    Pobiera prompt z URL z cache (TTL) i fallbackiem do ostatniej dobrej wersji.
    Awaria GitHuba NIE blokuje operatora (stary kod robił st.stop()).
    """
    if not url:
        return ""
    now = time.time()
    with _prompt_lock:
        cached = _prompt_cache.get(url)
        if cached and now - cached["fetched"] < _PROMPT_TTL:
            return cached["text"]
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        text = resp.text
        with _prompt_lock:
            _prompt_cache[url] = {"text": text, "fetched": now}
        return text
    except Exception as e:  # noqa: BLE001 — każda awaria sieci/repo
        with _prompt_lock:
            cached = _prompt_cache.get(url)
        if cached:
            log.warning("Prompt z %s niedostępny (%s) — używam ostatniej dobrej wersji.", url, e)
            return cached["text"]
        log.error("Prompt z %s niedostępny i brak wersji w cache: %s", url, e)
        return ""


# Skrót grupy → literalna ROLA, której oczekuje prompt (Grupa_Operatorska).
_GRUPA_DO_ROLI = {"DE": "Operatorzy_DE", "FR": "Operatorzy_FR", "UKPL": "Operatorzy_UK/PL"}


def build_start_params(*, operator: str, data: str, grupa: str, tryb: str = "standard",
                       notag: bool = False, analizbior: bool = False,
                       godziny_fedex: str = "8-16:30", godziny_ups: str = "8-18") -> str:
    """
    Blok parametrów startowych doklejany na KOŃCU promptu — 1:1 z v1_9 §3 (linia 777).
    Klucze (dokładnie te): domyslny_operator, domyslna_data (DD.MM), Grupa_Operatorska
    (=rola, np. Operatorzy_DE), domyslny_tryb, notag, analizbior, godziny_fedex, godziny_ups.
    Prawo do dzwonienia v1_9 bierze z TABELI OSÓB (TEL_JEZYK), nie z flagi — to wstrzykniemy
    z listy operatorów przy warstwie sterującej.
    """
    rola = _GRUPA_DO_ROLI.get(grupa, "Operatorzy_DE")
    return (
        "\n# PARAMETRY STARTOWE\n"
        f"domyslny_operator={operator}\n"
        f"domyslna_data={data}\n"
        f"Grupa_Operatorska={rola}\n"
        f"domyslny_tryb={tryb}\n"
        f"notag={'TAK' if notag else 'NIE'}\n"
        f"analizbior={'TAK' if analizbior else 'NIE'}\n"
        f"godziny_fedex={godziny_fedex}\n"
        f"godziny_ups={godziny_ups}\n"
    )


# --- Dostawcy ------------------------------------------------------------------
class StubProvider:
    """
    Zaślepka do pracy lokalnej bez GCP. Zwraca wiarygodną odpowiedź z TAG-iem (żeby da się
    było domknąć sprawę) i — gdy wsad wygląda na zlecenie kuriera — marker [FORUM_WRITE|...],
    by przetestować ścieżkę forum w trybie 'sucho'. NIE jest to prawdziwe AI.
    """

    name = "stub"

    def respond(self, system_prompt: str, messages: List[dict], *, temperature: float = 0.0) -> str:
        last = messages[-1]["content"] if messages else ""
        tag = "C#:" + time.strftime("%d.%m") + ";PZ=PZ2;DRABES=WA1"
        parts = [
            "[ZAŚLEPKA AI — lokalnie, bez GCP]",
            "Krok teraz: skontaktuj się z klientem i potwierdź adres odbioru.",
            "",
            "Draft do klienta:",
            "Dzień dobry, w sprawie zwrotu prosimy o potwierdzenie adresu odbioru. "
            "Z poważaniem, Zespół Obsługi Klienta",
            "",
            f"TAG: {tag}",
        ]
        if "kurier" in (last or "").lower():
            parts.append("[FORUM_WRITE|cel=AUTOS_KURIERZY|tresc=Zamówienie: 000000 — proszę o kuriera]")
        return "\n".join(parts)


class VertexProvider:
    """
    Prawdziwy dostawca (Vertex/Gemini). Pakiet ładowany leniwie — apka działa lokalnie bez niego.
    Rotacja projektów GCP (rozłożenie limitów) + łańcuch fallbacku modeli + retry na 429/503.
    """

    name = "vertex"
    # Modele zgodne z tym, czego używała stara apka (allowed_models).
    FALLBACK_CHAIN = ["gemini-2.5-pro", "gemini-3-pro-preview"]

    def __init__(self, project_ids: List[str], location: str):
        self._projects = project_ids
        self._location = location
        self._idx = 0

    def _init_vertex(self, project: str):
        import vertexai  # leniwy import — może nie być lokalnie
        vertexai.init(project=project, location=self._location)

    def respond(self, system_prompt: str, messages: List[dict], *, temperature: float = 0.0) -> str:
        from vertexai.generative_models import Content, GenerativeModel, Part  # leniwy import

        project = self._projects[self._idx % len(self._projects)]
        self._idx += 1
        history = [
            Content(role=("user" if m["role"] == "user" else "model"),
                    parts=[Part.from_text(m["content"])])
            for m in messages
        ]
        last_err: Optional[Exception] = None
        for model_name in [self.FALLBACK_CHAIN[0]] + self.FALLBACK_CHAIN[1:]:
            for attempt in range(3):
                try:
                    self._init_vertex(project)
                    model = GenerativeModel(model_name, system_instruction=system_prompt)
                    resp = model.generate_content(
                        history, generation_config={"temperature": temperature})
                    return resp.text
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    msg = str(e).lower()
                    if any(k in msg for k in ("429", "503", "quota", "resource")):
                        time.sleep(min(2.0 * (attempt + 1), 6.0))
                        project = self._projects[self._idx % len(self._projects)]
                        self._idx += 1
                        continue
                    break  # błąd nie-przejściowy → spróbuj kolejnego modelu
        raise RuntimeError(f"Vertex niedostępny po fallbackach: {last_err}")


_provider = None
_provider_lock = threading.Lock()


def get_provider():
    """Vertex gdy skonfigurowany i dostępny; inaczej zaślepka (lokalnie)."""
    global _provider
    with _provider_lock:
        if _provider is not None:
            return _provider
        if config.GCP_PROJECT_IDS:
            try:
                import vertexai  # noqa: F401 — sprawdzenie dostępności pakietu
                _provider = VertexProvider(config.GCP_PROJECT_IDS, config.GCP_LOCATION)
                log.info("AI: VertexProvider (%d projektów).", len(config.GCP_PROJECT_IDS))
                return _provider
            except Exception as e:  # noqa: BLE001
                log.warning("AI: Vertex skonfigurowany, ale pakiet niedostępny (%s) — zaślepka.", e)
        _provider = StubProvider()
        log.info("AI: StubProvider (brak konfiguracji GCP).")
        return _provider
