from apscheduler.schedulers.background import BackgroundScheduler

from ml.isolation_forest import IsolationForestModel, retrain_and_score
from ml.lstm_iot import LSTMIoTModel, retrain_all


def score_isolation_only() -> None:
    """Re-score les IPs avec le modele Isolation Forest deja entraine.
    Pas de re-entrainement (rapide), juste l inference + push gauge Mimir.
    """
    try:
        model = IsolationForestModel()
        if model.model is None:
            model.train()
        model.score()
    except Exception as exc:
        print(f"[ML-SCORE] isolation_forest score error: {exc}", flush=True)


def score_lstm_only() -> None:
    """Re-score chaque type de device IoT avec le LSTM existant."""
    for device_type in ["ECG", "PUMP", "VENTILATOR"]:
        try:
            m = LSTMIoTModel(device_type)
            m.score_latest(device_type.lower())
        except Exception as exc:
            print(f"[ML-SCORE] lstm {device_type} score error: {exc}", flush=True)


def start_retrain_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    # --- Re-entrainement (couteux, peu frequent) ---
    scheduler.add_job(retrain_and_score, "interval", hours=24,
                      id="isolation_forest_retrain_24h", replace_existing=True)
    scheduler.add_job(retrain_all, "interval", days=7,
                      id="lstm_iot_retrain_7d", replace_existing=True)

    # --- Scoring frequent (rapide, temps reel) ---
    # Re-score Isolation Forest toutes les 60 secondes pour voir les attaques
    # en quelques secondes dans le dashboard ML.
    scheduler.add_job(score_isolation_only, "interval", seconds=60,
                      id="isolation_forest_score_1m", replace_existing=True,
                      next_run_time=None, max_instances=1, coalesce=True)
    # Re-score LSTM toutes les 2 minutes
    scheduler.add_job(score_lstm_only, "interval", seconds=120,
                      id="lstm_score_2m", replace_existing=True,
                      max_instances=1, coalesce=True)

    scheduler.start()
    # Premier scoring immediat au demarrage pour ne pas attendre 60s
    try:
        score_isolation_only()
    except Exception:
        pass
    return scheduler
