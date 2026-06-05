import json
import os
import random
import time
from dataclasses import dataclass

import paho.mqtt.client as mqtt


@dataclass
class Ventilator:
    device_id: str
    ward: str
    topic: str = "hospital/iot/ventilator"

    def reading(self) -> dict:
        anomalous = random.random() < 0.04
        pressure = random.uniform(16, 28) if not anomalous else random.uniform(35, 50)
        resp = random.randint(12, 20) if not anomalous else random.choice([random.randint(4, 8), random.randint(32, 45)])
        score = random.uniform(0.04, 0.22) if not anomalous else random.uniform(0.88, 0.99)
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "job": "iot-gateway",
            "env": os.getenv("ENVIRONMENT", "production"),
            "event_type": "IoT_ANOMALY" if anomalous else "IOT_READING",
            "severity": "EMERGENCY" if anomalous else "INFO",
            "source_ip": self.device_id,
            "hospital": os.getenv("HOSPITAL_NAME", "CHU-Rabat"),
            "device_id": self.device_id,
            "device_type": "VENTILATOR",
            "ward": self.ward,
            "pressure": round(pressure, 2),
            "respiratory_rate": resp,
            "ml_anomaly_score": round(score, 4),
        }

    def run(self, client: mqtt.Client, interval: float = 7.0) -> None:
        while True:
            client.publish(self.topic, json.dumps(self.reading(), separators=(",", ":")))
            time.sleep(interval)
