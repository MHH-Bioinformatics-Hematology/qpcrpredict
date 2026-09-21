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
| `tabpfn_v25`, `tabpfn_v26`, `tabpfn_v3` | TabPFN | GPU recommended for training; non-commercial license, see below |

All families are installed with the package. They are trained on the same features and return a probability, so the quality and review
gate works identically with each of them.

## License of the TabPFN families

The pretrained TabPFN models (`tabpfn_v25`, `tabpfn_v26`, `tabpfn_v3`) are licensed by Prior Labs
GmbH under the TabPFN Non-Commercial Licenses. A model bundle of these families contains the
pretrained model, so the license applies to the bundle as well.

- **Allowed:** academic, non-commercial research, including benchmarking and evaluation.
- **Requires a commercial license from Prior Labs GmbH:** use in a commercial setting, in routine
  diagnostics or any other production deployment, and offering the model as part of a hosted
  service.
- **When you distribute a TabPFN bundle:** include the license text and the attribution notice of
  the TabPFN version, state that the bundle is a derivative, and keep "TabPFN" at the beginning of
  the model name. The public data deposit shows this layout, see [Public data](data.md).

`qpcrpredict` prints this license note when a TabPFN bundle is trained, inspected or used, and
stores it in the bundle. `qpcrpredict predict --disallow-family tabpfn` refuses such bundles; the
Galaxy tool always sets this option. All other model families, including the packaged `hist_gb`
model, carry no such restriction. In the laboratory of the authors no TabPFN model is deployed for
this reason. Built with PriorLabs-TabPFN.

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
