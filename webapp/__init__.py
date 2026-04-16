from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from config import Config
from ml.train import train_and_save

from .api import api_bp
from .auth import auth_bp
from .child import child_bp
from .extensions import db, login_manager
from .models import MessageRecord
from .parent import parent_bp


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

    with app.app_context():
        db.create_all()

    @app.cli.command("train-models")
    def train_models_command() -> None:
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
        )
        print("Training complete.")
        print(f"Linear accuracy: {metrics['linear_accuracy']:.3f}")
        print(f"Random forest accuracy: {metrics['random_forest_accuracy']:.3f}")
        print(f"Ensemble accuracy: {metrics['ensemble_accuracy']:.3f}")

    return app
