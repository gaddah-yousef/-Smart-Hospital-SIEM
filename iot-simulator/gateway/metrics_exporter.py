from prometheus_client import Gauge

HEART_RATE = Gauge(
    "hospital_iot_heart_rate_bpm",
    "ECG heart rate in beats per minute",
    ["device_id", "device_type", "ward"],
)
SPO2 = Gauge(
    "hospital_iot_spo2_percent",
    "ECG oxygen saturation percentage",
    ["device_id", "device_type", "ward"],
)
FLOW_RATE = Gauge(
    "hospital_iot_flow_rate_mlh",
    "Infusion pump flow rate in milliliters per hour",
    ["device_id", "device_type", "ward"],
)
VENT_PRESSURE = Gauge(
    "hospital_iot_pressure_cmh2o",
    "Ventilator pressure in centimeters of water",
    ["device_id", "device_type", "ward"],
)
RESP_RATE = Gauge(
    "hospital_iot_respiratory_rate_bpm",
    "Ventilator respiratory rate breaths per minute",
    ["device_id", "device_type", "ward"],
)
RADIATION_DOSE = Gauge(
    "hospital_iot_radiation_dose_mgy",
    "CT scanner radiation dose in milligray",
    ["device_id", "device_type", "ward"],
)
ANOMALY_SCORE = Gauge(
    "hospital_iot_anomaly_score",
    "IoT device anomaly score between 0 and 1",
    ["device_id", "device_type", "ward"],
)


def update_metrics(event: dict) -> None:
    labels = {
        "device_id": str(event.get("device_id", "unknown")),
        "device_type": str(event.get("device_type", "unknown")),
        "ward": str(event.get("ward", "unknown")),
    }
    if "heart_rate" in event:
        HEART_RATE.labels(**labels).set(float(event["heart_rate"]))
    if "spo2" in event:
        SPO2.labels(**labels).set(float(event["spo2"]))
    if "flow_rate" in event:
        FLOW_RATE.labels(**labels).set(float(event["flow_rate"]))
    if "pressure" in event:
        VENT_PRESSURE.labels(**labels).set(float(event["pressure"]))
    if "respiratory_rate" in event:
        RESP_RATE.labels(**labels).set(float(event["respiratory_rate"]))
    if "radiation_dose" in event:
        RADIATION_DOSE.labels(**labels).set(float(event["radiation_dose"]))
    ANOMALY_SCORE.labels(**labels).set(float(event.get("ml_anomaly_score", 0.0)))
