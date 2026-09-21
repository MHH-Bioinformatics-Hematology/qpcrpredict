# Decision logic

The classifier alone returns a probability. The quality and review gate turns this probability
into the reported decision by applying the run-acceptance rules of the laboratory and by deferring
ambiguous samples to a human. The gate is rule-based, fully transparent and configurable.

## Step 1: is the sample assessable?

A sample is not assessable (`decision = na`, `redo = True`) if one of the following holds.

| Check | Default threshold | Recommendation |
|---|---|---|
| reference gene missing | | repeat the run |
| reference copies too low | below 1,000 copies | repeat with newly synthesized cDNA |
| reference standard curve not linear | R² below 0.95 | repeat the run |
| target standard curve not linear | R² below 0.95 | repeat the run |

The thresholds and the recommendation texts shown here are those of the default assay; all are
set in the [assay configuration](assay.md). The material quality is reported for every sample: sufficient at 10,000 reference copies or more,
limited between 1,000 and 10,000 copies, insufficient below 1,000 copies. Limited material does not
block the call but is added as an annotation.

## Step 2: classifier call and replicate rule

For an assessable sample two calls are made.

Classifier call
: positive if the probability reaches the decision threshold (0.5), negative otherwise.

Replicate rule
: positive if at least 2 of the 3 target replicate wells have a Ct below 41. This is the objective
  criterion of the laboratory's standard operating procedure.

## Step 3: is the sample ambiguous?

A sample is deferred to human classification (`decision = review`) if

- the classifier is not confident, that is the probability lies between 0.35 and 0.65, or
- the classifier call and the replicate rule disagree.

The `review_reason` column states which condition applied. Otherwise the classifier call is
reported as `positive` or `negative`.

## Annotations

Annotations never change the decision. They are added for

- limited material (1,000 to 10,000 reference copies),
- a weak positive, where fewer than 2 replicate wells have a Ct below 41,
- a low-level positive, where a positive sample has fewer than 250 target copies per 10,000
  reference copies. The wording of this annotation is set in the assay configuration
  ("MRD at low level" in the default assay).

## Thresholds

All thresholds are set in the `qc` section of the assay configuration and correspond to the fields
of `qpcrpredict.QCThresholds`. The configuration is stored inside the model bundle, so a trained model
always carries the thresholds it was built with.

| Field | Default | Meaning |
|---|---|---|
| `ref_sufficient` | 10000 | reference copies at or above this value: sufficient material |
| `ref_insufficient` | 1000 | reference copies below this value: not assessable |
| `r2_min` | 0.95 | minimal R² of the standard curves |
| `ct_pos_max` | 41 | a well counts as detected below this Ct |
| `min_pos_replicates` | 2 | detected wells required by the replicate rule |
| `low_level_ratio` | 250 | ratio below which a positive is annotated as low level |
| `decision_threshold` | 0.5 | probability at or above which the classifier call is positive |
| `enable_review` | True | switch the review tier on or off |
| `review_prob_lo` | 0.35 | lower bound of the probability band that triggers review |
| `review_prob_hi` | 0.65 | upper bound of the probability band that triggers review |
| `review_flag_discordant` | False | also defer samples with exactly 1 detected replicate |
| `review_ct_lo`, `review_ct_hi` | 39, 42 | Ct band used only when no probability is available |

The defaults follow the standard operating procedure of the laboratory in which the tool was
developed. The decision threshold of 0.5 and the review band were fixed in advance and were not
tuned on the data.

## Using the gate from Python

```python
from qpcrpredict import QCThresholds, assess

T = QCThresholds(ref_insufficient=2000, review_prob_lo=0.30, review_prob_hi=0.70)
row = dict(ref_qty_mean=15800, r2_target=0.998, r2_ref=0.995,
           tg_n_below_cutoff=1, tg_n_wells=3, ratio_calc=0.8, tg_ct_mean=40.6)
result = assess(row, T=T, classifier_prob=0.41, reference="ABL1")
print(result["decision"], result["review_reasons"])
```
