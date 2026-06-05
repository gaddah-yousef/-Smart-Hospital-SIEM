from typing import Any

import requests


class MimirClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def query(self, promql: str) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/prometheus/api/v1/query", params={"query": promql}, timeout=10)
        response.raise_for_status()
        return response.json()

    def query_range(self, promql: str, start: int, end: int, step: str = "30s") -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/prometheus/api/v1/query_range",
            params={"query": promql, "start": start, "end": end, "step": step},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
