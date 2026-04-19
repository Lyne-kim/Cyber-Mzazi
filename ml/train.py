from __future__ import annotations

import json
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .artifacts import resolve_transformer_artifact_dir
from .labels import RISK_TERMS, SAFE_LABEL, SUPPORTED_LABELS


CHUNK_SIZE = 20_000


class TextDataset(Dataset):
    def __init__(self, texts: list[str], labels: list[int], tokenizer, max_length: int):
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=max_length,
        )
        self.labels = labels

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict:
        item = {
            key: torch.tensor(value[idx], dtype=torch.long)
            for key, value in self.encodings.items()
        }
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item


def seed_everything(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _clean_text(value: object) -> str:
    text = str(value or "")
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_language(value: object, default: str = "mixed") -> str:
    language = _clean_text(value).lower()
    return language or default


def _join_indicators(*values: object) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, dict):
            parts.extend(_join_indicators(*value.values()).split(","))
            continue
        if isinstance(value, (list, tuple, set)):
            parts.extend(_join_indicators(*value).split(","))
            continue
        text = _clean_text(value)
        if text:
            parts.append(text)
    normalized = []
    seen = set()
    for part in parts:
        if not part:
            continue
        for token in [item.strip() for item in part.split(",") if item.strip()]:
            if token not in seen:
                seen.add(token)
                normalized.append(token)
    return ",".join(normalized)


def _make_row(
    text: object,
    label: str,
    *,
    risk_indicators: object = "",
    language: object = "mixed",
    source_name: str,
) -> dict | None:
    cleaned_text = _clean_text(text)
    normalized_label = _clean_text(label).lower()
    if not cleaned_text or normalized_label not in SUPPORTED_LABELS:
        return None
    return {
        "text": cleaned_text,
        "risk_indicators": _join_indicators(risk_indicators) or ",".join(
            RISK_TERMS.get(normalized_label, ["review"])
        ),
        "threat_type": normalized_label,
        "language": _clean_language(language),
        "source_name": source_name,
    }


def _sample_frame(df: pd.DataFrame, limit: int, seed: int = 42) -> pd.DataFrame:
    if limit <= 0 or len(df) <= limit:
        return df
    return df.sample(n=limit, random_state=seed)


def _cap_by_group(df: pd.DataFrame, columns: list[str], limit: int) -> pd.DataFrame:
    if limit <= 0 or df.empty:
        return df
    return (
        df.groupby(columns, group_keys=False, dropna=False)
        .apply(lambda group: _sample_frame(group, limit))
        .reset_index(drop=True)
    )


def _safe_json_objects(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    objects: list[dict] = []
    depth = 0
    start = None
    for index, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    objects.append(json.loads(text[start : index + 1]))
                except json.JSONDecodeError:
                    continue
                start = None
    return objects


def _load_normalized_csv(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    rows = []
    for row in df.to_dict(orient="records"):
        rows.append(
            _make_row(
                row.get("text"),
                row.get("threat_type"),
                risk_indicators=row.get("risk_indicators"),
                language=row.get("language", "mixed"),
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_bongo_scam(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    rows = []
    for row in df.to_dict(orient="records"):
        label = (
            "financial_fraud"
            if _clean_text(row.get("Category")).lower() == "scam"
            else SAFE_LABEL
        )
        rows.append(
            _make_row(
                row.get("Sms"),
                label,
                risk_indicators=row.get("Category"),
                language="sw",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_grooming_swahili(path: Path) -> list[dict]:
    df = pd.read_csv(path, encoding="latin1")
    rows = []
    for row in df.to_dict(orient="records"):
        label = "sexual_content" if _clean_text(row.get("CLASS")).lower() == "sexual" else SAFE_LABEL
        rows.append(
            _make_row(
                row.get("TEXT"),
                label,
                risk_indicators=row.get("CLASS"),
                language="sw",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_multilabel_cyberbully(path: Path) -> list[dict]:
    df = pd.read_csv(path, encoding="latin1")
    rows = []
    for row in df.to_dict(orient="records"):
        indicators = []
        if int(row.get("sexual", 0) or 0) == 1:
            label = "sexual_content"
            indicators.append("sexual")
        elif int(row.get("threat", 0) or 0) == 1:
            label = "violence"
            indicators.append("threat")
        elif int(row.get("religious", 0) or 0) == 1:
            label = "hate_speech"
            indicators.append("religious")
        elif int(row.get("bully", 0) or 0) == 1:
            label = "cyberbullying"
            indicators.append("bully")
        elif int(row.get("spam", 0) or 0) == 1:
            label = "scam"
            indicators.append("spam")
        else:
            label = SAFE_LABEL
        rows.append(
            _make_row(
                row.get("comment"),
                label,
                risk_indicators=indicators,
                language="mixed",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_fact_dataset(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    rows = []
    for row in df.to_dict(orient="records"):
        raw_label = _clean_text(row.get("label")).lower()
        label = "misinformation" if raw_label == "fake" else SAFE_LABEL
        rows.append(
            _make_row(
                row.get("text") or row.get("tweet"),
                label,
                risk_indicators=raw_label,
                language=row.get("language", "mixed"),
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_dataset_xlsx(path: Path) -> list[dict]:
    df = pd.read_excel(path)
    rows = []
    label_map = {
        "violence": "violence",
        "bullying": "cyberbullying",
        "sexual": "sexual_content",
        "safe": SAFE_LABEL,
    }
    for row in df.to_dict(orient="records"):
        raw_label = _clean_text(row.get("threat_type")).lower()
        rows.append(
            _make_row(
                row.get("message"),
                label_map.get(raw_label, SAFE_LABEL),
                risk_indicators=raw_label,
                language="en",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_common_malware(path: Path) -> list[dict]:
    rows = []
    for item in _safe_json_objects(path):
        rows.append(
            _make_row(
                item.get("Input", ""),
                "malware",
                risk_indicators=item.get("Metadata", {}),
                language="en",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_romance_scam(path: Path) -> list[dict]:
    rows = []
    for item in _safe_json_objects(path):
        payload = item.get("input", {})
        rows.append(
            _make_row(
                payload.get("message", ""),
                "scam",
                risk_indicators=item.get("output", {}).get("indicators", []),
                language="en",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_mobile_threats(path: Path) -> list[dict]:
    rows = []
    for item in _safe_json_objects(path):
        metadata = item.get("Metadata", {})
        text = item.get("Input", "")
        metadata_text = json.dumps(metadata, ensure_ascii=False).lower()
        label = "phishing" if "phish" in text.lower() or "phish" in metadata_text else "malware"
        rows.append(
            _make_row(
                text,
                label,
                risk_indicators=metadata,
                language="en",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_phishing_email(path: Path) -> list[dict]:
    rows = []
    for item in _safe_json_objects(path):
        payload = item.get("input", {})
        text = " ".join(
            [
                _clean_text(payload.get("sender_email")),
                _clean_text(payload.get("subject")),
                _clean_text(payload.get("body")),
            ]
        )
        rows.append(
            _make_row(
                text,
                "phishing",
                risk_indicators=item.get("output", {}).get("indicators", []),
                language="en",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_ransomware(path: Path) -> list[dict]:
    rows = []
    for item in _safe_json_objects(path):
        rows.append(
            _make_row(
                item.get("Input", ""),
                "malware",
                risk_indicators=item.get("Metadata", {}),
                language="en",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_bot_detection(path: Path) -> list[dict]:
    df = pd.read_csv(path, usecols=["Tweet", "Bot Label", "Hashtags"])
    rows = []
    for row in df.to_dict(orient="records"):
        label = "bot_activity" if int(row.get("Bot Label", 0) or 0) == 1 else SAFE_LABEL
        rows.append(
            _make_row(
                f"{row.get('Tweet', '')} {row.get('Hashtags', '')}",
                label,
                risk_indicators="bot_label",
                language="en",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_malicious_phish(path: Path) -> list[dict]:
    df = pd.read_csv(path, usecols=["url", "type"])
    label_map = {
        "benign": SAFE_LABEL,
        "phishing": "phishing",
        "malware": "malware",
        "defacement": "malware",
    }
    rows = []
    for row in df.to_dict(orient="records"):
        raw_label = _clean_text(row.get("type")).lower()
        rows.append(
            _make_row(
                row.get("url"),
                label_map.get(raw_label, "phishing"),
                risk_indicators=raw_label,
                language="en",
                source_name=path.name,
            )
        )
    return [row for row in rows if row]


def _load_original_toxicity(path: Path) -> list[dict]:
    rows = []
    per_label_budget = {
        SAFE_LABEL: 80,
        "cyberbullying": 80,
        "violence": 60,
        "hate_speech": 60,
        "sexual_content": 60,
    }
    counts = {label: 0 for label in per_label_budget}
    usecols = [
        "comment_text",
        "target",
        "severe_toxicity",
        "identity_attack",
        "insult",
        "threat",
        "sexual_explicit",
    ]
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=CHUNK_SIZE, low_memory=False):
        for row in chunk.to_dict(orient="records"):
            sexual_score = float(row.get("sexual_explicit") or 0.0)
            threat_score = float(row.get("threat") or 0.0)
            hate_score = float(row.get("identity_attack") or 0.0)
            bullying_score = max(
                float(row.get("target") or 0.0),
                float(row.get("severe_toxicity") or 0.0),
                float(row.get("insult") or 0.0),
            )
            if sexual_score >= 0.35:
                label = "sexual_content"
                indicators = "sexual_explicit"
            elif threat_score >= 0.30:
                label = "violence"
                indicators = "threat"
            elif hate_score >= 0.30:
                label = "hate_speech"
                indicators = "identity_attack"
            elif bullying_score >= 0.45:
                label = "cyberbullying"
                indicators = "toxicity"
            elif (
                bullying_score <= 0.05
                and sexual_score <= 0.02
                and threat_score <= 0.02
                and hate_score <= 0.02
            ):
                label = SAFE_LABEL
                indicators = "benign"
            else:
                continue

            if counts[label] >= per_label_budget[label]:
                continue
            normalized = _make_row(
                row.get("comment_text"),
                label,
                risk_indicators=indicators,
                language="en",
                source_name=path.name,
            )
            if normalized:
                rows.append(normalized)
                counts[label] += 1
            if all(counts[key] >= per_label_budget[key] for key in per_label_budget):
                return rows
    return rows


def _load_feedback_rows(feedback_rows: list[dict] | None) -> list[dict]:
    feedback_rows = feedback_rows or []
    rows = []
    for row in feedback_rows:
        normalized = _make_row(
            row.get("text"),
            row.get("threat_type"),
            risk_indicators=row.get("risk_indicators"),
            language=row.get("language", "mixed"),
            source_name="review_feedback",
        )
        if normalized:
            rows.append(normalized)
    return rows


SOURCE_LOADERS = {
    "dataset.csv": _load_normalized_csv,
    "bongo_scam (1).csv": _load_bongo_scam,
    "Grooming Swahili Data sets.csv": _load_grooming_swahili,
    "Multilablel Cyberbully Data.csv": _load_multilabel_cyberbully,
    "train_dataset.csv": _load_fact_dataset,
    "dataset2.xlsx": _load_dataset_xlsx,
    "common-malware-vectors.json": _load_common_malware,
    "facebook-romance-scams.json": _load_romance_scam,
    "mobile-threats-detection.json": _load_mobile_threats,
    "phishing-email-inbound.json": _load_phishing_email,
    "ransomware-cases.json": _load_ransomware,
    "bot_detection_data.csv": _load_bot_detection,
    "malicious_phish.csv": _load_malicious_phish,
    "original.csv": _load_original_toxicity,
}


def _collect_rows_from_path(dataset_path: str) -> tuple[list[dict], list[str], list[str]]:
    path = Path(dataset_path)
    if path.is_file():
        loader = SOURCE_LOADERS.get(path.name, _load_normalized_csv)
        return loader(path), [path.name], []

    if not path.is_dir():
        raise FileNotFoundError(f"Dataset path does not exist: {dataset_path}")

    rows: list[dict] = []
    used_sources: list[str] = []
    skipped_sources: list[str] = []
    for item in sorted(path.iterdir(), key=lambda entry: entry.name.lower()):
        if not item.is_file():
            continue
        loader = SOURCE_LOADERS.get(item.name)
        if loader is None:
            skipped_sources.append(item.name)
            continue
        rows.extend(loader(item))
        used_sources.append(item.name)
    return rows, used_sources, skipped_sources


def build_training_frame(
    dataset_path: str,
    feedback_rows: list[dict] | None = None,
    *,
    max_rows_per_label: int = 180,
    max_rows_per_source_label: int = 80,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    source_rows, used_sources, skipped_sources = _collect_rows_from_path(dataset_path)
    source_rows.extend(_load_feedback_rows(feedback_rows))

    if not source_rows:
        raise ValueError("No valid training rows were found in the dataset sources.")

    df = pd.DataFrame(source_rows)
    df["text"] = df["text"].fillna("").astype(str).str.strip()
    df["threat_type"] = df["threat_type"].fillna("").astype(str).str.strip().str.lower()
    df["risk_indicators"] = df["risk_indicators"].fillna("").astype(str)
    df["language"] = df["language"].fillna("mixed").astype(str)
    df["source_name"] = df["source_name"].fillna("unknown").astype(str)
    df = df[df["text"].ne("")]
    df = df[df["threat_type"].isin(SUPPORTED_LABELS)]
    df = df.drop_duplicates(subset=["text", "threat_type"]).reset_index(drop=True)
    df = _cap_by_group(df, ["source_name", "threat_type"], max_rows_per_source_label)
    df = _cap_by_group(df, ["threat_type"], max_rows_per_label)
    if df.empty:
        raise ValueError("No valid training rows remained after normalization.")
    return df.reset_index(drop=True), used_sources, skipped_sources


def train_one_epoch(model, loader: DataLoader, optimizer, device: torch.device) -> float:
    model.train()
    total_loss = 0.0

    for batch in loader:
        optimizer.zero_grad(set_to_none=True)
        batch = {key: value.to(device) for key, value in batch.items()}
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        total_loss += float(loss.item())

    return total_loss / max(len(loader), 1)


def evaluate(model, loader: DataLoader, device: torch.device, classes: list[str]) -> dict:
    model.eval()
    predictions: list[int] = []
    labels: list[int] = []
    total_loss = 0.0

    with torch.no_grad():
        for batch in loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            total_loss += float(outputs.loss.item())
            preds = torch.argmax(outputs.logits, dim=1)
            predictions.extend(preds.cpu().tolist())
            labels.extend(batch["labels"].cpu().tolist())

    predicted_labels = [classes[idx] for idx in predictions]
    true_labels = [classes[idx] for idx in labels]
    return {
        "validation_loss": total_loss / max(len(loader), 1),
        "validation_accuracy": accuracy_score(true_labels, predicted_labels),
        "validation_macro_f1": f1_score(true_labels, predicted_labels, average="macro"),
        "validation_report": classification_report(
            true_labels,
            predicted_labels,
            labels=classes,
            output_dict=True,
            zero_division=0,
        ),
    }


def train_and_save(
    dataset_path: str,
    artifact_path: str,
    metrics_path: str,
    feedback_rows: list[dict] | None = None,
    *,
    model_name: str = "distilbert-base-multilingual-cased",
    epochs: int = 2,
    batch_size: int = 8,
    max_length: int = 160,
    max_rows_per_label: int = 180,
    max_rows_per_source_label: int = 80,
) -> dict:
    seed_everything(42)
    print(f"Preparing training data from {dataset_path}...", flush=True)
    df, used_sources, skipped_sources = build_training_frame(
        dataset_path,
        feedback_rows,
        max_rows_per_label=max_rows_per_label,
        max_rows_per_source_label=max_rows_per_source_label,
    )
    print(
        "Loaded "
        f"{len(df)} normalized rows across {len(used_sources)} sources. "
        f"Classes: {df['threat_type'].value_counts().to_dict()}",
        flush=True,
    )
    if skipped_sources:
        print(f"Skipped non-dataset files: {skipped_sources}", flush=True)

    texts = df["text"].tolist()
    labels = df["threat_type"].tolist()
    classes = sorted(set(labels), key=lambda label: SUPPORTED_LABELS.index(label))
    class_to_index = {label: index for index, label in enumerate(classes)}
    encoded = [class_to_index[label] for label in labels]

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        encoded,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )

    print(f"Loading tokenizer for {model_name}...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
    print(f"Loading base model for {model_name}...", flush=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(classes),
        id2label={idx: label for idx, label in enumerate(classes)},
        label2id=class_to_index,
    )

    train_dataset = TextDataset(x_train, y_train, tokenizer, max_length=max_length)
    test_dataset = TextDataset(x_test, y_test, tokenizer, max_length=max_length)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)

    epoch_history = []
    for epoch_index in range(epochs):
        print(f"Starting epoch {epoch_index + 1}/{epochs}...", flush=True)
        train_loss = train_one_epoch(model, train_loader, optimizer, device)
        validation_metrics = evaluate(model, test_loader, device, classes)
        print(
            f"Epoch {epoch_index + 1}/{epochs} complete. "
            f"train_loss={train_loss:.4f}, "
            f"validation_accuracy={validation_metrics['validation_accuracy']:.3f}, "
            f"validation_macro_f1={validation_metrics['validation_macro_f1']:.3f}",
            flush=True,
        )
        epoch_history.append(
            {
                "epoch": epoch_index + 1,
                "train_loss": train_loss,
                **validation_metrics,
            }
        )

    final_metrics = epoch_history[-1]
    metrics = {
        "dataset_path": dataset_path,
        "dataset_rows": int(len(df)),
        "classes": classes,
        "model_name": model_name,
        "epochs": epochs,
        "batch_size": batch_size,
        "max_length": max_length,
        "max_rows_per_label": max_rows_per_label,
        "max_rows_per_source_label": max_rows_per_source_label,
        "device": str(device),
        "class_distribution": df["threat_type"].value_counts().to_dict(),
        "source_distribution": df["source_name"].value_counts().to_dict(),
        "used_sources": used_sources,
        "skipped_sources": skipped_sources,
        "history": epoch_history,
        "validation_accuracy": final_metrics["validation_accuracy"],
        "validation_macro_f1": final_metrics["validation_macro_f1"],
        "validation_loss": final_metrics["validation_loss"],
        "validation_report": final_metrics["validation_report"],
    }

    artifact_dir = resolve_transformer_artifact_dir(artifact_path)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    metrics_file = Path(metrics_path)
    metrics_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving model artifacts to {artifact_dir}...", flush=True)
    model.save_pretrained(artifact_dir)
    tokenizer.save_pretrained(artifact_dir)
    (artifact_dir / "metadata.json").write_text(
        json.dumps(
            {
                "classes": classes,
                "model_name": model_name,
                "max_length": max_length,
                "label_to_index": class_to_index,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
