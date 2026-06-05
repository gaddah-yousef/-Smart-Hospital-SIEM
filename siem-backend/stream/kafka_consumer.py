import json

import faust
from prometheus_client import start_http_server

from stream.rule_engine import RuleEngine

app = faust.App(
    "hospital-siem-stream",
    broker="kafka://kafka:9092",
    store="memory://",
    topic_partitions=1,
)

# Decodage JSON manuel via value_type=bytes pour robustesse multi-version Faust.
auth_events = app.topic("hospital.auth.events", value_type=bytes)
patient_events = app.topic("hospital.patient.access", value_type=bytes)
api_events = app.topic("hospital.api.events", value_type=bytes)
iot_ecg = app.topic("hospital.iot.ecg", value_type=bytes)
iot_pump = app.topic("hospital.iot.pump", value_type=bytes)
iot_ventilator = app.topic("hospital.iot.ventilator", value_type=bytes)
iot_scanner = app.topic("hospital.iot.scanner", value_type=bytes)
network_zeek = app.topic("hospital.network.zeek", value_type=bytes)

engine = RuleEngine()
start_http_server(9102)


def _decode(value):
    """Decode bytes -> dict en gerant les erreurs de format."""
    try:
        if isinstance(value, bytes):
            return json.loads(value.decode("utf-8"))
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, dict):
            return value
    except Exception as exc:
        print(f"[kafka_consumer] decode error: {exc}", flush=True)
    return None


@app.agent(auth_events)
async def process_auth(stream):
    async for raw in stream:
        event = _decode(raw)
        if event:
            engine.evaluate(event)


@app.agent(patient_events)
async def process_patient(stream):
    async for raw in stream:
        event = _decode(raw)
        if event:
            engine.evaluate(event)


@app.agent(api_events)
async def process_api(stream):
    async for raw in stream:
        event = _decode(raw)
        if event:
            engine.evaluate(event)


@app.agent(iot_ecg)
async def process_ecg(stream):
    async for raw in stream:
        event = _decode(raw)
        if event:
            engine.evaluate(event)


@app.agent(iot_pump)
async def process_pump(stream):
    async for raw in stream:
        event = _decode(raw)
        if event:
            engine.evaluate(event)


@app.agent(iot_ventilator)
async def process_ventilator(stream):
    async for raw in stream:
        event = _decode(raw)
        if event:
            engine.evaluate(event)


@app.agent(iot_scanner)
async def process_scanner(stream):
    async for raw in stream:
        event = _decode(raw)
        if event:
            engine.evaluate(event)


@app.agent(network_zeek)
async def process_network(stream):
    async for raw in stream:
        event = _decode(raw)
        if event:
            engine.evaluate(event)


if __name__ == "__main__":
    app.main()
