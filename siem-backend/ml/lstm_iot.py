import os
import time
from pathlib import Path

import numpy as np
from prometheus_client import Gauge
from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.models import load_model

from mimir_client import MimirClient

LSTM_ERROR = Gauge(
    "hospital_ml_lstm_reconstruction_error",
    "LSTM reconstruction error per IoT device",
    ["device_id", "device_type"],
)


class LSTMIoTModel:
    def __init__(self, device_type: str, model_dir: str = "/app/ml/models"):
        self.device_type = device_type
        self.model_path = Path(model_dir) / f"lstm_{device_type.lower()}.h5"
        self.mimir = MimirClient(os.getenv("MIMIR_URL", "http://mimir:9009"))
        self.model = load_model(self.model_path) if self.model_path.exists() else self._build()
        self.threshold = 0.1

    def _build(self):
        model = Sequential(
            [
                Input(shape=(60, 4)),
                LSTM(128, return_sequences=True),
                Dropout(0.2),
                LSTM(64),
                Dense(4),
            ]
        )
        model.compile(optimizer="adam", loss="mse")
        return model

    def fetch_sequences(self) -> np.ndarray:
        end = int(time.time())
        start = end - 48 * 3600
        queries = [
            f'hospital_iot_heart_rate_bpm{{device_type="{self.device_type}"}}',
            f'hospital_iot_spo2_percent{{device_type="{self.device_type}"}}',
            f'hospital_iot_flow_rate_mlh{{device_type="{self.device_type}"}}',
            f'hospital_iot_anomaly_score{{device_type="{self.device_type}"}}',
        ]
        series = []
        for promql in queries:
            data = self.mimir.query_range(promql, start, end, "30s")
            values = []
            for result in data.get("data", {}).get("result", []):
                values.extend(float(v[1]) for v in result.get("values", []))
            series.append(values[:5760])
        width = min([len(s) for s in series if s] or [120])
        if width < 60:
            base = np.random.normal(0.2, 0.05, size=(120, 4))
        else:
            base = np.array([s[:width] for s in series], dtype=float).T
        windows = [base[i : i + 60] for i in range(0, len(base) - 60)]
        return np.array(windows if windows else [np.random.normal(0.2, 0.05, size=(60, 4))])

    def train(self) -> None:
        x = self.fetch_sequences()
        y = x[:, -1, :]
        self.model.fit(x, y, epochs=2, batch_size=32, verbose=0)
        pred = self.model.predict(x, verbose=0)
        errors = np.mean(np.square(pred - y), axis=1)
        self.threshold = float(errors.mean() + 2.5 * errors.std())
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(self.model_path)

    def score_latest(self, device_id: str = "unknown") -> float:
        x = self.fetch_sequences()[-1:]
        y = x[:, -1, :]
        pred = self.model.predict(x, verbose=0)
        error = float(np.mean(np.square(pred - y)))
        LSTM_ERROR.labels(device_id=device_id, device_type=self.device_type).set(error)
        return error


def retrain_all():
    results = {}
    for device_type in ["ECG", "PUMP", "VENTILATOR"]:
        model = LSTMIoTModel(device_type)
        model.train()
        results[device_type] = model.score_latest(device_type.lower())
    return results
