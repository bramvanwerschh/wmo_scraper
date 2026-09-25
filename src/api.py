"""Ophalen bij CVDR/overheid.nl: beleefd (max 1 req/s), met retry en hervatbare caching.

Alle SRU-responses en documentbestanden worden ruw op schijf bewaard (§4 van de opdracht).
Bestaat een bestand al, dan wordt het niet opnieuw opgehaald.
"""

import time
from pathlib import Path

import requests

from src.config import ROOT


class CvdrClient:
    def __init__(self, config: dict):
        self.config = config
        self.user_agent = config["user_agent"]
        self.rate_limit = config["scrapen"]["rate_limit_seconds"]
        self.max_retries = config["scrapen"]["max_retries"]
        self.backoff = config["scrapen"]["backoff_seconds"]
        self.timeout = config["scrapen"]["timeout_seconds"]
        self._last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = self.user_agent

    def _wacht_voor_rate_limit(self):
        verstreken = time.monotonic() - self._last_request_time
        wachttijd = self.rate_limit - verstreken
        if wachttijd > 0:
            time.sleep(wachttijd)

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        laatste_fout = None
        for poging in range(1, self.max_retries + 1):
            self._wacht_voor_rate_limit()
            self._last_request_time = time.monotonic()
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp
                laatste_fout = f"HTTP {resp.status_code}"
            except requests.RequestException as e:
                laatste_fout = str(e)
            if poging < self.max_retries:
                time.sleep(self.backoff * poging)
        raise RuntimeError(f"Ophalen mislukt na {self.max_retries} pogingen: {url} ({laatste_fout})")

    def sru_search(self, query: str, start_record: int = 1, maximum_records: int | None = None) -> str:
        """Eén SRU searchRetrieve-call. Geeft de ruwe XML-tekst terug."""
        sru = self.config["sru"]
        params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "x-connection": sru["x_connection"],
            "query": query,
            "maximumRecords": str(maximum_records or sru["maximum_records"]),
            "startRecord": str(start_record),
        }
        resp = self._get(sru["base_url"], params=params)
        return resp.text

    def haal_op_of_cache(self, url: str, cache_pad: Path, params: dict | None = None) -> bytes:
        """Haalt url op, tenzij cache_pad al bestaat (hervatbaar/idempotent, §4.2)."""
        if cache_pad.exists():
            return cache_pad.read_bytes()
        resp = self._get(url, params=params)
        cache_pad.parent.mkdir(parents=True, exist_ok=True)
        cache_pad.write_bytes(resp.content)
        return resp.content
