from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import requests


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


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def download_and_extract_transformer_artifact(
    artifact_url: str,
    artifact_path: str | Path,
    *,
    timeout_seconds: int = 600,
) -> Path:
    artifact_dir = resolve_transformer_artifact_dir(artifact_path)
    ensure_parent_dir(artifact_dir)
    temp_root = artifact_dir.parent / ".model_download_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(artifact_url)
    archive_name = Path(parsed.path).name or "message_model.zip"
    try:
        with tempfile.TemporaryDirectory(
            prefix="cyber-mzazi-model-",
            dir=temp_root,
        ) as tmp_dir:
            archive_path = Path(tmp_dir) / archive_name
            with requests.get(artifact_url, stream=True, timeout=timeout_seconds) as response:
                response.raise_for_status()
                with archive_path.open("wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file_handle.write(chunk)

            extracted_dir = Path(tmp_dir) / "extracted"
            extracted_dir.mkdir(parents=True, exist_ok=True)
            with ZipFile(archive_path) as archive:
                archive.extractall(extracted_dir)

            config_files = list(extracted_dir.rglob("config.json"))
            if not config_files:
                raise RuntimeError(
                    f"No transformer artifact was found in downloaded archive: {artifact_url}"
                )
            source_dir = config_files[0].parent

            if artifact_dir.exists():
                shutil.rmtree(artifact_dir)
            shutil.copytree(source_dir, artifact_dir)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return artifact_dir
