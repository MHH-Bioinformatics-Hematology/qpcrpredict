# Changelog

## 1

- First release, as part of the LeukoPredict tools.
- `qpcrpredict predict`, `qpcrpredict train`, `qpcrpredict assay`, `qpcrpredict convert` and `qpcrpredict info`.
- Input formats: Applied Biosystems `.eds` and RDML (versions 1.1 to 1.4).
- Assay configuration: targets, reference gene, control and standard names, label vocabulary,
  cycle number, thresholds and texts are defined in a JSON file and stored in the model bundle.
  Packaged configurations `aml_mrd` (default) and `generic`.
- Packaged default model (`hist_gb`, 26 features, 1,487 training analyses of 534 patients) for AML molecular MRD.
- Second packaged model `aml_mrd_eln2025` and assay configuration of the same name with the thresholds of the 2025 ELN MRD update (Ct 40 per well, 10,000 *ABL1* copies for a negative call); `--model` accepts the name of a packaged model.
- Four-way decision with the quality and review gate.
- License note for the TabPFN families; `--disallow-family` refuses bundles of a model family.
- Bioconda package (Linux and macOS) with all model families included.
- Galaxy tool wrapper (ToolShed owner `mhh-hematology`).
