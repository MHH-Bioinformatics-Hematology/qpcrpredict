# Prediction

```text
qpcrpredict predict --run RUN --target TARGET [--model MODEL] [--assay ASSAY]
               [--disallow-family PREFIX] [--sample SAMPLE] [--out OUT] [--quiet]
```

`qpcrpredict-predict` is an equivalent stand-alone entry point.

## Parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `--run` | yes | | One run file, `.eds` or `.rdml`. `--eds` is accepted as an alias. |
| `--target` | yes | | Target to score: a target name or alias of the assay, or a detector name as written on the plate. For the default assay: `NPM1`, `RUNX1::RUNX1T1`, `CBFB::MYH11`, `PML::RARA`, `BCR::ABL1`, and spellings such as `t(8;21)` or `inv16`. `--gene` is accepted as an alias. |
| `--model` | no | packaged model | Model bundle (`.pkl`) written by `qpcrpredict train`. |
| `--assay` | no | from the model | Assay configuration (packaged name or JSON file) that overrides the one stored in the model bundle. |
| `--disallow-family` | no | | Refuse model bundles of this family, for example `tabpfn`, see [License of the TabPFN families](models.md#license-of-the-tabpfn-families). May be repeated. |
| `--sample` | no | all samples | Score only the sample with this name. The comparison ignores case. |
| `--out` | no | | Write the result table as tab-separated text to this path. |
| `--quiet` | no | off | Suppress the console report. Useful in pipelines together with `--out`. |

## What happens in a call

1. The run file is read (`.eds` or RDML), missing quantities and baseline-subtracted curves are
   computed, and the wells are grouped by sample name and target.
2. All patient samples that have wells of the requested target are selected. A target is a
   family of detectors, see [Targets are scored per family](assay.md#targets-are-scored-per-family). Standards and
   controls are excluded.
3. For each sample, 26 features are computed from the target wells and the reference wells of the
   same sample (see [Features](features.md)).
4. The classifier returns the probability that the sample is positive.
5. The quality and review gate combines this probability with the run-acceptance rules and
   returns the final decision (see [Decision logic](decision.md)).

## Examples

All samples of one target, with a result file:

```bash
qpcrpredict predict --run run_0100.eds --target PML::RARA --out run_0100.pml_rara.tsv
```

A plate that carries two targets is scored with one call per target:

```bash
qpcrpredict predict --run run_0207.eds --target NPM1 --out run_0207.npm1.tsv --quiet
qpcrpredict predict --run run_0207.eds --target CBFB::MYH11 --out run_0207.cbfb.tsv --quiet
```

A whole folder of runs:

```bash
for f in eds/*.eds; do
    qpcrpredict predict --run "$f" --target NPM1 --out "calls/$(basename "$f" .eds).tsv" --quiet
done
```

If the run contains no patient sample of the requested target, the command stops with a message
that lists the detector names found on the plate. This helps to spot a wrong `--target` value or an
unrecognized detector spelling. If `--sample` names a sample that has no wells of the target, the
result contains one row with `decision = not_found`.

## Exit status

`0` on success. A non-zero status is returned if the run file cannot be read, the gene cannot be
resolved, the model bundle cannot be loaded or the run contains no sample of the requested target.
