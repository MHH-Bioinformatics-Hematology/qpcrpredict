# qpcrpredict

*Part of the **LeukoPredict** tools: trained calls from the raw data of diagnostic instruments,
developed for leukemia diagnostics at Hannover Medical School.*

`qpcrpredict` predicts the positive or negative call of a real-time PCR assay directly from the raw
run file of the instrument. It reads Applied Biosystems `.eds` files and the vendor-neutral RDML
format. It was developed for the qualitative molecular measurable residual disease (MRD) result in
acute myeloid leukemia (AML), and the packaged model covers that application.

In routine diagnostics this call is made by a laboratory scientist who inspects the Ct values, the
amplification curves and the run-acceptance criteria in the instrument software. `qpcrpredict` reads the
same raw data, applies a trained classifier and the run-acceptance rules, and returns one of four
decisions per sample:

| Decision | Meaning |
|---|---|
| `positive` | the target transcript is detected |
| `negative` | the target transcript is not detected |
| `review` | the result is borderline and is deferred to a human |
| `na` | the run is not assessable for this sample and should be repeated |

Every `review` and `na` decision comes with the reason and a recommended action. The tool is a
decision-support step. It prepares the call; a laboratory scientist reviews and approves every run.

The packaged model and the default assay cover mutated *NPM1*, *RUNX1::RUNX1T1*, *CBFB::MYH11*,
*PML::RARA* and *BCR::ABL1*, each quantified against the reference gene *ABL1*. Nothing of this is
fixed in the code: targets, reference gene, control names and thresholds are defined in an
[assay configuration](assay.md), so the tool can be trained for any standard-curve qPCR assay.

!!! warning "Intended use"
    `qpcrpredict` is research software. It is not a certified in vitro diagnostic device. The packaged model
    was trained on the data of one laboratory, one instrument type and one set of assays. Validate it on
    your own data, or train your own model, before relying on its output.

## The LeukoPredict tools

| Tool | Instrument data | Purpose |
|---|---|---|
| `qpcrpredict` | real-time PCR run files (`.eds`, RDML) | positive/negative call of a qPCR assay; packaged model for AML molecular MRD |
| `cepredict` | capillary electrophoresis traces (`.fsa`) | mutation and fusion calls from fragment analysis (in preparation) |

The tools share one design: features come only from the raw instrument file, a trained model makes
the call, a rule-based gate defers what is uncertain, and everything assay-specific is
configuration, not code.
