"""Quality-control and review gate around the positive/negative classifier.

The gate turns runs that cannot be evaluated into an explicit 'na' (repeat) decision and
ambiguous calls into 'review' (for human classification), each with a readable reason. All
inputs are derived from the run file. All thresholds and texts come from the assay configuration.

Rules
  * Material quality from the mean reference-gene quantity:
        >= ref_sufficient                    -> 'sufficient'
        ref_insufficient .. ref_sufficient   -> 'limited' (usable, annotated)
        <  ref_insufficient                  -> 'insufficient' -> not assessable -> repeat
  * Standard-curve linearity R^2 (target and reference) >= r2_min, else not assessable -> repeat
  * Replicate rule: target Ct < ct_pos_max in >= min_pos_replicates wells -> positive
  * Low level: ratio < low_level_ratio -> annotation on a positive call
"""
from dataclasses import dataclass, fields
import math

# threshold names used by bundles written before the assay configuration existed
_LEGACY = {"abl_sufficient": "ref_sufficient", "abl_insufficient": "ref_insufficient",
           "mrd_low_level": "low_level_ratio"}


@dataclass
class QCThresholds:
    ref_sufficient: float = 10000.0
    ref_insufficient: float = 1000.0
    r2_min: float = 0.95
    ct_pos_max: float = 41.0
    min_pos_replicates: int = 2
    low_level_ratio: float = 250.0
    decision_threshold: float = 0.5    # p(pos) at or above this value -> classifier call positive
    # ---- review tier ----
    enable_review: bool = True
    review_prob_lo: float = 0.35       # p(pos) in [lo, hi] -> model is unsure (primary trigger)
    review_prob_hi: float = 0.65
    review_flag_discordant: bool = False  # also review a triplicate with exactly one detected well
    review_ct_lo: float = 39.0         # Ct band at the detection limit (fallback without probability)
    review_ct_hi: float = 42.0

    @classmethod
    def from_dict(cls, d):
        d = {_LEGACY.get(k, k): v for k, v in (d or {}).items()}
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})


_TEXTS = {
    "low_level": "low-level positive",
    "redo_material": "Repeat the measurement with new template.",
    "redo_run": "Repeat the run (re-check the standard curve and the reference).",
    "review": "For human classification: borderline result.",
}


def _num(x):
    try:
        x = float(x)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def quality_category(ref_qty, T=QCThresholds()):
    a = _num(ref_qty)
    if a is None:
        return "unknown"
    if a >= T.ref_sufficient:
        return "sufficient"
    if a >= T.ref_insufficient:
        return "limited"
    return "insufficient"


def assess(row, classifier_call=None, T=QCThresholds(), classifier_prob=None,
           reference="reference", ratio_scale=10000.0, texts=None):
    """row: dict-like with ref_qty_mean, r2_target, r2_ref, tg_n_below_cutoff, tg_n_wells,
    ratio_calc, tg_ct_mean. classifier_call: optional 'pos'/'neg'. classifier_prob: p(pos).
    reference: display name of the reference gene. Returns dict: decision
    ('positive'|'negative'|'na'|'review'), redo, review, quality, reasons[], annotations[],
    recommendation."""
    tx = dict(_TEXTS)
    tx.update(texts or {})
    ref = _num(row.get("ref_qty_mean"))
    r2t = _num(row.get("r2_target"))
    r2r = _num(row.get("r2_ref"))
    n_pos = int(_num(row.get("tg_n_below_cutoff")) or 0)
    nw = int(_num(row.get("tg_n_wells")) or 3)
    ratio = _num(row.get("ratio_calc"))
    prob = _num(classifier_prob)
    quality = quality_category(ref, T)

    hard = []  # reasons that make the result not assessable
    if ref is None:
        hard.append(f"{reference} reference missing - material quality cannot be assessed")
    elif ref < T.ref_insufficient:
        hard.append(f"insufficient starting material: {reference} copies {ref:.0f} < {T.ref_insufficient:.0f}")
    if r2r is not None and r2r < T.r2_min:
        hard.append(f"{reference} standard curve not linear: R2={r2r:.3f} < {T.r2_min}")
    if r2t is not None and r2t < T.r2_min:
        hard.append(f"target standard curve not linear: R2={r2t:.3f} < {T.r2_min}")

    if hard:
        rec = tx["redo_material"] if (ref is not None and ref < T.ref_insufficient) else tx["redo_run"]
        return dict(decision="na", redo=True, review=False, quality=quality, reasons=hard,
                    annotations=[], recommendation=rec)

    # ---- assessable: model + objective replicate rule ----
    if classifier_call in ("pos", "neg"):
        model_call = classifier_call
    elif prob is not None:
        model_call = "pos" if prob >= T.decision_threshold else "neg"
    else:
        model_call = "pos" if n_pos >= T.min_pos_replicates else "neg"
    rule_call = "pos" if n_pos >= T.min_pos_replicates else "neg"
    call = "positive" if model_call == "pos" else "negative"

    ann = []
    if quality == "limited":
        ann.append(f"limited material ({T.ref_insufficient:.0f}-{T.ref_sufficient:.0f} {reference} copies)"
                   " - interpret with caution")
    if call == "positive" and n_pos and n_pos < T.min_pos_replicates:
        ann.append(f"weak/uncertain positive: only {int(n_pos)}/{int(nw)} target replicates < {T.ct_pos_max:.0f}")
    if call == "positive" and ratio is not None and ratio < T.low_level_ratio:
        ann.append(f"{tx['low_level']} (<{T.low_level_ratio:.0f} copies per {ratio_scale:g} {reference})")

    review = []
    if T.enable_review:
        tgct = _num(row.get("tg_ct_mean"))
        conflict = (model_call != rule_call)
        discordant = (n_pos == 1 and nw >= 2)
        if prob is not None:
            if T.review_prob_lo <= prob <= T.review_prob_hi:
                review.append(f"model not confident (p={prob:.2f})")
            if conflict:
                review.append(f"model call ({model_call}) conflicts with the Ct rule "
                              f"({rule_call}, {n_pos}/{nw} wells<{T.ct_pos_max:.0f})")
            if T.review_flag_discordant and discordant:
                review.append(f"discordant replicates: only 1/{nw} wells Ct<{T.ct_pos_max:.0f}")
        else:
            if conflict:
                review.append(f"call ({model_call}) conflicts with the Ct rule ({rule_call})")
            if discordant:
                review.append(f"discordant replicates: only 1/{nw} wells Ct<{T.ct_pos_max:.0f}")
            if n_pos >= 1 and ratio is not None and ratio < T.low_level_ratio:
                review.append(f"low-level signal: ratio {ratio:.0f} < {T.low_level_ratio:.0f}")
            if tgct is not None and T.review_ct_lo <= tgct <= T.review_ct_hi and n_pos < nw:
                review.append(f"borderline Ct {tgct:.1f} at the ~{T.ct_pos_max:.0f} detection limit")
    if review:
        return dict(decision="review", redo=False, review=True, quality=quality,
                    reasons=[], annotations=ann, review_reasons=review, model_call=call,
                    recommendation=tx["review"])
    return dict(decision=call, redo=False, review=False, quality=quality, reasons=[],
                annotations=ann, recommendation="")


def assess_frame(df, calls=None, probs=None, T=QCThresholds()):
    """Vectorised over a DataFrame. calls: optional 'pos'/'neg' per row; probs: p(pos) per row."""
    import pandas as pd
    out = []
    calls = list(calls) if calls is not None else [None] * len(df)
    probs = list(probs) if probs is not None else [None] * len(df)
    for (_, r), c, p in zip(df.iterrows(), calls, probs):
        a = assess(r.to_dict(), classifier_call=c, T=T, classifier_prob=p)
        out.append(dict(decision=a["decision"], redo=a["redo"], review=a.get("review", False),
                        qc_quality=a["quality"], qc_reason="; ".join(a["reasons"]),
                        qc_review_reason="; ".join(a.get("review_reasons", [])),
                        qc_annotation="; ".join(a["annotations"]), recommendation=a["recommendation"]))
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(out)], axis=1)
