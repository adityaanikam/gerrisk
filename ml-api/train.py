"""
GeriRisk model training
=======================
Retrains the three risk classifiers that `main.py` serves, from the CSVs in
`training_data/`, and writes the results to a *separate* output directory so
the committed artefacts in `models/` are never touched.

The split, the seed and the hyper-parameters below were recovered from the
committed artefacts rather than chosen freshly; see the "Model training"
section of the repository README for how.

Usage
-----
    python train.py                              # all three models
    python train.py --only fall                  # one model
    python train.py --sample-size 120            # quick smoke run
    python train.py --output-dir /tmp/out

MLflow
------
Runs are logged through the local file backend (`mlruns/`, gitignored).
Point `--mlflow-uri` elsewhere, or pass `--no-mlflow`, to change that.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

# MLflow phones home and prints an agent hint on import; neither is wanted in a
# training script, and both must be set before the import happens. MLflow 3 also
# refuses the file backend unless asked to allow it, and the file backend is what
# this script uses so that a run needs no database.
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = HERE / "training_data"
DEFAULT_OUTPUT_DIR = HERE / "models_retrained"
DEFAULT_MLFLOW_URI = (HERE.parent / "mlruns").as_uri()

# The split recovered from the committed scalers: every one of them reports
# n_samples_seen_ == 699 out of 999 rows, and only this combination reproduces
# their mean_ and scale_ exactly.
TEST_SIZE = 0.3
RANDOM_STATE = 42
STRATIFY = True


@dataclass(frozen=True)
class ModelSpec:
    """One risk model: its data, its feature order and how to build it."""

    name: str
    csv: str
    label: str
    # Feature order must match the vectors built in main.py predict().
    features: tuple[str, ...]
    build: Callable[[], ClassifierMixin]
    model_filename: str
    scaler_filename: str


SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        name="cardiac",
        csv="cardiac_risk_training_data.csv",
        label="cardiac_risk_label",
        features=(
            "avgHeartRate",
            "maxHeartRate",
            "minHeartRate",
            "minSpO2",
            "totalSteps",
            "recordCount",
        ),
        build=lambda: RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        model_filename="cardiac_risk_model.pkl",
        scaler_filename="cardiac_scaler.pkl",
    ),
    ModelSpec(
        name="fall",
        csv="fall_risk_training_data.csv",
        label="fall_risk_label",
        features=("avgHeartRate", "totalSteps", "recordCount"),
        build=lambda: LogisticRegression(
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        model_filename="fall_risk_model.pkl",
        scaler_filename="fall_scaler.pkl",
    ),
    ModelSpec(
        name="respiratory",
        csv="respiratory_risk_training_data.csv",
        label="respiratory_risk_label",
        features=("minSpO2", "avgHeartRate", "recordCount"),
        build=lambda: LogisticRegression(
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        model_filename="respiratory_risk_model.pkl",
        scaler_filename="respiratory_scaler.pkl",
    ),
)

SPECS_BY_NAME = {spec.name: spec for spec in SPECS}


def load_dataset(
    spec: ModelSpec,
    data_dir: Path,
    sample_size: Optional[int] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Read one CSV and return (X, y), optionally down to a stratified sample."""
    path = data_dir / spec.csv
    if not path.exists():
        raise FileNotFoundError(
            f"Training data not found: {path}. "
            "See the README for where these CSVs come from."
        )
    frame = pd.read_csv(path)
    missing = [c for c in (*spec.features, spec.label) if c not in frame.columns]
    if missing:
        raise ValueError(f"{path.name} is missing columns: {missing}")

    if sample_size is not None and sample_size < len(frame):
        frame, _ = train_test_split(
            frame,
            train_size=sample_size,
            random_state=RANDOM_STATE,
            stratify=frame[spec.label],
        )

    X = frame[list(spec.features)].to_numpy(dtype=float)
    y = frame[spec.label].to_numpy(dtype=int)
    return X, y


def evaluate(model: ClassifierMixin, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Precision, recall, F1 and ROC AUC for the positive class."""
    predicted = model.predict(X)
    scores = model.predict_proba(X)[:, 1]
    return {
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, scores)),
    }


def train_one(
    spec: ModelSpec,
    data_dir: Path,
    output_dir: Path,
    sample_size: Optional[int] = None,
) -> dict[str, Any]:
    """Fit one model, write its artefacts and return its held-out metrics."""
    X, y = load_dataset(spec, data_dir, sample_size=sample_size)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y if STRATIFY else None,
    )

    scaler = StandardScaler().fit(X_train)
    model = spec.build()
    model.fit(scaler.transform(X_train), y_train)

    metrics = evaluate(model, scaler.transform(X_test), y_test)

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / spec.model_filename
    scaler_path = output_dir / spec.scaler_filename
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    return {
        "name": spec.name,
        "metrics": metrics,
        "params": {
            "algorithm": type(model).__name__,
            "features": list(spec.features),
            "n_rows": int(len(X)),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "test_size": TEST_SIZE,
            "random_state": RANDOM_STATE,
            "stratify": STRATIFY,
            "positive_rate": float(y.mean()),
            "sklearn_version": sklearn.__version__,
            **{f"model__{k}": v for k, v in model.get_params().items()},
        },
        "artifacts": {"model": model_path, "scaler": scaler_path},
    }


def _log_to_mlflow(result: dict[str, Any], experiment: str, tracking_uri: str) -> None:
    """Log one result as an MLflow run against the file backend."""
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=result["name"]):
        mlflow.log_params(
            {k: ("None" if v is None else v) for k, v in result["params"].items()}
        )
        mlflow.log_metrics(result["metrics"])
        mlflow.set_tags(
            {
                "model": result["name"],
                "python": platform.python_version(),
                "sklearn": sklearn.__version__,
            }
        )
        for path in result["artifacts"].values():
            mlflow.log_artifact(str(path), artifact_path="model")


def train_all(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    only: Optional[str] = None,
    sample_size: Optional[int] = None,
    mlflow_uri: Optional[str] = DEFAULT_MLFLOW_URI,
    experiment: str = "geririsk-risk-models",
) -> dict[str, dict[str, float]]:
    """Train the selected models and return {name: metrics}.

    Pass ``mlflow_uri=None`` to skip MLflow logging entirely.
    """
    specs = SPECS if only is None else (SPECS_BY_NAME[only],)
    out: dict[str, dict[str, float]] = {}

    for spec in specs:
        result = train_one(spec, data_dir, output_dir, sample_size=sample_size)
        out[spec.name] = result["metrics"]

        params = result["params"]
        print(f"\n{spec.name}: {params['algorithm']}")
        print(
            f"  rows {params['n_rows']} "
            f"(train {params['n_train']} / held out {params['n_test']}), "
            f"positive rate {params['positive_rate']:.3f}"
        )
        for metric, value in result["metrics"].items():
            print(f"  {metric:<9} {value:.4f}")
        print(f"  wrote {result['artifacts']['model']}")
        print(f"  wrote {result['artifacts']['scaler']}")

        if mlflow_uri:
            _log_to_mlflow(result, experiment, mlflow_uri)

    if mlflow_uri:
        print(f"\nMLflow runs logged to {mlflow_uri} (experiment {experiment!r})")
    return out


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="where the retrained artefacts go; never models/",
    )
    parser.add_argument("--only", choices=sorted(SPECS_BY_NAME), default=None)
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="train on a stratified sample of this many rows instead of all of them",
    )
    parser.add_argument("--mlflow-uri", default=DEFAULT_MLFLOW_URI)
    parser.add_argument("--experiment", default="geririsk-risk-models")
    parser.add_argument("--no-mlflow", action="store_true")
    parser.add_argument(
        "--json",
        action="store_true",
        help="also print the metrics as JSON on the last line",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    committed = (HERE / "models").resolve()
    if args.output_dir.resolve() == committed:
        raise SystemExit(
            f"Refusing to write to {committed}: those artefacts are committed. "
            "Choose another --output-dir."
        )

    metrics = train_all(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        only=args.only,
        sample_size=args.sample_size,
        mlflow_uri=None if args.no_mlflow else args.mlflow_uri,
        experiment=args.experiment,
    )
    if args.json:
        print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
