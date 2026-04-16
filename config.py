import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://cyber_mzazi:cyber_mzazi@localhost:3306/cyber_mzazi",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATASET_PATH = os.getenv("DATASET_PATH", str(BASE_DIR / "dataset.csv"))
    MODEL_ARTIFACT_PATH = os.getenv(
        "MODEL_ARTIFACT_PATH",
        str(BASE_DIR / "artifacts" / "message_model.joblib"),
    )
    MODEL_METRICS_PATH = os.getenv(
        "MODEL_METRICS_PATH",
        str(BASE_DIR / "artifacts" / "training_metrics.json"),
    )
    WEB_VERIFIER_URL = os.getenv("WEB_VERIFIER_URL", "")
    WEB_VERIFIER_TOKEN = os.getenv("WEB_VERIFIER_TOKEN", "")
    LOGOUT_REQUEST_EXPIRY_MINUTES = int(
        os.getenv("LOGOUT_REQUEST_EXPIRY_MINUTES", "30")
    )
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
