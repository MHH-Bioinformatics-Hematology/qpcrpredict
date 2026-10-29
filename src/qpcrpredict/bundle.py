"""Model bundle: the fitted pipeline plus everything needed to reproduce the decision.

A bundle is a joblib dictionary with the keys pipeline, rep, model_name, classes, feature_dim,
n_train, assay (the complete assay configuration the model was trained with), cv_metrics and
created. Bundles written by earlier versions carry ``qc_thresholds`` and no assay; they are read
with the packaged default assay and their stored thresholds.
"""
import os
import joblib

from .assay import load_assay

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.join(_HERE, "data", "aml_mrd_model.pkl")


def default_model_path():
    """Path to the model shipped inside the package, or None if not bundled."""
    return _DEFAULT if os.path.exists(_DEFAULT) else None


def packaged_models():
    """Names of the models shipped inside the package (``aml_mrd``, ``aml_mrd_abl10k``)."""
    d = os.path.join(_HERE, "data")
    return sorted(f[:-len("_model.pkl")] for f in os.listdir(d) if f.endswith("_model.pkl"))


def packaged_model_path(name):
    """Path of a packaged model given its name, or None."""
    p = os.path.join(_HERE, "data", f"{name}_model.pkl")
    return p if os.path.exists(p) else None


def load_bundle(path=None):
    """Load a bundle. If path is None, fall back to the packaged default model."""
    if path is None:
        path = default_model_path()
        if path is None:
            raise SystemExit("no model given and no packaged default model found; pass --model")
    if not os.path.exists(path):
        packaged = packaged_model_path(path)
        if packaged is None:
            raise SystemExit(f"model bundle not found: {path} (packaged models: {', '.join(packaged_models())})")
        path = packaged
    b = joblib.load(path)
    if not isinstance(b, dict) or "pipeline" not in b:
        raise SystemExit(f"{path} is not a model bundle")
    return b


def bundle_assay(bundle, override=None):
    """The assay a bundle was trained with. ``override`` (name, path, dict or Assay) wins."""
    if override is not None:
        return load_assay(override)
    if bundle.get("assay"):
        return load_assay(bundle["assay"])
    a = load_assay()                      # bundle from before the assay configuration existed
    if bundle.get("qc_thresholds"):
        from .qc import QCThresholds
        from dataclasses import asdict
        a.qc.update(asdict(QCThresholds.from_dict(bundle["qc_thresholds"])))
    return a


def save_bundle(bundle, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    joblib.dump(bundle, path)
    import json
    with open(os.path.splitext(path)[0] + ".json", "w") as f:
        json.dump({k: v for k, v in bundle.items() if k != "pipeline"}, f, indent=2, default=str)
