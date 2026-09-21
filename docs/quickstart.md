# Quick start

## Predict one run

One `.eds` file is one 96-well plate and usually contains several patient samples. A prediction
call scores all patient samples of one target on that plate.

```bash
qpcrpredict predict --run run_0100.eds --target RUNX1::RUNX1T1 --out calls.tsv
```

Console report:

```text
run    : run_0100.eds   run_date=2021-01-01
target : AML1_ETO   assay=aml_mrd   model=hist_gb (rep=all)
==========================================================================
  Sample 1345      -> POSITIVE         p(pos)=1.000
       note   : MRD at low level (<250 copies per 10000 ABL1)
  Sample 2393      -> POSITIVE         p(pos)=1.000
  Sample 831       -> NEGATIVE         p(pos)=0.000
  Sample 533       -> REVIEW (human)   p(pos)=0.020  [model leans negative]
       why    : model call (neg) conflicts with the Ct rule (pos, 2/3 wells<41)
       action : For human classification: borderline / low-level result ...
  Sample 2612      -> N.A. -> REDO     p(pos)=1.000
       reason : insufficient starting material: ABL1 copies 653 < 1000
       action : Repeat the assay with newly synthesised cDNA. ...
==========================================================================
summary: {'positive': 4, 'negative': 2, 'review': 2, 'na': 1}
```

The same information is written to `calls.tsv`, one row per sample. All columns are described in
[Output](output.md).

## Score a single sample

```bash
qpcrpredict predict --run run_0100.eds --target RUNX1::RUNX1T1 --sample "Sample 1345"
```

## Train your own model

```bash
qpcrpredict train --runs-dir eds/ --labels samples.csv --out my_model.pkl
qpcrpredict predict --run run_0100.eds --target NPM1 --model my_model.pkl
```

The labels table needs a sample, a target and a label column. See [Training](train.md).

## Use another format or another assay

```bash
qpcrpredict predict --run plate.rdml --target NPM1            # RDML works like .eds
qpcrpredict assay --show generic > my_assay.json             # start your own assay
```

See [Input data](input.md) and [Assay configuration](assay.md).

## Try it with public data

The anonymized run files and labels of the publication are available from Zenodo (see
[Public data](data.md)). After download, both commands above work unchanged on that data.
