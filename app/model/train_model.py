"""
train_model.py
--------------
Trains a RandomForest classifier to detect phishing URLs from the
engineered features in feature_extractor.py, and saves:
  - model.pkl   (trained classifier)
  - scaler.pkl  (StandardScaler fit on training features)
  - metrics.json (accuracy / precision / recall / f1 on a held-out set)

Run:
    python app/model/train_model.py
"""

import os
import csv
import json
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix,
)

from feature_extractor import extract_features, features_to_vector, FEATURE_NAMES
from dataset_generator import save_dataset

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "urls_dataset.csv")
MODEL_DIR = os.path.dirname(__file__)


def load_dataset(path):
    urls, labels = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            urls.append(row["url"])
            labels.append(int(row["label"]))
    return urls, labels


def build_feature_matrix(urls):
    vectors = []
    for u in urls:
        feats = extract_features(u)
        vectors.append(features_to_vector(feats))
    return np.array(vectors, dtype=float)


def main():
    if not os.path.exists(DATA_PATH):
        print("Dataset not found — generating a fresh synthetic dataset...")
        save_dataset(DATA_PATH, n_per_class=1500)

    urls, labels = load_dataset(DATA_PATH)
    X = build_feature_matrix(urls)
    y = np.array(labels)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4),
        "f1_score": round(f1_score(y_test, y_pred), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "feature_importances": {
            name: round(float(imp), 4)
            for name, imp in sorted(
                zip(FEATURE_NAMES, clf.feature_importances_),
                key=lambda x: -x[1],
            )
        },
    }

    joblib.dump(clf, os.path.join(MODEL_DIR, "model.pkl"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print("Training complete.")
    print(json.dumps({k: v for k, v in metrics.items() if k != "feature_importances"}, indent=2))
    print(f"\nModel saved to {os.path.join(MODEL_DIR, 'model.pkl')}")


if __name__ == "__main__":
    main()
