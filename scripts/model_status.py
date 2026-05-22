from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ModuleNotFoundError:
    _load_env_file(PROJECT_ROOT / ".env")

from config import Config
from ml.labels import SUPPORTED_LABELS


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _format_time(path: Path) -> str:
    if not path.exists():
        return "missing"
    modified_at = datetime.fromtimestamp(path.stat().st_mtime)
    return modified_at.strftime("%Y-%m-%d %H:%M:%S")


def _print_list(title: str, values: list[str]) -> None:
    print(f"\n{title}")
    for value in values:
        print(f"  - {value}")


def main() -> None:
    artifact_path = Path(Config.MODEL_ARTIFACT_PATH)
    metrics_path = Path(Config.MODEL_METRICS_PATH)
    metadata_path = artifact_path / "metadata.json"

    metrics = _load_json(metrics_path)
    metadata = _load_json(metadata_path)
    classes = metadata.get("classes") or metrics.get("classes") or []
    history = metrics.get("history") or []
    configured_dataset_path = Path(Config.DATASET_PATH)
    trained_dataset_path = Path(metrics.get("dataset_path", Config.DATASET_PATH))

    print("Cyber Mzazi Model Status")
    print("========================")
    print(f"Configured dataset path: {configured_dataset_path}")
    print(f"Configured dataset exists: {'yes' if configured_dataset_path.exists() else 'no'}")
    print(f"Last trained dataset path: {trained_dataset_path}")
    print(f"Last trained dataset exists: {'yes' if trained_dataset_path.exists() else 'no'}")
    print(f"Model artifact path: {artifact_path}")
    print(f"Model metadata: {metadata_path}")
    print(f"Metrics file: {metrics_path}")
    print(f"Metrics updated: {_format_time(metrics_path)}")
    print(f"Model updated: {_format_time(metadata_path)}")
    print(f"Model provider: {Config.MODEL_PROVIDER}")
    print(f"External model API: {Config.MODEL_API_URL or 'not configured'}")
    if configured_dataset_path != trained_dataset_path:
        print("Dataset warning: configured dataset path differs from the last trained dataset path.")

    print("\nTraining Summary")
    print("----------------")
    print(f"Model name: {metrics.get('model_name', metadata.get('model_name', 'unknown'))}")
    print(f"Rows used: {metrics.get('dataset_rows', 'unknown')}")
    print(f"Epochs: {metrics.get('epochs', 'unknown')}")
    print(f"Batch size: {metrics.get('batch_size', 'unknown')}")
    print(f"Max length: {metrics.get('max_length', metadata.get('max_length', 'unknown'))}")
    print(f"Device: {metrics.get('device', 'unknown')}")
    print(f"Validation accuracy: {metrics.get('validation_accuracy', 'unknown')}")
    print(f"Validation macro F1: {metrics.get('validation_macro_f1', 'unknown')}")
    print(f"Validation loss: {metrics.get('validation_loss', 'unknown')}")

    _print_list("Active Code Labels", list(SUPPORTED_LABELS))
    _print_list("Model Artifact Labels", list(classes))

    if list(SUPPORTED_LABELS) == list(classes):
        print("\nLabel check: code labels match model artifact labels.")
    else:
        print("\nLabel check: code labels do NOT match model artifact labels.")

    class_distribution = metrics.get("class_distribution") or {}
    if class_distribution:
        print("\nTraining Class Distribution")
        for label, count in class_distribution.items():
            print(f"  - {label}: {count}")

    if history:
        print("\nEpoch History")
        print("  epoch | train_loss | val_loss | val_accuracy | val_macro_f1")
        for row in history:
            print(
                "  "
                f"{row.get('epoch', '?'):>5} | "
                f"{float(row.get('train_loss', 0)):.4f} | "
                f"{float(row.get('validation_loss', 0)):.4f} | "
                f"{float(row.get('validation_accuracy', 0)):.4f} | "
                f"{float(row.get('validation_macro_f1', 0)):.4f}"
            )


if __name__ == "__main__":
    main()
