# Training data

Three labelled CSVs, one per risk model. `../train.py` reads them from here.

| File | Rows | Feature columns | Label column |
|------|------|-----------------|--------------|
| `cardiac_risk_training_data.csv` | 999 | `avgHeartRate`, `maxHeartRate`, `minHeartRate`, `minSpO2`, `totalSteps`, `recordCount` | `cardiac_risk_label` |
| `fall_risk_training_data.csv` | 999 | `avgHeartRate`, `totalSteps`, `recordCount` | `fall_risk_label` |
| `respiratory_risk_training_data.csv` | 999 | `minSpO2`, `avgHeartRate`, `recordCount` | `respiratory_risk_label` |

The column order in each file is the feature order `main.py` builds its vectors
in, and the order recorded in each committed artefact's `feature_names_in_`.

## Source and attribution

Copied unmodified from [`atharvapawar9/GeriRisk`](https://github.com/atharvapawar9/GeriRisk),
path `GeriRiskCSVs/`, at commit `8c0d0e81`. Author: **atharvapawar9**. Licensed
**MIT** (`Copyright (c) 2026 Atharva`).

## Labels are rule-derived

These labels are not clinical outcomes. A single threshold on one column
recovers almost all of each label, so any model trained on them scores near
100%. See the "Model training" section of the repository README for the
measurements.
