"""Training: fit a positive/negative classifier from run files and a labels table.

A corpus is
  * a folder of run files (.eds or .rdml; subfolders are searched)
  * a labels table (CSV/TSV/XLS/XLSX) with one row per sample and target:
        sample   : sample name as written in the run file
        target   : target, in any spelling the assay accepts
        label    : positive or negative (other rows are ignored)
        run_file : file name inside the folder (optional; if absent every run is searched)

Features come only from the run files; the label is the training target. Rows that share a
sample identifier are kept in one cross-validation fold. The assay configuration used for
training is stored in the model bundle, so prediction always uses the same definitions.
"""
import os
import sys
import argparse
import datetime

import pandas as pd

from .assay import load_assay
from .io import load_run, list_runs
from . import features as F
from . import models as M
from .bundle import save_bundle


def _read_table(path):
    if path.lower().endswith((".tsv", ".tab", ".txt")):
        return pd.read_csv(path, sep="\t", dtype=str)
    if path.lower().endswith((".xls", ".xlsx")):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)


def _pick(cols, names):
    low = {c.lower().strip(): c for c in cols}
    for n in names:
        if n in low:
            return low[n]
    return None


def features_from_corpus(runs_dir, labels_path, rep, assay=None, log=print):
    """Rebuild (df_meta, X) straight from (run folder + labels table)."""
    A = load_assay(assay)
    lab = _read_table(labels_path)
    lcfg = A.cfg.get("label_columns") or {}
    sc = _pick(lab.columns, lcfg.get("sample", ["sample_id", "sample"]))
    gc = _pick(lab.columns, lcfg.get("target", ["target", "gene"]))
    lc = _pick(lab.columns, lcfg.get("label", ["label"]))
    fc = _pick(lab.columns, lcfg.get("run_file", ["run_file", "eds_file"]))
    if sc is None or gc is None or lc is None:
        raise SystemExit(f"labels table needs sample, target and label columns; found {list(lab.columns)}")

    lab["_label"] = lab[lc].map(A.normalize_label)
    lab = lab[lab["_label"].isin(["pos", "neg"])].reset_index(drop=True)
    if lab.empty:
        raise SystemExit("no positive/negative labelled rows in the labels table")

    all_runs = list_runs(runs_dir)
    if not all_runs:
        raise SystemExit(f"no .eds or .rdml files found under {runs_dir}")
    cache = {}

    def _parsed(path):
        if path not in cache:
            try:
                cache[path] = load_run(path, A)
            except Exception:
                cache[path] = None
        return cache[path]

    rows, curves, meta = [], [], []
    miss = 0
    for i, r in lab.iterrows():
        family = A.resolve_target(str(r[gc]))
        sid = str(r[sc]).strip()
        if fc and isinstance(r[fc], str) and r[fc].strip():
            cand = [all_runs.get(os.path.basename(r[fc].strip()))]
        else:
            cand = list(all_runs.values())
        rec = None
        for p in cand:
            if not p:
                continue
            parsed = _parsed(p)
            if parsed is None:
                continue
            rec = F.sample_feature_record(parsed, sid, family, A)
            if rec is not None:
                break
        if rec is None:
            miss += 1
            continue
        row, cv = rec
        rows.append(row)
        curves.append(cv)
        meta.append(dict(sample_id=sid, family=family, label=r["_label"]))
        if (i + 1) % 500 == 0:
            log(f"  ...{i + 1}/{len(lab)} rows featurised")
    if not rows:
        raise SystemExit("could not featurise any labelled sample (check the run folder and the sample names)")
    df = pd.DataFrame(rows)
    md = pd.DataFrame(meta)
    for c in md.columns:
        df[c] = md[c].values
    df["y"] = (df["label"] == "pos").astype(int)
    df["group"] = df["sample_id"].map(A.group_id)
    cu = pd.DataFrame(curves)
    X, _ = F.build_features(df, cu, rep, A.ct_cap)
    log(f"[features] {len(df)} samples featurised ({miss} labelled rows had no matching wells)")
    return df, X


def fit(runs_dir, labels_path, model_name="hist_gb", rep="all", out="model.pkl", cv=True,
        assay=None, log=print):
    A = load_assay(assay)
    df, X = features_from_corpus(runs_dir, labels_path, rep, assay=A, log=log)
    y = df["y"].to_numpy()
    g = df["group"].to_numpy()
    log(f"[fit] {len(df)} samples | pos={int(y.sum())} neg={int((y == 0).sum())} | assay={A.name} "
        f"| rep={rep} | model={model_name}")

    cv_metrics = None
    if cv:
        log("[fit] grouped 5-fold CV ...")
        cv_metrics = M.eval_cv(X, y, g, model_name, n_splits=5)
        if cv_metrics:
            log("      " + "  ".join(f"{k}={cv_metrics[k]}" for k in
                ("roc_auc", "pr_auc", "accuracy", "precision", "recall", "specificity", "f1", "f2", "mcc")))
        else:
            log("      (not enough groups/classes for CV; skipped)")

    note = M.license_note(model_name)
    if note:
        log("[license] " + note)
    log("[fit] training final model on ALL samples ...")
    clf = M.make_model(model_name)
    clf.fit(X, y)
    bundle = dict(pipeline=clf, rep=rep, model_name=M.resolve_model(model_name), classes=["neg", "pos"],
                  feature_dim=int(X.shape[1]), n_train=len(df), assay=A.to_dict(),
                  cv_metrics=cv_metrics, created=datetime.date.today().isoformat(),
                  note="positive/negative classifier; pair with qpcrpredict.qc.assess for the 4-way decision.")
    if note:
        bundle["license"] = note
    save_bundle(bundle, out)
    log(f"[fit] saved model bundle -> {out}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="qpcrpredict train",
        description="Train a positive/negative classifier from a folder of run files and a labels table.")
    ap.add_argument("--runs-dir", "--eds-dir", dest="runs_dir", required=True,
                    help="folder containing the run files (.eds or .rdml)")
    ap.add_argument("--labels", required=True, help="labels table: sample, target, label[, run_file]")
    ap.add_argument("--assay", default=None,
                    help="assay configuration: packaged name or JSON file (default: the packaged default assay)")
    ap.add_argument("--model", default="hist_gb",
                    help="model family: " + ", ".join(M.ALL_MODELS) + " (default hist_gb)")
    ap.add_argument("--rep", default="all", choices=F.ALL_REPS + ["curve_ta_ablrel"],
                    help="feature representation (default all)")
    ap.add_argument("--out", default="model.pkl", help="output model bundle path")
    ap.add_argument("--no-cv", action="store_true", help="skip cross-validation reporting")
    a = ap.parse_args(argv)
    try:
        fit(a.runs_dir, a.labels, model_name=a.model, rep=a.rep, out=a.out, cv=not a.no_cv, assay=a.assay)
    except ValueError as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    sys.exit(main())
