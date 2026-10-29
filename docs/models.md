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
stores it in the bundle. `qpcrpredict predict --disallow-family tabpfn` refuses such bundles. The
Galaxy tool sets this option unless the server operator has enabled TabPFN models, see
[Galaxy](galaxy.md#tabpfn-models). All other model families, including the packaged `hist_gb`
model, carry no such restriction. In the laboratory of the authors no TabPFN model is deployed for
this reason. Built with PriorLabs-TabPFN.

## The packaged models

Two models are shipped. `--model` accepts a path to a bundle or the name of a packaged model.

| `--model` | Labels it was trained on | Thresholds of its gate |
|---|---|---|
| `aml_mrd` (default) | the calls of the laboratory as reported, 2019 to 2025 | laboratory SOP: a well counts as amplified below Ct 41; a negative call needs at least 1,000 *ABL1* copies, 1,000 to 9,999 is annotated as limited |
| `aml_mrd_eln2025` | the same calls, overridden where the 2025 ELN MRD update gives a definite different answer: at least 2 of 3 wells below Ct 40 is positive, fewer with at least 10,000 *ABL1* copies is negative, fewer with fewer copies is not evaluable and was excluded | ELN 2025: Ct 40 per well, 10,000 *ABL1* copies for a negative call |

The `aml_mrd_eln2025` model was trained on 1,271 analyses (944 positive, 327 negative) of 510 patients; 216 analyses of the modeling set were not evaluable under the 2025 thresholds and 38 calls were overridden. Choose it where the laboratory reports under the 2025 update.

### aml_mrd

| Property | Value |
|---|---|
| Family | `hist_gb` |
| Representation | `all` (26 features) |
| Training analyses | 1,487 (1,044 positive, 443 negative) from 534 patients who agreed to the publication of their data |
| Targets | *NPM1*, *RUNX1::RUNX1T1*, *CBFB::MYH11*, *PML::RARA*, *BCR::ABL1* |
| Period | 2019 to 2025, single center |

`hist_gb` was chosen as the default because it needs only scikit-learn, trains in seconds, handles
missing values natively and was the best family on the held-out temporal test of the publication.
The differences between the top families are small, see [Performance](performance.md).

## Choosing a family for your own data

Start with `hist_gb`. Compare families with the cross-validation report of `qpcrpredict train`, and
confirm the choice on a temporal hold-out, because the ranking on cross-validation and on later
data can differ. TabPFN needs a GPU for practical training times.
