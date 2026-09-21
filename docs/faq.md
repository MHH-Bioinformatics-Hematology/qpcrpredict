# Frequently asked questions

## Does qpcrpredict replace the laboratory scientist?

No. The tool makes the first-pass interpretation. Every run is still reviewed and approved by a
person, and samples with a `review` or `na` decision need full manual inspection.

## Do I need a sample sheet that lists the genes?

No. The detector name and the sample name of every well are stored in the run file, and the
[assay configuration](assay.md) defines how they are interpreted: which detectors are targets,
which one is the reference gene, and which sample names are controls. A table is needed only for
training, where it supplies the labels.

## Why is a clearly amplified sample reported as `na`?

The decision is `na` when the run-acceptance criteria are not met, independent of the target
signal. The most frequent reason is an *ABL1* copy number below 1,000. The `reason` column states
which criterion failed.

## Why is a sample reported as `review` although the probability is close to 0 or 1?

The sample is deferred when the classifier and the replicate rule disagree, independent of the
probability. A typical case is a late, low amplification in 2 of 3 wells that the classifier
recognizes as the curve of a negative sample. The `review_reason` column names the conflict.

## The command stops with "no patient samples for gene ... found"

The message lists the detector names on the plate. Either the run does not contain the target, or
the detector spelling is not recognized. See [Input data](input.md).

## My sample is missing from the result

Check that the target wells and the *ABL1* wells carry exactly the same sample name, and that the
name is not interpreted as a control, for example because it starts with `pos` or `neg `.

## Can I use run files of another instrument?

Yes, through RDML. Most qPCR software can export RDML, and `qpcrpredict` reads it like an `.eds` file,
see [Input data](input.md). The packaged model was trained on one instrument type, so for another
instrument train your own model, or at least verify the packaged one on your own labeled runs.
The native `.eds` reader covers the format written by the 7500 Software (versions 2.x).

## Can I use other targets, another reference gene or a different cycle number?

Yes. None of this is fixed in the code. Write an [assay configuration](assay.md) with your
targets, reference gene, control names, cycle number and thresholds, and train a model with it.

## Can I change the thresholds?

Yes. The thresholds are part of the assay configuration that is stored in the model bundle. Pass
a modified configuration with `--assay` to `qpcrpredict predict`, see [Decision logic](decision.md).
Changing them does not require retraining.

## Are results reproducible?

Prediction is deterministic for a given model bundle and software version. Training draws the
cross-validation folds anew, so the reported metrics vary slightly between runs.

## Does it run on Windows?

No. `qpcrpredict` is distributed through Bioconda, which provides packages for Linux and macOS only.
Run files from the Windows instrument computer are transferred to a Linux or macOS machine, or to
a Galaxy server, for prediction.

## Does the tool send data anywhere?

No. All processing is local. Run files contain sample names, operator names and dates, so treat
them as patient-related data.
