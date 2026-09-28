# Performance

All figures are from the accompanying publication and refer to the data of one laboratory. They
describe agreement with the call reported by that laboratory.

## Locked temporal test

The model was developed on the analyses from 2019 to 2023 (944 analyses, 401 patients) and
evaluated once on the 543 analyses from 2024 to 2025 (205 patients), which were not used in any
development step. Only patients who agreed to the publication of their data are included.

| Metric | `hist_gb` |
|---|---|
| ROC-AUC | 0.984 |
| PR-AUC | 0.993 |
| F2 | 0.936 |
| Recall | 0.925 |
| Specificity | 0.965 |
| Brier score | 0.052 |

With the quality and review gate, 90.2% of the analyses received an automatic positive or negative
call, 6.3% were deferred to review and 3.5% were marked for repetition. The automatic calls agreed
with the laboratory in 98.6%.

## Cross-validation on all data

Patient-grouped 5-fold cross-validation over all 1,487 analyses:

| Model | Recall | Specificity | F2 | ROC-AUC |
|---|---|---|---|---|
| `hist_gb` | 0.976 | 0.939 | 0.976 | 0.990 |
| `tabpfn_v26` | 0.974 | 0.948 | 0.975 | 0.990 |
| `tabpfn_v3` | 0.973 | 0.941 | 0.974 | 0.990 |
| `extra_trees` | 0.972 | 0.937 | 0.972 | 0.989 |
| `lightgbm` | 0.970 | 0.944 | 0.971 | 0.990 |
| `tabpfn_v25` | 0.969 | 0.944 | 0.971 | 0.990 |
| `catboost` | 0.964 | 0.946 | 0.966 | 0.990 |
| `random_forest` | 0.962 | 0.946 | 0.965 | 0.987 |
| `logreg` | 0.936 | 0.953 | 0.944 | 0.984 |

## Comparison with the replicate rule

The objective replicate rule alone (at least 2 of 3 wells with Ct below 41) is more sensitive than
the model (recall 0.986 against 0.976) and less specific (0.892 against 0.939). The rule returns
only yes or no, whereas the model returns a probability that identifies the uncertain samples.
Within the same gate, 3.2% of the analyses were deferred to review with the model and 36.1% with
the rule.

## Limitations

- Single center, one instrument type, one set of assays.
- The reference is the reported laboratory call, which itself has a small disagreement rate
  between repeated evaluations of the same plate.
- *BCR::ABL1* is represented by very few samples.
- Simulated instrument drift changes the calibrated metrics more than the ranking metrics, so the
  probability threshold should be verified on local data.
