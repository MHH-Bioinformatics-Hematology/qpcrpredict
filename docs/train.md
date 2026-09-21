# Training

```text
qpcrpredict train --runs-dir DIR --labels LABELS [--assay ASSAY] [--model MODEL] [--rep REP]
             [--out OUT] [--no-cv]
```

`qpcrpredict-train` is an equivalent stand-alone entry point.

Train your own model if your assays, instrument settings or reporting rules differ from those of
the packaged model, or to update a model with new data.

## Parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `--runs-dir` | yes | | Folder with the run files (`.eds` or `.rdml`). Subfolders are searched. `--eds-dir` is accepted as an alias. |
| `--labels` | yes | | Labels table, see below. CSV, TSV, `.xls` or `.xlsx`. |
| `--assay` | no | `aml_mrd` | Assay configuration: packaged name or JSON file, see [Assay configuration](assay.md). It is stored in the model bundle. |
| `--model` | no | `hist_gb` | Model family, see [Models](models.md). |
| `--rep` | no | `all` | Feature representation, see [Features](features.md). |
| `--out` | no | `model.pkl` | Path of the model bundle to write. A `.json` file with the provenance is written next to it. |
| `--no-cv` | no | off | Skip the cross-validation report and only fit the final model. |

## Labels table

One row per sample and target.

| Column | Required | Accepted header names | Content |
|---|---|---|---|
| sample | yes | `sample_id`, `sample`, `sample name`, `samplename` | sample name exactly as on the plate (case is ignored) |
| target | yes | `target`, `gene`, `target name`, `detector`, `assay` | target, in any spelling accepted by `--target` |
| label | yes | `label`, `class`, `result`, `y` | `positive` or `negative`; short forms such as `pos` and `neg` are accepted |
| run file | no | `run_file`, `eds_file`, `rdml_file`, `file`, `filename` | file name of the run that contains the sample |

Give the run file whenever a sample name can occur in more than one run. Without it, the sample is
looked up in all run files. Rows with a label other than positive or negative are ignored. Further
columns are allowed and ignored. The accepted header names and label words are part of the assay
configuration and can be extended there.

```text
sample_id,gene,label,eds_file
Sample 1345,AML1_ETO,positive,run_0100.eds
Sample 1682,AML1_ETO,negative,run_0100.eds
Sample 2393,AML1_ETO,positive,run_0100.eds
```

## What the command does

1. For every labeled row, the sample is located in its run file and the features are computed.
   Rows for which no matching wells are found are counted and reported.
2. Unless `--no-cv` is given, grouped stratified 5-fold cross-validation is run and ROC-AUC,
   PR-AUC, accuracy, precision, recall, specificity, F1, F2 and MCC are printed. Rows that share a
   sample identifier always fall into the same fold, so repeated measurements of one sample cannot
   leak between training and test folds.
3. The final model is fit on all labeled rows and saved.

```text
[features] 1897 samples featurised (0 labelled rows had no matching wells)
[fit] 1897 samples | pos=1330 neg=567 | rep=all | model=hist_gb
[fit] patient-grouped 5-fold CV ...
      roc_auc=0.9919  pr_auc=0.9968  accuracy=0.9668  precision=0.9788  recall=0.9737
      specificity=0.9506  f1=0.9763  f2=0.9747  mcc=0.9211
[fit] training final model on ALL samples ...
[fit] saved model bundle -> my_model.pkl
```

Training on about 1,900 samples takes a few seconds with `hist_gb` on a standard workstation.

## The model bundle

The `.pkl` file is a joblib dictionary that holds everything needed for prediction.

| Key | Content |
|---|---|
| `pipeline` | fitted scikit-learn pipeline (imputation, scaling where needed, classifier) |
| `rep` | feature representation |
| `model_name` | model family |
| `classes` | `["neg", "pos"]` |
| `feature_dim` | number of features |
| `n_train` | number of training samples |
| `assay` | the complete assay configuration used for training, including the thresholds of the gate |
| `cv_metrics` | cross-validation metrics, if computed |
| `created` | creation date |

`qpcrpredict info --model my_model.pkl` prints this information.

!!! warning "Security"
    Model bundles are pickle files. Loading a pickle file executes code. Only load bundles that you
    created yourself or that come from a source you trust.

## Recommendations

- Use labels that were reported by your laboratory, not labels derived from the Ct values, so the
  model learns the expert call and not the replicate rule.
- Keep a temporal hold-out: train on the earlier years and evaluate once on the most recent data
  before you put a model into use.
- Keep scikit-learn at the same minor version for training and prediction.
