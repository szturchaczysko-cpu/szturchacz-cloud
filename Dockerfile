# Szablon Dockerfile pod Cloud Run (skopiuj do nowej apki, dostosuj jeśli trzeba).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Najpierw zależności (lepszy cache warstw).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod aplikacji.
COPY app ./app

# Użytkownik bez uprawnień roota.
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Katalog na dane w zapisywalnym /tmp (Cloud Run: /tmp jest writable, ale ULOTNY —
# trwałe dane trzymaj w Firestore, nie tutaj).
ENV DATA_DIR=/tmp/app-data

# Cloud Run podaje port w $PORT (domyślnie 8080) — NIE wpisuj go na sztywno.
ENV PORT=8080
EXPOSE 8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
