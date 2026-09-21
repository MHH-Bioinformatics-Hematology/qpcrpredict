# qpcrpredict

*Part of the **LeukoPredict** tools: trained calls from the raw data of diagnostic instruments,
developed for leukemia diagnostics at Hannover Medical School.*

`qpcrpredict` predicts the positive or negative call of a real-time PCR assay directly from the
raw run file of the instrument (Applied Biosystems `.eds`, or the vendor-neutral RDML format). It
was developed for the qualitative molecular measurable residual disease (MRD) result in acute
myeloid leukemia, and the packaged model covers that application. Nothing assay-specific is fixed
in the code: targets, reference gene, control names, cycle number and thresholds are defined in an
assay configuration, so a model can be trained for any standard-curve qPCR assay.

Documentation: https://qpcrpredict.readthedocs.io/

## Install

```bash
conda create -n qpcrpredict -c conda-forge -c bioconda qpcrpredict
conda activate qpcrpredict
```

Linux and macOS. All dependencies, including the optional model families, come with the package.

## Use

```bash
# score every sample of one target in a run (.eds or .rdml); the packaged model is the default
qpcrpredict predict --run run.eds --target NPM1 --out calls.tsv

# train a model from run files and a labels table (sample, target, label[, run_file])
qpcrpredict train --runs-dir runs/ --labels labels.csv --out model.pkl

# other assays: start from the template, check it against a plate, train with it
qpcrpredict assay --show generic > my_assay.json
qpcrpredict assay --check plate.rdml --assay my_assay.json
qpcrpredict train --runs-dir runs/ --labels labels.csv --assay my_assay.json --out my_model.pkl
```

Each sample is called **positive**, **negative**, **review** (deferred to a human) or **na**
(not assessable, repeat), with the reason and a recommendation. `qpcrpredict info` prints the
provenance and cross-validation metrics of a model.

## Documentation and citation

The documentation covers the input formats, every option, the output columns, the decision
logic, the assay configuration and the Python API: https://qpcrpredict.readthedocs.io/

If you use `qpcrpredict`, please cite the publication given in the documentation.

## Intended use

`qpcrpredict` is research software and not a certified in vitro diagnostic device. The packaged
model was trained on the data of one laboratory, one instrument type and one set of assays.
Validate it on your own data, or train your own model, before relying on its output.

## License

MIT
