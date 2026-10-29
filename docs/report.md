# HTML report

```text
qpcrpredict report TABLE [TABLE ...] --out REPORT.html [--run RUN ...] [--title TITLE]
                   [--subtitle TEXT] [--assay ASSAY]
```

`qpcrpredict report` turns one or more prediction tables (the `--out` files of
[`qpcrpredict predict`](predict.md)) into a single self-contained HTML page. The page needs no
network access and opens in any browser, so it can be stored with the run, attached to a mail or
served from Galaxy.

## Parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `TABLE` | yes | | One or more prediction tables. They are merged; each table keeps its run through the `run_file` column. |
| `--out` | yes | | The HTML file to write. |
| `--run` | no | | A run file (`.eds` or RDML) of one of the tables. Its amplification curves are drawn in the report. May be repeated; a run file is matched to the table rows by its file name. |
| `--title` | no | `qPCR report` | Title in the header, for example the batch or run name. |
| `--subtitle` | no | number of analyses and runs | Second line of the header. |
| `--assay` | no | `aml_mrd` | Assay configuration used to read the run files for the curves. |

## What the page shows

- **Overview**: the number of analyses and how many were called positive, negative, review and
  n.d., and the share called automatically. The filter chips of the header restrict every table to
  one call, the search field finds samples, targets, runs and reasons.
- **One section per run**: the run date, the assay and the standard-curve R² of the target and the
  reference, and a table with one row per analysis: the call, the probability of the model, the
  model's own call, the mean target Ct, the number of wells below the Ct cutoff, the reference
  copies, the ratio, the material quality and the reasons. Columns sort on click.
- **Details of an analysis** (click a row): the full reasons, annotations and the recommended
  action, and, when the run file was given, the curves of the three target wells and the three
  reference wells with the Ct of every well marked.

The page remembers the chosen filter, sort order, font size and light or dark theme in the
browser. It prints on paper with the tables expanded.

## Example

```bash
qpcrpredict predict --run run_0014.eds --target NPM1 --model aml_mrd.pkl --out run_0014.tsv --quiet
qpcrpredict predict --run run_0030.eds --target NPM1 --model aml_mrd.pkl --out run_0030.tsv --quiet
qpcrpredict report run_0014.tsv run_0030.tsv --run run_0014.eds --run run_0030.eds \
                   --title "NPM1 batch 2026-10-29" --out report.html
```

The same report is available as a Galaxy tool, see [Galaxy](galaxy.md).
