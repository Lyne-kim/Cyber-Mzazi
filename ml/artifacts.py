from __future__ import annotations

from pathlib import Path


def resolve_transformer_artifact_dir(artifact_path: str | Path) -> Path:
    path = Path(artifact_path)
    if path.suffix:
        return path.with_suffix("")
    return path


def resolve_legacy_artifact_file(artifact_path: str | Path) -> Path:
    path = Path(artifact_path)
    if path.suffix:
        return path
    return path.with_suffix(".joblib")


def transformer_artifact_exists(artifact_path: str | Path) -> bool:
    artifact_dir = resolve_transformer_artifact_dir(artifact_path)
    return artifact_dir.is_dir() and (artifact_dir / "config.json").exists()
