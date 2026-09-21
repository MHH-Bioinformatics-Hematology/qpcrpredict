"""Model zoo + patient-grouped cross-validation + the full binary-metric suite.

Default model is scikit-learn's HistGradientBoosting (no extra dependencies, native NaN handling).
LightGBM / CatBoost need the [boost] extra; TabPFN needs the [tabpfn] extra. Those imports are
lazy, so the core package installs and runs with scikit-learn alone.
"""
import time
import numpy as np

ALL_MODELS = ["logreg", "random_forest", "extra_trees", "hist_gb", "lightgbm", "catboost",
              "tabpfn_v25", "tabpfn_v26", "tabpfn_v3"]

# friendly aliases accepted on the CLI
MODEL_ALIASES = {"histgb": "hist_gb", "hgb": "hist_gb", "rf": "random_forest",
                 "et": "extra_trees", "lgbm": "lightgbm", "lgb": "lightgbm", "cat": "catboost"}


# Model families whose pretrained weights carry a restrictive license. The text is stored in every
# bundle of such a family and shown when the bundle is trained, inspected or refused.
RESTRICTED_LICENSES = {
    "tabpfn": ("TabPFN models are licensed by Prior Labs GmbH for non-commercial use only. A bundle of "
               "this family contains the pretrained TabPFN model. It may be used for academic, "
               "non-commercial research. Use in a commercial setting, in routine diagnostics or any "
               "other production deployment, or as part of a hosted service, requires a separate "
               "commercial license from Prior Labs GmbH. Built with PriorLabs-TabPFN."),
}


def license_note(model_name):
    """License text for a restricted model family, or None."""
    for prefix, text in RESTRICTED_LICENSES.items():
        if str(model_name or "").lower().startswith(prefix):
            return text
    return None


def resolve_model(name):
    return MODEL_ALIASES.get(name, name)


def make_model(name):
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler

    name = resolve_model(name)
    if name == "logreg":
        from sklearn.linear_model import LogisticRegression
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(max_iter=5000, class_weight="balanced"))
    if name == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        return make_pipeline(SimpleImputer(strategy="median"),
                             RandomForestClassifier(n_estimators=400, class_weight="balanced",
                                                    n_jobs=-1, random_state=0))
    if name == "extra_trees":
        from sklearn.ensemble import ExtraTreesClassifier
        return make_pipeline(SimpleImputer(strategy="median"),
                             ExtraTreesClassifier(n_estimators=400, class_weight="balanced",
                                                  n_jobs=-1, random_state=0))
    if name == "hist_gb":
        from sklearn.ensemble import HistGradientBoostingClassifier
        return HistGradientBoostingClassifier(random_state=0)  # handles NaN natively
    if name == "lightgbm":
        from lightgbm import LGBMClassifier
        return make_pipeline(SimpleImputer(strategy="median"),
                             LGBMClassifier(n_estimators=400, class_weight="balanced",
                                            random_state=0, verbose=-1))
    if name == "catboost":
        from catboost import CatBoostClassifier
        return make_pipeline(SimpleImputer(strategy="median"),
                             CatBoostClassifier(iterations=400, depth=6, verbose=0,
                                                random_state=0, auto_class_weights="Balanced"))
    if name.startswith("tabpfn"):
        import os
        from tabpfn import TabPFNClassifier
        ckpt = {"tabpfn_v25": "tabpfn-v2.5-classifier-v2.5_default.ckpt",
                "tabpfn_v26": "tabpfn-v2.6-classifier-v2.6_default.ckpt",
                "tabpfn_v3": "tabpfn-v3-classifier-v3_default.ckpt"}[name]
        path = os.path.expanduser(os.path.join("~/.cache/tabpfn", ckpt))
        device = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
        except Exception:
            pass
        kw = dict(device=device, ignore_pretraining_limits=True, random_state=0)
        if os.path.exists(path):
            kw["model_path"] = path
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             TabPFNClassifier(**kw))
    raise ValueError(f"unknown model '{name}' (choices: {', '.join(ALL_MODELS)})")


# ----------------------------------------------------------------- metrics
def fbeta(precision, recall, beta):
    b2 = beta * beta
    d = b2 * precision + recall
    return (1 + b2) * precision * recall / d if d > 0 else 0.0


def _mcc_safe(y_true, y_pred):
    from sklearn.metrics import matthews_corrcoef
    try:
        return matthews_corrcoef(y_true, y_pred)
    except Exception:
        return 0.0


def classification_metrics(y_true, y_pred, y_score):
    """Full binary-metric suite (positive class = 1). Threshold metrics at 0.5 + ROC/PR-AUC."""
    from sklearn.metrics import (roc_auc_score, average_precision_score, confusion_matrix,
                                 cohen_kappa_score, brier_score_loss)
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    P = tp / (tp + fp) if (tp + fp) else 0.0
    R = tp / (tp + fn) if (tp + fn) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    npv = tn / (tn + fn) if (tn + fn) else 0.0
    acc = (tp + tn) / (tp + tn + fp + fn)
    bal_acc = 0.5 * (R + spec)
    out = dict(
        tp=int(tp), fp=int(fp), tn=int(tn), fn=int(fn),
        prevalence=round((tp + fn) / len(y_true), 4),
        accuracy=round(acc, 4), balanced_accuracy=round(bal_acc, 4),
        precision=round(P, 4), recall=round(R, 4), sensitivity=round(R, 4),
        specificity=round(spec, 4), npv=round(npv, 4),
        f1=round(fbeta(P, R, 1), 4), f2=round(fbeta(P, R, 2), 4), f0_5=round(fbeta(P, R, 0.5), 4),
        mcc=round(_mcc_safe(y_true, y_pred), 4),
        cohen_kappa=round(cohen_kappa_score(y_true, y_pred), 4),
        youden_j=round(R + spec - 1, 4), markedness=round(P + npv - 1, 4),
    )
    try:
        out["roc_auc"] = round(roc_auc_score(y_true, y_score), 4)
        out["pr_auc"] = round(average_precision_score(y_true, y_score), 4)
        out["brier"] = round(brier_score_loss(y_true, y_score), 4)
    except ValueError:
        out["roc_auc"] = out["pr_auc"] = out["brier"] = None
    return out


# ----------------------------------------------------------------- cross-validation
def eval_cv(X, y, groups, model_name, n_splits=5, seed=0):
    """Patient-grouped StratifiedGroupKFold; out-of-fold metrics. None if too few groups/classes."""
    from sklearn.model_selection import StratifiedGroupKFold
    y = np.asarray(y)
    if len(np.unique(y)) < 2:
        return None
    minc = int(min(np.bincount(y)))
    if minc < 2 or len(np.unique(groups)) < n_splits:
        return None
    k = min(n_splits, minc, len(np.unique(groups)))
    if k < 2:
        return None
    skf = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=seed)
    oof_p = np.full(len(y), np.nan)
    oof_pred = np.full(len(y), np.nan)
    t0 = time.time()
    for tr, te in skf.split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            continue
        m = make_model(model_name)
        m.fit(X[tr], y[tr])
        oof_p[te] = m.predict_proba(X[te])[:, 1]
        oof_pred[te] = (oof_p[te] >= 0.5).astype(int)
    mask = ~np.isnan(oof_p)
    yt = y[mask]
    if len(np.unique(yt)) < 2:
        return None
    res = dict(model=model_name, n=int(mask.sum()), pos=int(yt.sum()), neg=int((yt == 0).sum()),
               folds=k, fit_time=round(time.time() - t0, 1))
    res.update(classification_metrics(yt, oof_pred[mask].astype(int), oof_p[mask]))
    return res


def oof_proba(X, y, groups, model_name, n_splits=5, seed=0):
    """Out-of-fold positive-class probabilities across the whole array."""
    from sklearn.model_selection import StratifiedGroupKFold
    y = np.asarray(y)
    oof = np.full(len(y), np.nan)
    k = min(n_splits, int(min(np.bincount(y))), len(np.unique(groups)))
    skf = StratifiedGroupKFold(n_splits=max(k, 2), shuffle=True, random_state=seed)
    for tr, te in skf.split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            continue
        m = make_model(model_name)
        m.fit(X[tr], y[tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
    return oof
