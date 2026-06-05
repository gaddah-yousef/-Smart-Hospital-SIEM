import json
import os
import smtplib
from email.message import EmailMessage


def send_email(alert: dict) -> bool:
    """Envoi d alerte SIEM par email.

    Lit les parametres SMTP depuis l environnement (.env).
    Retourne False si SMTP n est pas configure (ChangeMe_*) pour eviter
    de casser le pipeline d alerte quand le serveur mail n est pas pret.
    """
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", user)
    recipient = os.getenv("SMTP_TO", "yousef.gaddah@enim.ac.ma")

    if not host or not user or password.startswith("ChangeMe") or user.startswith("ChangeMe"):
        return False

    msg = EmailMessage()
    msg["Subject"] = (
        f"[Smart Hospital SIEM] {alert.get('severity','UNKNOWN')} - "
        f"{alert.get('rule','siem_alert')} from {alert.get('source_ip','unknown')}"
    )
    msg["From"] = sender
    msg["To"] = recipient

    body = (
        "ALERTE SIEM Smart Hospital\n"
        "==========================\n"
        f"Hopital    : {alert.get('hospital','CHU-Rabat')}\n"
        f"Regle      : {alert.get('rule','unknown')}\n"
        f"Severite   : {alert.get('severity','UNKNOWN')}\n"
        f"Source IP  : {alert.get('source_ip','unknown')}\n"
        f"MITRE      : {alert.get('mitre','-')}\n"
        f"Horodatage : {alert.get('timestamp','-')}\n"
        f"Alert ID   : {alert.get('alert_id','-')}\n\n"
        "Evenement declencheur :\n"
        f"{json.dumps(alert.get('matched_event', {}), indent=2, ensure_ascii=False)}\n\n"
        "Voir Grafana : http://localhost:3000/alerting/list\n"
    )
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        print(f"[email_notifier] echec envoi a {recipient}: {exc}")
        return False
