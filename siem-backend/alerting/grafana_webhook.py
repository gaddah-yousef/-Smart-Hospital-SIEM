from fastapi import APIRouter

from api.alerts import ALERTS

router = APIRouter(prefix="/webhooks/grafana", tags=["grafana-webhook"])


@router.post("")
async def receive_grafana_alert(payload: dict):
    for alert in payload.get("alerts", []):
        ALERTS.append(
            {
                "alert_id": alert.get("fingerprint"),
                "rule": alert.get("labels", {}).get("alertname", "grafana_alert"),
                "severity": alert.get("labels", {}).get("severity", "unknown"),
                "source": "grafana",
                "status": alert.get("status", "firing"),
                "payload": alert,
            }
        )
    return {"accepted": True, "count": len(payload.get("alerts", []))}
