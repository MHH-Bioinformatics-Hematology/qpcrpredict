"""Prediction: score one qPCR run for a target with a trained model.

Contract
  input 1 : one run file (.eds or .rdml)
  input 2 : a target (selects which assay on the plate to score)
  input 3 : a trained model bundle (.pkl)  [optional: falls back to the packaged default]

For every sample that carries the target in the run (or a single --sample) the result is
positive / negative / review / na, with the reason and a recommendation. The assay configuration
(targets, reference gene, control names, thresholds) is taken from the model bundle.
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd

from .io import load_run
from . import features as F
from . import qc as QC
from .bundle import load_bundle, bundle_assay
from .models import license_note


def _r(x):
    try:
        x = float(x)
        return None if np.isnan(x) else round(x, 3)
    except (TypeError, ValueError):
        return None


def samples_for_family(parsed, family, assay):
    """Every distinct non-control sample that has a well of this target family in the run."""
    seen, out = set(), []
    for w in parsed["wells"]:
        s = (w["sample"] or "").strip()
        fam, _sub, kind = assay.normalize_target(w["detector"], w.get("target_type"))
        if not s or assay.is_control(s, w.get("task")) or fam != family or kind not in ("target", "target_other"):
            continue
        if s.upper() in seen:
            continue
        seen.add(s.upper())
        out.append(s)
    return out


def predict(run_path, target, model_path=None, sample=None, out_path=None, quiet=False, assay=None,
            disallow_families=()):
    """Return a DataFrame of predictions for ``target`` in ``run_path`` using ``model_path``.
    ``assay`` overrides the assay configuration stored in the model bundle. ``disallow_families``
    lists model-family prefixes (for example "tabpfn") whose bundles are refused."""
    bundle = load_bundle(model_path)
    family_name = str(bundle.get("model_name") or "").lower()
    for prefix in disallow_families or ():
        if family_name.startswith(str(prefix).lower()):
            raise SystemExit(f"model family '{family_name}' is not allowed here. "
                             + (license_note(family_name) or ""))
    A = bundle_assay(bundle, assay)
    family = A.resolve_target(target)
    rep = bundle["rep"]
    clf = bundle["pipeline"]
    T = QC.QCThresholds.from_dict(A.qc)

    parsed = load_run(run_path, A)
    run_date = parsed["meta"].get("run_date")
    samples = [sample] if sample else samples_for_family(parsed, family, A)
    if not samples:
        raise SystemExit(
            f"no samples for target '{target}' (family {family}) found in "
            f"{os.path.basename(run_path)}. Detectors present: "
            f"{sorted({w['detector'] for w in parsed['wells'] if w['detector']})}"
        )

    results = []
    for sid in samples:
        sid = str(sid).strip()
        rec = F.sample_feature_record(parsed, sid, family, A)
        if rec is None:
            results.append(dict(sample=sid, target=target, family=family, run_date=run_date,
                                decision="not_found", ml_prob=np.nan,
                                reason=f"no {family} wells for sample '{sid}' in this run"))
            continue
        row, curves = rec
        dfm = pd.DataFrame([{**row, "family": family, "sample_id": sid}])
        cum = pd.DataFrame([curves])
        X, _ = F.build_features(dfm, cum, rep, A.ct_cap)
        prob = float(clf.predict_proba(X)[0, 1])
        ml_call = "pos" if prob >= T.decision_threshold else "neg"
        a = QC.assess(row, classifier_call=ml_call, T=T, classifier_prob=prob,
                      reference=A.reference_name, ratio_scale=A.ratio_scale, texts=A.texts)
        results.append(dict(
            sample=sid, target=target, family=family, run_date=run_date,
            decision=a["decision"], redo=a["redo"], review=a.get("review", False),
            model_call=a.get("model_call", "positive" if ml_call == "pos" else "negative"),
            ml_prob=round(prob, 4), quality=a["quality"],
            ref_qty_mean=_r(row.get("ref_qty_mean")),
            r2_target=row.get("r2_target"), r2_ref=row.get("r2_ref"),
            tg_ct_mean=_r(row.get("tg_ct_mean")), tg_n_below_cutoff=row.get("tg_n_below_cutoff"),
            ratio=_r(row.get("ratio_calc")),
            reason="; ".join(a["reasons"]) if a["reasons"] else "",
            review_reason="; ".join(a.get("review_reasons", [])),
            annotation="; ".join(a["annotations"]) if a["annotations"] else "",
            recommendation=a["recommendation"]))
    res = pd.DataFrame(results)

    if not quiet:
        _report(res, run_path, run_date, bundle, family, A)
    if out_path:
        res.to_csv(out_path, sep="\t", index=False)
        if not quiet:
            print(f"\nwrote {out_path}")
    return res


def _report(res, run_path, run_date, bundle, family, assay):
    print(f"\nrun    : {os.path.basename(run_path)}   run_date={run_date}")
    print(f"target : {family}   assay={assay.name}   model={bundle.get('model_name')} (rep={bundle.get('rep')})")
    print("=" * 92)
    tagmap = {"positive": "POSITIVE", "negative": "NEGATIVE", "na": "N.A. -> REDO",
              "review": "REVIEW (human)", "not_found": "NOT FOUND"}
    for _, r in res.iterrows():
        tag = tagmap.get(r["decision"], r["decision"].upper())
        prob = f"p(pos)={r['ml_prob']:.3f}" if pd.notna(r.get("ml_prob")) else ""

        def _txt(k):
            v = r.get(k)
            return v if isinstance(v, str) and v.strip() else ""

        lean = f"  [model leans {r.get('model_call')}]" if r["decision"] == "review" and _txt("model_call") else ""
        print(f"  {str(r['sample'])[:16]:16s} -> {tag:16s} {prob}{lean}")
        for label, key in (("reason", "reason"), ("why", "review_reason"),
                           ("note", "annotation"), ("action", "recommendation")):
            if _txt(key):
                print(f"       {label:7s}: {_txt(key)}")
    print("=" * 92)
    print("summary:", res["decision"].value_counts().to_dict())
    note = license_note(bundle.get("model_name"))
    if note:
        print("license:", note)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="qpcrpredict predict",
        description="Predict the positive/negative call for one target in one qPCR run (.eds or .rdml).")
    ap.add_argument("--run", "--eds", dest="run", required=True, help="one run file (.eds or .rdml)")
    ap.add_argument("--target", "--gene", dest="target", required=True,
                    help="target to score: a target name or alias of the assay, or a detector name "
                         "as written on the plate (see 'qpcrpredict assay')")
    ap.add_argument("--model", default=None,
                    help="trained model bundle (.pkl); default = packaged model")
    ap.add_argument("--assay", default=None,
                    help="assay configuration (packaged name or JSON file) that overrides the one "
                         "stored in the model bundle")
    ap.add_argument("--disallow-family", action="append", default=[], metavar="PREFIX",
                    help="refuse model bundles of this family, for example 'tabpfn' where the "
                         "non-commercial TabPFN license does not permit their use; may be repeated")
    ap.add_argument("--sample", default=None,
                    help="score only this sample (default: all samples of the target)")
    ap.add_argument("--out", default=None, help="write predictions as TSV here")
    ap.add_argument("--quiet", action="store_true", help="suppress the console report")
    a = ap.parse_args(argv)
    try:
        predict(a.run, a.target, a.model, sample=a.sample, out_path=a.out, quiet=a.quiet, assay=a.assay,
                disallow_families=a.disallow_family)
    except ValueError as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    sys.exit(main())
