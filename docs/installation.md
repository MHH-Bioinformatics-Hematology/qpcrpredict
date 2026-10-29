# Installation

`qpcrpredict` is distributed as a Bioconda package and supports Linux and macOS. Windows is not
supported. Python 3.9 or later is required and is installed together with the package. Prediction
with the released models needs no GPU. The package contains no model: download a released model bundle (see [Models](models.md#released-models)) or train your own.

## Bioconda

```bash
conda create -n qpcrpredict -c conda-forge -c bioconda qpcrpredict
conda activate qpcrpredict
qpcrpredict --version
```

`mamba` can be used in place of `conda`. The package is not distributed through pip.

## What the package contains

The Bioconda package installs all dependencies, so no further installation step is needed for any
function of the tool.

| Dependency | Used for |
|---|---|
| NumPy, pandas, SciPy, pyarrow, joblib | data handling, feature computation, model bundles |
| scikit-learn | the released models (`hist_gb`), `logreg`, `random_forest`, `extra_trees` |
| LightGBM, CatBoost | model families `lightgbm` and `catboost` |
| PyTorch, TabPFN | model families `tabpfn_v25`, `tabpfn_v26`, `tabpfn_v3` |
| openpyxl, xlrd | reading a labels table from `.xlsx` or `.xls` |

TabPFN downloads its model checkpoints on first use and needs a GPU for practical training times.
The pretrained TabPFN models are licensed for non-commercial use only, see
[License of the TabPFN families](models.md#license-of-the-tabpfn-families).
All other functions run on a CPU.

## Check the installation

```bash
qpcrpredict info
```

This prints the version, the supported targets and the available model families; with `--model` it prints the provenance of a model bundle (model family, number of training samples, creation date and cross-validation metrics).

## Galaxy

A Galaxy tool wrapper is available from the Galaxy ToolShed (owner `mhh-hematology`, tool `qpcrpredict`). An
administrator installs it like any other ToolShed tool; the Bioconda package is resolved
automatically. See [Galaxy](galaxy.md).
