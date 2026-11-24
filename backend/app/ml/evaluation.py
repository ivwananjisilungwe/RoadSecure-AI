from collections.abc import Callable
from time import perf_counter_ns

import numpy as np

from .synthetic import Dataset


def metrics(labels: np.ndarray, decisions: np.ndarray) -> dict:
    actual = labels.astype(bool)
    predicted = decisions.astype(bool)
    tp = int(np.count_nonzero(actual & predicted))
    tn = int(np.count_nonzero(~actual & ~predicted))
    fp = int(np.count_nonzero(~actual & predicted))
    fn = int(np.count_nonzero(actual & ~predicted))
    return {
        "accuracy": (tp + tn) / len(actual),
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1_score": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
    }


def select_threshold(validation: Dataset, scores: np.ndarray) -> float:
    # Include the no-alert operating point. Use lower FPR to break F1 ties.
    candidates = np.append(np.unique(scores), np.nextafter(scores.max(), np.inf))

    def rank(threshold: float) -> tuple:
        result = metrics(validation.labels, scores >= threshold)
        return result["f1_score"], -result["false_positive_rate"], threshold

    return float(max(candidates, key=rank))


def timed_experiment(dataset: Dataset, decide: Callable[[dict], bool]) -> dict:
    decide(dataset.events[0])  # Warm a single call before collecting measurements.
    predictions = np.empty(len(dataset.events), dtype=bool)
    elapsed_ms = np.empty(len(dataset.events), dtype=float)
    for index, event in enumerate(dataset.events):
        start = perf_counter_ns()
        decision = decide(event)
        elapsed_ms[index] = (perf_counter_ns() - start) / 1_000_000
        predictions[index] = decision
    return {
        **metrics(dataset.labels, predictions),
        "mean_processing_ms": float(np.mean(elapsed_ms)),
        "median_processing_ms": float(np.median(elapsed_ms)),
        "p95_processing_ms": float(np.percentile(elapsed_ms, 95)),
    }
