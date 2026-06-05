import os
import time

from fastapi import APIRouter, Depends, Query

from api.auth import require_role
from mimir_client import MimirClient

router = APIRouter(prefix="/metrics", tags=["metrics"])
mimir = MimirClient(os.getenv("MIMIR_URL", "http://mimir:9009"))


@router.get("/query")
def query_metric(
    promql: str = Query("hospital_iot_anomaly_score"),
    user: dict = Depends(require_role("Admin", "Analyst", "Viewer")),
):
    return mimir.query(promql)


@router.get("/range")
def query_metric_range(
    promql: str = Query("hospital_ml_isolation_score"),
    hours: int = 6,
    step: str = "30s",
    user: dict = Depends(require_role("Admin", "Analyst", "Viewer")),
):
    end = int(time.time())
    start = end - hours * 3600
    return mimir.query_range(promql, start, end, step)
