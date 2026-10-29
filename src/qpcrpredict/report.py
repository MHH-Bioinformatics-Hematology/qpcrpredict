"""HTML report from one or more prediction tables of ``qpcrpredict predict``.

The tables are embedded as JSON in a self-contained page (no external resources) that groups the
analyses by run, shows the four-way call with its reasons, and, when the run files are given, the
amplification curves of the target and reference wells of every sample.
"""
import argparse
import datetime
import json
import os
import sys

import pandas as pd

from . import __version__

_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "report_template.html")


def _curves_for(run_path, rows, assay_name=None):
    """Per (run, sample, family): the target and reference well curves and Cts of one run file."""
    from .assay import load_assay
    from .features import group_plate
    from .io import load_run
    A = load_assay(assay_name) if assay_name else load_assay(None)
    parsed = load_run(run_path, A)
    groups, r2 = group_plate(parsed, A)
    out, info = {}, {"run_date": parsed["meta"].get("run_date"), "assay": A.name, "r2": {k: float(v) for k, v in r2.items() if v is not None}}

    n_cycles = int(A.n_cycles)

    def wells(ws):
        cur, cts = [], []
        for w in ws:
            drn = (w.get("drn") or [])[:n_cycles]
            cur.append([round(float(v), 4) if v not in (None, "") else 0.0 for v in drn])
            try:
                cts.append(round(float(w.get("ct")), 2))
            except (TypeError, ValueError):
                cts.append(None)
        return cur, cts
    for r in rows:
        su = str(r["sample"]).upper().strip(); fam = r["family"]
        tw = groups.get((su, fam), []); rw = groups.get((su, A.reference_family), [])
        if not tw:
            continue
        tc, tct = wells(tw); rc, rct = wells(rw)
        n = max([len(c) for c in tc + rc] + [1])
        out[f"{os.path.basename(run_path)}\u0000{su}\u0000{fam}"] = dict(cycles=n, target=tc, target_ct=tct, reference=rc, reference_ct=rct)
    return out, info


def build(tables, out_path, runs=(), title="", subtitle="", assay=None):
    frames = []
    for t in tables:
        df = pd.read_csv(t, sep="\t", dtype=str, keep_default_na=False)
        if "run_file" not in df.columns:
            df["run_file"] = os.path.basename(t)
        frames.append(df)
    if not frames:
        raise SystemExit("no prediction table given")
    df = pd.concat(frames, ignore_index=True)
    for c in ("sample", "target", "family", "decision"):
        if c not in df.columns:
            raise SystemExit(f"{tables[0]}: not a prediction table of qpcrpredict predict (column '{c}' missing)")
    curves, runinfo = {}, {}
    by_base = {os.path.basename(p): p for p in runs}
    for rf, sub in df.groupby("run_file"):
        path = by_base.get(rf)
        if not path:
            continue
        c, info = _curves_for(path, sub.to_dict("records"), assay)
        curves.update(c); runinfo[rf] = info
    for rf in df.run_file.unique():
        runinfo.setdefault(rf, {})
        sub = df[df.run_file == rf]
        if "run_date" in sub.columns and sub.run_date.iloc[0]:
            runinfo[rf].setdefault("run_date", sub.run_date.iloc[0])
    data = dict(header=list(df.columns), rows=df.values.tolist(), runs=runinfo, curves=curves,
                title=title or "qPCR report", subtitle=subtitle or f"{len(df)} analyses in {df.run_file.nunique()} runs",
                footer=f"qpcrpredict {__version__}, report written {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}. Research software; every call is subject to approval by the laboratory.")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = open(_TEMPLATE, encoding="utf-8").read()
    assert page.count("__DATA__") == 1
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page.replace("__DATA__", payload))
    return len(df), len(curves)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="qpcrpredict report", description="Write a self-contained HTML report from one or more prediction tables.")
    ap.add_argument("tables", nargs="+", help="prediction tables (--out of qpcrpredict predict), tab-separated")
    ap.add_argument("--run", action="append", default=[], metavar="RUN", help="run file (.eds or .rdml) of one of the tables; its curves are shown. May be repeated. Matched to the tables by file name.")
    ap.add_argument("--out", required=True, help="HTML file to write")
    ap.add_argument("--title", default="", help="title shown in the header, for example the run or batch name")
    ap.add_argument("--subtitle", default="", help="second line of the header")
    ap.add_argument("--assay", default=None, help="assay configuration used to read the run files (default: aml_mrd)")
    a = ap.parse_args(argv)
    n, c = build(a.tables, a.out, runs=a.run, title=a.title, subtitle=a.subtitle, assay=a.assay)
    print(f"wrote {a.out}: {n} analyses, curves for {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
