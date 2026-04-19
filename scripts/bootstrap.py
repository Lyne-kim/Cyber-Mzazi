from __future__ import annotations

import os
from pathlib import Path
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from app import app
from ml.artifacts import transformer_artifact_exists
from ml.train import train_and_save
from webapp.extensions import db
from webapp.models import MessageRecord
from webapp.services.schema import ensure_runtime_schema


def collect_feedback_rows() -> list[dict]:
    feedback_rows = []
    reviewed_messages = MessageRecord.query.filter(
        MessageRecord.reviewed_label.isnot(None)
    ).all()
    for message in reviewed_messages:
        feedback_rows.append(
            {
                "text": message.message_text,
                "risk_indicators": message.risk_indicators,
                "threat_type": message.reviewed_label,
                "language": "mixed",
            }
        )
    return feedback_rows


def main() -> None:
    with app.app_context():
        ensure_runtime_schema()
        print("Database tables are ready.", flush=True)

        artifact_path = Path(app.config["MODEL_ARTIFACT_PATH"])
        force_retrain = os.getenv("FORCE_MODEL_RETRAIN", "false").lower() == "true"
        if transformer_artifact_exists(artifact_path) and not force_retrain:
            print("Model artifact already exists. Skipping retraining.", flush=True)
            return

        if not transformer_artifact_exists(artifact_path) and not force_retrain:
            print(
                "Model artifact is missing. Skipping bootstrap retraining so the web "
                "service can start. Commit the artifact files or set "
                "FORCE_MODEL_RETRAIN=true for a one-time rebuild.",
                flush=True,
            )
            return

        metrics = train_and_save(
            app.config["DATASET_PATH"],
            app.config["MODEL_ARTIFACT_PATH"],
            app.config["MODEL_METRICS_PATH"],
            feedback_rows=collect_feedback_rows(),
            model_name=app.config["TRANSFORMER_MODEL_NAME"],
            epochs=app.config["TRANSFORMER_EPOCHS"],
            batch_size=app.config["TRANSFORMER_BATCH_SIZE"],
            max_length=app.config["TRANSFORMER_MAX_LENGTH"],
            max_rows_per_label=app.config["TRAINING_MAX_ROWS_PER_LABEL"],
            max_rows_per_source_label=app.config["TRAINING_MAX_ROWS_PER_SOURCE_LABEL"],
        )
        print(
            "Model training complete. "
            f"Validation accuracy: {metrics['validation_accuracy']:.3f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
