import os
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _default_dataset_path() -> str:
    downloads_dataset_dir = Path.home() / "Downloads" / "datasets"
    if downloads_dataset_dir.exists():
        return str(downloads_dataset_dir)
    return str(BASE_DIR / "dataset.csv")


def _default_model_artifact_path() -> str:
    artifacts_dir = BASE_DIR / "artifacts"
    candidates = []
    if artifacts_dir.exists():
        for item in artifacts_dir.iterdir():
            if (
                item.is_dir()
                and item.name.startswith("message_model")
                and "backup" not in item.name
                and (item / "config.json").exists()
            ):
                candidates.append(item)
    if candidates:
        def sort_key(path: Path) -> tuple[int, float]:
            match = re.search(r"stage(\d+)$", path.name)
            stage = int(match.group(1)) if match else 0
            return (stage, path.stat().st_mtime)

        candidates.sort(key=sort_key, reverse=True)
        return str(candidates[0])
    return str(artifacts_dir / "message_model")


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
    DATASET_PATH = os.getenv("DATASET_PATH", _default_dataset_path())
    MODEL_ARTIFACT_PATH = os.getenv(
        "MODEL_ARTIFACT_PATH",
        _default_model_artifact_path(),
    )
    MODEL_METRICS_PATH = os.getenv(
        "MODEL_METRICS_PATH",
        str(BASE_DIR / "artifacts" / "training_metrics.json"),
    )
    MODEL_ARTIFACT_URL = os.getenv("MODEL_ARTIFACT_URL", "").strip()
    MODEL_API_URL = os.getenv("MODEL_API_URL", "").strip()
    MODEL_API_TOKEN = os.getenv("MODEL_API_TOKEN", "").strip()
    MODEL_INFERENCE_TOKEN = os.getenv("MODEL_INFERENCE_TOKEN", "").strip()
    MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "auto").strip().lower()
    ENABLE_HEURISTIC_FALLBACK = os.getenv(
        "ENABLE_HEURISTIC_FALLBACK",
        "true",
    ).lower() == "true"
    TRANSFORMER_MODEL_NAME = os.getenv(
        "TRANSFORMER_MODEL_NAME",
        "distilbert-base-multilingual-cased",
    ).strip()
    TRANSFORMER_MAX_LENGTH = int(os.getenv("TRANSFORMER_MAX_LENGTH", "160"))
    TRANSFORMER_EPOCHS = int(os.getenv("TRANSFORMER_EPOCHS", "2"))
    TRANSFORMER_BATCH_SIZE = int(os.getenv("TRANSFORMER_BATCH_SIZE", "8"))
    TRAINING_MAX_ROWS_PER_LABEL = int(
        os.getenv("TRAINING_MAX_ROWS_PER_LABEL", "180")
    )
    TRAINING_MAX_ROWS_PER_SOURCE_LABEL = int(
        os.getenv("TRAINING_MAX_ROWS_PER_SOURCE_LABEL", "80")
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
