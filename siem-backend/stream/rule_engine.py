import json
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path

import threading

import yaml
from confluent_kafka import Producer
from prometheus_client import Counter

from alerting.email_notifier import send_email
from alerting.telegram_notifier import send_telegram
from loki_client import LokiClient
from stream.correlator import SlidingCorrelator


def _async_notify(alert: dict) -> None:
    """Envoi email + telegram dans un thread daemon — ne bloque pas Faust."""
    try:
        send_telegram(alert)
    except Exception as exc:
        print(f"[notify] telegram error: {exc}", flush=True)
    try:
        send_email(alert)
    except Exception as exc:
        print(f"[notify] email error: {exc}", flush=True)

ALERT_COUNTER = Counter(
    "hospital_siem_alert_total",
    "Total generated SIEM alerts",
    ["rule", "severity", "hospital"],
)


class RuleEngine:
    def __init__(self, rules_dir: str = "/app/detection-rules"):
        self.rules_dir = Path(rules_dir)
        self.rules = self._load_rules()
        self.failed_logins: dict[str, deque[float]] = defaultdict(deque)
        self.correlator = SlidingCorrelator()
        self.producer = Producer({"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")})
        self.loki = LokiClient(os.getenv("LOKI_URL", "http://loki:3100"))

    def _load_rules(self) -> dict[str, dict]:
        rules = {}
        for path in sorted(self.rules_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            rules[data["rule"]] = data
        return rules

    def evaluate(self, event: dict) -> list[dict]:
        if not isinstance(event, dict):
            return []
        self.correlator.add(event)
        alerts: list[dict] = []
        event_type = event.get("event_type")
        source_ip = str(event.get("source_ip", "unknown"))
        now = time.time()

        if event_type == "LOGIN_FAILED":
            window = self.failed_logins[source_ip]
            window.append(now)
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= 5:
                alerts.append(self._alert("brute_force_login", event, count=len(window)))
                window.clear()

        if event_type == "UNAUTHORIZED_ACCESS":
            alerts.append(self._alert("unauthorized_patient_access", event))

        if self._is_iot_critical(event):
            alerts.append(self._alert("iot_critical_anomaly", event))

        if len(self.correlator.distinct_services(source_ip, 120)) >= 4:
            alerts.append(self._alert("lateral_movement", event, distinct_services=len(self.correlator.distinct_services(source_ip, 120))))

        file_count = int(event.get("file_access_count", 0) or 0)
        ratio = self.correlator.outbound_baseline_ratio(source_ip, 10)
        if file_count > 100 and ratio > 3:
            alerts.append(self._alert("ransomware_pattern", event, outbound_ratio=round(ratio, 2)))

        for alert in alerts:
            self.publish_alert(alert)
        return alerts

    def _is_iot_critical(self, event: dict) -> bool:
        return (
            float(event.get("ml_anomaly_score", 0.0) or 0.0) > 0.85
            or float(event.get("heart_rate", 0.0) or 0.0) > 180
            or (event.get("spo2") is not None and float(event.get("spo2", 100.0)) < 80)
        )

    def _alert(self, rule_name: str, event: dict, **extra) -> dict:
        rule = self.rules.get(rule_name, {})
        alert = {
            "alert_id": str(uuid.uuid4()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "job": "siem-backend",
            "env": os.getenv("ENVIRONMENT", "production"),
            "event_type": "SIEM_ALERT",
            "severity": rule.get("severity", "HIGH"),
            "source_ip": str(event.get("source_ip", "unknown")),
            "hospital": os.getenv("HOSPITAL_NAME", "CHU-Rabat"),
            "rule": rule_name,
            "mitre": rule.get("mitre"),
            "loki_label": rule.get("loki_label", rule_name),
            "matched_event": event,
        }
        alert.update(extra)
        return alert

    def publish_alert(self, alert: dict) -> None:
        rule_label = alert["rule"].replace("_login", "").replace("_pattern", "")
        ALERT_COUNTER.labels(rule=rule_label, severity=alert["severity"], hospital=alert["hospital"]).inc()
        payload = json.dumps(alert, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self.producer.produce("hospital.alerts.siem", key=alert["source_ip"], value=payload)
        self.producer.flush(1)
        self.loki.push(
            {
                "job": "siem-backend",
                "env": alert["env"],
                "event_type": "SIEM_ALERT",
                "severity": alert["severity"],
                "source_ip": alert["source_ip"],
                "hospital": alert["hospital"],
                "rule": alert["rule"],
            },
            alert,
        )
        # Notifications externes lances en thread daemon pour ne pas bloquer
        # la boucle async de Faust (sinon process_api/etc se figent).
        threading.Thread(target=_async_notify, args=(alert,), daemon=True).start()
