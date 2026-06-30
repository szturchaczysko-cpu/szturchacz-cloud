"""
Warstwa „reguły → kod" — TWARDE, deterministyczne reguły biznesowe wyciągnięte z
prompt-kartoteki Szturchacza (`zrodlo/szturchacz/szturchacz_vnext_v1_9.txt`).

Dlaczego osobny moduł:
    To są reguły o konsekwencjach PRAWNYCH i FINANSOWYCH (kwoty windykacyjne, terminy
    K1-K5, routing wpisów na forum, link do punktu UPS). Kartoteka wprost mówi:
    „Decyzję »czy windykować/kasować« podejmuje AI; KWOTĘ liczy kod." (CLAUDE.md).
    LLM regularnie myli się w arytmetyce dat/progów i w literałach (spacja vs podkreślnik,
    ENG vs EN) — patrz analiza_prompt. Stąd: liczenie i literały po stronie kodu.

Zasady techniczne:
    - Tylko stdlib (datetime, re, typing). ZERO sieci, ZERO Streamlita, ZERO google.
    - Parametry biznesowe (progi, terminy, pivoty dat, tablice) to STAŁE MODUŁU na górze
      pliku, żeby panel koordynatora mógł je nadpisywać bez ruszania logiki.
    - Funkcje czyste — bez efektów ubocznych, bez I/O.

Odwołania w docstringach mają format „§sekcja, linie ~N-M" do pliku promptu powyżej.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Dict, List, Optional

# =============================================================================
# PARAMETRY BIZNESOWE (STAŁE) — edytowalne w panelu koordynatora
# =============================================================================

# --- Kwota za bezumowne korzystanie (Austausch) ------------------------------
# §6.9, korekta wzoru w 16.26 (linie ~2878-2898). Progi wg dni_od_dostawy:
#   1-21 dni  -> 0      (jeszcze w 21-dniowym terminie umownym)
#   22-28 dni -> próg 1
#   29-35 dni -> próg 2
#   36+  dni  -> próg 3 = CAP (po dojściu do capu kwota NIE rośnie)
PROG_DNI_START = 22          # poniżej tej granicy kwota = 0
TYDZIEN_DNI = 7              # szerokość progu w dniach
PROGI_EUR = (300, 600, 900)  # próg 1 / 2 / 3 ; ostatni = CAP
PROGI_PLN = (900, 1500, 2400)  # próg 1 / 2 / 3 ; ostatni = CAP
CAP_EUR = PROGI_EUR[-1]
CAP_PLN = PROGI_PLN[-1]
TERMIN_UMOWNY_AUSTAUSCH_DNI = 21  # §6.9: 21 dni od dostawy = termin zwrotu

# --- Okno kasacji długu ------------------------------------------------------
# §6.9 OKNO KASACJI (linie ~1111-1137): każda wiadomość resetuje okno na +10 dni
# roboczych; zwrot starej części w oknie kasuje całą kwotę.
OKNO_KASACJI_DNI_ROBOCZE = 10

# --- Etapy prawne K1-K5 ------------------------------------------------------
# §6.9 K4/K5 (linie ~1446-1448, 1515). K4_deadline_30 jest STAŁY i NIEresetowalny
# przez neutralne odpowiedzi klienta (linie ~1450-1459). K5 = 7 dni ciszy.
TERMIN_K4_DNI = 30          # dni kalendarzowe od wysłania PDF (nieresetowalny)
TERMIN_K5_DNI = 7           # dni kalendarzowe od K5 do toksycznych aktywów

# --- Wybór kuriera -----------------------------------------------------------
# §10.1 / §11.4.0 (linie ~1877-1881). Pivot dat Reguły Indeksowej.
PIVOT_REGULA_INDEKSOWA = date(2025, 12, 1)  # dostawy ≤ pivot → Reguła Indeksowa
# §4.9 (pakowanie FedEx zwrotny): pivot liczby elementów / wymogu zdjęcia. NIE dotyczy
# wyboru kuriera (to robi PIVOT_REGULA_INDEKSOWA) — osobna reguła pakowania (§10.6, do wdrożenia).
PIVOT_FEDEX_ZWROTNY = date(2025, 11, 24)
PROG_SKRZYN_DBSCHENKER = 2   # >= tylu skrzyń → DB Schenker (tylko skrzynie)
KOLEKTOR_KURIER = "UPS"      # KOLEKTOR → zawsze UPS

# Reguła Indeksowa (§10.1, linie ~1877-1881). KOMPLETNA wg promptu v1.9.
# A) FedEx gdy prefiks4 (pierwsze 4 znaki indeksu) jest w tej tablicy:
FEDEX_PREFIXY = (
    "126T", "131M", "132M", "136T", "1411", "1421", "1431", "1433", "14TD",
    "1562", "156T", "1611", "1621", "1633", "165M", "165T", "1662", "166T",
    "1711", "1721", "1731", "1733", "1811", "1821", "1911", "1921", "1922",
    "1951", "1952", "1953", "195J", "1961", "1962", "196T", "19TD", "2011",
    "205M", "205T", "2061", "2062", "206C", "206T", "207D", "20TD", "2211",
    "2221", "2254", "225U", "2262", "226T", "2362", "236M", "2551", "2552",
    "2553", "2554", "2561", "2562", "2564", "256T", "25DH", "2854", "3062",
    "306M",
)
# B) LUB FedEx gdy CAŁY indeks (dokładnie) jest w tej tablicy:
FEDEX_INDEKSY_PELNE = (
    "145TDI5GRUP1", "145TDI5GRUP10", "145TDI5GRUP12", "145TDI5GRUP13",
    "145TDI5GRUP2", "145TDI5GRUP3", "145TDI5GRUP5", "145TDI5GRUP6",
    "145TDI5SSGRUP1", "145TDI5SSGRUP2", "146TSI6GRUP5", "146TSI6GRUP6",
    "146TSI6GRUP7", "146TSI6GRUP8", "146TSI6GRUP9", "146TSI6SSGRUP10",
    "146TSI6SSGRUP16", "146TSI6SSGRUP8", "195TDI5GRUP1", "195TDI5GRUP11",
    "195TDI5GRUP12", "195TDI5GRUP13", "195TDI5GRUP14", "195TDI5GRUP16",
    "195TDI5GRUP2", "195TDI5GRUP21", "195TDI5GRUP3", "195TDI5GRUP4",
    "195TDI5GRUP6", "195TDI5GRUP7", "195TDI5GRUP8", "195TDI5GRUP9",
)
# Prefiksy indeksów oznaczające KOLEKTOR (§9.4, linia ~1872: ORG/REG/BMW → kolektor).
KOLEKTOR_PREFIXY = ("ORG", "REG", "BMW")

# --- Przelicznik skrzynia → paleta (DB Schenker) -----------------------------
# §11.4 (linie ~2301-2321). DB Schenker tylko dla skrzyń, nigdy kolektory.
SKRZYN_NA_PALETE = 3         # max skrzyń na jednej palecie DBS

# --- Link UPS Access Point ---------------------------------------------------
# §11.4.1 (linie ~2178-2224). Tylko KOLEKTOR + KURIER_OPCJA=ETYKIETA_PUNKT.
UPS_BASE_URL = "https://www.ups.com/{seg}/business-solutions/pickup-dropoff-options"
# Tabela WYJĄTKÓW (kraj ≠ język), zaszyta sztywno (linie ~2188-2210). KOMPLETNA wg v1.9.
UPS_AP_WYJATKI: Dict[str, str] = {
    "AT": "/at/de/",  # Austria → niemiecki
    "BE": "/be/en/",  # Belgia → angielski
    "CH": "/ch/de/",  # Szwajcaria → niemiecki
    "CZ": "/cz/cs/",  # Czechy → czeski
    "GB": "/gb/en/",
    "IE": "/ie/en/",
    "DK": "/dk/en/",
    "SE": "/se/en/",
    "FI": "/fi/en/",
    "NO": "/no/en/",
    "RO": "/ro/en/",
    "BG": "/bg/en/",
    "HR": "/hr/en/",
    "SI": "/si/en/",
    "LU": "/lu/en/",
    "GR": "/gr/en/",
    "EE": "/ee/en/",
    "LV": "/lv/en/",
    "LT": "/lt/en/",
}

# --- Routing forum -----------------------------------------------------------
# §0.1.1.3 (linie ~426-475) i §12 (linie ~2502-2531). LITERAŁY co do znaku.
# PUŁAPKI: "NIEPOZAMYKANE AUSTAUSCHE" ze SPACJĄ (nie podkreślnik);
#          "Telefonisci_ENG" dla EN (nie _EN); ukośniki w "_UK/PL".
ROUTING_TEMATY: Dict[str, Dict[str, str]] = {
    # token/temat -> {cel, user_do}
    "zlecenie_kuriera": {"cel": "AUTOS_KURIERZY", "user_do": "TEAM_ATOMOWKI"},
    "etykieta": {"cel": "AUTOS_KURIERZY", "user_do": "TEAM_ATOMOWKI"},
    "atom": {"cel": "AUTOS_KURIERZY", "user_do": "TEAM_ATOMOWKI"},
    "problem_po_zleceniu": {"cel": "SPEDYCJA_REKLAMACJE", "user_do": "SPEDYCJA_REKLAMACJE"},
    "reklamacja_kurierska": {"cel": "SPEDYCJA_REKLAMACJE", "user_do": "SPEDYCJA_REKLAMACJE"},
    "sped": {"cel": "SPEDYCJA_REKLAMACJE", "user_do": "SPEDYCJA_REKLAMACJE"},
    "reklamacja": {"cel": "CZATOSZTUR_REKLAMACJE", "user_do": "DZIAŁ_EKSPERCKI"},
    "mozna_szturchac": {"cel": "CZATOSZTUR_REKLAMACJE", "user_do": "DZIAŁ_EKSPERCKI"},
    # PUŁAPKA: user_do ze SPACJĄ, cel z podkreślnikiem.
    "niepozamykane": {"cel": "NIEPOZAMYKANE_AUSTAUSCHE", "user_do": "NIEPOZAMYKANE AUSTAUSCHE"},
    "zielonka": {"cel": "NIEPOZAMYKANE_AUSTAUSCHE", "user_do": "NIEPOZAMYKANE AUSTAUSCHE"},
    "aus": {"cel": "NIEPOZAMYKANE_AUSTAUSCHE", "user_do": "NIEPOZAMYKANE AUSTAUSCHE"},
    # SZTURZE techniczne (błędy aplikacji) → ZAWSZE cel=szturchacz_błędy.
    "blad_techniczny": {"cel": "szturchacz_błędy", "user_do": "SZTURZE_WSPARCIE"},
}

# Mapowanie KRAJ (bucket) -> literalny segment CZATOSZTUR i Operatorzy (linie ~472-475).
# PUŁAPKA: ukośniki w "_UK/PL".
CZATOSZTUR_WG_KRAJU: Dict[str, Dict[str, str]] = {
    "DE": {"czatoszt": "CZATOSZTUR_DE", "operatorzy": "Operatorzy_DE"},
    "FR": {"czatoszt": "CZATOSZTUR_FR", "operatorzy": "Operatorzy_FR"},
    "UKPL": {"czatoszt": "CZATOSZTUR_UK/PL", "operatorzy": "Operatorzy_UK/PL"},
}

# Mapowanie języka telefonu -> literalna grupa Telefonisci (linie ~464-470).
# PUŁAPKA: "Telefonisci_ENG" dla EN.
TELEFONISCI_WG_JEZYKA: Dict[str, str] = {
    "FR": "Telefonisci_FR",
    "DE": "Telefonisci_DE",
    "PL": "Telefonisci_PL",
    "IT": "Telefonisci_IT",
    "ES": "Telefonisci_ES",
    "EN": "Telefonisci_ENG",
}

# Mapowanie nazwy kraju -> bucket KRAJ (linie ~454-458).
# Słowa-klucze (lowercase) → bucket. Kolejność: DE, FR; reszta → UKPL.
KRAJ_DO_GRUPY: Dict[str, str] = {
    # DE
    "germany": "DE", "deutschland": "DE", "niemcy": "DE",
    "austria": "DE", "osterreich": "DE", "österreich": "DE",
    "schweiz": "DE", "switzerland": "DE", "szwajcaria": "DE",
    "liechtenstein": "DE",
    "de": "DE", "at": "DE", "ch": "DE", "li": "DE",
    # FR
    "france": "FR", "francja": "FR",
    "belgium": "FR", "belgique": "FR", "belgia": "FR",
    "spain": "FR", "españa": "FR", "espana": "FR", "hiszpania": "FR",
    "italy": "FR", "italia": "FR", "włochy": "FR", "wlochy": "FR",
    "fr": "FR", "be": "FR", "es": "FR", "it": "FR",
}

# --- Zakazane frazy (guardrail prawny) ---------------------------------------
# §6.9 (linie ~1170-1178). Filtr post-generacyjny outputu AI do klienta.
# Dopasowanie BEZ względu na wielkość liter. „NATYCHMIAST" pisane KRZYKIEM (caps)
# obsługujemy osobno (patrz znajdz_zakazane).
ZAKAZANE_FRAZY = (
    "kliencie-dłużniku",
    "kliencie-dluzniku",
    "dłużniku",
    "dluzniku",
    "strata którą generujecie",
    "strata ktora generujecie",
    "sąd. windykacja. faktura.",
    "sad. windykacja. faktura.",
    "toksyczny aktyw",
    "toksyczne aktywa",
    "klient problemowy",
    "uruchamia się licznik",
    "uruchamia sie licznik",
    "system nalicza",
    "pozwiemy",
    "wezwiemy komornika",
    "komornik",
    "koniec rozmów",
    "koniec rozmow",
)

# Stop-słowa diamentu (§ klasyfikacja log_diamond): obecność = NIE diament.
DIAMENT_STOP_SLOWA = ("bump", "ponaglenie", "eskalacja", "dopyt", "podbicie")
# Typy zleceń, które NIE są diamentem (zmiana/cofnięcie/ponowienie).
DIAMENT_TYPY_NIE = ("zmiana", "cofniete", "cofnięte", "ponowienie")


# =============================================================================
# FUNKCJE — KWOTY (§6.9)
# =============================================================================

def kwota_naliczona(dni_od_dostawy: int, waluta: str = "EUR") -> int:
    """
    Kwota za bezumowne korzystanie z części wymiennej (Austausch).

    ŹRÓDŁO PRAWDY = TABELA PROGÓW (§6.9, case 16.26, linie ~2878-2898):
        dni 1-21  -> 0      (termin umowny Austausch)
        dni 22-28 -> próg 1 (300 EUR / 900 PLN)
        dni 29-35 -> próg 2 (600 EUR / 1500 PLN)
        dni 36+   -> próg 3 = CAP (900 EUR / 2400 PLN)

    Wzór realizujący tę tabelę: tygodnie = (dni - 22) // 7 + 1, cap na progu 3.
    UWAGA — ROZSTRZYGNIĘCIE NIEJEDNOZNACZNOŚCI: prompt podaje wzór DWA razy
    niespójnie. Case 16.25 (linia ~2863): `min(((dni-21)//7)*300, 900)` daje 0 na
    dzień 22 — BŁĘDNY, prompt go odrzuca. Case 16.26 (linia ~2885) podaje
    „korektę": `max(1, (dni-21)//7+1)`, ale ona TEŻ łamie granice tabeli
    (dzień 28 → 2 zamiast 1, dzień 35 → 3 zamiast 2). Ponieważ to roszczenie
    finansowe, za źródło prawdy biorę JAWNĄ TABELĘ PROGÓW z 16.26 (22-28/29-35/36+),
    a nie żadną z dwóch sprzecznych formuł. Wzór `(dni-22)//7+1` odtwarza tabelę 1:1.

    Dlaczego kod, nie AI:
        To roszczenie finansowe wobec klienta. LLM regularnie myli arytmetykę
        dat/progów (sam prompt łapie model na błędzie w 16.26). Błąd = żądanie
        900 EUR od klienta jeszcze w terminie = ryzyko prawne.
    """
    if dni_od_dostawy < PROG_DNI_START:
        return 0
    progi = PROGI_PLN if str(waluta).upper() == "PLN" else PROGI_EUR
    tygodnie = (dni_od_dostawy - PROG_DNI_START) // TYDZIEN_DNI + 1
    idx = min(tygodnie, len(progi)) - 1  # CAP na ostatnim progu
    return progi[idx]


def waluta_dla(kraj_lub_grupa: str) -> str:
    """
    Waluta naliczenia: PLN dla Polski, EUR dla reszty.

    Reguła (§6.9, linie ~1234): „EUR poza PL, PLN dla PL".

    Dlaczego kod: deterministyczne mapowanie. Zła waluta = złe roszczenie.
    """
    k = (kraj_lub_grupa or "").strip().lower()
    if k in ("pl", "poland", "polska", "polen"):
        return "PLN"
    return "EUR"


def typ_komunikatu(kwota: int, kwota_poprzednia: int) -> str:
    """
    Typ wiadomości windykacyjnej A/B/C (§6.9, linie ~1239-1242, 2878-2898).

    TYP B  -> kwota > kwota_poprzednia (skok progu): wiadomość dostaje zdanie
              „naliczona kwota wzrosła z [POPRZEDNIA] do [AKTUALNA]".
    TYP A/C -> kwota == kwota_poprzednia: BRAK wzmianki o wzroście.

    UWAGA — KONWENCJA POPRZEDNIEJ KWOTY (§6.9, linia ~1242, case 16.26):
        po KAŻDEJ wysłanej wiadomości prompt zapisuje
        `kwota_naliczona_poprzednia = kwota_naliczona`. Pierwsza wiadomość ma więc
        poprzednia == kwota (16.26 Wejście A: oba =300 → TYP A). Dlatego wołający
        przekazuje poprzednią kwotę = bieżącej kwocie przy pierwszej wiadomości.
        Rozróżnienie A (pierwsza, poprzednia==0 na samym starcie) vs C (cap
        utrzymany) jest KOSMETYCZNE — oba dają identyczną treść (zero wzmianki).
        Zwracamy „A" gdy poprzednia==0 (stan początkowy), inaczej „C".

    Dlaczego kod: decyzja wynika WYŁĄCZNIE z porównania dwóch liczb.
    """
    if kwota > kwota_poprzednia:
        return "B"
    if kwota_poprzednia <= 0:
        return "A"
    return "C"


# =============================================================================
# FUNKCJE — KALENDARZ / TERMINY (§6.9)
# =============================================================================

def dni_robocze_po(start: date, n: int) -> date:
    """
    Dodaje `n` dni roboczych do `start`, pomijając soboty i niedziele.

    Używane przez okno kasacji (+10 dni roboczych) i zielonkę (+2 dni robocze).
    UWAGA: liczy tylko dni robocze; NIE uwzględnia świąt (brak kalendarza świąt
    w prompcie — gdyby był potrzebny, dołożyć tablicę świąt jako STAŁĄ).

    Dlaczego kod: liczenie dni roboczych to arytmetyka kalendarzowa. LLM gubi
    weekendy → klient dostaje sprzeczne terminy skasowania długu (§6.9).
    """
    if n <= 0:
        return start
    d = start
    dodane = 0
    while dodane < n:
        d = d + timedelta(days=1)
        if d.weekday() < 5:  # 0=pon ... 4=pt ; 5,6 = sob,niedz
            dodane += 1
    return d


def okno_kasacji(data_ostatniej_wiadomosci: date) -> date:
    """
    Okno kasacji długu = data ostatniej wiadomości + 10 dni roboczych.

    Reguła (§6.9 OKNO KASACJI, linie ~1111-1121): każda wiadomość do klienta
    RESETUJE okno. Zwrot starej części w oknie → kwota_naliczona = 0, sprawa
    zamknięta. Po toksycznych aktywach kwota NIE podlega anulowaniu (osobna decyzja).

    Dlaczego kod: deterministyczna mechanika kalendarzowo-stanowa.
    """
    return dni_robocze_po(data_ostatniej_wiadomosci, OKNO_KASACJI_DNI_ROBOCZE)


def termin_k4(data_wyslania_pdf: date) -> date:
    """
    Termin K4 = data wysłania PDF + 30 dni KALENDARZOWYCH.

    Reguła (§6.9 K4, linie ~1446-1451): K4_deadline_30 jest STAŁY i NIEresetowalny
    przez neutralne odpowiedzi klienta („dostałem PDF", „muszę przemyśleć" — linie
    ~1450-1459 wprost zakazują resetu).

    Dlaczego kod: stały deadline prawny. AI ma tendencję resetować go „neutralną"
    odpowiedzią klienta → cała windykacja się rozjeżdża.
    """
    return data_wyslania_pdf + timedelta(days=TERMIN_K4_DNI)


def termin_k5(data: date) -> date:
    """
    Termin K5 = data wiadomości K5 + 7 dni KALENDARZOWYCH.

    Reguła (§6.9 K5, linie ~1500-1523): po 7 dniach ciszy → tag finalny
    toksyczne_aktywa=TAK.

    Dlaczego kod: stały deadline; po nim kwota staje się egzekwowalna formalnie.
    """
    return data + timedelta(days=TERMIN_K5_DNI)


TERMIN_ODBIORU_KANDYDAT_DNI = 2  # §11.1.2: kandydat = dziś + 2 dni


def termin_odbioru(najwczesniej: Optional[date] = None, dzis: Optional[date] = None) -> date:
    """
    Najwcześniejszy realny termin odbioru kuriera (§11.1.2).

    Reguła: kandydat = dziś + 2 dni; wynik = pierwszy DZIEŃ ROBOCZY nie wcześniejszy
    niż max(kandydat, najwczesniej). Weekend przesuwa na poniedziałek.

    Dlaczego kod: arytmetyka kalendarzowa z weekendem. AI poda termin na sobotę albo
    „jutro" mimo zakazu — kurier nie przyjedzie.
    """
    d = dzis or date.today()
    cel = d + timedelta(days=TERMIN_ODBIORU_KANDYDAT_DNI)
    if najwczesniej and najwczesniej > cel:
        cel = najwczesniej
    while cel.weekday() >= 5:  # sob/niedz → poniedziałek
        cel = cel + timedelta(days=1)
    return cel


# =============================================================================
# FUNKCJE — KURIER / LOGISTYKA (§10.1, §11.4)
# =============================================================================

def _czy_kolektor(index_handlowy: Optional[str]) -> bool:
    """ORG/REG/BMW na początku indeksu → kolektor (§9.4, linia ~1872)."""
    if not index_handlowy:
        return False
    idx = str(index_handlowy).strip().upper()
    return any(idx.startswith(p) for p in KOLEKTOR_PREFIXY)


def regula_indeksowa(index_handlowy: str) -> str:
    """
    Reguła Indeksowa: indeks → "FedEx" albo "UPS" (§10.1, linie ~1877-1881).

    FedEx gdy: A) pierwsze 4 znaki indeksu w FEDEX_PREFIXY, LUB
               B) cały indeks w FEDEX_INDEKSY_PELNE.
    Inaczej → UPS.

    Dlaczego kod: lookup w ~100-elementowej tablicy. To dokładnie to, w czym AI
    halucynuje (zgadnie zły kurier → zlecenie odrzucone, podwójny podjazd).
    """
    idx = (index_handlowy or "").strip().upper()
    if not idx:
        return "UPS"
    if idx in FEDEX_INDEKSY_PELNE:
        return "FEDEX"
    if idx[:4] in FEDEX_PREFIXY:
        return "FEDEX"
    return "UPS"


def wybor_kuriera(
    *,
    towar_typ: str,
    liczba_skrzyn: int,
    kurier_pierwotny: Optional[str],
    index_handlowy: Optional[str],
    data_dostawy: Optional[date] = None,
    rekomendacja_dbschenker: bool = False,
) -> dict:
    """
    Drzewo decyzyjne wyboru kuriera zwrotnego (§10.1 / §11.4.0, linie ~1877-1881, 2055-2110).

    Kolejność (kaskada, pierwszy pasujący wygrywa):
      1) KOLEKTOR → zawsze UPS.
      2) >= PROG_SKRZYN_DBSCHENKER skrzyń (lub rekomendacja) → DB Schenker
         (TYLKO skrzynie, nigdy kolektory — to już wyłapane w kroku 1).
      3) kurier_pierwotny znany → ten sam kurier wraca (dostawy > pivot:
         „ten sam kurier co dostarczył", §10.2).
      4) nieznany + skrzynia → Reguła Indeksowa. Aktywna gdy dostawa ≤ pivot
         (2025-12-01); wynik: FedEx wg tablicy, reszta UPS. Gdy data_dostawy
         > pivot a kurier pierwotny nieznany → nie da się rozstrzygnąć → pytaj.
      5) nadal niepewne → {"kurier": None, "pytaj": True}.

    Zwraca {"kurier": str|None, "pytaj": bool, "powod": str}.

    Dlaczego kod: czysta kaskada warunków + lookup + pivot dat. Zero kreatywności.
    """
    typ = (towar_typ or "").strip().upper()

    # 1) KOLEKTOR → zawsze UPS
    if typ == "KOLEKTOR" or _czy_kolektor(index_handlowy):
        return {"kurier": KOLEKTOR_KURIER, "pytaj": False,
                "powod": "KOLEKTOR → zawsze UPS (§10.1)"}

    # 2) >= 2 skrzynie lub rekomendacja → DB Schenker (tylko skrzynie)
    if liczba_skrzyn >= PROG_SKRZYN_DBSCHENKER or rekomendacja_dbschenker:
        return {"kurier": "DBSCHENKER", "pytaj": False,
                "powod": f">= {PROG_SKRZYN_DBSCHENKER} skrzyń / rekomendacja → DB Schenker (§11.4.0)"}

    # 3) kurier pierwotny znany → ten sam wraca
    if kurier_pierwotny:
        return {"kurier": str(kurier_pierwotny).strip().upper(), "pytaj": False,
                "powod": "kurier pierwotny znany → ten sam wraca (§10.2)"}

    # 4) nieznany + skrzynia → Reguła Indeksowa (tylko dostawy ≤ pivot)
    if index_handlowy:
        if data_dostawy is None or data_dostawy <= PIVOT_REGULA_INDEKSOWA:
            kurier = regula_indeksowa(index_handlowy)
            return {"kurier": kurier, "pytaj": False,
                    "powod": f"Reguła Indeksowa (dostawa ≤ {PIVOT_REGULA_INDEKSOWA}) → {kurier} (§10.1)"}
        # dostawa > pivot, kurier pierwotny nieznany → nie da się ustalić
        return {"kurier": None, "pytaj": True,
                "powod": f"dostawa > {PIVOT_REGULA_INDEKSOWA} a kurier pierwotny nieznany → zapytaj operatora (§10.2)"}

    # 5) nadal niepewne
    return {"kurier": None, "pytaj": True,
            "powod": "brak danych do rozstrzygnięcia → zapytaj operatora"}


def skrzynie_na_palety(n: int) -> list:
    """
    Przelicznik skrzynia → paleta DB Schenker + podział na „nogi" transportu.

    Reguła (§11.4, linie ~2301-2321):
        1-3 skrzynie = 1 paleta DBS (jedna noga).
        4 = 3 na palecie DBS + 1 osobno oryginalnym kurierem (DWIE nogi).
        5 = 3 + 2 ; 6 = 3 + 3 (też dwie nogi).
    Czyli: pierwsze max 3 skrzynie idą DB Schenkerem na palecie; nadwyżka (>3)
    idzie osobną nogą (DB Schenker dla 2-3 skrzyń nadwyżki to >= próg, ale prompt
    opisuje nadwyżkę jako „osobno oryginalnym kurierem" / drugą nogę — patrz powód).

    Zwraca listę „nóg": [{"kurier", "liczba_skrzyn", "palety", "rola"}].

    Dlaczego kod: deterministyczna funkcja N → podział. AI błędnie rozdziela
    (4 na jednej palecie / kolektor DB Schenkerem) → kurier nie odbierze.
    """
    if n <= 0:
        return []
    nogi: List[dict] = []
    glowna = min(n, SKRZYN_NA_PALETE)
    nogi.append({
        "kurier": "DBSCHENKER",
        "liczba_skrzyn": glowna,
        "palety": 1,
        "rola": "glowna",
    })
    nadwyzka = n - SKRZYN_NA_PALETE
    if nadwyzka > 0:
        # 4 skrzynie: nadwyżka=1 → osobno oryginalnym kurierem.
        # 5-6 skrzyń: nadwyżka 2-3 → druga noga (osobna paleta DBS).
        if nadwyzka == 1:
            nogi.append({
                "kurier": "ORYGINALNY",  # do uzupełnienia kurierem pierwotnym sprawy
                "liczba_skrzyn": 1,
                "palety": 0,
                "rola": "dodatkowa",
            })
        else:
            nogi.append({
                "kurier": "DBSCHENKER",
                "liczba_skrzyn": nadwyzka,
                "palety": 1,
                "rola": "dodatkowa",
            })
    return nogi


def ups_access_point_link(kraj_kod: str, jezyk: Optional[str] = None) -> str:
    """
    Link do punktu UPS Access Point (§11.4.1, linie ~2178-2224).

    TYLKO dla KOLEKTOR + KURIER_OPCJA=ETYKIETA_PUNKT (egzekwuje wywołujący).
    Logika 3-poziomowa:
      1) kraj w UPS_AP_WYJATKI → użyj segmentu z tabeli (np. BE→/be/en/, AT→/at/de/).
      2) kraj poza tabelą → reguła domyślna /{kraj}/{kraj}/ (PL→/pl/pl/).
      3) brak/nieznany kraj → fallback /{kraj}/en/ (np. ""→//en/).

    Parametr `jezyk` jest opcjonalnym nadpisaniem dla reguły domyślnej (segment
    /{kraj}/{jezyk}/) — używaj tylko gdy panel koordynatora wymusza inny język.

    Dlaczego kod: budowa URL z tablicy odwzorowań. AI generuje martwy link
    (zły kod kraju/języka) → klient nie nada paczki.
    """
    kod = (kraj_kod or "").strip().upper()
    if not kod:
        return UPS_BASE_URL.format(seg="/en/")  # fallback bez kraju
    if kod in UPS_AP_WYJATKI:
        seg = UPS_AP_WYJATKI[kod]
    elif jezyk:
        seg = f"/{kod.lower()}/{jezyk.strip().lower()}/"
    else:
        low = kod.lower()
        seg = f"/{low}/{low}/"  # reguła domyślna
    return UPS_BASE_URL.format(seg=seg.strip("/"))


# =============================================================================
# FUNKCJE — ROUTING FORUM (§0.1.1.3, §12)
# =============================================================================

def kraj_na_grupe(kraj: str) -> str:
    """
    Nazwa/kod kraju → bucket KRAJ: "DE" / "FR" / "UKPL" (§0.1.1.3, linie ~454-458).

    DE: Germany/Austria/Schweiz/Switzerland/Liechtenstein.
    FR: France/Belgium/Spain/Italy.
    UKPL: reszta (UK, PL, IE, NL, LU, PT, SE, DK, HR, SI, RO, FI, BG, CZ, SK, HU, NO, ...).

    UWAGA: prompt zakazuje DEFAULTOWANIA do UKPL gdy kraju NIE da się ustalić ze
    źródła (linia ~459). Ta funkcja mapuje JUŻ USTALONĄ nazwę kraju — pusty/None
    powinien być wyłapany wcześniej (przed wywołaniem), tu zwracamy "UKPL" jako
    bucket dla wszystkich pozostałych ZNANYCH krajów, zgodnie z tabelą.

    Dlaczego kod: skończony słownik bucketów. AI wrzuca Szwajcarię do UKPL →
    wpis idzie złym kanałem/językiem.
    """
    k = (kraj or "").strip().lower()
    return KRAJ_DO_GRUPY.get(k, "UKPL")


def routing_forum(token: str, kraj: Optional[str] = None, jezyk: Optional[str] = None) -> dict:
    """
    Routing wpisu na forum: token/temat → {cel, user_do} LITERALNIE
    (§0.1.1.3, linie ~426-475; §12, linie ~2502-2531).

    Tokeny zależne od kraju/języka (rozwiązywane dynamicznie):
      - "delegacja_telefonu" → cel=CZATOSZTUR_[KRAJ], user_do=Telefonisci_[JEZYK].
      - "raport_telefon" / "operatorzy" → cel=CZATOSZTUR_[KRAJ], user_do=Operatorzy_[KRAJ].
      - "k3" / "pismo5" → cel=CZATOSZTUR_[KRAJ], user_do=justyna.
    Tokeny stałe (token: w ROUTING_TEMATY): zlecenie kuriera, sped, reklamacja,
    niepozamykane/zielonka, błąd techniczny.

    PUŁAPKI LITERALNE (egzekwowane przez stałe):
      - user_do "NIEPOZAMYKANE AUSTAUSCHE" ma SPACJĘ (nie podkreślnik).
      - "Telefonisci_ENG" dla EN (nie _EN).
      - ukośniki w "CZATOSZTUR_UK/PL" i "Operatorzy_UK/PL".

    Dlaczego kod: tablica literałów z pułapkami (spacja vs podkreślnik, ENG vs EN).
    AI generuje "NIEPOZAMYKANE_AUSTAUSCHE" z podkreślnikiem → API forum 400.
    """
    t = (token or "").strip().lower()
    bucket = kraj_na_grupe(kraj) if kraj else "UKPL"
    czat = CZATOSZTUR_WG_KRAJU[bucket]

    if t in ("delegacja_telefonu", "telefon", "tel"):
        jez = (jezyk or "EN").strip().upper()
        user = TELEFONISCI_WG_JEZYKA.get(jez, TELEFONISCI_WG_JEZYKA["EN"])
        return {"cel": czat["czatoszt"], "user_do": user}

    if t in ("raport_telefon", "operatorzy", "po_telefonie"):
        return {"cel": czat["czatoszt"], "user_do": czat["operatorzy"]}

    if t in ("k3", "pismo5", "pismo_5_etapu"):
        return {"cel": czat["czatoszt"], "user_do": "justyna"}

    if t in ROUTING_TEMATY:
        # kopia, żeby nie zwracać współdzielonej referencji stałej
        return dict(ROUTING_TEMATY[t])

    # nieznany token → bezpieczny brak routingu (wywołujący ma zapytać operatora)
    return {"cel": None, "user_do": None}


# =============================================================================
# FUNKCJE — GUARDRAIL PRAWNY: ZAKAZANE FRAZY (§6.9)
# =============================================================================

def znajdz_zakazane(text: str) -> list:
    """
    Zwraca listę zakazanych fraz wykrytych w tekście (§6.9, linie ~1170-1178).

    Dopasowanie BEZ względu na wielkość liter dla fraz z ZAKAZANE_FRAZY.
    Dodatkowo: „NATYCHMIAST" pisane KRZYKIEM (wielkie litery jako krzyk) — wykrywane
    osobno, bo zakazana jest forma WERSALIKOWA, nie słowo samo w sobie (linia ~1174).

    Dlaczego kod: guardrail prawny/wizerunkowy, nie kreatywność. Bez filtra AI
    pod presją wygeneruje groźbę („pozwiemy", „komornik") = ryzyko naruszenia
    przepisów o windykacji/nękaniu.
    """
    if not text:
        return []
    low = text.lower()
    znalezione = [f for f in ZAKAZANE_FRAZY if f in low]
    # „NATYCHMIAST" krzykiem: tylko gdy występuje WERSALIKAMI w oryginale.
    if re.search(r"\bNATYCHMIAST\b", text):
        znalezione.append("NATYCHMIAST (krzyk wersalikami)")
    return znalezione


def ma_zakazane(text: str) -> bool:
    """True jeśli tekst zawiera choć jedną zakazaną frazę (§6.9). Dlaczego kod: bramka bool."""
    return len(znajdz_zakazane(text)) > 0


# =============================================================================
# FUNKCJE — KLASYFIKACJA DIAMENTU (log_diamond)
# =============================================================================

def klasyfikuj_diament(tresc_posta: str, cel: str) -> dict:
    """
    Klasyfikacja czy wpis forumowy to DIAMENT (skuteczne zlecenie kuriera = PZ6),
    zgodna z mechaniką `log_diamond` (StatsStore.diamenty_dzis, store.py).

    Reguły:
      - czy_diament = True TYLKO gdy treść zawiera wzorzec „Zamówienie: NNN"
        (numer zamówienia) ORAZ NIE zawiera stop-słów (bump/ponaglenie/eskalacja/
        dopyt/podbicie) ORAZ typ_zlecenia nie jest z DIAMENT_TYPY_NIE.
      - typ_zlecenia: zmiana/cofnięte/ponowienie → NIE diament; etykieta UPS punkt /
        zlecenie kuriera → diament.
      - kategoria_towaru: "Kolektor" (ORG/REG/BMW lub słowo kolektor) / "Skrzynia".
      - kurier: wyciągany z treści (UPS/FEDEX/DBSCHENKER) jeśli się da; KOLEKTOR →
        fallback UPS + flaga anomalii gdy w treści jest INNY kurier niż UPS.

    Zwraca {"czy_diament", "typ_zlecenia", "kurier", "kategoria_towaru", "anomalia"}.

    Dlaczego kod: detekcja diamentu zasila licznik sukcesu operatora (Diamentoza) —
    musi być spójna i deterministyczna; AI policzyłoby niespójnie między sesjami.
    """
    tresc = tresc_posta or ""
    low = tresc.lower()

    # numer zamówienia: „Zamówienie: 374593" (z polskimi znakami lub bez)
    m_nr = re.search(r"zam[oó]wienie\s*:\s*([0-9]{4,7})", low)
    ma_numer = bool(m_nr)

    # stop-słowa: obecność = NIE diament
    ma_stop = any(s in low for s in DIAMENT_STOP_SLOWA)

    # typ zlecenia
    typ_zlecenia = "zlecenie"
    if "zmian" in low:
        typ_zlecenia = "zmiana"
    elif "cofni" in low or "cofnięt" in low or "cofniet" in low:
        typ_zlecenia = "cofniete"
    elif "ponowieni" in low or "ponów" in low or "ponow" in low:
        typ_zlecenia = "ponowienie"
    elif "etykiet" in low and ("punkt" in low or "access" in low):
        typ_zlecenia = "etykieta_ups_punkt"
    typ_nie_diament = typ_zlecenia in ("zmiana", "cofniete", "ponowienie")

    # kategoria towaru
    if "kolektor" in low or any(p.lower() in low for p in KOLEKTOR_PREFIXY):
        kategoria = "Kolektor"
    elif "skrzyni" in low or "skrzyn" in low:
        kategoria = "Skrzynia"
    else:
        kategoria = ""

    # kurier z treści
    kurier = None
    if "dbschenker" in low or "db schenker" in low or "schenker" in low:
        kurier = "DBSCHENKER"
    elif "fedex" in low:
        kurier = "FEDEX"
    elif "ups" in low:
        kurier = "UPS"

    # anomalia: kolektor MUSI iść UPS-em; inny kurier w treści = anomalia
    anomalia = False
    if kategoria == "Kolektor":
        if kurier and kurier != "UPS":
            anomalia = True
        if kurier is None:
            kurier = KOLEKTOR_KURIER  # fallback UPS dla kolektora

    czy_diament = ma_numer and not ma_stop and not typ_nie_diament

    return {
        "czy_diament": czy_diament,
        "typ_zlecenia": typ_zlecenia,
        "kurier": kurier,
        "kategoria_towaru": kategoria,
        "anomalia": anomalia,
    }


# =============================================================================
# FUNKCJE — SEKWENCJA BUMP / ESKALACJI (§0.1.1.2)
# =============================================================================

# Progi powod_n: poniżej progu NIE bumpuj (forum podało powód). §0.1.1.2 l.236-239.
POWOD_N_PROG_DOPYTANIE = 3        # default: powod_n=3 → neutralne dopytanie
POWOD_N_PROG_DOPYTANIE_K3 = 2     # FORUM_K3 ma krótsze SLA → próg 2


def nastepny_bump(bump: int, ea: int = 0, zablokowana: bool = False) -> dict:
    """
    Następny krok 7-krokowej sekwencji eskalacji (§0.1.1.2, l.131-208) z licznika (bump, ea).

    Sekwencja: 0 wpis → 1 bump1 → 2 bump2 → 3 EA(jednorazowo) → 4 bump3 → 5 bump4 →
    6 SZTURZE proceduralne (zablokowana) → RESTART (bump=0, ea=0).
    Bumpy 1-4 ZAWSZE do grupy pierwotnej; EA jednorazowo w cyklu; SZTURZE do celu kroku 0.
    Obsługa legacy ea=2 (stara sekwencja 8-krokowa, l.202-207): mapuj na bezpieczny następny krok.

    Zwraca {"akcja", "nowy_bump", "nowy_ea", "do_kogo"}.

    Dlaczego kod: czysty automat z licznikiem. LLM gubi licznik (robi EA dwa razy, pomija
    krok, nie restartuje) → spam na forum albo sprawa cicho umiera. Determinizm to naprawia.
    """
    b = int(bump or 0)
    e = int(ea or 0)
    if zablokowana:
        return {"akcja": "restart", "nowy_bump": 0, "nowy_ea": 0, "do_kogo": "grupa_pierwotna"}
    # Legacy ea=2 (sekwencja 8-krokowa z v1.5.2) → bezpieczny następny krok wg nowej sekwencji.
    if e >= 2:
        if b >= 4:
            return {"akcja": "szturze_proceduralne", "nowy_bump": b, "nowy_ea": e, "do_kogo": "SZTURZE_WSPARCIE"}
        if b == 3:
            return {"akcja": "bump4", "nowy_bump": 4, "nowy_ea": e, "do_kogo": "grupa_pierwotna"}
        if b == 2:
            return {"akcja": "bump3", "nowy_bump": 3, "nowy_ea": e, "do_kogo": "grupa_pierwotna"}
    if b <= 0:
        return {"akcja": "bump1", "nowy_bump": 1, "nowy_ea": e, "do_kogo": "grupa_pierwotna"}
    if b == 1:
        return {"akcja": "bump2", "nowy_bump": 2, "nowy_ea": e, "do_kogo": "grupa_pierwotna"}
    if b == 2 and e < 1:
        return {"akcja": "eskalacja_EA", "nowy_bump": 2, "nowy_ea": 1, "do_kogo": "EA"}
    if b == 2 and e >= 1:
        return {"akcja": "bump3", "nowy_bump": 3, "nowy_ea": e, "do_kogo": "grupa_pierwotna"}
    if b == 3:
        return {"akcja": "bump4", "nowy_bump": 4, "nowy_ea": e, "do_kogo": "grupa_pierwotna"}
    # b >= 4
    return {"akcja": "szturze_proceduralne", "nowy_bump": b, "nowy_ea": e, "do_kogo": "SZTURZE_WSPARCIE"}


def czy_bumpowac(powod_n: Optional[int], forum_k3: bool = False) -> bool:
    """
    Czy wolno bumpować mimo podanego powodu (§0.1.1.2 „POWÓD PODANY ≠ BUMPUJ", l.210-244).
    powod_n poniżej progu → NIE bumpuj (forum podało powód). Brak powodu (None) → bumpuj wg sekwencji.

    Dlaczego kod: progi liczbowe i osie powod vs bump — deterministyczna mechanika.
    """
    if powod_n is None:
        return True
    prog = POWOD_N_PROG_DOPYTANIE_K3 if forum_k3 else POWOD_N_PROG_DOPYTANIE
    return int(powod_n) >= prog


# =============================================================================
# SANITY — asercje uruchamiane przez `python3 reguly.py`
# =============================================================================
if __name__ == "__main__":
    # --- kwota_naliczona (§6.9 / 16.26) ---
    assert kwota_naliczona(10) == 0, "dni < 22 → 0"
    assert kwota_naliczona(21) == 0, "ostatni dzień terminu umownego → 0"
    assert kwota_naliczona(22) == 300, "dzień 22 → 300 (KOREKTA WZORU 16.26)"
    assert kwota_naliczona(28) == 300, "dzień 28 → 300"
    assert kwota_naliczona(29) == 600, "dzień 29 → 600"
    assert kwota_naliczona(35) == 600, "dzień 35 → 600"
    assert kwota_naliczona(36) == 900, "dzień 36 → 900 (cap)"
    assert kwota_naliczona(67) == 900, "cap utrzymany (case 16.25)"
    assert kwota_naliczona(22, "PLN") == 900, "PLN próg 1"
    assert kwota_naliczona(29, "PLN") == 1500, "PLN próg 2"
    assert kwota_naliczona(36, "PLN") == 2400, "PLN cap"

    # --- waluta ---
    assert waluta_dla("PL") == "PLN"
    assert waluta_dla("Poland") == "PLN"
    assert waluta_dla("DE") == "EUR"

    # --- typ komunikatu (§6.9) ---
    assert typ_komunikatu(600, 300) == "B", "skok progu 300→600 → B (case 16.26 Wejście B)"
    assert typ_komunikatu(900, 600) == "B", "skok 600→900 → B (case 16.26 Wejście C)"
    assert typ_komunikatu(300, 300) == "C", "pierwsza wiadomość: konwencja poprzednia==kwota → brak wzmianki"
    assert typ_komunikatu(0, 0) == "A", "stan początkowy bez kwoty → A"
    assert typ_komunikatu(900, 900) == "C", "cap utrzymany 900==900 → C (case 16.26 Wejście D)"

    # --- dni robocze ---
    piatek = date(2026, 6, 26)  # piątek
    assert piatek.weekday() == 4
    assert dni_robocze_po(piatek, 1) == date(2026, 6, 29), "piątek +1 dzień roboczy = poniedziałek"
    assert dni_robocze_po(piatek, 5) == date(2026, 7, 3), "piątek +5 dni roboczych = następny piątek"
    assert okno_kasacji(piatek) == dni_robocze_po(piatek, 10)

    # --- terminy K4/K5 (kalendarzowe) ---
    assert termin_k4(date(2026, 4, 30)) == date(2026, 5, 30), "K4 +30 dni kalendarzowych"
    assert termin_k5(date(2026, 5, 30)) == date(2026, 6, 6), "K5 +7 dni kalendarzowych"

    # --- termin odbioru (§11.1.2): kandydat=dziś+2, weekend→poniedziałek ---
    # środa 2026-06-24 +2 = piątek 26.06 (dzień roboczy)
    assert termin_odbioru(dzis=date(2026, 6, 24)) == date(2026, 6, 26)
    # czwartek 2026-06-25 +2 = sobota 27.06 → poniedziałek 29.06
    assert termin_odbioru(dzis=date(2026, 6, 25)) == date(2026, 6, 29)
    # najwcześniej wymusza późniejszą datę (i roluje weekend)
    assert termin_odbioru(najwczesniej=date(2026, 7, 4), dzis=date(2026, 6, 24)) == date(2026, 7, 6)

    # --- wybór kuriera (§10.1) ---
    assert wybor_kuriera(towar_typ="KOLEKTOR", liczba_skrzyn=1,
                         kurier_pierwotny=None, index_handlowy=None)["kurier"] == "UPS"
    assert wybor_kuriera(towar_typ="SKRZYNIA", liczba_skrzyn=2,
                         kurier_pierwotny=None, index_handlowy=None)["kurier"] == "DBSCHENKER"
    assert wybor_kuriera(towar_typ="SKRZYNIA", liczba_skrzyn=1,
                         kurier_pierwotny="FEDEX", index_handlowy=None)["kurier"] == "FEDEX"
    # Reguła Indeksowa: prefiks FedEx
    assert wybor_kuriera(towar_typ="SKRZYNIA", liczba_skrzyn=1, kurier_pierwotny=None,
                         index_handlowy="126TXYZ", data_dostawy=date(2025, 6, 1))["kurier"] == "FEDEX"
    # Reguła Indeksowa: pełny indeks FedEx
    assert regula_indeksowa("145TDI5GRUP1") == "FEDEX"
    # Reguła Indeksowa: nie-FedEx → UPS
    assert regula_indeksowa("9999ABC") == "UPS"
    # niepewne (brak danych) → pytaj
    assert wybor_kuriera(towar_typ="SKRZYNIA", liczba_skrzyn=1,
                         kurier_pierwotny=None, index_handlowy=None)["pytaj"] is True
    # ORG → kolektor → UPS niezależnie od liczby skrzyń (kolektor nie idzie DBS)
    assert wybor_kuriera(towar_typ="", liczba_skrzyn=5, kurier_pierwotny=None,
                         index_handlowy="ORG123")["kurier"] == "UPS"

    # --- skrzynie na palety (§11.4) ---
    assert len(skrzynie_na_palety(3)) == 1, "1-3 skrzynie = 1 noga"
    assert len(skrzynie_na_palety(4)) == 2, "4 skrzynie = dwie nogi"
    assert skrzynie_na_palety(4)[0]["liczba_skrzyn"] == 3
    assert skrzynie_na_palety(4)[1]["liczba_skrzyn"] == 1
    assert skrzynie_na_palety(6)[1]["liczba_skrzyn"] == 3

    # --- link UPS Access Point (§11.4.1) ---
    assert ups_access_point_link("BE") == \
        "https://www.ups.com/be/en/business-solutions/pickup-dropoff-options"
    assert ups_access_point_link("AT") == \
        "https://www.ups.com/at/de/business-solutions/pickup-dropoff-options"
    assert ups_access_point_link("PL") == \
        "https://www.ups.com/pl/pl/business-solutions/pickup-dropoff-options"
    assert ups_access_point_link("CZ") == \
        "https://www.ups.com/cz/cs/business-solutions/pickup-dropoff-options"

    # --- routing forum (§0.1.1.3) — PUŁAPKI LITERALNE ---
    r_aus = routing_forum("niepozamykane")
    assert r_aus["user_do"] == "NIEPOZAMYKANE AUSTAUSCHE", "user_do ze SPACJĄ"
    assert " " in r_aus["user_do"] and "_AUSTAUSCHE" not in r_aus["user_do"]
    assert r_aus["cel"] == "NIEPOZAMYKANE_AUSTAUSCHE", "cel z podkreślnikiem"
    assert routing_forum("delegacja_telefonu", jezyk="EN")["user_do"] == "Telefonisci_ENG"
    assert routing_forum("operatorzy", kraj="UK")["user_do"] == "Operatorzy_UK/PL"
    assert routing_forum("zlecenie_kuriera")["cel"] == "AUTOS_KURIERZY"
    assert routing_forum("k3", kraj="DE") == {"cel": "CZATOSZTUR_DE", "user_do": "justyna"}

    # --- kraj na grupę ---
    assert kraj_na_grupe("Schweiz") == "DE"
    assert kraj_na_grupe("Belgium") == "FR"
    assert kraj_na_grupe("Netherlands") == "UKPL"
    assert kraj_na_grupe("Poland") == "UKPL"

    # --- zakazane frazy (§6.9) ---
    assert ma_zakazane("Drogi kliencie-dłużniku") is True
    assert ma_zakazane("Pozwiemy Państwa") is True
    assert ma_zakazane("Reaguj NATYCHMIAST") is True, "krzyk wersalikami"
    assert ma_zakazane("reaguj natychmiast") is False, "małe litery = dozwolone"
    assert ma_zakazane("Drogi Kliencie, prosimy o kontakt") is False

    # --- diament (log_diamond) ---
    d = klasyfikuj_diament("Zlecenie kuriera UPS. Zamówienie: 374593. Kolektor.", "AUTOS_KURIERZY")
    assert d["czy_diament"] is True
    assert d["kategoria_towaru"] == "Kolektor"
    assert d["kurier"] == "UPS"
    d2 = klasyfikuj_diament("Bump 1. Zamówienie: 374593", "AUTOS_KURIERZY")
    assert d2["czy_diament"] is False, "stop-słowo bump → nie diament"
    d3 = klasyfikuj_diament("Zmiana zlecenia. Zamówienie: 374593", "AUTOS_KURIERZY")
    assert d3["czy_diament"] is False and d3["typ_zlecenia"] == "zmiana"
    d4 = klasyfikuj_diament("Zlecenie kuriera FEDEX. Zamówienie: 100200. Kolektor.", "AUTOS_KURIERZY")
    assert d4["anomalia"] is True, "kolektor z innym kurierem niż UPS = anomalia"

    # --- sekwencja bump (§0.1.1.2) ---
    assert nastepny_bump(0)["akcja"] == "bump1"
    assert nastepny_bump(1)["akcja"] == "bump2"
    assert nastepny_bump(2, 0)["akcja"] == "eskalacja_EA"
    assert nastepny_bump(2, 1)["akcja"] == "bump3"
    assert nastepny_bump(3, 1)["akcja"] == "bump4"
    assert nastepny_bump(4, 1)["akcja"] == "szturze_proceduralne"
    assert nastepny_bump(4, 1, zablokowana=True)["akcja"] == "restart"
    assert nastepny_bump(0, 0, zablokowana=True)["nowy_bump"] == 0
    # legacy ea=2
    assert nastepny_bump(4, 2)["akcja"] == "szturze_proceduralne"
    assert nastepny_bump(2, 2)["akcja"] == "bump3"
    assert nastepny_bump(3, 2)["akcja"] == "bump4"
    # powód podany ≠ bumpuj
    assert czy_bumpowac(None) is True
    assert czy_bumpowac(1) is False and czy_bumpowac(2) is False and czy_bumpowac(3) is True
    assert czy_bumpowac(2, forum_k3=True) is True, "K3 próg 2"

    print("OK — wszystkie asercje sanity przeszły.")
