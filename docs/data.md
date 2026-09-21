# Public data

The anonymized data of the publication are deposited at Zenodo.

| Item | Content |
|---|---|
| `eds/run_0001.eds` to `eds/run_0386.eds` | 386 raw run files |
| `samples.csv` | 1,897 sample measurements with the laboratory call |
| `README.md` | description of the deposit |

`samples.csv` is a valid labels table for `qpcrpredict train`:

| Column | Meaning |
|---|---|
| `sample_id` | sample name as it appears inside the run file |
| `gene` | target family |
| `label` | `positive` or `negative`, as reported by the laboratory |
| `eds_file` | run file that contains the measurement |
| `target_subtype` | transcript or mutation subtype of the assay |
| `year` | year of the laboratory report |
| `split` | `development` (2019 to 2023) or `temporal_test` (2024 to 2025) |
| `material` | bone marrow, peripheral blood or other |
| `laboratory_quality` | material quality reported by the laboratory |
| `repeat_run` | true if the measurement is a repeat of an earlier run |
| `cv_group` | grouping key used for grouped cross-validation |

## Reproduce the packaged model

```bash
qpcrpredict train --runs-dir eds/ --labels samples.csv --model hist_gb --out reproduced.pkl
```

## Reproduce the temporal test

```bash
head -1 samples.csv > dev.csv
grep ",development," samples.csv >> dev.csv
qpcrpredict train --runs-dir eds/ --labels dev.csv --model hist_gb --out dev.pkl
```

Then score the run files of the `temporal_test` rows with `--model dev.pkl` and compare the
`model_call` column with `label`.

## Anonymization

Sample names were replaced by `Sample N` with random numbers, consistently across all run files.
Run files were renamed, operator names and file paths were removed, and all timestamps of a run
were shifted so that the run starts on 1 January of the year of the laboratory report.
Fluorescence data, Ct values and quantities are unchanged.
