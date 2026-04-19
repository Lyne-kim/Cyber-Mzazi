from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from config import Config
from ml.labels import SUPPORTED_LABELS, label_title, label_tone

from .api import api_bp
from .auth import auth_bp
from .child import child_bp
from .extensions import db, login_manager
from .models import MessageRecord
from .parent import parent_bp
from .ui_text import SUPPORTED_LANGUAGES, get_language, t


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}},
        supports_credentials=True,
    )

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(child_bp)

    @app.context_processor
    def inject_ui_helpers() -> dict:
        return {
            "t": t,
            "ui_language": get_language(),
            "supported_languages": SUPPORTED_LANGUAGES,
            "review_labels": SUPPORTED_LABELS,
            "label_title": label_title,
            "label_tone": label_tone,
        }

    @app.cli.command("train-models")
    def train_models_command() -> None:
        from ml.train import train_and_save

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

        metrics = train_and_save(
            app.config["DATASET_PATH"],
            app.config["MODEL_ARTIFACT_PATH"],
            app.config["MODEL_METRICS_PATH"],
            feedback_rows=feedback_rows,
            model_name=app.config["TRANSFORMER_MODEL_NAME"],
            epochs=app.config["TRANSFORMER_EPOCHS"],
            batch_size=app.config["TRANSFORMER_BATCH_SIZE"],
            max_length=app.config["TRANSFORMER_MAX_LENGTH"],
            max_rows_per_label=app.config["TRAINING_MAX_ROWS_PER_LABEL"],
            max_rows_per_source_label=app.config["TRAINING_MAX_ROWS_PER_SOURCE_LABEL"],
        )
        print("Training complete.")
        print(f"Validation accuracy: {metrics['validation_accuracy']:.3f}")
        print(f"Validation macro F1: {metrics['validation_macro_f1']:.3f}")

    return app
