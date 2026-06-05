import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from confluent_kafka import Producer
from prometheus_client import start_http_server

sys.path.append(str(Path(__file__).resolve().parents[1]))

from devices.ct_scanner import CTScanner
from devices.ecg_monitor import ECGMonitor
from devices.infusion_pump import InfusionPump
from devices.ventilator import Ventilator
from gateway.metrics_exporter import update_metrics

LOG_PATH = Path("/var/log/hospital/iot_gateway.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("iot-gateway")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_PATH)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.propagate = False

TOPIC_MAP = {
    "hospital/iot/ecg": "hospital.iot.ecg",
    "hospital/iot/pump": "hospital.iot.pump",
    "hospital/iot/ventilator": "hospital.iot.ventilator",
    "hospital/iot/scanner": "hospital.iot.scanner",
}

producer = Producer(
    {
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        "client.id": "iot-mqtt-to-kafka",
        "linger.ms": 20,
    }
)


def write_log(event: dict) -> None:
    logger.info(json.dumps(event, separators=(",", ":"), sort_keys=True))


def on_connect(client, userdata, flags, reason_code, properties=None):
    client.subscribe("hospital/iot/#", qos=0)


def on_message(client, userdata, msg):
    event = json.loads(msg.payload.decode("utf-8"))
    event.setdefault("job", "iot-gateway")
    event.setdefault("env", os.getenv("ENVIRONMENT", "production"))
    event.setdefault("hospital", os.getenv("HOSPITAL_NAME", "CHU-Rabat"))
    event.setdefault("source_ip", event.get("device_id", "unknown"))
    write_log(event)
    update_metrics(event)
    kafka_topic = TOPIC_MAP.get(msg.topic, "hospital.iot.scanner")
    producer.produce(kafka_topic, key=str(event.get("device_id", "unknown")), value=json.dumps(event).encode("utf-8"))
    producer.poll(0)


def start_device_threads(client: mqtt.Client) -> None:
    devices = [
        ECGMonitor("ECG-ICU-01", "ICU"),
        ECGMonitor("ECG-CARD-02", "Cardiology"),
        InfusionPump("PUMP-ICU-01", "ICU"),
        Ventilator("VENT-ICU-01", "ICU"),
        CTScanner("CT-RAD-01", "Radiology"),
    ]
    for device in devices:
        thread = threading.Thread(target=device.run, args=(client,), daemon=True)
        thread.start()


def main():
    start_http_server(9090)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="iot-gateway")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(os.getenv("MQTT_HOST", "mosquitto"), int(os.getenv("MQTT_PORT", "1883")), 60)
    client.loop_start()
    time.sleep(2)
    start_device_threads(client)
    while True:
        producer.flush(1)
        time.sleep(1)


if __name__ == "__main__":
    main()
