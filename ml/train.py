from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor


def build_text_frame(df: pd.DataFrame) -> pd.Series:
    return df["text"].fillna("")


def softmax(scores: np.ndarray) -> np.ndarray:
    scores = scores - np.max(scores, axis=1, keepdims=True)
    exp_scores = np.exp(scores)
    return exp_scores / exp_scores.sum(axis=1, keepdims=True)


def train_and_save(
    dataset_path: str,
    artifact_path: str,
    metrics_path: str,
    feedback_rows: list[dict] | None = None,
) -> dict:
    df = pd.read_csv(dataset_path)
    feedback_rows = feedback_rows or []

    if feedback_rows:
        feedback_df = pd.DataFrame(feedback_rows)
        df = pd.concat([df, feedback_df], ignore_index=True)

    required_columns = {"text", "risk_indicators", "threat_type", "language"}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    text_data = build_text_frame(df)
    labels = df["threat_type"].astype(str)
    classes = sorted(labels.unique())
    class_to_index = {label: index for index, label in enumerate(classes)}
    encoded = labels.map(class_to_index).to_numpy()
    y_one_hot = np.eye(len(classes))[encoded]

    x_train, x_test, y_train_one_hot, y_test_one_hot, y_train, y_test = train_test_split(
        text_data,
        y_one_hot,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )

    vectorizer = TfidfVectorizer(max_features=4000, ngram_range=(1, 2), sublinear_tf=True)
    x_train_tfidf = vectorizer.fit_transform(x_train)
    x_test_tfidf = vectorizer.transform(x_test)

    svd_components = min(200, x_train_tfidf.shape[1] - 1)
    svd = TruncatedSVD(n_components=max(2, svd_components), random_state=42)
    x_train_dense = svd.fit_transform(x_train_tfidf)
    x_test_dense = svd.transform(x_test_tfidf)

    linear_model = MultiOutputRegressor(LinearRegression())
    linear_model.fit(x_train_dense, y_train_one_hot)

    rf_model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced_subsample",
        min_samples_leaf=2,
    )
    rf_model.fit(x_train_dense, y_train)

    linear_scores = np.clip(linear_model.predict(x_test_dense), 1e-9, None)
    linear_probs = softmax(linear_scores)
    rf_probs = rf_model.predict_proba(x_test_dense)
    rf_prob_matrix = np.vstack(rf_probs).T if isinstance(rf_probs, list) else rf_probs
    blended_probs = (0.45 * linear_probs) + (0.55 * rf_prob_matrix)

    linear_predictions = [classes[idx] for idx in np.argmax(linear_probs, axis=1)]
    rf_predictions = rf_model.predict(x_test_dense)
    blended_predictions = [classes[idx] for idx in np.argmax(blended_probs, axis=1)]

    metrics = {
        "dataset_rows": int(len(df)),
        "classes": classes,
        "linear_accuracy": accuracy_score(y_test, linear_predictions),
        "random_forest_accuracy": accuracy_score(y_test, rf_predictions),
        "ensemble_accuracy": accuracy_score(y_test, blended_predictions),
        "ensemble_report": classification_report(
            y_test, blended_predictions, output_dict=True, zero_division=0
        ),
    }

    artifact = {
        "vectorizer": vectorizer,
        "svd": svd,
        "linear_model": linear_model,
        "rf_model": rf_model,
        "classes": classes,
    }

    artifact_file = Path(artifact_path)
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    metrics_file = Path(metrics_path)
    metrics_file.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(artifact, artifact_file)
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
