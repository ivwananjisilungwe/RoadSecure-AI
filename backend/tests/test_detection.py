from pathlib import Path

import numpy as np
import pytest

from app.detection import Detector, severity_for
from app.ml.evaluation import metrics, select_threshold
from app.ml.features import FEATURES, feature_vector
from app.ml.rules import RULES, evaluate_rules
from app.ml.synthetic import SCENARIOS, generate_dataset, simulate


@pytest.mark.parametrize(
    ("scenario", "rule_id", "contribution"),
    [
        ("failed_login", "RS-01", 25),
        ("outside_hours", "RS-02", 15),
        ("unknown_device", "RS-03", 20),
        ("large_transfer", "RS-04", 25),
        ("privileged_action", "RS-05", 35),
        ("sensitive_access", "RS-06", 30),
    ],
)
def test_rule_explanations(scenario, rule_id, contribution):
    finding, = evaluate_rules(simulate(scenario))
    assert finding["rule_id"] == rule_id
    assert finding["risk_contribution"] == contribution
    assert finding["explanation"]
    assert finding["evidence"]


def test_legitimate_privileged_action_has_no_rule_match():
    assert evaluate_rules(simulate("legitimate_admin")) == []


@pytest.mark.parametrize(
    ("risk", "expected"),
    [(0, "LOW"), (24, "LOW"), (25, "MEDIUM"), (49, "MEDIUM"),
     (50, "HIGH"), (74, "HIGH"), (75, "CRITICAL"), (100, "CRITICAL")],
)
def test_severity_boundaries(risk, expected):
    assert severity_for(risk) == expected


class ConstantScorer:
    def __init__(self, anomaly_score):
        self.anomaly_score = anomaly_score

    def score_samples(self, matrix):
        assert matrix.shape == (1, len(FEATURES))
        return np.array([-self.anomaly_score])


@pytest.mark.parametrize(
    ("scenario", "model_score", "risk", "should_alert"),
    [
        ("normal", 0.4, 0, False),
        ("normal", 0.6, 20, True),
        ("outside_hours", 0.4, 15, True),
        ("failed_login", 0.4, 25, True),
        ("privileged_action", 0.6, 55, True),
        ("combined", 0.6, 100, True),
    ],
)
def test_hybrid_risk_and_alert_independence(scenario, model_score, risk, should_alert):
    detector = Detector(ConstantScorer(model_score), {"model": {"decision_threshold": 0.5}})
    result = detector.detect(simulate(scenario))
    assert result["risk_score"] == risk
    assert result["should_alert"] is should_alert


def test_features_and_dataset_generation_are_reproducible():
    dataset = generate_dataset(60, 42, anomaly_fraction=0.2)
    copy = generate_dataset(60, 42, anomaly_fraction=0.2)
    independent = generate_dataset(60, 43, anomaly_fraction=0.2)
    assert dataset.labels.sum() == 12
    np.testing.assert_array_equal(dataset.features, copy.features)
    assert set(map(tuple, dataset.features)).isdisjoint(map(tuple, independent.features))
    assert feature_vector(simulate("normal")).tolist() == [0, 31, 3, 0, 0, 0, 0, 3]
    assert len(RULES) == 6
    assert len(SCENARIOS) == 11


def test_metrics_and_validation_threshold_reconcile():
    labels = np.array([0, 0, 1, 1])
    result = metrics(labels, np.array([0, 1, 0, 1]))
    assert result["accuracy"] == result["f1_score"] == result["false_positive_rate"] == 0.5
    dataset = generate_dataset(4, 3, anomaly_fraction=0.5)
    scores = np.where(dataset.labels, 0.7, 0.3)
    assert select_threshold(dataset, scores) == 0.7


def test_missing_model_names_local_training_command(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ROADSECURE_DATA_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="python -m app.detection train"):
        Detector.load()


def test_trained_artifact_and_evaluation_when_available():
    from app.detection import model_path

    if not model_path().exists():
        pytest.skip("Run python -m app.detection train to verify the trained artifact.")
    detector = Detector.load()
    normal = detector.detect(simulate("normal"))
    critical = detector.detect(simulate("combined"))
    assert not normal["should_alert"]
    assert critical["severity"] == "CRITICAL"
    assert critical["ml_prediction"] == "anomaly"
    assert normal["anomaly_score"] < critical["anomaly_score"]
    report = detector.evaluation
    assert report["datasets"]["train"]["anomalies"] == 0
    assert report["datasets"]["test"]["count"] == 2_000
    for experiment in report["experiments"].values():
        assert experiment["true_positives"] + experiment["false_negatives"] == 400
        assert experiment["true_negatives"] + experiment["false_positives"] == 1_600
        assert experiment["p95_processing_ms"] >= experiment["median_processing_ms"] > 0
