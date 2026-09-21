# Changelog

## 1

- First release, as part of the LeukoPredict tools.
- `qpcrpredict predict`, `qpcrpredict train`, `qpcrpredict assay`, `qpcrpredict convert` and `qpcrpredict info`.
- Input formats: Applied Biosystems `.eds` and RDML (versions 1.1 to 1.4).
- Assay configuration: targets, reference gene, control and standard names, label vocabulary,
  cycle number, thresholds and texts are defined in a JSON file and stored in the model bundle.
  Packaged configurations `aml_mrd` (default) and `generic`.
- Packaged default model (`hist_gb`, 26 features, 1,897 training samples) for AML molecular MRD.
- Four-way decision with the quality and review gate.
- Bioconda package (Linux and macOS) with all model families included.
- Galaxy tool wrapper (ToolShed owner `mhh-hematology`).
