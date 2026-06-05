import os

import requests


def send_telegram(alert: dict) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or token.startswith("ChangeMe") or not chat_id or chat_id.startswith("ChangeMe"):
        return False
    text = f"[{alert.get('severity','UNKNOWN')}] {alert.get('rule','siem_alert')} from {alert.get('source_ip','unknown')}"
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )
    return response.ok
