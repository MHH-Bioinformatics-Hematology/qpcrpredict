# Changelog

## 1

- First release, as part of the LeukoPredict tools.
- `qpcrpredict predict`, `qpcrpredict train`, `qpcrpredict assay`, `qpcrpredict convert` and `qpcrpredict info`.
- Input formats: Applied Biosystems `.eds` and RDML (versions 1.1 to 1.4).
- Assay configuration: targets, reference gene, control and standard names, label vocabulary,
  cycle number, thresholds and texts are defined in a JSON file and stored in the model bundle.
- No model inside the package: the released models (`aml_mrd.pkl`, 1,444 training analyses of 530 patients, and `aml_mrd_abl10k.pkl` under the reference-gene rule of the ELN MRD recommendations) are published with the data deposit, and `--model` is required.
- Built-in assay configurations `aml_mrd`, `aml_mrd_abl10k` and `generic`.
- `qpcrpredict report` writes a self-contained HTML report from one or more prediction tables, with the amplification curves when the run files are given.
- The result table carries a `call` column with the reported wording; a run that cannot be evaluated is called `n.d.`, and `n.d.` in a label table means not evaluable.
- Four-way decision with the quality and review gate.
- License note for the TabPFN families; `--disallow-family` refuses bundles of a model family.
- Bioconda package (Linux and macOS) with all model families included.
- Galaxy tool wrapper (ToolShed owner `mhh-hematology`).
