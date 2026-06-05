import json
import os
import time
from typing import Any

from confluent_kafka import Producer


TOPIC_MAP = {
    "LOGIN_FAILED": "hospital.auth.events",
    "LOGIN_SUCCESS": "hospital.auth.events",
    "PATIENT_ACCESS": "hospital.patient.access",
    "UNAUTHORIZED_ACCESS": "hospital.patient.access",
    "FILE_ACCESS": "hospital.api.events",
    "API_HEALTH": "hospital.api.events",
}


class KafkaLogProducer:
    def __init__(self):
        self.producer = Producer(
            {
                "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
                "client.id": "hospital-api-log-producer",
                "linger.ms": 20,
            }
        )

    def publish(self, event: dict[str, Any]) -> None:
        topic = TOPIC_MAP.get(event.get("event_type", ""), "hospital.api.events")
        payload = json.dumps(event, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self.producer.produce(topic, key=str(event.get("source_ip", "unknown")), value=payload)
        self.producer.poll(0)

    def flush(self) -> None:
        self.producer.flush(5)


def base_event(event_type: str, severity: str, source_ip: str, **fields: Any) -> dict[str, Any]:
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "job": "hospital-api",
        "env": os.getenv("ENVIRONMENT", "production"),
        "event_type": event_type,
        "severity": severity,
        "source_ip": source_ip,
        "hospital": os.getenv("HOSPITAL_NAME", "CHU-Rabat"),
    }
    event.update(fields)
    return event
