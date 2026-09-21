# Performance

All figures are from the accompanying publication and refer to the data of one laboratory. They
describe agreement with the call reported by that laboratory.

## Locked temporal test

The model was developed on the runs from 2019 to 2023 (1,223 samples) and evaluated once on the
674 samples from 2024 to 2025, which were not used in any development step.

| Metric | `hist_gb` |
|---|---|
| ROC-AUC | 0.986 |
| PR-AUC | 0.994 |
| F2 | 0.950 |
| Recall | 0.942 |
| Specificity | 0.957 |
| Brier score | 0.048 |

With the quality and review gate, 91.7% of the samples received an automatic positive or negative
call, 4.5% were deferred to review and 3.9% were marked for repetition. The automatic calls agreed
with the laboratory in 98.1%.

## Cross-validation on all data

Grouped 5-fold cross-validation over all 1,897 samples:

| Model | Recall | Specificity | F2 | ROC-AUC |
|---|---|---|---|---|
| `hist_gb` | 0.974 | 0.940 | 0.974 | 0.991 |
| `tabpfn_v26` | 0.972 | 0.951 | 0.974 | 0.991 |
| `lightgbm` | 0.971 | 0.949 | 0.972 | 0.991 |
| `extra_trees` | 0.971 | 0.944 | 0.972 | 0.989 |
| `catboost` | 0.965 | 0.949 | 0.967 | 0.992 |
| `random_forest` | 0.962 | 0.958 | 0.966 | 0.989 |
| `logreg` | 0.943 | 0.959 | 0.950 | 0.987 |

## Comparison with the replicate rule

The objective replicate rule alone (at least 2 of 3 wells with Ct below 41) is more sensitive than
the model (recall 0.987 against 0.974) and less specific (0.889 against 0.940). The rule returns
only yes or no, whereas the model returns a probability that identifies the uncertain samples.
Within the same gate, 3.2% of the samples were deferred to review with the model and 36.0% with
the rule.

## Limitations

- Single center, one instrument type, one set of assays.
- The reference is the reported laboratory call, which itself has a small disagreement rate
  between repeated evaluations of the same plate.
- *BCR::ABL1* is represented by very few samples.
- Simulated instrument drift changes the calibrated metrics more than the ranking metrics, so the
  probability threshold should be verified on local data.
