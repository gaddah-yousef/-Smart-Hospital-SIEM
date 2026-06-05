import argparse
import json
import os
import time

import paho.mqtt.client as mqtt


def main():
    parser = argparse.ArgumentParser(description="Publish an emergency IoT anomaly over MQTT.")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--device-id", default="ECG-ICU-CRITICAL")
    args = parser.parse_args()

    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "job": "iot-gateway",
        "env": "production",
        "event_type": "IoT_ANOMALY",
        "severity": "EMERGENCY",
        "source_ip": args.device_id,
        "hospital": "CHU-Rabat",
        "device_id": args.device_id,
        "device_type": "ECG",
        "ward": "ICU",
        "heart_rate": 205,
        "spo2": 72,
        "ml_anomaly_score": 0.97,
    }
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="attack-sim-iot-critical")
    client.connect(args.host, args.port, 60)
    client.publish("hospital/iot/ecg", json.dumps(event, separators=(",", ":")))
    client.disconnect()
    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    main()
