# Kontener v11 — stary silnik streamlitowy AS-IS (decyzja właściciela 2026-07-02).
# Pliki silnika = kopie 1:1 z szturchacz-test, NIE DOTYKAĆ. Nasze są tylko: Dockerfile + odpalka.py.
FROM python:3.11-slim

# Polskie znaki to ładunek funkcjonalny (nazwy wątków forum, np. „szturchacz_błędy") —
# bez locale pl_PL.UTF-8 API forum odpowiada błędem 400.
RUN apt-get update && apt-get install -y --no-install-recommends locales \
    && sed -i 's/^# *pl_PL.UTF-8/pl_PL.UTF-8/' /etc/locale.gen && locale-gen \
    && locale -a | grep -qi '^pl_PL' \
    && rm -rf /var/lib/apt/lists/*
ENV LANG=pl_PL.UTF-8 LC_ALL=pl_PL.UTF-8 PYTHONUTF8=1 PYTHONUNBUFFERED=1

WORKDIR /app
# requirements.txt = kopia 1:1 (bez wersji, nietykalna); constraints.txt = NASZE pinowanie
# z przetestowanego środowiska — bez niego świeży build może wciągnąć wersje łamiące importy silnika
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY app_vertex_ew.py forum_module.py szturchacz_vnext_v1_11.txt odpalka.py ./

# non-root — twardy wymóg naszego Cloud Run; zapis TYLKO do .streamlit (kod zostaje root/read-only)
RUN useradd -m -u 1000 silnik && mkdir -p /app/.streamlit && chown silnik:silnik /app/.streamlit
USER silnik
# Docker nie ustawia HOME z passwd — a Streamlit pisze do ~/.streamlit
ENV HOME=/home/silnik

# Nasłuch na $PORT robi odpalka.py (Cloud Run poda PORT; lokalnie 8501)
CMD ["python", "odpalka.py"]
