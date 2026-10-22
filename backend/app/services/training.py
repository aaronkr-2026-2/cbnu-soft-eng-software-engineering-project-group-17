"""Train and evaluate the sleep-stage model.

Run manually:   python -m app.services.training

The model is trained on SYNTHETIC nights (see synthetic.py) because labelled
real data (EEG-scored hypnograms) is not available to this project. The
reported accuracy is therefore accuracy on simulated data from the same
generator - an upper bound that says nothing about real-world performance.
"""
import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, cohen_kappa_score

from .. import config
from .features import FEATURE_COLUMNS, build_features
from .synthetic import generate_nights

MODEL_FILE = "stage_model.joblib"


def _dataset(nights: list[dict]) -> tuple[pd.DataFrame, pd.Series]:
    x = pd.concat([build_features(n["data"]) for n in nights], ignore_index=True)
    y = pd.concat([n["data"]["stage_true"] for n in nights], ignore_index=True)
    return x, y


def train_and_save(n_nights: int | None = None, seed: int = 7, model_dir: Path | None = None) -> dict:
    """Train on synthetic nights, evaluate on held-out nights, save, return the bundle."""
    n_nights = n_nights or config.TRAIN_NIGHTS
    model_dir = Path(model_dir or config.MODEL_DIR)

    nights = generate_nights(n_nights, seed, last_night=date(2026, 1, 1))
    split = max(1, int(len(nights) * 0.8))
    # Split by whole nights (not by minutes) so test nights are never seen in training.
    x_train, y_train = _dataset(nights[:split])
    x_test, y_test = _dataset(nights[split:])

    clf = RandomForestClassifier(
        n_estimators=100, max_depth=12, class_weight="balanced", random_state=42, n_jobs=-1
    )
    clf.fit(x_train, y_train)
    predicted = clf.predict(x_test)

    report = classification_report(y_test, predicted, output_dict=True, zero_division=0)
    metrics = {
        "trained_on": "synthetic",
        "train_nights": split,
        "test_nights": len(nights) - split,
        "accuracy": round(float(accuracy_score(y_test, predicted)), 3),
        "cohen_kappa": round(float(cohen_kappa_score(y_test, predicted)), 3),
        "recall_by_stage": {s: round(float(report[s]["recall"]), 3) for s in ("wake", "light", "deep", "rem") if s in report},
        "features": FEATURE_COLUMNS,
        "sklearn_version": sklearn.__version__,
        "warning": "Measured on simulated nights from the same generator; not a measure of real-world accuracy.",
    }

    model_dir.mkdir(parents=True, exist_ok=True)
    bundle = {"model": clf, "metrics": metrics}
    joblib.dump(bundle, model_dir / MODEL_FILE)
    (model_dir / "stage_model_metrics.json").write_text(json.dumps(metrics, indent=2))
    return bundle


def load_or_train() -> dict:
    """Load the saved model, or train a new one if none exists or it cannot be loaded."""
    path = Path(config.MODEL_DIR) / MODEL_FILE
    if path.exists():
        try:
            # joblib uses pickle: only ever load files that this app wrote itself.
            bundle = joblib.load(path)
            if bundle["metrics"].get("sklearn_version") == sklearn.__version__:
                return bundle
        except Exception:  # noqa: BLE001 - corrupt or incompatible file: retrain below
            pass
    return train_and_save()


if __name__ == "__main__":
    result = train_and_save()
    print(json.dumps(result["metrics"], indent=2))
