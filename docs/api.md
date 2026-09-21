# Python API

The command-line tools are thin wrappers around a small Python API.

## Predict

```python
from qpcrpredict.predict import predict

calls = predict("run_0100.eds", "RUNX1::RUNX1T1", quiet=True)
print(calls[["sample", "decision", "ml_prob", "review_reason"]])
```

`predict(run_path, target, model_path=None, sample=None, out_path=None, quiet=False, assay=None)`

`predict` returns a pandas DataFrame with the columns described in [Output](output.md). `model_path`
selects a model bundle, `sample` restricts scoring to one sample and `out_path` additionally writes
the table to a file.

## Train

```python
from qpcrpredict.train import fit

fit("eds/", "samples.csv", model_name="hist_gb", rep="all", out="my_model.pkl", cv=True)
```

`fit(runs_dir, labels_path, model_name="hist_gb", rep="all", out="model.pkl", cv=True, assay=None, log=print)`

## Read a run file

```python
from qpcrpredict import load_assay, load_run

assay = load_assay()                    # default assay; or a name, a JSON path or a dict
run = load_run("run_0100.eds", assay)   # .eds or .rdml
print(run["meta"])
well = run["wells"][0]
print(well["sample"], well["detector"], well["task"], well["ct"], well["qty"])
print(len(well["drn"]))      # 40 cycles
```

`load_run(path, assay)` reads an `.eds` or RDML file, computes missing quantities and
baseline-subtracted curves, and returns a dictionary with the keys `path`, `meta` and `wells`.
`parse_eds(path)` and `parse_rdml(path)` are the format-specific readers without that completion,
and `write_rdml(run, path)` writes a run as RDML.

Each well is a dictionary with the keys `well`, `sample`, `detector`, `task`, `ct`, `avg_ct`,
`ct_sd`, `qty`, `avg_qty`, `qty_sd`, `rn` and `drn`. `rn` and `drn` are the normalized and the
baseline-subtracted fluorescence curve. Wells read from RDML also carry `target_type`.

## Assay and targets

```python
from qpcrpredict import load_assay, packaged_assays

packaged_assays()                       # ['aml_mrd', 'generic']
a = load_assay("aml_mrd")
a.reference_name                        # 'ABL1'
a.target_names                          # ['NPM1', 'PML::RARA', ...]
a.resolve_target("t(8;21)")             # 'AML1_ETO'
a.normalize_target("NPM1 mut A")        # ('NPM1', 'NPM1_A', 'target')
a.is_control("Neg Ko")                  # True
```

`resolve_gene`, `normalize_target` and `GENE_CHOICES` at package level apply the default assay and
are kept for compatibility.


## Quality and review gate

`QCThresholds(...)` is a dataclass whose fields are listed in [Decision logic](decision.md).

`assess(row, classifier_call=None, T=QCThresholds(), classifier_prob=None, reference="reference", ratio_scale=10000, texts=None)` returns a dictionary with the keys `decision`, `redo`, `review`, `quality`, `reasons`, `annotations`, `recommendation` and, for deferred samples, `review_reasons` and `model_call`. `row` needs the fields `ref_qty_mean`, `r2_target`, `r2_ref`, `tg_n_below_cutoff`, `tg_n_wells`, `ratio_calc` and `tg_ct_mean`. `QCThresholds.from_dict(assay.qc)` builds the thresholds of an assay.

`assess_frame(df, calls=None, probs=None, T=QCThresholds())` applies the same rules to every row of a DataFrame.


See [Decision logic](decision.md) for the rules and an example.

## Model bundles

`load_bundle(path=None)` loads a bundle, or the packaged model if no path is given. `save_bundle(bundle, path)` writes a bundle and its `.json` provenance file.

```python
from qpcrpredict.bundle import load_bundle

bundle = load_bundle()                 # packaged model
bundle = load_bundle("my_model.pkl")   # own model
print(bundle["model_name"], bundle["n_train"], bundle["cv_metrics"])

from qpcrpredict.bundle import bundle_assay
assay = bundle_assay(bundle)           # the assay the model was trained with
```

