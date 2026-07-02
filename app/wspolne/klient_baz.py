"""Cienki klient silnika baz on-prem — JEDYNY punkt styku apki-kafelka z bazami.

Skopiuj do apki i importuj: `from klient import czytaj, zapis_taga`.
Apka NIE widzi połączeń, tuneli ani sekretów — wszystko trzyma usługa `db-broker`.

Tryb (auto):
- PROD: ustaw env `ONPREM_DB_BROKER_URL` = URL usługi db-broker. Klient woła HTTPS z ID-tokenem
  (audience = URL brokera) z metadata servera Cloud Run; nagłówek Authorization: Bearer <token>.
  Wołający musi mieć rolę `run.invoker` na usłudze db-broker.
- DEV: bez `ONPREM_DB_BROKER_URL` — woła lokalny `silnik_baz` przez tunel z Maca (tylko gdzie jest dostępny).

Zwroty: `czytaj` -> lista rekordów (dict). `zapis_taga` -> odpowiedź brokera (na razie zawsze 'sucho').
"""
import json
import os
import urllib.parse
import urllib.request


def _broker_url():
    return os.environ.get("ONPREM_DB_BROKER_URL")


def _id_token(audience: str) -> str:
    url = ("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/"
           "default/identity?audience=" + urllib.parse.quote(audience, safe=""))
    req = urllib.request.Request(url, headers={"Metadata-Flavor": "Google"})
    return urllib.request.urlopen(req, timeout=10).read().decode()


def _post(sciezka: str, body: dict) -> dict:
    base = _broker_url().rstrip("/")
    token = _id_token(base)
    req = urllib.request.Request(
        base + sciezka, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def czytaj(baza: str, sql: str, params=None, limit: int = 1000):
    """READ-ONLY. Zwraca listę rekordów (dict)."""
    if _broker_url():
        return _post("/czytaj", {"baza": baza, "sql": sql, "params": params, "limit": limit})["wiersze"]
    from silnik_baz import czytaj as _local  # tylko DEV na Macu z silnikiem
    return _local(baza, sql, params).head(limit).to_dict("records")


def zapis_taga(dok_id: int, content_tag: str, autor: str):
    """Zapis taga (ItemsTag + audyt TagsHistory). WRITE OFF (sucho) do osobnego OK."""
    if _broker_url():
        return _post("/zapis_taga", {"dok_id": dok_id, "content_tag": content_tag, "autor": autor})
    return {"tryb": "sucho-dev", "wykonano": False, "uwaga": "Realny zapis robi broker; WRITE i tak OFF."}
