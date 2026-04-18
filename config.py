import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("mysql://"):
        return raw_url.replace("mysql://", "mysql+pymysql://", 1)
    if raw_url.startswith("mysql+mysqldb://"):
        return raw_url.replace("mysql+mysqldb://", "mysql+pymysql://", 1)
    return raw_url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://cyber_mzazi:cyber_mzazi@localhost:3306/cyber_mzazi",
        )
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
    APP_BASE_URL = os.getenv("APP_BASE_URL", "").rstrip("/")
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    ANDROID_COMPANION_DOWNLOAD_URL = os.getenv("ANDROID_COMPANION_DOWNLOAD_URL", "")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    MYSQL_SSL_CA_PATH = os.getenv("MYSQL_SSL_CA_PATH", "")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "").strip()
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "").strip()
    EMAIL_VERIFICATION_MAX_AGE = int(
        os.getenv("EMAIL_VERIFICATION_MAX_AGE", "86400")
    )
    ALERT_EMAIL_ENABLED = os.getenv("ALERT_EMAIL_ENABLED", "true").lower() == "true"
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"connect_args": {"ssl": {"ca": MYSQL_SSL_CA_PATH}}}
        if MYSQL_SSL_CA_PATH
        else {}
    )
