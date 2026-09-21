# Models

## Model families

| `--model` | Family | Note |
|---|---|---|
| `hist_gb` | histogram-based gradient boosting (scikit-learn) | default |
| `logreg` | logistic regression | |
| `random_forest` | random forest | |
| `extra_trees` | extremely randomized trees | |
| `lightgbm` | LightGBM | |
| `catboost` | CatBoost | |
| `tabpfn_v25`, `tabpfn_v26`, `tabpfn_v3` | TabPFN | GPU recommended for training |

All families are installed with the package. They are trained on the same features and return a probability, so the quality and review
gate works identically with each of them.

## The packaged model

| Property | Value |
|---|---|
| Family | `hist_gb` |
| Representation | `all` (26 features) |
| Training samples | 1,897 (1,330 positive, 567 negative) |
| Targets | *NPM1*, *RUNX1::RUNX1T1*, *CBFB::MYH11*, *PML::RARA*, *BCR::ABL1* |
| Period | 2019 to 2025, single center |

`hist_gb` was chosen as the default because it needs only scikit-learn, trains in seconds, handles
missing values natively and was the best family on the held-out temporal test of the publication.
The differences between the top families are small, see [Performance](performance.md).

## Choosing a family for your own data

Start with `hist_gb`. Compare families with the cross-validation report of `qpcrpredict train`, and
confirm the choice on a temporal hold-out, because the ranking on cross-validation and on later
data can differ. TabPFN needs a GPU for practical training times.
