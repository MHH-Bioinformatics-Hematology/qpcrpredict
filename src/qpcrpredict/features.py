"""Feature extraction: raw wells -> per-sample summary + curves -> model feature matrix.

A 'sample' is one sample's target replicate wells plus its reference-gene replicate wells on one
plate. This module is the single source of truth shared by training and inference, so the model
always sees identically built features. Everything assay-specific (reference gene, target names,
cycle number, Ct limits, ratio scale) comes from the :class:`qpcrpredict.assay.Assay` that is passed in.
"""
import collections
import numpy as np

from .io import standard_curve


# ------------------------------------------------------------------ scalars / curves
def to_num(x):
    s = str(x).strip().lower()
    if s in ("", "undetermined", "undet", "nan", "none"):
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def curve_arr(cells, n_cycles):
    """Curve as a fixed-length array: truncated or padded with NaN to the assay's cycle number."""
    a = np.full(n_cycles, np.nan)
    if cells is not None:
        for i, v in enumerate(list(cells)[:n_cycles]):
            try:
                a[i] = float(v)
            except (TypeError, ValueError):
                pass
    return a


def std_curve_r2(well_list, assay):
    """R^2 of Ct ~ log10(known quantity) over a target's standard wells (linearity QC)."""
    sc = standard_curve(well_list, assay)
    return sc["r2"] if sc else None


# columns the model's 'summary' representation consumes (order matters for build_features)
SUMMARY_COLS = ["tg_ct_mean", "tg_ct_min", "tg_ct_sd", "tg_n_detected", "tg_n_wells",
                "tg_qty_mean", "ref_ct_mean", "ref_qty_mean", "ratio_calc", "has_ref"]


def build_sample_row(target_wells, ref_wells, assay, r2_target=None, r2_ref=None):
    """target_wells / ref_wells: lists of well dicts (keys ct, qty, drn, rn).
    Returns (row, curves): row = summary + QC scalars; curves = tdrn/trn/rdrn/rrn arrays."""
    n = assay.n_cycles
    ct_max = float(assay.qc["ct_pos_max"])
    tct = np.array([to_num(w["ct"]) for w in target_wells], float)
    tqty = np.array([to_num(w["qty"]) for w in target_wells], float)
    rct = np.array([to_num(w["ct"]) for w in ref_wells], float)
    rqty = np.array([to_num(w["qty"]) for w in ref_wells], float)

    def mean_curve(wells, key):
        if not wells:
            return np.full(n, np.nan)
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                return np.nanmean([curve_arr(w.get(key), n) for w in wells], axis=0)

    t_drn, t_rn = mean_curve(target_wells, "drn"), mean_curve(target_wells, "rn")
    r_drn, r_rn = mean_curve(ref_wells, "drn"), mean_curve(ref_wells, "rn")

    def m(a, f, k=0):
        v = a[~np.isnan(a)]
        return f(v) if len(v) > k else np.nan

    ref_qty_mean = m(rqty, np.nanmean)
    tg_qty_mean = m(tqty, np.nanmean)
    row = dict(
        tg_ct_mean=m(tct, np.nanmean),
        tg_ct_min=m(tct, np.nanmin),
        tg_ct_sd=m(tct, np.nanstd, k=1),
        tg_n_detected=int(np.sum(~np.isnan(tct))),
        tg_n_wells=len(tct),
        tg_n_below_cutoff=int(np.sum(tct < ct_max)),
        tg_qty_mean=tg_qty_mean,
        ref_ct_mean=m(rct, np.nanmean),
        ref_qty_mean=ref_qty_mean,
        has_ref=bool(len(ref_wells) > 0),
        r2_target=r2_target,
        r2_ref=r2_ref,
    )
    row["ratio_calc"] = (
        tg_qty_mean / ref_qty_mean * assay.ratio_scale
        if (ref_qty_mean and not np.isnan(ref_qty_mean) and ref_qty_mean > 0 and not np.isnan(tg_qty_mean))
        else np.nan
    )
    curves = {}
    for i in range(n):
        curves[f"tdrn{i}"] = t_drn[i]
        curves[f"trn{i}"] = t_rn[i]
        curves[f"rdrn{i}"] = r_drn[i]
        curves[f"rrn{i}"] = r_rn[i]
    return row, curves


def _family(w, assay):
    return assay.normalize_target(w.get("detector"), w.get("target_type"))[0]


def group_plate(parsed, assay):
    """parsed run -> ({(sample_upper, family): [wells]}, {family: standard-curve R^2})."""
    groups = collections.defaultdict(list)
    by_fam = collections.defaultdict(list)
    for w in parsed["wells"]:
        fam = _family(w, assay)
        groups[((w["sample"] or "").upper().strip(), fam)].append(w)
        by_fam[fam].append(w)
    r2 = {}
    for fam, ws in by_fam.items():
        if fam is None:
            continue
        v = std_curve_r2(ws, assay)
        if v is not None:
            r2[fam] = v
    return groups, r2


def sample_feature_record(parsed, sample_id, family, assay):
    """Given a parsed run, a sample id and a target FAMILY, gather that sample's target wells and
    its reference wells and build (row, curves). Returns None if there are no target wells."""
    groups, r2 = group_plate(parsed, assay)
    su = sample_id.upper().strip()
    ref = assay.reference_family
    tw = groups.get((su, family), [])
    rw = groups.get((su, ref), [])
    if not tw:
        return None
    return build_sample_row(tw, rw, assay, r2.get(family), r2.get(ref))


# ------------------------------------------------------------------ model feature matrix
def _curve_block(cu, prefix):
    cols = sorted((c for c in cu.columns if c.startswith(prefix) and c[len(prefix):].isdigit()),
                  key=lambda c: int(c[len(prefix):]))
    return cu[cols].to_numpy(float)


def _t(cu):
    return _curve_block(cu, "tdrn")


def _a(cu):
    return _curve_block(cu, "rdrn")


def _curve_feats(C):
    """Engineered features per amplification curve (rows=samples, cols=cycles)."""
    C = np.nan_to_num(C, nan=0.0)
    n, m = C.shape
    out = {}
    mx = C.max(1)
    out["max"] = mx
    out["final"] = C[:, -1]
    out["area"] = C.sum(1)
    d = np.diff(C, axis=1)
    out["maxslope"] = d.max(1)
    out["cyc_maxslope"] = d.argmax(1).astype(float)
    thr = 0.2 * np.where(mx > 0, mx, 1)[:, None]
    above = C >= thr
    first = np.where(above.any(1), above.argmax(1), float(m))
    out["cyc_thr20"] = first.astype(float)
    out["mean_last10"] = C[:, -10:].mean(1)
    out["mean_first10"] = C[:, :10].mean(1)
    return np.column_stack([out[k] for k in out]), list(out.keys())


def _summary(df, ct_cap=50.0):
    import numpy as _np
    cols = list(SUMMARY_COLS)
    X = df[cols].copy()
    for c in ["tg_ct_mean", "tg_ct_min", "ref_ct_mean"]:
        X[c] = X[c].clip(upper=ct_cap).fillna(float(ct_cap))
    for c in ["tg_qty_mean", "ref_qty_mean", "ratio_calc"]:
        X[c] = _np.log1p(X[c].clip(lower=0)).fillna(0.0)
    X["tg_ct_sd"] = X["tg_ct_sd"].fillna(0.0)
    X["has_ref"] = X["has_ref"].astype(float)
    return X.to_numpy(float), cols


ALL_REPS = ["curve_t_raw", "curve_ta_raw", "curve_t_maxnorm", "curve_t_minmax",
            "curve_ta_refrel", "curve_feats", "summary", "all"]


def _build_features(df, cu, rep, ct_cap=50.0):
    T = _t(cu)
    A = _a(cu)
    NCYC = T.shape[1]
    if rep == "curve_t_raw":
        return T, [f"t{i}" for i in range(NCYC)]
    if rep == "curve_ta_raw":
        return np.hstack([T, A]), [f"t{i}" for i in range(NCYC)] + [f"r{i}" for i in range(NCYC)]
    if rep == "curve_t_maxnorm":
        mx = np.nanmax(T, 1, keepdims=True)
        mx[mx == 0] = 1
        return np.nan_to_num(T / mx), [f"tn{i}" for i in range(NCYC)]
    if rep == "curve_t_minmax":
        mn = np.nanmin(T, 1, keepdims=True)
        mx = np.nanmax(T, 1, keepdims=True)
        rng = mx - mn
        rng[rng == 0] = 1
        return np.nan_to_num((T - mn) / rng), [f"tm{i}" for i in range(NCYC)]
    if rep in ("curve_ta_refrel", "curve_ta_ablrel"):
        return np.hstack([np.nan_to_num(T - A), A]), [f"tr{i}" for i in range(NCYC)] + [f"r{i}" for i in range(NCYC)]
    if rep == "curve_feats":
        ft, nt = _curve_feats(T)
        fa, na = _curve_feats(A)
        return np.hstack([ft, fa]), [f"t_{k}" for k in nt] + [f"r_{k}" for k in na]
    if rep == "summary":
        return _summary(df, ct_cap)
    if rep == "all":
        Xc, nc = _curve_feats(T)
        Xa, na = _curve_feats(A)
        Xs, ns = _summary(df, ct_cap)
        return np.hstack([Xc, Xa, Xs]), [f"t_{k}" for k in nc] + [f"r_{k}" for k in na] + ns
    raise ValueError(rep)


def build_features(df, cu, rep, ct_cap=50.0):
    """Return (X, feature_names) for a representation choice. inf -> nan (imputers handle)."""
    X, names = _build_features(df, cu, rep, ct_cap)
    X = np.where(np.isfinite(X), X, np.nan)
    return X, names
