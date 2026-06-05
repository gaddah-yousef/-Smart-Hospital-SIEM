import json
import os
import random
import time
from dataclasses import dataclass

import paho.mqtt.client as mqtt


@dataclass
class InfusionPump:
    device_id: str
    ward: str
    topic: str = "hospital/iot/pump"

    def reading(self) -> dict:
        anomalous = random.random() < 0.05
        flow_rate = random.uniform(40, 90) if not anomalous else random.choice([random.uniform(0, 5), random.uniform(180, 260)])
        score = random.uniform(0.03, 0.20) if not anomalous else random.uniform(0.87, 0.98)
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "job": "iot-gateway",
            "env": os.getenv("ENVIRONMENT", "production"),
            "event_type": "IoT_ANOMALY" if anomalous else "IOT_READING",
            "severity": "EMERGENCY" if anomalous else "INFO",
            "source_ip": self.device_id,
            "hospital": os.getenv("HOSPITAL_NAME", "CHU-Rabat"),
            "device_id": self.device_id,
            "device_type": "PUMP",
            "ward": self.ward,
            "flow_rate": round(flow_rate, 2),
            "ml_anomaly_score": round(score, 4),
        }

    def run(self, client: mqtt.Client, interval: float = 6.0) -> None:
        while True:
            client.publish(self.topic, json.dumps(self.reading(), separators=(",", ":")))
            time.sleep(interval)
