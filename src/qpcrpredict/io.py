"""Format-independent loading of one qPCR run.

``load_run`` reads an ABI ``.eds`` project file or an RDML file and returns the common structure
{'path', 'meta', 'wells'}. ``complete_run`` then fills in what a format does not provide:

* the baseline-subtracted curve (``drn``), computed from ``rn`` by subtracting the mean
  fluorescence of the baseline cycles of the assay;
* quantities of unknown wells, computed from the standard curve of their target on the same
  plate (Ct against log10 of the assigned standard quantity). This is done only for targets for
  which the file provides no quantity at all, as in RDML.

Values that the run file already provides are never overwritten, so ``.eds`` files, which carry
the instrument's own baseline correction and quantities, pass through unchanged.
"""
import collections
import os
import zipfile

import numpy as np

from .eds import parse_eds
from .rdml import parse_rdml, is_rdml

RUN_EXTENSIONS = (".eds", ".rdml", ".rdm")


def detect_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".rdml", ".rdm"):
        return "rdml"
    if ext == ".eds":
        return "eds"
    if is_rdml(path):
        return "rdml"
    try:
        with zipfile.ZipFile(path) as z:
            if any(n.endswith("analysis_result.txt") for n in z.namelist()):
                return "eds"
    except zipfile.BadZipFile:
        pass
    with open(path, "rb") as f:
        if b"<rdml" in f.read(2000):
            return "rdml"
    raise ValueError(f"{path}: unknown run-file format (expected .eds or .rdml)")


def _f(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def standard_curve(wells, assay):
    """Fit Ct = slope * log10(quantity) + intercept over the standard wells.
    Returns dict(slope, intercept, r2, n) or None."""
    pts = []
    for w in wells:
        if not assay.is_standard(w):
            continue
        q, c = _f(w.get("qty")), _f(w.get("ct"))
        if q is not None and c is not None and q > 0 and c < assay.std_ct_max:
            pts.append((q, c))
    if len(pts) < 3:
        return None
    x = np.log10([q for q, _ in pts])
    y = np.array([c for _, c in pts], float)
    if np.ptp(x) == 0:
        return None
    slope, icpt = np.polyfit(x, y, 1)
    den = np.sum((y - y.mean()) ** 2)
    if den == 0:
        return None
    r2 = 1 - np.sum((y - (slope * x + icpt)) ** 2) / den
    return dict(slope=float(slope), intercept=float(icpt), r2=float(round(r2, 4)), n=len(pts))


def complete_run(parsed, assay):
    lo, hi = assay.baseline_cycles
    by_family = collections.defaultdict(list)
    for w in parsed["wells"]:
        if w.get("drn") is None and w.get("rn"):
            rn = np.array([_f(v) if _f(v) is not None else np.nan for v in w["rn"]], float)
            base = rn[max(lo - 1, 0):hi]
            if np.isfinite(base).any():
                w["drn"] = list(rn - np.nanmean(base))
        fam = assay.normalize_target(w.get("detector"), w.get("target_type"))[0]
        by_family[fam].append(w)
    for fam, ws in by_family.items():
        # only when the format gives no quantities for this target at all (RDML); a file that
        # carries the instrument's own quantities (.eds) is left exactly as it is
        if fam is None or any(str(w.get("qty") or "").strip() for w in ws if not assay.is_standard(w)):
            continue
        sc = standard_curve(ws, assay)
        if sc is None or sc["slope"] == 0:
            continue
        for w in ws:
            if str(w.get("qty") or "").strip():
                continue
            c = _f(w.get("ct"))
            if c is not None:
                w["qty"] = float(10 ** ((c - sc["intercept"]) / sc["slope"]))
    return parsed


def load_run(path, assay):
    """Read one run file of any supported format and complete it for the given assay."""
    fmt = detect_format(path)
    parsed = parse_rdml(path) if fmt == "rdml" else parse_eds(path)
    parsed["meta"].setdefault("format", fmt)
    return complete_run(parsed, assay)


def list_runs(folder):
    out = {}
    for dp, _, fs in os.walk(folder):
        for f in fs:
            if f.lower().endswith(RUN_EXTENSIONS):
                out[f] = os.path.join(dp, f)
    return out
