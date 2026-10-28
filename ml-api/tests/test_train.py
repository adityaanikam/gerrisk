"""train.py must run end to end on a small sample and hand back metrics."""

import sys
from pathlib import Path

import joblib
import pytest

ML_API = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_API))

import train  # noqa: E402

METRIC_NAMES = {"precision", "recall", "f1", "roc_auc"}


def test_train_all_on_a_small_sample_returns_metrics(tmp_path):
    out = tmp_path / "models_out"
    metrics = train.train_all(
        data_dir=train.DEFAULT_DATA_DIR,
        output_dir=out,
        sample_size=150,
        mlflow_uri=None,
    )

    assert set(metrics) == {"cardiac", "fall", "respiratory"}
    for name, scores in metrics.items():
        assert set(scores) == METRIC_NAMES, name
        for metric, value in scores.items():
            assert 0.0 <= value <= 1.0, f"{name}.{metric} = {value}"


def test_train_all_writes_loadable_artefacts_to_the_output_dir(tmp_path):
    out = tmp_path / "models_out"
    train.train_all(
        data_dir=train.DEFAULT_DATA_DIR,
        output_dir=out,
        only="fall",
        sample_size=150,
        mlflow_uri=None,
    )

    spec = train.SPECS_BY_NAME["fall"]
    model = joblib.load(out / spec.model_filename)
    scaler = joblib.load(out / spec.scaler_filename)
    assert model.n_features_in_ == len(spec.features)
    assert scaler.n_features_in_ == len(spec.features)


def test_train_all_never_touches_the_committed_models(tmp_path):
    """The committed artefacts are the ones main.py serves; keep them put."""
    committed = ML_API / "models"
    before = {p.name: p.stat().st_mtime_ns for p in committed.glob("*.pkl")}
    assert before, "expected committed .pkl artefacts in models/"

    train.train_all(
        data_dir=train.DEFAULT_DATA_DIR,
        output_dir=tmp_path / "models_out",
        only="fall",
        sample_size=150,
        mlflow_uri=None,
    )

    after = {p.name: p.stat().st_mtime_ns for p in committed.glob("*.pkl")}
    assert after == before


def test_the_cli_refuses_to_overwrite_the_committed_models():
    with pytest.raises(SystemExit):
        train.main(["--output-dir", str(ML_API / "models"), "--no-mlflow"])


def test_the_recovered_split_sizes_match_the_committed_scalers():
    """999 rows in, 699 train and 300 held out, which is what the scalers saw."""
    spec = train.SPECS_BY_NAME["cardiac"]
    X, y = train.load_dataset(spec, train.DEFAULT_DATA_DIR)
    assert len(X) == 999

    committed_scaler = joblib.load(ML_API / "models" / spec.scaler_filename)
    assert int(round(len(X) * (1 - train.TEST_SIZE))) == int(
        committed_scaler.n_samples_seen_
    )


def test_mlflow_logging_writes_runs_to_a_file_backend(tmp_path):
    runs_dir = tmp_path / "mlruns"
    train.train_all(
        data_dir=train.DEFAULT_DATA_DIR,
        output_dir=tmp_path / "models_out",
        only="fall",
        sample_size=150,
        mlflow_uri=runs_dir.as_uri(),
        experiment="geririsk-test",
    )

    logged_metrics = sorted(p.name for p in runs_dir.glob("*/*/metrics/*"))
    assert logged_metrics == sorted(METRIC_NAMES)
    assert list(runs_dir.glob("*/*/artifacts/model/*.pkl"))
