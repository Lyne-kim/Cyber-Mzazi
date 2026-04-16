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
        print("Database tables are ready.")

        artifact_path = Path(app.config["MODEL_ARTIFACT_PATH"])
        force_retrain = os.getenv("FORCE_MODEL_RETRAIN", "false").lower() == "true"
        if artifact_path.exists() and not force_retrain:
            print("Model artifact already exists. Skipping retraining.")
            return

        metrics = train_and_save(
            app.config["DATASET_PATH"],
            app.config["MODEL_ARTIFACT_PATH"],
            app.config["MODEL_METRICS_PATH"],
            feedback_rows=collect_feedback_rows(),
        )
        print(
            "Model training complete. "
            f"Ensemble accuracy: {metrics['ensemble_accuracy']:.3f}"
        )


if __name__ == "__main__":
    main()
