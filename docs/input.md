# Input data

`qpcrpredict` reads two run-file formats. Both are converted to the same internal structure, so
features, model and decision logic are identical for them.

| Format | Extension | Source |
|---|---|---|
| Applied Biosystems project file | `.eds` | 7500 Software; primary format, used for the packaged model |
| RDML | `.rdml`, `.rdm` | vendor-neutral open standard ([rdml.org](https://rdml.org)), exported by most qPCR software |

The format is detected from the file content, so the extension does not matter.

## Applied Biosystems .eds

An `.eds` file is a ZIP archive. Two of its members are used:

| Member | Content used |
|---|---|
| `apldbio/sds/analysis_result.txt` | per-well table: sample name, detector, task, Ct, quantity, and the 40-cycle Rn and ΔRn amplification curves |
| `apldbio/sds/experiment.xml` | run name and run date |

The run must have been analyzed in the instrument software before export, so that Ct values,
quantities and the standard curve are present. No spreadsheet export is needed.

## RDML

An RDML file is a ZIP archive with one XML document. Versions 1.1 to 1.4 are read, with the
Python standard library only. From each reaction `qpcrpredict` takes the sample, the target, the Cq
and the fluorescence curve; from each sample its type (unknown, standard, no-template control and
so on) and the assigned quantity of standards; from each target whether it is a reference.

RDML does not store two things that an `.eds` file provides, so `qpcrpredict` computes them:

- **Quantities.** The standard curve of each target is fitted on the plate (Cq against the
  logarithm of the assigned standard quantity) and the quantities of the unknown wells are
  calculated from it.
- **Baseline-subtracted curve.** If the file carries no background values, the mean fluorescence
  of the baseline cycles of the assay (default cycles 3 to 15) is subtracted.

Values that a file already provides are not recomputed. `.eds` files contain them and are used as
they are.

On our data, converting `.eds` runs to RDML and scoring both gave the same decision for 97.6% of
466 samples, and the computed reference quantities agreed with the instrument to four digits.
The remaining differences come from the simpler baseline correction. Train and predict on the
same format where possible.

```bash
qpcrpredict convert --run run_0100.eds --out run_0100.rdml
```

## Plate layout

`qpcrpredict` expects a standard-curve quantification plate with the following elements. The names
used here are those of the default assay; all of them are set in the [assay configuration](assay.md).

Patient samples
: Each sample is measured in replicate wells (three in the reference layout) for the target and in
  replicate wells for the reference gene *ABL1* on the same plate. Target and *ABL1* wells are
  linked through an identical sample name.

Standard curve
: Each assay on the plate, including *ABL1*, has its own dilution series with the task
  `STANDARD` and assigned quantities. The linearity (R²) of each curve is a run-acceptance
  criterion.

Controls
: A negative control sample and no-template control wells (task `NTC`).

Several target assays can share one plate, for example two *NPM1* mutation subtypes. They share
the *ABL1* wells of each sample.

## Sample names

Wells are grouped into samples by their sample name, so all replicate wells of one sample, target
and *ABL1*, must carry exactly the same name. Names are otherwise free text.

Wells are never scored if the sample name is empty or marks a control. Which names and which
well tasks mark a control is defined in the assay configuration. In the default assay, names
are controls when they start with `pos`, `neg `, `std`, `ntc` or `blank`, or contain terms such
as `control`, `neg ko` or `standard`.

## Detector names

The detector name of each well identifies the assay. Spelling varies between plates, so names are
normalized to a target family and a subtype by the patterns of the assay configuration. Examples
for the default assay:

| Detector name on the plate | Family | Option for `--target` |
|---|---|---|
| `NPM1 mut A`, `NPM1B`, `NPM1 D` | `NPM1` | `NPM1` |
| `AML1-ETO`, `t(8;21)`, `RUNX1-RUNX1T1` | `AML1_ETO` | `RUNX1::RUNX1T1` |
| `inv16 A`, `CBFB-MYH11 D` | `CBFB_MYH11` | `CBFB::MYH11` |
| `PML-RARA bcr1`, `t(15;17) B` | `PML_RARA` | `PML::RARA` |
| `BCR-ABL` | `BCR_ABL` | `BCR::ABL1` |
| `ABL`, `ABL1` | reference | not applicable |

If a detector name on your plates is not recognized, add a pattern to your assay configuration.
`qpcrpredict assay --check RUN` shows how every detector and sample name of a run is interpreted.

## Labels table (training only)

Training needs a table with one row per sample and target. See [Training](train.md).
