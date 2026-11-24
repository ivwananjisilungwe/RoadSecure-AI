from collections.abc import Mapping

import numpy as np

FEATURES = (
    "failed_login_count",
    "requests_per_minute",
    "data_transfer_mb",
    "outside_working_hours",
    "unknown_device",
    "unusual_location",
    "privileged_action",
    "sensitive_records_accessed",
)


def feature_vector(event: Mapping) -> np.ndarray:
    """Extract runtime features in the same order used for training."""
    return np.asarray([event.get(key, 0) for key in FEATURES], dtype=np.float64)
