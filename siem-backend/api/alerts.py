from fastapi import APIRouter, Depends

from api.auth import require_role

router = APIRouter(prefix="/alerts", tags=["alerts"])
ALERTS: list[dict] = []


@router.get("")
def list_alerts(user: dict = Depends(require_role("Admin", "Analyst", "Viewer"))):
    return {"alerts": ALERTS[-200:], "count": len(ALERTS)}


@router.post("")
def create_alert(alert: dict, user: dict = Depends(require_role("Admin", "Analyst"))):
    ALERTS.append(alert)
    return {"created": True, "alert": alert}


@router.patch("/{alert_id}/ack")
def acknowledge_alert(alert_id: str, user: dict = Depends(require_role("Admin", "Analyst"))):
    for alert in ALERTS:
        if str(alert.get("alert_id")) == alert_id:
            alert["status"] = "acknowledged"
            alert["acknowledged_by"] = user["username"]
            return {"updated": True, "alert": alert}
    return {"updated": False, "reason": "alert not found"}
