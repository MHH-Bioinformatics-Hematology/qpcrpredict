# Assay configuration

An **assay configuration** is a JSON file that defines the target names, the reference gene, the
names of controls and standards, the vocabulary of the labels, the cycle number and the
thresholds. To use `qpcrpredict` for a different assay, write a configuration for it and train a
model with that configuration.

## Packaged configurations

| Name | Content |
|---|---|
| `aml_mrd` | Default. AML molecular MRD: mutated *NPM1*, *RUNX1::RUNX1T1*, *CBFB::MYH11*, *PML::RARA*, *BCR::ABL1*, reference *ABL1*. This is the configuration of the packaged model. |
| `generic` | Template for any standard-curve qPCR assay with one reference gene. Every detector that is not the reference is its own target. |

```bash
qpcrpredict assay                          # list the packaged configurations
qpcrpredict assay --show generic > my_assay.json
```

## Writing your own

Start from `generic`, edit the file, and check it against one of your run files:

```bash
qpcrpredict assay --check my_run.rdml --assay my_assay.json
```

The check prints how every detector on the plate is interpreted (reference, target or noise) and
which sample names are taken as controls. Adjust the configuration until this matches your plate.

## How a plate is interpreted

When a plate is set up on the instrument, each well gets a **detector name** (for example
`NPM1 mut A` or `ABL`) and a **sample name**. Both are stored in the run file. `qpcrpredict` reads
them from there and interprets them with the assay configuration, so prediction needs only the
run file. A labels table is needed for [training](train.md).

### The reference gene

```json
"references": [
  {"name": "ABL1", "family": "ABL", "patterns": ["\\babl\\b", "c-?abl", "abl ?probe", "abl1"]},
  {"name": "GAPDH", "family": "GAPDH", "patterns": ["gapdh"]}
]
```

Every detector whose name matches one of the patterns is a reference well. The **first** entry is
the reference used for normalization, for the ratio and for the material-quality check; `name` is
how it appears in reports. To normalize to another gene, change this block. In RDML files a target
marked as `ref` is also taken as the reference if no pattern matches it.

The reference wells of a sample are found through the sample name: target wells and reference
wells that carry exactly the same sample name belong together.

### Controls and standards

```json
"controls": {
  "exact":    ["ntc", "blank", "h2o", "water"],
  "prefixes": ["pos", "neg ", "std", "ntc", "blank"],
  "contains": ["control", "neg ko", "pos ko", "standard"],
  "tasks":    []
},
"standards": {"tasks": ["STANDARD"], "sample_prefixes": ["STD"], "ct_max": 45}
```

A well is a control, and is never scored, if its sample name equals an `exact` entry, starts with
a `prefixes` entry or contains a `contains` entry (case is ignored), or if its well task is listed
under `tasks`. Standards are recognized by their task or by a sample-name prefix. Their assigned
quantities give the standard curve and its R². The example is shortened; print the full default
with `qpcrpredict assay --show aml_mrd`.

### Checking a plate

```bash
qpcrpredict assay --check run_0207.eds
```

```text
assay aml_mrd; 75 wells; format eds

detector -> family / subtype / kind
  'NPM1 mut B'                     -> NPM1 / NPM1_B / target
  'NPM1 mut D'                     -> NPM1 / NPM1_D / target
  'ABL'                            -> ABL / ABL / reference

sample name -> role (wells)
  'Sample 416'                     -> sample (6)
  'Neg Ko'                         -> control (9)
  'Sample 760'                     -> sample (6)
  'STD2'                           -> control (6)
  'STD3'                           -> control (9)
```

Each sample here has 6 wells: 3 for its target and 3 for the reference. If a detector shows up as
`target_other` although it is one of your targets, or a patient sample shows up as `control`,
adjust the patterns.

### Targets are scored per family

`--target` selects a **family**. All detectors of that family are treated as one target. On the
plate above, `NPM1 mut B` and `NPM1 mut D` both belong to the family `NPM1`, so `--target NPM1`
scores every sample on the NPM1 wells it has. This fits a layout in which each sample carries one
subtype. If one sample carried wells of two subtypes on the same plate, their replicates would be
pooled into one call. To call them separately, define them as two targets with their own `family`
in the assay configuration.

## Fields

| Field | Meaning |
|---|---|
| `name`, `description` | Identification. The name is shown in reports and stored in the model. |
| `n_cycles` | Number of PCR cycles. Shorter curves are padded, longer ones truncated. |
| `baseline_cycles` | First and last cycle of the baseline, used when the run file has no baseline-subtracted curve (RDML). |
| `references` | List of reference genes, each with `name`, `family` and `patterns`. The first entry is the reference used for normalization. |
| `targets` | List of targets, see below. May be empty. |
| `unknown_target_family` | Family given to detectors that match no target. `null` makes each such detector its own target. |
| `noise_patterns` | Detector names to ignore. |
| `controls` | Sample names that are controls: `exact`, `prefixes`, `contains`, and well `tasks` that mark controls. |
| `standards` | How standard wells are recognized (`tasks`, `sample_prefixes`) and the highest Ct used for the curve (`ct_max`). |
| `labels` | Vocabulary of the labels table for `pos`, `neg` and `na`, each with `exact` and `prefixes`. |
| `label_columns` | Accepted header names of the labels table for `sample`, `target`, `label` and `run_file`. |
| `group_id_strip` | Regular expression removed from the sample name to form the cross-validation group. `null` uses the sample name. |
| `ct_cap` | Value used for undetermined Ct in the features. |
| `ratio_scale` | The reported ratio is target quantity per this many reference copies. |
| `qc` | Thresholds of the quality and review gate, see [Decision logic](decision.md). |
| `texts` | Wording of the low-level annotation and of the recommendations. |

All patterns are regular expressions applied to the lower-cased name.

### A target

```json
{
  "name": "NPM1",
  "family": "NPM1",
  "aliases": ["npm1", "npm"],
  "patterns": ["npm"],
  "subtypes": [{"pattern": "npm\\s*1?\\s*(?:mut)?\\s*([abd])\\b", "subtype": "NPM1_{1}"}],
  "default_subtype": "NPM1_X"
}
```

`name` is what the user passes to `--target`. `family` is the internal code; all detectors of one
family are scored as one target. `aliases` are further accepted spellings of `--target`.
`patterns` decide which detector names on a plate belong to the target. `subtypes` is optional:
the first matching rule names the subtype, and `{1}` is replaced by the first captured group.

## The configuration is stored in the model

`qpcrpredict train --assay my_assay.json` stores the complete configuration inside the model bundle.
`qpcrpredict predict` reads it from there, so prediction always uses the definitions and thresholds
the model was trained with. `--assay` on `predict` overrides it, for example to try other
thresholds without retraining.

## Example: a different assay in three commands

```bash
qpcrpredict assay --show generic > my_assay.json      # then set the reference gene and thresholds
qpcrpredict train --runs-dir runs/ --labels labels.csv --assay my_assay.json --out my_model.pkl
qpcrpredict predict --run runs/plate_07.rdml --target "MyTarget" --model my_model.pkl
```
