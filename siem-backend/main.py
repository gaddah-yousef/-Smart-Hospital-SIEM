import asyncio
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from prometheus_client import start_http_server

from alerting.grafana_webhook import router as grafana_webhook_router
from api.alerts import ALERTS, router as alerts_router
from api.auth import router as auth_router
from api.events import router as events_router
from api.metrics import router as metrics_router
from ml.retrain_scheduler import start_retrain_scheduler

app = FastAPI(title="Smart Hospital Grafana SIEM", version="1.0.0")
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(events_router)
app.include_router(metrics_router)
app.include_router(grafana_webhook_router)

clients: Set[WebSocket] = set()


@app.on_event("startup")
async def startup():
    start_http_server(9101)
    start_retrain_scheduler()


@app.get("/health")
def health():
    return {"status": "ok", "service": "siem-backend"}


@app.get("/")
def root():
    return {"service": "Smart Hospital Grafana SIEM", "docs": "/docs", "metrics": ":9101/metrics"}


@app.websocket("/ws/alerts")
async def alerts_socket(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    cursor = len(ALERTS)
    try:
        while True:
            while cursor < len(ALERTS):
                await websocket.send_json(ALERTS[cursor])
                cursor += 1
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        clients.discard(websocket)
