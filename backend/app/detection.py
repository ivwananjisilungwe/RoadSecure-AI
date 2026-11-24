"""Hybrid telemetry detector and local training entry point."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from .ml.evaluation import select_threshold, timed_experiment
from .ml.features import FEATURES, feature_vector
from .ml.rules import evaluate_rules
from .ml.synthetic import Dataset, generate_dataset, simulate

MODEL_VERSION = "roadsecure-iforest-v1"
MODEL_FILENAME = "roadsecure-iforest.joblib"
ML_CONTRIBUTION = 20


def model_path() -> Path:
    default = Path(__file__).resolve().parents[1] / "data"
    return Path(os.getenv("ROADSECURE_DATA_DIR", str(default))) / MODEL_FILENAME


def severity_for(risk_score: int) -> str:
    if risk_score >= 75:
        return "CRITICAL"
    if risk_score >= 50:
        return "HIGH"
    if risk_score >= 25:
        return "MEDIUM"
    return "LOW"


class Detector:
    def __init__(self, pipeline: Pipeline, evaluation: dict):
        self.pipeline = pipeline
        self.evaluation = evaluation
        self.threshold = evaluation["model"]["decision_threshold"]

    @classmethod
    def load(cls) -> Detector:
        path = model_path()
        if not path.is_file():
            raise RuntimeError("RoadSecure model missing. Run python -m app.detection train from backend.")
        # Joblib can execute serialized code. This path is local operator configuration only.
        try:
            artifact = joblib.load(path)
            metadata = artifact["evaluation"]["model"]
            if (
                metadata["version"] != MODEL_VERSION
                or metadata["dependency_versions"]["scikit-learn"] != sklearn.__version__
                or metadata["feature_schema"] != list(FEATURES)
                or not np.isfinite(metadata["decision_threshold"])
                or artifact["pipeline"].n_features_in_ != len(FEATURES)
            ):
                raise ValueError("Model metadata or dependency compatibility check failed")
            return cls(artifact["pipeline"], artifact["evaluation"])
        except Exception as exc:
            raise RuntimeError("RoadSecure model is incompatible or damaged. Retrain locally.") from exc

    def score(self, event: Mapping) -> float:
        return float(-self.pipeline.score_samples(feature_vector(event).reshape(1, -1))[0])

    def predict_anomaly(self, event: Mapping) -> bool:
        return self.score(event) >= self.threshold

    def detect(self, event: Mapping) -> dict:
        matches = evaluate_rules(event)
        score = self.score(event)
        anomalous = score >= self.threshold
        risk_score = min(100, sum(match["risk_contribution"] for match in matches)
                         + (ML_CONTRIBUTION if anomalous else 0))
        should_alert = bool(matches or anomalous)
        return {
            "rule_results": matches,
            "ml_prediction": "anomaly" if anomalous else "normal",
            "anomaly_score": score,
            "risk_score": risk_score,
            "severity": severity_for(risk_score),
            "detection_result": "suspicious" if should_alert else "normal",
            "should_alert": should_alert,
        }


def _dataset_summary(dataset: Dataset) -> dict:
    records = json.dumps(dataset.events, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(records + dataset.labels.tobytes()).hexdigest()
    return {
        "count": len(dataset.events),
        "anomalies": int(dataset.labels.sum()),
        "seed": dataset.seed,
        "fingerprint": digest,
    }



def run_experiments(detector: Detector, test: Dataset) -> dict:
    return {
        "rules": timed_experiment(test, lambda event: bool(evaluate_rules(event))),
        "isolation_forest": timed_experiment(test, detector.predict_anomaly),
        "hybrid": timed_experiment(test, lambda event: detector.detect(event)["should_alert"]),
    }


def evaluate() -> dict:
    detector = Detector.load()
    report = detector.evaluation
    stored_test = report["datasets"]["test"]
    test = generate_dataset(
        stored_test["count"], stored_test["seed"],
        anomaly_fraction=stored_test["anomalies"] / stored_test["count"],
    )
    if _dataset_summary(test) != stored_test:
        raise RuntimeError("The regenerated held-out dataset does not match the model's test fingerprint.")
    return {**report, "experiments": run_experiments(detector, test)}


def train() -> dict:
    training = generate_dataset(5_000, 42)
    validation = generate_dataset(1_000, 1042, anomaly_fraction=0.2)
    test = generate_dataset(2_000, 2042, anomaly_fraction=0.2)
    train_features, validation_features, test_features = (
        training.features, validation.features, test.features
    )
    rows = [tuple(row) for split in (train_features, validation_features, test_features) for row in split]
    if len(set(rows)) != len(rows):
        raise RuntimeError("Duplicate feature observations found in the evaluation datasets.")

    hyperparameters = {"n_estimators": 180, "contamination": 0.06, "random_state": 42}
    pipeline = make_pipeline(StandardScaler(), IsolationForest(**hyperparameters)).fit(train_features)
    validation_scores = -pipeline.score_samples(validation_features)
    decision_threshold = select_threshold(validation, validation_scores)
    datasets = {
        "train": _dataset_summary(training),
        "validation": _dataset_summary(validation),
        "test": _dataset_summary(test),
    }
    report = {
        "model": {
            "version": MODEL_VERSION,
            "feature_schema": list(FEATURES),
            "decision_threshold": decision_threshold,
            "training_timestamp": datetime.now(timezone.utc).isoformat(),
            "training_fingerprint": datasets["train"]["fingerprint"],
            "hyperparameters": hyperparameters,
            "dependency_versions": {
                "numpy": np.__version__,
                "scikit-learn": sklearn.__version__,
                "joblib": joblib.__version__,
            },
            "evaluation_artifact": "evaluation.json",
        },
        "datasets": datasets,
        "experiments": {},
    }
    detector = Detector(pipeline, report)
    report["experiments"] = run_experiments(detector, test)
    destination = model_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as staging:
        staging_path = Path(staging)
        model = staging_path / destination.name
        evaluation = staging_path / "evaluation.json"
        joblib.dump({"pipeline": pipeline, "evaluation": report}, model)
        evaluation.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        model.replace(destination)
        evaluation.replace(destination.with_name(evaluation.name))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("train", "evaluate"))
    args = parser.parse_args()
    report = train() if args.action == "train" else evaluate()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
