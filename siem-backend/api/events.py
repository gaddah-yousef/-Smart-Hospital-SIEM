import os
import time

from fastapi import APIRouter, Depends, Query

from api.auth import require_role
from loki_client import LokiClient

router = APIRouter(prefix="/events", tags=["events"])
loki = LokiClient(os.getenv("LOKI_URL", "http://loki:3100"))


@router.get("")
def query_events(
    query: str = Query('{job="hospital-api"} | json'),
    minutes: int = 60,
    user: dict = Depends(require_role("Admin", "Analyst", "Viewer")),
):
    end_ns = time.time_ns()
    start_ns = end_ns - minutes * 60 * 1_000_000_000
    return loki.query_range(query, start_ns=start_ns, end_ns=end_ns)
