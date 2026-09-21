# Features

All features are computed from the run file alone. The target family is not a feature, so one
model serves all targets.

For each sample, the ΔRn curves of the target replicate wells are averaged to one target curve,
and those of the reference-gene wells to one reference curve. The curve length is the cycle number
of the assay (40 in the default assay).

## The default representation `all` (26 features)

### Curve-shape descriptors (8 per curve, 16 in total)

Computed for the target curve (prefix `t_`) and the reference curve (prefix `r_`).

| Feature | Definition |
|---|---|
| `max` | maximum of the curve |
| `final` | value at the last cycle |
| `area` | sum over all cycles |
| `maxslope` | largest increase between two consecutive cycles |
| `cyc_maxslope` | cycle at which the largest increase occurs |
| `cyc_thr20` | first cycle at which the curve reaches 20% of its maximum (the cycle number if never) |
| `mean_last10` | mean of the last 10 cycles |
| `mean_first10` | mean of the first 10 cycles |

### Ct and quantity summary (10 features)

| Feature | Definition |
|---|---|
| `tg_ct_mean` | mean Ct of the target wells; undetermined wells and values above 50 are set to 50 |
| `tg_ct_min` | lowest Ct of the target wells, capped at 50 |
| `tg_ct_sd` | standard deviation of the target Ct values |
| `tg_n_detected` | number of target wells with a Ct value |
| `tg_n_wells` | number of target wells |
| `tg_qty_mean` | mean target quantity, as log(1+x) |
| `ref_ct_mean` | mean Ct of the reference wells, capped at 50 |
| `ref_qty_mean` | mean reference quantity, as log(1+x) |
| `ratio_calc` | target copies per 10,000 reference copies, as log(1+x) |
| `has_ref` | 1 if reference wells were found for the sample |

Missing values are imputed inside the model pipeline.

## Other representations

`--rep` selects an alternative input. These were used in the benchmark of the publication and are
kept for experiments.

| `--rep` | Features | Content |
|---|---|---|
| `all` | 26 | curve-shape descriptors of both curves and the summary (default) |
| `summary` | 10 | Ct and quantity summary only |
| `curve_feats` | 16 | curve-shape descriptors only |
| `curve_t_raw` | 40 | raw target curve |
| `curve_ta_raw` | 80 | raw target and reference curves |
| `curve_t_maxnorm` | 40 | target curve divided by its maximum |
| `curve_t_minmax` | 40 | target curve scaled to the range 0 to 1 |
| `curve_ta_refrel` | 80 | target curve minus reference curve, and the reference curve |

## Feature contributions

In the packaged model the mean target Ct is the most influential feature. By SHAP value, the
summary features account for about 65% of the total contribution, the target-curve descriptors for
about 26% and the *ABL1*-curve descriptors for about 9%.
