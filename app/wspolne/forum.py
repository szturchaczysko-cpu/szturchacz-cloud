"""
MODUŁ FORUM F15 — czysty klient (de-Streamlit) dla apki FastAPI.

Port modułu `forum_module.py` (Streamlit) do wstrzykiwanej klasy ForumClient.
Logika integracji (REST, payloady, prywatność, filtrowanie drzewka, diamenty)
zachowana 1:1 z oryginału — odcięty jest tylko Streamlit (st.secrets/session_state/
toast/print) i globalny Firestore. Zależności wstrzykiwane przez konstruktor.

Endpointy F15:
- POST /api/wpisy/CreatePost  — tworzenie/edycja postów (PISANIE)
- POST /api/wpisy/GetPostTree — czytanie podwątków (CZYTANIE)
Nick bota: chatoszturek. Token: stały Bearer z config.FORUM_BEARER_TOKEN.

=====================================================================
PUBLICZNY INTERFEJS  —  ForumClient
=====================================================================

    client = ForumClient(memory: ForumMemoryStore, diament_logger=None)

      memory          : ForumMemoryStore — most numer_zamówienia ↔ wpisy forum
                        (metody load(numer)->dict, save(numer, cel, entry)->None).
      diament_logger  : Optional[callable(entry: dict) -> None] — wołany ZAMIAST
                        zapisu Firestore w klasyfikacji diamentu. Apka podłącza tu
                        zapis do swojego store. None → diament tylko liczony i logowany.

    Atrybut self.live = (config.FORUM_MODE == "live").
      live == False (tryb "sucho"): CreatePost NIE wysyła realnie — loguje zamierzony
      payload i zwraca symulowany sukces (new_post_id="DRYRUN"). GetPostTree działa
      normalnie (czytanie jest bezpieczne).

    Metody publiczne:

      write_to_thread(cel, tresc, *, user_od, ai_user, source_type, numer=None) -> dict
          Wpis na znany wątek (FORUM_THREADS[cel]). Tytuł = numer zamówienia z treści.
          Idempotencja zleceń kuriera (cel=AUTOS_KURIERZY): jeśli w self.memory(numer)
          istnieje już wpis dla tego celu — nie wysyła ponownie (chroni przed podwójnym
          zamówieniem kuriera w autopilocie). Zwraca dict z success/new_post_id/FORUM_ID/...

      read_subtree(cel, numer) -> dict
          Czyta i filtruje podwątek po numerze zamówienia + hierarchii.
          Zwraca {success, posts, thread_title, count} albo {success: False, error}.

      execute_actions(ai_text, *, user_od, ai_user, source_type) -> dict
          Parsuje markery [FORUM_WRITE|...] / [FORUM_READ|...] z odpowiedzi AI,
          wykonuje je i PODMIENIA marker w tekście na komunikat.
          Zwraca {"text": podmieniony_tekst, "reads": [...], "writes": [...]}.

      auto_load_context(numer) -> str
          Buduje [FORUM_CONTEXT] (pamięć → skan, ostatnie 10 postów na cel,
          wykrycie odpowiedzi człowieka = autor != chatoszturek). Bezpiecznik pustego
          odczytu. Pusty string gdy brak kontekstu.

      check_answer(numer, cel=None) -> bool
          Czy pod wątkiem (delegacji) jest odpowiedź nie-bota? Używane przez nocny
          autopilot do routingu telefonów. cel=None → sprawdza wszystkie cele w pamięci.
"""
from __future__ import annotations

import re
import json  # noqa: F401  (część kontraktu importów; payloady idą przez requests json=)
import logging

import requests

from .. import config
from .store import ForumMemoryStore

log = logging.getLogger("forum")


# --- KONFIGURACJA ---
FORUM_USER = "chatoszturek"
USE_NEW_SUBTHREADS = True

# Whitelist znanych userów indywidualnych (type=1)
# Sprzedawcy, telefoniści jako osoby, chatoszturek
KNOWN_INDIVIDUAL_USERS = {
    "chatoszturek", "chatek", "chatosztur",
    # Sprzedawcy z underscore
    "kasia_k", "anna_m", "oliwia_m", "klaudia_k",
    # Osoby z whitelist
    "sylwia", "justyna", "romana", "EwelinaG",
}


def _is_individual_user(nick):
    """True jeśli nick to pojedynczy user (type=1), False jeśli grupa (type=2)."""
    if not nick:
        return True
    # Jawna whitelista
    if nick in KNOWN_INDIVIDUAL_USERS:
        return True
    if nick.lower() in {u.lower() for u in KNOWN_INDIVIDUAL_USERS}:
        return True
    # Heurystyka: grupa = wszystko WIELKIMI lub z "/"
    if nick.isupper():
        return False
    if "/" in nick:
        return False
    # Grupy "mieszane": Telefoniści_DE, Operatorzy_DE
    if re.match(r'^[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+_[A-Z]{2,}$', nick):
        return False
    # Domyślnie: user
    return True


def _strip_html(text):
    return re.sub(r'<[^>]+>', ' ', text).strip()


CHATOSZTUREK_DISCLAIMER = (
    '<br><br>---<br>'
    '<b>Jestem Chatoszturkiem AI, asystentem działu zwrotów.</b> '
    'Jeśli ta wiadomość wymaga korekty — odpisz tutaj.'
)


# ==========================================
# MAPOWANIE WĄTKÓW FORUM (PROD — znane post_id)
# ==========================================

FORUM_THREADS = {
    "AUTOS_KURIERZY": {
        "post_id": 5687, "korzen_id": None,
        "grupa": "TEAM_ATOMOWKI", "grupa_type": 2,
        "opis": "Zlecenie kuriera/etykiety/atomówki (§11.4)",
    },
    "SPEDYCJA_REKLAMACJE": {
        "post_id": 5693, "korzen_id": None,
        "grupa": "SPEDYCJA_REKLAMACJE", "grupa_type": 2,
        "opis": "Problemy po zleceniu kuriera (§10.4)",
    },
    "CZATOSZTUR_REKLAMACJE": {
        "post_id": 5688, "korzen_id": None,
        "grupa": "DZIAŁ_EKSPERCKI", "grupa_type": 2,
        "opis": "Reklamacja 'co dalej / można szturchać' (§5.3)",
    },
    "NIEPOZAMYKANE_AUSTAUSCHE": {
        "post_id": 5692, "korzen_id": None,
        "grupa": "NIEPOZAMYKANE AUSTAUSCHE", "grupa_type": 2,
        "opis": "Niezamknięte Austausche / zielonka (§10.5)",
    },
    "CZATOSZTUR_DE": {
        "post_id": 5690, "korzen_id": None,
        "grupa": "Operatorzy_DE", "grupa_type": 2,
        "opis": "Czatosztur DE — delegacje TEL, zapytania (§8.3)",
    },
    "CZATOSZTUR_FR": {
        "post_id": 5689, "korzen_id": None,
        "grupa": "Operatorzy_FR", "grupa_type": 2,
        "opis": "Czatosztur FR (§8.3)",
    },
    "CZATOSZTUR_UKPL": {
        "post_id": 5691, "korzen_id": None,
        "grupa": "Operatorzy_UK/PL", "grupa_type": 2,
        "opis": "Czatosztur UK/PL (alias z underscore)",
    },
    "CZATOSZTUR_UK/PL": {
        "post_id": 5691, "korzen_id": None,
        "grupa": "Operatorzy_UK/PL", "grupa_type": 2,
        "opis": "Czatosztur UK/PL (z ukośnikiem — literalna nazwa)",
    },
    "szturchacz_błędy": {
        "post_id": 5703, "korzen_id": None,
        "grupa": "SZTURZE_WSPARCIE", "grupa_type": 2,
        "opis": "Zgłoszenia błędów AI / integracji forum",
    },
}


def _get_thread_raw(cel):
    """Case-insensitive lookup w FORUM_THREADS."""
    info = FORUM_THREADS.get(cel)
    if info:
        return info
    if not cel:
        return None
    # Case-insensitive fallback — gdyby AI wysłała 'czatosztur_fr' małymi
    for _k, _v in FORUM_THREADS.items():
        if _k.lower() == cel.lower():
            log.info("THREAD LOOKUP: case-insensitive match: '%s' → '%s'", cel, _k)
            return _v
    return None


# ==========================================
# PARSOWANIE MARKERÓW Z ODPOWIEDZI AI
# ==========================================

FORUM_MARKER_PATTERN = re.compile(r'\[FORUM_(WRITE|READ)\|([^\]]+)\]', re.DOTALL)


def parse_forum_markers(ai_response):
    markers = []

    for m in FORUM_MARKER_PATTERN.finditer(ai_response):
        action = m.group(1).lower()
        params_str = m.group(2)

        params = {}
        if action == "write" and "|tresc=" in params_str:
            before_tresc, tresc = params_str.split("|tresc=", 1)
            params["tresc"] = tresc.strip()
            for part in before_tresc.split("|"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k.strip()] = v.strip()
        else:
            for part in params_str.split("|"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k.strip()] = v.strip()

        marker = {"type": action, "raw": m.group(0), "params": params}

        if action == "write":
            marker["cel"] = params.get("cel", "")
            marker["tresc"] = params.get("tresc", "")
            marker["do_odp_id"] = int(params["do_odp_id"]) if "do_odp_id" in params else None
            marker["user_do"] = params.get("user_do", None)
            marker["tytul"] = params.get("tytul", None)
        elif action == "read":
            marker["forum_id"] = int(params["forum_id"]) if "forum_id" in params else None
            marker["cel"] = params.get("cel", "")

        markers.append(marker)

    return markers


# ==========================================
# DIAMENTY v1.5.7d "pomijamyPZ6" — decyzja na podstawie TREŚCI posta
# ==========================================

# Stop-lista: posty zawierające te słowa NIE są diamentami (bumpy/ponaglenia/eskalacje).
# UWAGA: celowo BEZ "etykiet" — etykieta UPS punkt JEST diamentem (decyzja EA).
DIAMOND_STOP_WORDS = re.compile(r'(bump|ponaglenie|eskalacja|dopyt|podbicie)', re.IGNORECASE)

# Walidacja: prawdziwe zlecenie kuriera/etykiety zawsze zawiera "Zamówienie: NNN"
_RE_DIAMOND_ZAMOWIENIE = re.compile(r'Zam[óo]wienie\s*[:=]\s*(\d+)', re.IGNORECASE)

# Ekstrakcja z treści posta — tolerancja [:=] (tag C# w ai_text używa "=", treść posta ":")
_RE_DIAMOND_TOWAR = re.compile(r'TOWAR_TYP\s*[:=]\s*(KOLEKTOR|SKRZYNIA)', re.IGNORECASE)
# v1.5.7e: łapie też samo "Schenker" (normalizacja do DBSCHENKER w log_diamond)
_RE_DIAMOND_KURIER = re.compile(r'Kurier\s*[:=]\s*(UPS|FEDEX|(?:DB[\s_]?)?SCHENKER)', re.IGNORECASE)
_RE_DIAMOND_ETYKIETA = re.compile(r'(UPS_ETYKIETA_PUNKT|KURIER_OPCJA\s*[:=]\s*ETYKIETA_PUNKT)', re.IGNORECASE)
_RE_DIAMOND_KURIER_SLOWO = re.compile(r'(Kurier\s*[:=]|KURIER_PRZEWOZNIK)', re.IGNORECASE)

# v1.5.7e: typy NIE-diamentów ("anulowane") — frazy werdykt EA 1:1 (11.06.2026).
_RE_TYP_ZMIANA = re.compile(
    r'(KOREKTA|zmiana\s+terminu|nowy\s+termin|prze[łl]o[żz]|zmieni[łl]\s+dat|aktualizacja\s+zlecenia|notatk)',
    re.IGNORECASE)
# cofniete: WSTRZYMANIE / anulowanie / anulować / cofnięcie / rezygnacja
_RE_TYP_COFNIETE = re.compile(
    r'(WSTRZYMA|anulowa|cofni[ęe]|rezygnacj)',
    re.IGNORECASE)
# ponowienie: ponawiam / ponowienie / przypominam / brak odpowiedzi
_RE_TYP_PONOWIENIE = re.compile(
    r'(ponawiam|ponowieni|przypominam|brak\s+odpowiedzi)',
    re.IGNORECASE)
NIE_DIAMENT_TYPY = ("zmiana", "cofniete", "ponowienie")


def _validate_diamond_from_tresc(tresc):
    """Czy treść posta na AUTOS_KURIERZY to faktyczne zlecenie (diament)?

    Warunki: treść zawiera 'Zamówienie: NNN' AND nie zawiera słów stop-listy
    (bump/ponaglenie/eskalacja/dopyt/podbicie).
    """
    if not tresc:
        return False
    if not _RE_DIAMOND_ZAMOWIENIE.search(tresc):
        return False
    if DIAMOND_STOP_WORDS.search(tresc):
        return False
    return True


def _classify_typ_zlecenia(tresc):
    """Klasyfikacja typu zlecenia z treści posta.

    Kolejność (werdykt EA): zmiana → cofniete → ponowienie → etykieta_ups_punkt
    → kurier → inne. Typy zmiana/cofniete/ponowienie to NIE-diamenty (anulowane).
    """
    if not tresc:
        return "inne"
    if _RE_TYP_ZMIANA.search(tresc):
        return "zmiana"
    if _RE_TYP_COFNIETE.search(tresc):
        return "cofniete"
    if _RE_TYP_PONOWIENIE.search(tresc):
        return "ponowienie"
    if _RE_DIAMOND_ETYKIETA.search(tresc):
        return "etykieta_ups_punkt"
    if _RE_DIAMOND_KURIER_SLOWO.search(tresc):
        return "kurier"
    return "inne"


# ==========================================
# KLIENT FORUM
# ==========================================

class ForumClient:
    """Wstrzykiwany klient forum F15. Patrz docstring modułu."""

    def __init__(self, memory: ForumMemoryStore, diament_logger=None, awizacja_emitter=None):
        self.memory = memory
        self.diament_logger = diament_logger
        self.awizacja_emitter = awizacja_emitter   # callable(doc)->rec; awizacja kuriera fazy 1 (UPS skrzynia)
        self.base = config.FORUM_API_BASE
        self.live = (config.FORUM_MODE == "live")
        # Offline (lokalnie / brak realnego tokenu): nie wykonuj wywołań sieciowych,
        # żeby CZYTANIE forum nie wieszało się na timeoutach. Pisanie i tak gated self.live.
        _tok = config.FORUM_BEARER_TOKEN or ""
        self.can_call = bool(_tok) and not _tok.lower().startswith("wstaw")

    # --- niskopoziomowe HTTP -----------------------------------------------

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.FORUM_BEARER_TOKEN}",
        }

    # ==========================================
    # PISANIE — CreatePost
    # ==========================================

    def _forum_write(self, post_id, do_odp_id, user_do, tresc, user_do_type=1,
                     user_od=None, ai_user=None, tytul=None):
        """Wpis na forum (CreatePost).

        PRYWATNOŚĆ: AiUser = ZAWSZE konto AI ("chatoszturek"), NIGDY nick operatora.
        Faktyczny autor (operator albo "chatoszturek" w autopilocie) → SubThread.UserRzeczywisty.

        BEZPIECZNIK "na sucho": gdy self.live == False, NIE wysyła realnie — loguje
        zamierzony payload i zwraca symulowany sukces (new_post_id="DRYRUN").
        """
        if user_od is None:
            user_od = FORUM_USER

        # Stempel autora w treści — widoczne „przerobione przez" gdy za wpisem stoi OPERATOR (nie bot).
        if ai_user and ai_user != FORUM_USER and tresc and "Przerobione przez:" not in tresc:
            tresc = f"{tresc}<br><i>Przerobione przez: {ai_user}</i>"

        # from_user_type: 1=user, 2=grupa (jeśli wysyła grupa operatorów)
        from_user_type = 1 if _is_individual_user(user_od) else 2

        # UserRzeczywisty = faktyczny autor (login): operator (sesja) lub chatoszturek (autopilot/brak).
        user_rzeczywisty = ai_user if ai_user else FORUM_USER

        log.info("WRITE: post_id=%s, do_odp_id=%s, user_do=%s, type=%s",
                 post_id, do_odp_id, user_do, user_do_type)
        log.info("WRITE: user_od=%s, from_type=%s, AiUser=%s, UserRzeczywisty=%s, tytul=%r",
                 user_od, from_user_type, FORUM_USER, user_rzeczywisty, tytul)
        log.info("WRITE: tresc=%s...", (tresc or "")[:80])

        payload = {
            "thread": {
                "id": post_id,
                "title": tytul,
                "fromUser": user_od,
                "fromUserType": from_user_type,
                "toUser": user_do,
                "toUserType": user_do_type,
                "private": False,
            },
            "subThread": {
                "id": do_odp_id,
                "text": tresc,
                "fromUser": user_od,
                "fromUserType": from_user_type,
                "toUser": user_do,
                "toUserType": user_do_type,
                "type": 0,
                "title": tytul,
                "private": False,
                "AiGenerated": 1,
                "AiUser": FORUM_USER,                  # ZAWSZE konto AI (chatoszturek)
                "UserRzeczywisty": user_rzeczywisty,   # faktyczny autor: operator lub chatoszturek
                "SilentConfirmAfterCreate": False,
            },
        }

        # BEZPIECZNIK „na sucho": nie wysyłaj realnie, zwróć symulowany sukces.
        if not self.live:
            log.info("WRITE DRYRUN (FORUM_MODE=%s): zamierzony payload=%s",
                     config.FORUM_MODE, json.dumps(payload, ensure_ascii=False))
            return {
                "success": True,
                "new_post_id": "DRYRUN",
                "message": "DRYRUN — wpis NIE wysłany (FORUM_MODE != live)",
                "link": None,
                "dryrun": True,
            }

        try:
            resp = requests.post(
                f"{self.base}/api/wpisy/CreatePost",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "SUCCESS":
                msg = data.get("message", "")
                id_match = re.search(r'\(id:\s*(\d+)\)', msg)
                if not id_match:
                    id_match = re.search(r'id[:\s]+(\d+)', msg, re.IGNORECASE)
                if not id_match:
                    id_match = re.search(r'(\d{7,})', msg)
                new_id = int(id_match.group(1)) if id_match else None

                log.info("WRITE RESULT: success=True, new_id=%s, msg=%s", new_id, msg[:100])

                if not new_id:
                    log.warning("Forum API OK ale brak ID w: %s", msg[:200])

                return {
                    "success": True,
                    "new_post_id": new_id,
                    "message": msg,
                    "link": (
                        f"{self.base}/Wpisy/detailWpis?id={post_id}&do_odpid={new_id}#odp-{new_id}"
                        if new_id else None
                    ),
                }
            else:
                return {"success": False, "error": data.get("message", "Nieznany błąd")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==========================================
    # CZYTANIE — GetPostTree
    # ==========================================

    def _forum_read(self, branch_id=None, root_id=None, leaf_id=None, max_pages=5,
                    login_requested_by=None, login_acting_as=None, member_type_acting_as=None):
        """Czytanie drzewka (GetPostTree).

        PRYWATNOŚĆ: stare pole "login" USUNIĘTE. Autoryzacja przez stały bearer token,
        tożsamość w body: LoginRequestedBy + LoginActingAs(string) + MemberTypeActingAs(int).
        """
        if not self.can_call:
            return {"success": False, "error": "forum offline (brak realnego tokenu)"}

        all_posts = []
        thread_title = ""

        for page in range(1, max_pages + 1):
            # FIX 406: GetPostTree WYMAGA LoginActingAs (string) oraz MemberTypeActingAs
            # (int: 1=user, 2=grupa). Bez nich serwer zwraca 406 Not Acceptable.
            _lrb = login_requested_by or FORUM_USER
            _laa = login_acting_as or _lrb
            _mta = member_type_acting_as if member_type_acting_as else (
                1 if _is_individual_user(_laa) else 2)
            payload = {
                "root": root_id,
                "branch": branch_id,
                "leaf": leaf_id,
                "WholePage": None,
                "LoginRequestedBy": _lrb,           # zastępuje "login"; bez JWT
                "LoginActingAs": _laa,              # WYMAGANE (fix 406)
                "MemberTypeActingAs": _mta,         # WYMAGANE (fix 406): 1=user, 2=grupa
                "PagingInfo": {
                    "CurrentPage": page,
                },
            }

            try:
                resp = requests.post(
                    f"{self.base}/api/wpisy/GetPostTree",
                    headers=self._headers(),
                    json=payload,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("status") != "SUCCESS" or not data.get("tree"):
                    if page == 1:
                        return {"success": False, "error": data.get("message", "Brak danych")}
                    break

                tree = data["tree"]
                if page == 1:
                    thread_title = tree.get("Title", "")

                post_list = tree.get("PostList", [])
                if not post_list:
                    break

                for p in post_list:
                    all_posts.append({
                        "Id": p.get("Id"),
                        "Do_Odpid": p.get("Do_Odpid"),
                        "Text": p.get("Text", ""),
                        "UserAddName": p.get("UserAddName", ""),
                        "UserAddType": p.get("UserAddType"),       # 1=user, 2=grupa
                        "UserOdInGroup": p.get("UserOdInGroup"),   # faktyczny autor gdy nadawca=grupa
                        "UserToName": p.get("UserToName", ""),
                        "DateAdd": p.get("DateAdd", ""),
                        "Level": p.get("Level", 0),
                        "Hierarchy": p.get("Hierarchy", ""),
                    })

                paging = tree.get("PagingInfo", {})
                total_pages = paging.get("TotalPages", 1)
                if page >= total_pages:
                    break

            except Exception as e:
                if page == 1:
                    return {"success": False, "error": str(e)}
                break

        return {
            "success": True,
            "posts": all_posts,
            "thread_title": thread_title,
            "count": len(all_posts),
        }

    def _forum_read_subtree(self, branch_id=None, leaf_id=None, root_id=None,
                            from_post_id=None, nrzam=None):
        """Czyta wątek forum i wyciąga ORAZ FILTRUJE powiązane odpowiedzi.

        Bezpieczniki ZAWSZE odcinają śmietnik z innych zamówień, nawet w trybie
        awaryjnego doczytywania (fallback leaf). Jeśli wskazany post nie zawiera
        numeru zamówienia → ignoruj jego (fałszywe) ID.
        """
        result = self._forum_read(branch_id=branch_id, root_id=root_id, leaf_id=leaf_id)
        if not result.get("success"):
            return result

        start_hierarchy = None
        root_text = ""
        for p in result["posts"]:
            if p["Id"] == from_post_id:
                start_hierarchy = p["Hierarchy"]
                root_text = p.get("Text", "")
                break

        # BEZPIECZNIK: czy wczytany post faktycznie dotyczy naszego zamówienia
        if start_hierarchy and nrzam:
            if str(nrzam) not in root_text:
                log.warning("Post %s dotyczy innego numeru niż %s! Ignoruję to fałszywe ID.",
                            from_post_id, nrzam)
                start_hierarchy = None

        if not start_hierarchy and not nrzam:
            return {"success": False, "error": f"Nie znaleziono wpisu {from_post_id} lub fałszywe ID"}

        filtered = []
        seen_ids = set()
        for p in result["posts"]:
            pid = p["Id"]

            # 1. Pasuje do drzewka odpowiedzi (i przeszło bezpiecznik)
            if start_hierarchy and p["Hierarchy"].startswith(start_hierarchy):
                if pid not in seen_ids:
                    filtered.append(p)
                    seen_ids.add(pid)
                continue

            # 2. Pasuje po numerze zamówienia (nawet z błędem w hierarchii / trybem awaryjnym)
            if nrzam and str(nrzam) in p.get("Text", ""):
                if pid not in seen_ids:
                    filtered.append(p)
                    seen_ids.add(pid)

        if not filtered:
            return {"success": False, "error": f"Brak powiązanych postów dla zamówienia {nrzam}"}

        filtered = sorted(filtered, key=lambda x: x.get("DateAdd", ""))

        return {
            "success": True,
            "posts": filtered,
            "thread_title": result["thread_title"],
            "count": len(filtered),
        }

    # ==========================================
    # PAMIĘĆ FORUMOWA (przez self.memory)
    # ==========================================

    def _save_memory(self, numer, cel, forum_id, co="", is_new_subthread=USE_NEW_SUBTHREADS):
        """Zapis mostu numer ↔ wpis forum. Pierwszy wpis dla celu wygrywa (logika w store)."""
        log.info("SAVE_MEMORY: nrzam=%s, cel=%s, forum_id=%s", numer, cel, forum_id)
        entry = {
            "id": forum_id,
            "co": (co[:100] if co else ""),
            "new_subthread": is_new_subthread,
        }
        try:
            self.memory.save(str(numer), cel, entry)
        except Exception as e:
            log.warning("SAVE_MEMORY błąd: %s", e)

    def _load_memory(self, numer):
        try:
            return self.memory.load(str(numer)) or {}
        except Exception as e:
            log.warning("LOAD_MEMORY błąd: %s", e)
            return {}

    # ==========================================
    # KLASYFIKACJA DIAMENTU (zamiast Firestore → diament_logger)
    # ==========================================

    def _log_diamond(self, numer_zamowienia, operator, source_type,
                     forum_post_id=None, kurier=None, kategoria_towaru=None,
                     cel=None, grupa=None, pz=None, bump=None,
                     tresc=None, typ_zlecenia=None, is_new_subthread=True):
        """Klasyfikacja "diamentu" z TREŚCI posta. Zamiast zapisu Firestore woła
        self.diament_logger(entry) (jeśli ustawiony).

        Reguły zachowane 1:1: musi zawierać "Zamówienie: NNN", bez stop-słów
        (bump/ponaglenie/eskalacja/dopyt/podbicie); typy zmiana/cofniete/ponowienie
        = NIE diament; etykieta_ups_punkt/kurier = diament; "NOWE ID = DIAMENT";
        kolektor → UPS fallback + flaga anomalii. Błędy połykane.
        """
        # Klasyfikacja typu z treści ZANIM walidacja diamentu —
        # typy zmiana/cofniete/ponowienie (NIE-diamenty) ZAPISUJĄ się pod {numer}__{typ},
        # ale NIE liczą się jako diamenty.
        _typ_z_tresci = _classify_typ_zlecenia(tresc) if tresc else None
        _czy_diament = True
        if _typ_z_tresci in NIE_DIAMENT_TYPY:
            typ_zlecenia = _typ_z_tresci
            _czy_diament = False
            # NIE-diament też musi mieć "Zamówienie: NNN"; stop-lista odrzuca całkowicie.
            if not tresc or not _RE_DIAMOND_ZAMOWIENIE.search(tresc) or DIAMOND_STOP_WORDS.search(tresc):
                log.info("DIAMOND SKIP (nie-diament bez 'Zamówienie:' lub stop-słowo): nrzam=%s",
                         numer_zamowienia)
                return
        else:
            # Walidacja treści — post musi zawierać "Zamówienie: NNN" i NIE może mieć stop-słów.
            if tresc is not None and not _validate_diamond_from_tresc(tresc):
                log.info("DIAMOND SKIP (walidacja treści): nrzam=%s — brak 'Zamówienie:' lub stop-słowo",
                         numer_zamowienia)
                return

        # Ekstrakcja z treści posta (regexy tolerują [:=]) — pierwszeństwo nad meta z apek
        if tresc:
            _m_towar = _RE_DIAMOND_TOWAR.search(tresc)
            if _m_towar:
                kategoria_towaru = "Kolektor" if _m_towar.group(1).upper() == "KOLEKTOR" else "Skrzynia biegów"
            _m_kurier = _RE_DIAMOND_KURIER.search(tresc)
            if _m_kurier:
                kurier = _m_kurier.group(1).upper().replace(" ", "").replace("_", "")
                # samo "Schenker" normalizowane do DBSCHENKER
                if kurier == "SCHENKER":
                    kurier = "DBSCHENKER"
            if not numer_zamowienia:
                _m_nr = _RE_DIAMOND_ZAMOWIENIE.search(tresc)
                if _m_nr:
                    numer_zamowienia = _m_nr.group(1)
            if not typ_zlecenia:
                typ_zlecenia = _classify_typ_zlecenia(tresc)

        # REGUŁA "NOWE ID = DIAMENT": zlecenie kuriera liczy się RAZ — przy pierwotnym
        # wpisie tworzącym nowy podwątek. Wpis pod ISTNIEJĄCYM podwątkiem = NIE nowy diament.
        if not is_new_subthread and _czy_diament:
            _czy_diament = False
            if typ_zlecenia not in ("zmiana", "cofniete", "ponowienie"):
                typ_zlecenia = "zmiana"
            log.info("DIAMOND→ZMIANA (odpowiedź pod istniejącym podwątkiem, nie nowe ID): nrzam=%s, typ=%s",
                     numer_zamowienia, typ_zlecenia)

        # Zasada EA "kolektor → UPS, zawsze": kolektor bez kuriera → fallback UPS;
        # kolektor + inny kurier → zapis literalny + flaga anomalii.
        _anomalia_kolektor = False
        if kategoria_towaru == "Kolektor":
            if not kurier:
                kurier = "UPS"
            elif kurier != "UPS":
                _anomalia_kolektor = True

        if not numer_zamowienia:
            return

        try:
            entry = {
                "numer_zamowienia": str(numer_zamowienia),
                "operator": operator or "?",
                "source_type": source_type or "operator",
                "czy_diament": _czy_diament,
            }
            if _anomalia_kolektor:
                entry["anomalia_kolektor_kurier"] = True
            if forum_post_id:
                entry["forum_post_id"] = forum_post_id
            if kurier:
                entry["kurier"] = kurier
            if kategoria_towaru:
                entry["kategoria_towaru"] = kategoria_towaru
            if cel:
                entry["cel"] = cel
            if grupa:
                entry["grupa"] = grupa
            if pz:
                entry["pz"] = pz
            if bump is not None:
                entry["bump"] = bump
            if typ_zlecenia:
                entry["typ_zlecenia"] = typ_zlecenia

            if self.diament_logger:
                self.diament_logger(entry)
            log.info("DIAMOND LOGGED: nrzam=%s | diament=%s | op=%s | src=%s | cel=%s | typ=%s | kat=%s | kurier=%s",
                     numer_zamowienia, _czy_diament, operator, source_type, cel,
                     typ_zlecenia, kategoria_towaru, kurier)
        except Exception as e:
            # Połykamy błędy — log diamentu NIE może wywrócić wysyłki na forum
            log.warning("DIAMOND LOG ERROR (połknięty): %s", e)

    # ==========================================
    # API PUBLICZNE
    # ==========================================

    def write_to_thread(self, cel, tresc, *, user_od=None, ai_user=None,
                        source_type="operator", numer=None):
        """Wpis na znany wątek (FORUM_THREADS[cel]).

        Tytuł = numer zamówienia wyciągnięty z treści ("Zamówienie: NNNNNN").
        IDEMPOTENCJA: dla cel=AUTOS_KURIERZY (nowy wpis) — jeśli w self.memory(numer)
        istnieje już wpis dla tego celu, NIE wysyła ponownie (chroni przed podwójnym
        zamówieniem kuriera przy ponownym przebiegu autopilota).
        """
        info = _get_thread_raw(cel)
        if not info:
            log.warning("WRITE_TO_THREAD: cel=%s → NIEZNANY CEL", cel)
            return {"success": False, "error": f"Nieznany cel: {cel}"}

        # Pamięć forum dla tego numeru (jeśli numer znany)
        mem = self._load_memory(numer) if numer else {}
        _cel_existed_before = bool(mem) and (cel in mem)

        # IDEMPOTENCJA zlecenia kuriera: nowy podwątek na AUTOS_KURIERZY, a w pamięci
        # już jest wpis dla tego celu → pominięcie (nie zamawiamy kuriera dwa razy).
        if cel == "AUTOS_KURIERZY" and _cel_existed_before:
            log.warning("IDEMPOTENCJA: cel=AUTOS_KURIERZY dla nrzam=%s już ma wpis (id=%s) — POMIJAM ponowne zlecenie kuriera.",
                        numer, mem.get(cel, {}).get("id"))
            return {
                "success": True,
                "skipped_idempotent": True,
                "new_post_id": mem.get(cel, {}).get("id"),
                "FORUM_ID": mem.get(cel, {}).get("id"),
                "cel": cel,
                "message": "Pominięto — wpis dla tego zlecenia kuriera już istnieje (idempotencja).",
                "link": None,
            }

        # TYTUŁ = NUMER ZAMÓWIENIA z treści (zawsze). AI w treści zawsze pisze
        # "Zamówienie: 374593" — to wyciągamy jako tytuł.
        _nrzam_match = re.search(r'Zamówienie[:\s]+(\d{5,7})', tresc)
        tytul = _nrzam_match.group(1) if _nrzam_match else None

        # NOWE ID = DIAMENT? Nowy podwątek = cel jeszcze nie ma wpisu w pamięci dla nrzam.
        _is_new_subthread = not _cel_existed_before

        log.info("WRITE_TO_THREAD: cel=%s, tytul=%r, USE_NEW=%s, user_od=%s, ai_user=%s, new_subthread=%s",
                 cel, tytul, USE_NEW_SUBTHREADS, user_od, ai_user, _is_new_subthread)

        # Decyzja do_odp_id: kontynuacja z pamięci, inaczej NOWY PODWĄTEK.
        if mem and cel in mem:
            target_do_odp = mem[cel].get("id")
            log.info("  DECYZJA: kontynuacja z pamięci, target=%s", target_do_odp)
        else:
            target_do_odp = None
            log.info("  DECYZJA: NOWY PODWĄTEK (do_odp_id=None)")

        target_user = info.get("grupa", "EA")
        target_type = info.get("grupa_type", 1)

        # AWIZACJA KURIERA (faza 1: UPS skrzynia) — sygnał do apki Eweliny zamiast/obok forum.
        # shadow: awizacja + wpis na forum z nagłówkiem ostrzegawczym; live: awizacja, forum POMINIĘTY.
        _mode = config.KURIER_AWIZACJE_MODE
        zlec = None
        if cel == "AUTOS_KURIERZY" and _mode in ("shadow", "live") and self.awizacja_emitter:
            from . import awizacje
            zlec = awizacje.parsuj_zlecenie(tresc, numer=numer, kto=ai_user, source=source_type)
            if zlec:
                zlec["test_mode"] = (_mode == "shadow")
                if _mode == "shadow":
                    tresc = awizacje.KURIER_TEST_HEADER + "<br><br>" + tresc

        tresc_with_disclaimer = tresc + CHATOSZTUREK_DISCLAIMER

        if zlec and _mode == "live":
            # Tryb live: forum pominięty — leci sam sygnał (awizacja).
            log.info("AWIZACJA live: forum POMINIĘTY dla nrzam=%s (sam sygnał).", numer)
            result = {"success": True, "new_post_id": None, "awizacja_only": True,
                      "message": "Awizacja wysłana — wpis na forum pominięty (tryb live)."}
        else:
            result = self._forum_write(
                post_id=info["post_id"],
                do_odp_id=target_do_odp,
                user_do=target_user,
                tresc=tresc_with_disclaimer,
                user_do_type=target_type,
                user_od=user_od,
                ai_user=ai_user,
                tytul=tytul,
            )
        result["cel"] = cel
        result["tresc_skrot"] = tresc[:100] if tresc else ""

        # Emisja awizacji (niezależna od forum) — po ustaleniu forum_post_id.
        if zlec and self.awizacja_emitter and result.get("success"):
            try:
                zlec["sprawa"]["forum_post_id"] = result.get("new_post_id") or 0
                _aw = self.awizacja_emitter(zlec)
                result["awizacja"] = {
                    "emitted": not _aw.get("skipped_idempotent", False),
                    "skipped_idempotent": bool(_aw.get("skipped_idempotent")),
                    "id": _aw.get("id"), "nrZam": zlec["zlecenie"]["nrZam"],
                    "test_mode": zlec.get("test_mode"),
                }
                log.info("AWIZACJA wyemitowana: nrZam=%s id=%s skip=%s mode=%s",
                         zlec["zlecenie"]["nrZam"], _aw.get("id"),
                         _aw.get("skipped_idempotent"), _mode)
            except Exception as e:  # noqa: BLE001 — awizacja nie może wywrócić wysyłki
                log.warning("AWIZACJA EMIT ERROR (połknięty): %s", e)

        if result.get("success"):
            result["FORUM_ID"] = result.get("new_post_id")

            # Zapis do pamięci (pierwszy wpis dla celu wygrywa).
            if numer:
                self._save_memory(numer, cel, result.get("new_post_id"),
                                  co=cel, is_new_subthread=_is_new_subthread)

            # DIAMENT: każdy udany post na AUTOS_KURIERZY analizowany z treści.
            if cel == "AUTOS_KURIERZY":
                self._log_diamond(
                    numer_zamowienia=numer or (tytul if tytul else None),
                    operator=ai_user,
                    source_type=source_type,
                    forum_post_id=result.get("FORUM_ID"),
                    cel=cel,
                    grupa=info.get("grupa"),
                    tresc=tresc,
                    is_new_subthread=_is_new_subthread,
                )

        return result

    def read_subtree(self, cel, numer):
        """Czyta i filtruje podwątek po numerze zamówienia. Korzysta z pamięci (forum_id),
        z fallbackiem do korzenia wątku."""
        mem = self._load_memory(numer)
        thread_info = (_get_thread_raw(cel) or {})
        root_id = thread_info.get("post_id")

        forum_id = (mem.get(cel) or {}).get("id") if mem else None

        if forum_id:
            result = self._forum_read_subtree(branch_id=forum_id, from_post_id=forum_id, nrzam=numer)
            if not result.get("success"):
                result = self._forum_read_subtree(
                    leaf_id=forum_id, root_id=root_id, from_post_id=forum_id, nrzam=numer)
            return result

        # Brak ID w pamięci — czytamy korzeń wątku i filtrujemy po numerze.
        if root_id:
            return self._forum_read_subtree(root_id=root_id, nrzam=numer)
        return {"success": False, "error": f"Brak forum_id w pamięci i korzenia dla celu {cel}"}

    def execute_actions(self, ai_text, *, user_od=None, ai_user=None, source_type="operator"):
        """Parsuje markery [FORUM_WRITE|...] / [FORUM_READ|...] z odpowiedzi AI,
        wykonuje je i PODMIENIA marker w tekście na komunikat.

        Zwraca {"text": podmieniony_tekst, "reads": [...], "writes": [...]}.
        """
        markers = parse_forum_markers(ai_text)

        if not markers:
            return {"text": ai_text, "reads": [], "writes": []}

        modified = ai_text
        forum_reads = []
        forum_writes = []

        for marker in markers:
            if marker["type"] == "write":
                cel = marker.get("cel", "")
                tresc = marker.get("tresc", "")
                user_do = marker.get("user_do")

                # numer zamówienia z treści — klucz pamięci/idempotencji
                _nr_match = re.search(r'Zamówienie[:\s]+(\d{5,7})', tresc or "")
                _numer = _nr_match.group(1) if _nr_match else None

                result = self.write_to_thread(
                    cel=cel,
                    tresc=tresc,
                    user_od=user_od,
                    ai_user=ai_user,
                    source_type=source_type,
                    numer=_numer,
                )
                result["cel"] = cel
                result["tresc_skrot"] = tresc[:100] if tresc else ""
                forum_writes.append(result)

                if result.get("success"):
                    if result.get("skipped_idempotent"):
                        replacement = (
                            f"♻️ Pominąłem ponowną wysyłkę na forum ({cel}) — "
                            f"zlecenie dla tego zamówienia już istnieje. "
                            f"FORUM_ID={result.get('FORUM_ID', '?')}"
                        )
                    else:
                        replacement = (
                            f"✅ Wysłałem na forum ({cel}). "
                            f"Link: {result.get('link', '?')} "
                            f"FORUM_ID={result.get('FORUM_ID', '?')}"
                        )
                else:
                    # FALLBACK MANUALNY — API zwróciło błąd, operator musi wysłać ręcznie
                    _err = result.get('error', '?')
                    _user_do_final = user_do if user_do else "?"
                    _full_tresc = tresc if tresc else "(brak treści)"
                    replacement = (
                        f"❌ **Nie udało się automatycznie wysłać wpisu na forum.**\n\n"
                        f"**Cel:** `{cel}` | **Do:** `{_user_do_final}` | **Błąd:** `{_err}`\n\n"
                        f"**Skopiuj poniższą treść i wklej jako nowy wpis na forum (wątek {cel}, odbiorca {_user_do_final}):**\n\n"
                        f"```\n{_full_tresc}\n```\n\n"
                        f"**Po wysłaniu** wpisz w chatcie komendę z ID nowego wpisu:\n\n"
                        f"`SESJA WYNIK [NR_ZAM] – FORUM_ID: XXXXX` (gdzie XXXXX to numer ID wpisu z forum)"
                    )
                    result["fallback_needed"] = True
                    result["fallback_cel"] = cel
                    result["fallback_user_do"] = _user_do_final

                modified = modified.replace(marker["raw"], replacement)

            elif marker["type"] == "read":
                forum_id = marker.get("forum_id")
                cel = marker.get("cel", "")

                # numer zamówienia — z markera (forum_id) nie znamy, filtr po pamięci celu
                result = None
                if forum_id:
                    # Czytaj wpis + odpowiedzi; bez znanego nrzam filtr po hierarchii
                    result = self._forum_read_subtree(branch_id=forum_id, from_post_id=forum_id)
                    if not result.get("success"):
                        thread_info = (_get_thread_raw(cel) or {})
                        result = self._forum_read_subtree(
                            leaf_id=forum_id, root_id=thread_info.get("post_id"),
                            from_post_id=forum_id)
                elif cel:
                    # Bez forum_id — pusty kontekst (numer zamówienia nieznany w markerze).
                    result = {"success": True, "posts": [], "thread_title": "", "count": 0}
                else:
                    result = {"success": False, "error": "Brak forum_id i cel"}

                if result.get("success"):
                    if result["count"] == 0:
                        cel_name = cel or "forum"
                        forum_reads.append(
                            f"[FORUM_CONTEXT: {cel_name}] Brak wcześniejszych wpisów chatoszturka "
                            f"dla tego zamówienia. Jeśli trzeba pisać na forum — użyj FORUM_WRITE.")
                        replacement = f"📖 Forum ({cel_name}): brak wcześniejszych wpisów dla tego zamówienia."
                    else:
                        context_parts = [f"[FORUM_CONTEXT] ({result['count']} postów)"]
                        for p in result["posts"]:
                            date_str = p['DateAdd'][:10] if p.get('DateAdd') else '?'
                            context_parts.append(
                                f"[{date_str}] {p['UserAddName']} → {p['UserToName']}: "
                                f"{_strip_html(p['Text'][:500])}"
                            )
                        forum_reads.append("\n".join(context_parts))
                        replacement = f"📖 Pobrano {result['count']} postów z forum (kontekst wstrzyknięty)."
                else:
                    forum_reads.append(f"[FORUM_CONTEXT] Błąd: {result.get('error', '?')}")
                    replacement = f"❌ Błąd czytania z forum: {result.get('error', '?')}"

                modified = modified.replace(marker["raw"], replacement)

        return {"text": modified, "reads": forum_reads, "writes": forum_writes}

    def auto_load_context(self, numer):
        """Buduje [FORUM_CONTEXT] (pamięć → skan, ostatnie 10 postów na cel, wykrycie
        odpowiedzi człowieka = autor != chatoszturek). Bezpiecznik pustego odczytu.
        Zwraca pusty string gdy brak kontekstu.
        """
        log.info("AUTO_LOAD: start, nrzam=%s", numer)

        try:
            memory = self._load_memory(numer)

            if not memory:
                memory = self._scan_forum_for_case(str(numer))

            if not memory:
                log.info("AUTO_LOAD: scan też pusty → zwracam pusty kontekst")
                return ""

            context_parts = []
            for cel, info in memory.items():
                forum_id = info.get("id")
                if not forum_id:
                    continue

                is_new_subthread = info.get("new_subthread", USE_NEW_SUBTHREADS)
                log.info("AUTO_LOAD: czytam %s, forum_id=%s, new_sub=%s", cel, forum_id, is_new_subthread)

                thread_info = (_get_thread_raw(cel) or {})
                root_id = thread_info.get("post_id")

                # ZAWSZE filtruj po numerze zamówienia (nie ładuj całego wątku)
                if is_new_subthread:
                    result = self._forum_read_subtree(branch_id=forum_id, from_post_id=forum_id, nrzam=numer)
                    if not result.get("success"):
                        result = self._forum_read_subtree(
                            leaf_id=forum_id, root_id=root_id, from_post_id=forum_id, nrzam=numer)
                else:
                    if thread_info and thread_info.get("korzen_id") and thread_info.get("korzen_id") != "DIRECT":
                        log.info("  → subtree: branch=%s, from=%s", thread_info["korzen_id"], forum_id)
                        result = self._forum_read_subtree(
                            branch_id=thread_info["korzen_id"], from_post_id=forum_id, nrzam=numer)
                    else:
                        log.info("  → subtree (brak korzenia/DIRECT): branch=%s, from=%s", forum_id, forum_id)
                        result = self._forum_read_subtree(branch_id=forum_id, from_post_id=forum_id, nrzam=numer)
                        if not result.get("success"):
                            log.info("  → fallback leaf z filtrem: forum_id=%s", forum_id)
                            result = self._forum_read_subtree(
                                leaf_id=forum_id, root_id=root_id, from_post_id=forum_id, nrzam=numer)

                log.info("  → wynik odczytu: success=%s, postow=%s",
                         result.get("success"), result.get("count", 0))
                co = info.get("co", cel)

                if result.get("success") and result.get("posts"):
                    posts = result["posts"][-10:]

                    human_replies = [p for p in posts if p.get("UserAddName") != FORUM_USER]

                    if human_replies:
                        context_parts.append(
                            f"[FORUM_CONTEXT: {cel}] ({co}, {result['count']} postów. "
                            f"Ostatnia odpowiedź od: {human_replies[-1].get('UserAddName')})")
                    else:
                        context_parts.append(f"[FORUM_CONTEXT: {cel}] ({co}, brak nowych odpowiedzi)")

                    for p in posts:
                        date_str = p['DateAdd'][:10] if p.get('DateAdd') else '?'
                        context_parts.append(
                            f"  [{date_str}] {p['UserAddName']} → {p['UserToName']}: "
                            f"{_strip_html(p['Text'][:400])}"
                        )
                else:
                    err_msg = result.get("error", "API zwróciło pustą listę")
                    log.info("  → UWAGA: błąd lub brak postów (%s). Dodaję bezpiecznik.", err_msg)
                    context_parts.append(
                        f"[FORUM_CONTEXT: {cel}] ({co}, w pamięci istnieje wpis ID={forum_id}, "
                        f"ale odczyt nie znalazł odpowiedzi. Zakładam: brak nowych odpowiedzi.)")

            if context_parts:
                return "\n".join(context_parts)
            return ""

        except Exception as e:
            log.warning("AUTO_LOAD BŁĄD KRYTYCZNY: %s", e, exc_info=True)
            return ""

    def check_answer(self, numer, cel=None):
        """Czy pod wątkiem (delegacji) jest ODPOWIEDŹ CZŁOWIEKA (nie bota chatoszturek)?

        Używane przez nocny routing autopilota: jest odpowiedź telefonisty → standard;
        brak → woreczek. cel=None → sprawdza wszystkie cele w pamięci; inaczej tylko podany.
        Zwraca bool.
        """
        try:
            memory = self._load_memory(numer)
            if not memory:
                return False
            for _cel, info in memory.items():
                if cel and _cel != cel:
                    continue
                forum_id = info.get("id")
                if not forum_id:
                    continue
                result = self._forum_read_subtree(branch_id=forum_id, from_post_id=forum_id, nrzam=numer)
                if not result.get("success"):
                    # Fallback: czytaj korzeń wątku i filtruj po hierarchii+nrzam.
                    _root_id = (_get_thread_raw(_cel) or {}).get("post_id")
                    result = self._forum_read_subtree(
                        leaf_id=forum_id, root_id=_root_id, from_post_id=forum_id, nrzam=numer)
                if not result.get("success") or not result.get("posts"):
                    continue
                human = [p for p in result["posts"] if p.get("UserAddName") != FORUM_USER]
                if human:
                    return True
            return False
        except Exception as e:
            log.warning("CHECK_ANSWER BŁĄD: %s", e)
            return False

    # ==========================================
    # SKAN WĄTKÓW PO NUMERZE (gdy pamięć pusta)
    # ==========================================

    def _scan_forum_for_case(self, numer_zamowienia):
        found = {}
        nrzam = str(numer_zamowienia)
        log.info("SCAN: szukam %s w wątkach forum", nrzam)

        scanned_roots = set()
        for cel, info in FORUM_THREADS.items():
            post_id = info.get("post_id")
            if post_id in scanned_roots:
                continue
            scanned_roots.add(post_id)

            try:
                result = self._forum_read(root_id=post_id, max_pages=3)
                if not result.get("success") or not result.get("posts"):
                    continue

                for post in result["posts"]:
                    if post.get("UserAddName") != FORUM_USER:
                        continue
                    text = post.get("Text", "")
                    if nrzam not in text:
                        continue

                    post_forum_id = post.get("Id")
                    if not post_forum_id:
                        continue

                    text_lower = text.lower()
                    matched_cel = None
                    for c, cinfo in FORUM_THREADS.items():
                        if cinfo.get("post_id") != post_id:
                            continue
                        if "AUTOS_KURIERZY" == c and ("kurier" in text_lower or "zlecenie kuri" in text_lower or "etykiet" in text_lower):
                            matched_cel = c
                            break
                        elif "CZATOSZTUR_" in c and ("delegacja" in text_lower or "telefon" in text_lower):
                            matched_cel = c
                            break
                        elif "SPEDYCJA" in c and ("spedycj" in text_lower or "reklamacj" in text_lower):
                            matched_cel = c
                            break
                        elif "NIEPOZAMYKANE" in c and ("austausch" in text_lower or "zielonk" in text_lower):
                            matched_cel = c
                            break

                    if not matched_cel:
                        for c, cinfo in FORUM_THREADS.items():
                            if cinfo.get("post_id") == post_id:
                                matched_cel = c
                                break

                    if matched_cel and matched_cel not in found:
                        is_root = post.get("Do_Odpid") == 0 or post.get("Level") == 0
                        found[matched_cel] = {
                            "id": post_forum_id,
                            "new_subthread": is_root,
                            "co": f"scan: {matched_cel}",
                        }
                        self._save_memory(nrzam, matched_cel, post_forum_id,
                                          co=f"scan: {matched_cel}", is_new_subthread=is_root)
            except Exception as e:
                log.warning("SCAN ERROR: %s", e)
                continue

        return found if found else None
