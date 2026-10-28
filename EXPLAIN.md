# EXPLAIN: the four metrics, and what they say about this project

Every number here is from `ml-api/train.py` on the data in
`ml-api/training_data/`. Nothing is illustrative or made up.

---

## 1. The one table everything comes from

The cardiac model, scored on the 300 rows it was not trained on. 165 of those
rows carry label 1 and 135 carry label 0. The model's predictions land like
this:

|  | model says 1 | model says 0 |
|--|--------------|--------------|
| **actually 1** | TP = 163 | FN = 2 |
| **actually 0** | FP = 0 | TN = 135 |

Four letters, and the four metrics are all built from them.

- **TP** (true positive): flagged, and the label agreed.
- **FP** (false positive): flagged, and the label did not. A false alarm.
- **FN** (false negative): not flagged, but the label said 1. A miss.
- **TN** (true negative): not flagged, and the label agreed.

---

## 2. Precision

> Of the rows the model flagged, what fraction should have been flagged?

```
precision = TP / (TP + FP) = 163 / (163 + 0) = 1.0000
```

The cardiac model flagged 163 rows and every one of them was a 1. It never
cried wolf.

**Precision is the metric you care about when acting on a flag is expensive.**
If a flag pages a nurse at 3am, low precision means a tired nurse who stops
trusting the system.

Precision ignores the FN box entirely. A model that flags exactly one row, and
is right about it, has precision 1.0 and is useless.

---

## 3. Recall

> Of the rows that should have been flagged, what fraction did the model find?

```
recall = TP / (TP + FN) = 163 / (163 + 2) = 0.9879
```

Two of the 165 real positives slipped through. This is the only metric in the
cardiac row that is not a perfect 1.0, and those two rows are the entire reason.

**Recall is the metric you care about when missing something is expensive.** In
a screening tool, a miss is the harm you were trying to prevent.

Recall ignores the FP box. A model that flags every single row has recall 1.0,
precision equal to the base rate, and tells you nothing.

### Precision and recall pull against each other

`main.py` turns a probability into a label at a fixed cut (`>= 0.75` High,
`>= 0.40` Moderate). Lower the cut and you flag more rows: recall rises, and
precision falls as false alarms creep in. Raise it and the reverse happens.
There is no setting that improves both. Which way you move the cut is a
judgement about which mistake costs more, and it is not a modelling question.

---

## 4. F1

> One number that refuses to let either precision or recall off the hook.

F1 is the harmonic mean of the two:

```
F1 = 2 * (precision * recall) / (precision + recall)
   = 2 * (1.0000 * 0.9879) / (1.0000 + 0.9879)
   = 0.9939
```

The harmonic mean matters. A plain average of precision 1.0 and recall 0.0
would be a respectable-looking 0.5; F1 is 0.0. **F1 is near zero if either
input is near zero,** which is exactly the discipline you want when a single
number has to stand in for two.

Use F1 to compare models when you have no stated preference between a miss and
a false alarm. The moment you do have a preference, report precision and recall
separately and stop hiding behind one number.

---

## 5. ROC AUC

The first three metrics judge the model *after* its probabilities have been cut
into labels. ROC AUC judges the probabilities themselves and ignores the cut.

> Pick one random positive row and one random negative row. What is the chance
> the model gave the positive one the higher score?

```
roc_auc = 1.0000   (cardiac)
```

1.0 means the ranking is perfect: **every** one of the 165 positives scored
above **every** one of the 135 negatives. There exists a threshold that
separates them completely.

Note what this reveals when read against recall. Recall was 0.9879 because two
positives fell below the fixed `0.5` decision boundary, yet AUC is 1.0 because
those same two still scored above all 135 negatives. **Those two rows are a
threshold problem, not a ranking problem.** That is the distinction AUC exists
to make, and no amount of retraining fixes a badly placed cut.

One warning: AUC is computed over all thresholds, including absurd ones. On
heavily imbalanced data it can look healthy while the model is useless at any
threshold you would actually ship. Here the classes are near even (55/45), so
that trap does not apply.

---

## 6. So the models are excellent?

No. Here is the full table:

| Model | Precision | Recall | F1 | ROC AUC |
|-------|-----------|--------|----|---------|
| Cardiac | 1.0000 | 0.9879 | 0.9939 | 1.0000 |
| Fall | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Respiratory | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Two models are perfect on all four metrics. **In machine learning that is not a
result, it is a symptom.** Something has leaked, or the task is trivial. Here it
is the second.

Fitting a **depth-1** decision tree, a single `if` on a single column, on the
same 699 training rows gives this on the same 300 held-out rows:

| Dataset | The entire model | Held-out accuracy |
|---------|------------------|-------------------|
| Fall | `totalSteps <= 120` then 1, else 0 | 1.0000 |
| Respiratory | `avgHeartRate <= 91.95` then 0, else 1 | 1.0000 |
| Cardiac | `totalSteps <= 202.5` then 1, else 0 | 0.9933 |

A 200-tree random forest and a single comparison score the same, because
**the labels were generated by a threshold rule.** They are synthetic. No
patient outcome is recorded anywhere in these files.

So the honest reading of 1.0000 across the board is: *the models successfully
recovered the rule that generated the data.* That is a working pipeline, and it
is worth having a working pipeline. It is not evidence about cardiac, fall or
respiratory risk in a human being, and it must never be presented as such.

---

## 7. Ten questions you will be asked about this

**1. Why report precision and recall separately when you already have F1?**
F1 collapses them, and the two failure modes cost different things. A fall
detector that misses falls and one that cries wolf can share an F1 and need
opposite fixes. F1 is for ranking models; precision and recall are for
deciding whether to ship one.

**2. Accuracy is the obvious metric. Why is it not in the table?**
Because it rewards the majority class for free. At a 95/5 split, predicting
"no" every time scores 95%. Precision and recall are both defined on the
positive class, so a model that never predicts it scores zero, which is the
correct verdict. Here the classes are near even so accuracy would have been
informative, but reporting it would train the habit of trusting it when the
classes are not.

**3. Your ROC AUC is 1.0 but recall is 0.9879. Is one of them wrong?**
Neither. AUC scores the ranking, recall scores the labels after the threshold.
Two positives scored above all 135 negatives, so the ranking is perfect, but
they still landed below the 0.5 cut, so they count as misses. It localises the
problem to the threshold.

**4. When would you use PR AUC instead of ROC AUC?**
When positives are rare. ROC AUC's false-positive rate has the large negative
count in its denominator, so a flood of false positives barely moves it.
Precision-recall AUC puts false positives against true positives, which is the
trade-off you actually feel. On a 1-in-1000 outcome, use PR AUC.

**5. `class_weight="balanced"` is set on all three models. What does it do, and
does it matter here?**
It scales each class's contribution to the loss by the inverse of its
frequency, so the minority class cannot be ignored cheaply. Here the splits are
44.8/55.2 and 49.9/50.1, so it changes almost nothing. It is defensible
insurance, not a fix for anything in this data.

**6. Why fit the `StandardScaler` on the training rows only?**
Because fitting it on everything leaks the held-out rows' mean and variance
into training, and the score comes out flattering and wrong. `train.py` fits
the scaler inside the split. Separately, the random forest does not need
scaling at all, trees being invariant to monotone per-feature transforms; it is
there because the serving path in `main.py` applies a scaler to all three.

**7. How do you know the train/test split was `test_size=0.3, random_state=42,
stratify=y` if it was never written down?**
It was not assumed, it was searched. All three committed scalers report
`n_samples_seen_ == 699` of 999 rows. Refitting a scaler for every combination
of `test_size` in {0.3, 300}, `random_state` 0 to 200, and `stratify` on and
off, exactly one reproduces all three scalers' `mean_` and `scale_` to within
`1e-9`. The unstratified variants give the same 699 count but different
statistics, which is what makes `stratify=y` a finding rather than a guess.

**8. Why pin `scikit-learn==1.6.1` exactly instead of a compatible range?**
Because a pickle is not a format, it is a snapshot of object state. All six
artefacts carry `_sklearn_version == "1.6.1"`; loading them under another
release raises `InconsistentVersionWarning` and carries no promise that the
estimator still behaves identically. The previous `~=1.5.2` range could not
even load them cleanly. The pin moves only when the artefacts are retrained.

**9. Two LogisticRegression models reproduce their predictions but not their
coefficients. Why, and does it matter?**
The iteration counts match exactly (12 and 10), the split matches, and
scikit-learn is the same 1.6.1, so the data and the settings are right; the
coefficients differ by up to 3%, which points at a different SciPy L-BFGS-B
build. It does not matter for serving, since the held-out predictions are
identical, and it was not pinned down further. The cardiac forest is the real
gap: its tree-depth histogram is inconsistent with any fit on those 699 rows,
so its training set is genuinely unknown.

**10. If the labels are synthetic, what was the point of any of this?**
To make the pipeline honest and repeatable. There is now a recovered split, a
pinned library version, a script that retrains from source data with a fixed
seed, metrics on held-out rows, MLflow runs, tests that the shipped artefacts
still load and predict, and a written statement that the labels are
rule-derived. When real labelled data arrives, the only thing that changes is
the CSVs. The alternative, three undocumented pickles and no idea how they were
made, is the thing that cannot be improved.
