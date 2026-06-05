import time
from typing import Any

import requests


class LokiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def push(self, labels: dict[str, str], event: dict[str, Any]) -> None:
        payload = {
            "streams": [
                {
                    "stream": labels,
                    "values": [[str(time.time_ns()), self._json(event)]],
                }
            ]
        }
        requests.post(f"{self.base_url}/loki/api/v1/push", json=payload, timeout=5).raise_for_status()

    def query_range(self, query: str, start_ns: int | None = None, end_ns: int | None = None, limit: int = 1000) -> dict:
        params: dict[str, Any] = {"query": query, "limit": limit}
        if start_ns:
            params["start"] = start_ns
        if end_ns:
            params["end"] = end_ns
        response = requests.get(f"{self.base_url}/loki/api/v1/query_range", params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def query(self, query: str) -> dict:
        response = requests.get(f"{self.base_url}/loki/api/v1/query", params={"query": query}, timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _json(event: dict[str, Any]) -> str:
        import json

        return json.dumps(event, separators=(",", ":"), sort_keys=True)
