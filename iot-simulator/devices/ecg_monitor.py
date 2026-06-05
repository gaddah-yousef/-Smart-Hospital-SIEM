import json
import os
import random
import time
from dataclasses import dataclass

import paho.mqtt.client as mqtt


@dataclass
class ECGMonitor:
    device_id: str
    ward: str
    topic: str = "hospital/iot/ecg"

    def reading(self) -> dict:
        anomalous = random.random() < 0.06
        heart_rate = random.randint(45, 75) if not anomalous else random.choice([random.randint(181, 220), random.randint(25, 38)])
        spo2 = random.randint(95, 100) if not anomalous else random.randint(65, 79)
        score = random.uniform(0.05, 0.25) if not anomalous else random.uniform(0.86, 0.99)
        severity = "EMERGENCY" if anomalous else "INFO"
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "job": "iot-gateway",
            "env": os.getenv("ENVIRONMENT", "production"),
            "event_type": "IoT_ANOMALY" if anomalous else "IOT_READING",
            "severity": severity,
            "source_ip": self.device_id,
            "hospital": os.getenv("HOSPITAL_NAME", "CHU-Rabat"),
            "device_id": self.device_id,
            "device_type": "ECG",
            "ward": self.ward,
            "heart_rate": heart_rate,
            "spo2": spo2,
            "ml_anomaly_score": round(score, 4),
        }

    def run(self, client: mqtt.Client, interval: float = 5.0) -> None:
        while True:
            client.publish(self.topic, json.dumps(self.reading(), separators=(",", ":")))
            time.sleep(interval)


if __name__ == "__main__":
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ecg-monitor-standalone")
    mqtt_client.connect(os.getenv("MQTT_HOST", "localhost"), int(os.getenv("MQTT_PORT", "1883")), 60)
    ECGMonitor("ECG-ICU-01", "ICU").run(mqtt_client)
