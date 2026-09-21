# Output

`qpcrpredict predict --out` writes a tab-separated table with one row per sample. The Python function
`qpcrpredict.predict.predict` returns the same table as a pandas DataFrame.

## Columns

| Column | Description |
|---|---|
| `sample` | Sample name as written on the plate. |
| `target` | Target as given on the command line. |
| `family` | Target family of the assay configuration, for example `NPM1` or `AML1_ETO`. |
| `run_date` | Run date from the run file. |
| `decision` | Final decision: `positive`, `negative`, `review` or `na`. `not_found` if a sample requested with `--sample` has no wells of the target. |
| `redo` | `True` if the sample is not assessable and the measurement should be repeated. |
| `review` | `True` if the sample is deferred to human classification. |
| `model_call` | Call of the classifier alone, before the gate: `positive` or `negative`. |
| `ml_prob` | Classifier probability that the sample is positive, between 0 and 1. |
| `quality` | Material quality from the reference copy number: `sufficient`, `limited`, `insufficient` or `unknown`. |
| `ref_qty_mean` | Mean copy number of the reference gene over the replicate wells. |
| `r2_target` | R² of the standard curve of the target assay. |
| `r2_ref` | R² of the standard curve of the reference gene. |
| `tg_ct_mean` | Mean Ct of the target wells. |
| `tg_n_below_cutoff` | Number of target replicate wells with a Ct below the detection cutoff of the assay (41 in the default assay). |
| `ratio` | Target copies per 10,000 reference copies (the scale is set by `ratio_scale`). |
| `reason` | Why a sample is not assessable. Empty otherwise. |
| `review_reason` | Why a sample is deferred to review. Empty otherwise. |
| `annotation` | Remarks that do not change the decision, for example limited material or MRD at low level. |
| `recommendation` | Recommended action for `review` and `na` decisions. |

## Example

```text
     sample         target decision model_call  ml_prob      quality  ref_qty_mean  tg_ct_mean  tg_n_below_cutoff   ratio
Sample 1345 RUNX1::RUNX1T1 positive   positive   0.9999   sufficient       10630.9       35.61                  3    20.6
 Sample 831 RUNX1::RUNX1T1 negative   negative   0.0000   sufficient       18264.5       49.63                  0     0.0
 Sample 533 RUNX1::RUNX1T1   review   negative   0.0203   sufficient       11388.1       40.24                  2     2.0
Sample 2612 RUNX1::RUNX1T1       na   positive   0.9999 insufficient         653.3       30.30                  3 11950.4
```

Columns are abridged in this example.

## Reading the result

`decision` is the value to act on. `model_call` and `ml_prob` show what the classifier alone would
have said and explain a `review` decision: a sample with `model_call = negative` and
`tg_n_below_cutoff = 2` is deferred because the classifier and the replicate rule disagree.
