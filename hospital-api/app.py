import json
import logging
import os
import random
import time
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from log_producer import KafkaLogProducer, base_event
from tracing import configure_tracing, hash_patient_id

LOG_PATH = Path("/var/log/hospital/hospital_security.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("hospital-security")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_PATH)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.propagate = False

app = Flask(__name__)
tracer = configure_tracing(app)
producer = KafkaLogProducer()

USERS = {
    "admin": {"password": generate_password_hash("admin123"), "role": "Admin"},
    "doctor": {"password": generate_password_hash("doctor123"), "role": "Clinician"},
    "nurse": {"password": generate_password_hash("nurse123"), "role": "Nurse"},
    "billing": {"password": generate_password_hash("billing123"), "role": "Billing"},
}

PATIENTS = {
    "P-1001": {"name": "Redacted Alpha", "ward": "ICU", "risk": "high"},
    "P-1002": {"name": "Redacted Beta", "ward": "Cardiology", "risk": "medium"},
    "P-1003": {"name": "Redacted Gamma", "ward": "Radiology", "risk": "low"},
}


def source_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or request.remote_addr or "0.0.0.0"


def write_event(event: dict) -> None:
    logger.info(json.dumps(event, separators=(",", ":"), sort_keys=True))
    producer.publish(event)


@app.get("/health")
def health():
    event = base_event("API_HEALTH", "INFO", source_ip(), endpoint="/health")
    write_event(event)
    return jsonify({"status": "ok", "service": "hospital-api"})


@app.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", ""))
    password = str(body.get("password", ""))
    user = USERS.get(username)
    ok = bool(user and check_password_hash(user["password"], password))
    event_type = "LOGIN_SUCCESS" if ok else "LOGIN_FAILED"
    severity = "INFO" if ok else "HIGH"
    with tracer.start_as_current_span("hospital.login") as span:
        span.set_attribute("hospital.service", "hospital-api")
        span.set_attribute("hospital.patient_id", hash_patient_id(None))
        span.set_attribute("hospital.event_type", event_type)
        event = base_event(
            event_type,
            severity,
            source_ip(),
            username=username or "unknown",
            user_agent=request.headers.get("User-Agent", "unknown"),
            endpoint="/login",
            auth_result="success" if ok else "failure",
        )
        write_event(event)
    status = 200 if ok else 401
    return jsonify({"authenticated": ok, "role": user["role"] if ok else None}), status


@app.get("/patients/<patient_id>")
def patient_record(patient_id: str):
    username = request.headers.get("X-User", "anonymous")
    role = USERS.get(username, {}).get("role", "Unknown")
    authorized = role in {"Admin", "Clinician", "Nurse"}
    event_type = "PATIENT_ACCESS" if authorized else "UNAUTHORIZED_ACCESS"
    severity = "INFO" if authorized else "CRITICAL"
    with tracer.start_as_current_span("hospital.patient_access") as span:
        span.set_attribute("hospital.service", "hospital-api")
        span.set_attribute("hospital.patient_id", hash_patient_id(patient_id))
        span.set_attribute("hospital.event_type", event_type)
        event = base_event(
            event_type,
            severity,
            source_ip(),
            username=username,
            role=role,
            endpoint=f"/patients/{patient_id}",
            patient_id_hash=hash_patient_id(patient_id),
            action="read",
        )
        write_event(event)
    if not authorized:
        return jsonify({"error": "access denied"}), 403
    return jsonify(PATIENTS.get(patient_id, {"name": "Unknown", "ward": "Unknown", "risk": "unknown"}))


@app.post("/simulate/file-access")
def simulate_file_access():
    body = request.get_json(silent=True) or {}
    count = int(body.get("count", random.randint(1, 30)))
    outbound_bytes = int(body.get("outbound_bytes", random.randint(1000, 100000)))
    event = base_event(
        "FILE_ACCESS",
        "HIGH" if count > 100 else "INFO",
        source_ip(),
        endpoint="/simulate/file-access",
        file_access_count=count,
        outbound_bytes=outbound_bytes,
        baseline_outbound_bytes=30000,
        username=str(body.get("username", "workstation-service")),
    )
    write_event(event)
    return jsonify({"accepted": True, "event": event})


@app.get("/audit/recent")
def audit_recent():
    lines = LOG_PATH.read_text(encoding="utf-8").splitlines()[-50:] if LOG_PATH.exists() else []
    return jsonify([json.loads(line) for line in lines if line.strip()])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
