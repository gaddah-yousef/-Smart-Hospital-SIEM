import json
import os
import random
import time
from dataclasses import dataclass

import paho.mqtt.client as mqtt


@dataclass
class CTScanner:
    device_id: str
    ward: str
    topic: str = "hospital/iot/scanner"

    def reading(self) -> dict:
        anomalous = random.random() < 0.03
        dose = random.uniform(2, 10) if not anomalous else random.uniform(45, 80)
        score = random.uniform(0.02, 0.18) if not anomalous else random.uniform(0.9, 0.99)
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "job": "iot-gateway",
            "env": os.getenv("ENVIRONMENT", "production"),
            "event_type": "IoT_ANOMALY" if anomalous else "IOT_READING",
            "severity": "EMERGENCY" if anomalous else "INFO",
            "source_ip": self.device_id,
            "hospital": os.getenv("HOSPITAL_NAME", "CHU-Rabat"),
            "device_id": self.device_id,
            "device_type": "SCANNER",
            "ward": self.ward,
            "radiation_dose": round(dose, 2),
            "ml_anomaly_score": round(score, 4),
        }

    def run(self, client: mqtt.Client, interval: float = 12.0) -> None:
        while True:
            client.publish(self.topic, json.dumps(self.reading(), separators=(",", ":")))
            time.sleep(interval)
