"""The committed artefacts in models/ must stay loadable and predictable.

These are the files main.py serves, so a broken pickle or a changed feature
count is a production outage, not a style problem.
"""

from pathlib import Path

import joblib
import numpy as np
import pytest

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# (model file, scaler file, one sample row in the feature order main.py builds)
CASES = [
    pytest.param(
        "cardiac_risk_model.pkl",
        "cardiac_scaler.pkl",
        # avgHR, maxHR, minHR, minSpO2, totalSteps, recordCount
        [82.4, 115.2, 65.3, 96.4, 342.0, 122.0],
        id="cardiac",
    ),
    pytest.param(
        "fall_risk_model.pkl",
        "fall_scaler.pkl",
        # avgHR, totalSteps, recordCount
        [68.5, 450.0, 112.0],
        id="fall",
    ),
    pytest.param(
        "respiratory_risk_model.pkl",
        "respiratory_scaler.pkl",
        # minSpO2, avgHR, recordCount
        [96.2, 72.4, 85.0],
        id="respiratory",
    ),
]


@pytest.mark.parametrize("model_file, scaler_file, sample", CASES)
def test_committed_artefacts_predict_on_one_row(model_file, scaler_file, sample):
    model = joblib.load(MODELS_DIR / model_file)
    scaler = joblib.load(MODELS_DIR / scaler_file)

    assert scaler.n_features_in_ == len(sample)
    assert model.n_features_in_ == len(sample)
    assert list(model.classes_) == [0, 1]

    X = np.array([sample], dtype=float)
    scaled = scaler.transform(X)
    assert scaled.shape == X.shape

    proba = model.predict_proba(scaled)
    assert proba.shape == (1, 2)
    assert 0.0 <= proba[0][1] <= 1.0
    assert proba[0].sum() == pytest.approx(1.0)
    assert model.predict(scaled)[0] in (0, 1)


@pytest.mark.parametrize("model_file, scaler_file, sample", CASES)
def test_committed_artefacts_were_saved_with_the_pinned_sklearn(
    model_file, scaler_file, sample
):
    """requirements.txt pins the version these pickles were written with."""
    pinned = "1.6.1"
    for name in (model_file, scaler_file):
        artefact = joblib.load(MODELS_DIR / name)
        assert artefact.__getstate__()["_sklearn_version"] == pinned, name


@pytest.mark.parametrize("model_file, scaler_file, sample", CASES)
def test_scalers_were_fit_on_the_recovered_training_split(
    model_file, scaler_file, sample
):
    """699 of 999 rows, which is the test_size=0.3 split train.py reproduces."""
    scaler = joblib.load(MODELS_DIR / scaler_file)
    assert int(np.ravel(scaler.n_samples_seen_)[0]) == 699
