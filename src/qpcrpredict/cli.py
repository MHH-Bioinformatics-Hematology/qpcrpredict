"""Unified `qpcrpredict` command: predict | train | assay | convert | info."""
import sys
import json
import argparse

from . import __version__
from . import models as M


def _info(argv=None):
    ap = argparse.ArgumentParser(prog="qpcrpredict info", description="Show package and model information.")
    ap.add_argument("--model", default=None, help="describe this model bundle (default: packaged model)")
    a = ap.parse_args(argv)
    from .assay import packaged_assays
    from .bundle import default_model_path, load_bundle, bundle_assay
    from .io import RUN_EXTENSIONS
    print(f"qpcrpredict {__version__}")
    print("run formats   :", ", ".join(RUN_EXTENSIONS))
    print("assays        :", ", ".join(packaged_assays()))
    print("models        :", ", ".join(M.ALL_MODELS))
    dm = default_model_path()
    print("packaged model:", dm or "(none bundled)")
    path = a.model or dm
    if path:
        b = load_bundle(path)
        A = bundle_assay(b)
        print(f"\nbundle {path}")
        for k in ("model_name", "rep", "feature_dim", "n_train", "created", "classes"):
            if k in b:
                print(f"  {k:12s}: {b[k]}")
        print(f"  {'assay':12s}: {A.name}")
        print(f"  {'reference':12s}: {A.reference_name}")
        print(f"  {'targets':12s}: {', '.join(A.target_names) or '(any detector on the plate)'}")
        note = M.license_note(b.get("model_name"))
        if note:
            print(f"  {'license':12s}: {note}")
        if b.get("cv_metrics"):
            cm = b["cv_metrics"]
            keys = [k for k in ("roc_auc", "accuracy", "precision", "recall", "specificity", "f1", "f2", "mcc") if k in cm]
            print("  cv          : " + "  ".join(f"{k}={cm[k]}" for k in keys))


def _assay(argv=None):
    ap = argparse.ArgumentParser(
        prog="qpcrpredict assay",
        description="List the packaged assay configurations, print one as JSON (as a starting point "
                    "for your own), or check a configuration against a run file.")
    ap.add_argument("--show", metavar="ASSAY", default=None, help="print this assay configuration as JSON")
    ap.add_argument("--check", metavar="RUN", default=None,
                    help="run file (.eds or .rdml): show how its detectors and samples are interpreted")
    ap.add_argument("--assay", default=None, help="assay used with --check (name or JSON file)")
    a = ap.parse_args(argv)
    from .assay import load_assay, packaged_assays
    if a.show:
        print(json.dumps(load_assay(a.show).to_dict(), indent=2, ensure_ascii=False))
        return 0
    if a.check:
        import collections
        from .io import load_run
        A = load_assay(a.assay)
        run = load_run(a.check, A)
        dets = collections.OrderedDict()
        for w in run["wells"]:
            dets.setdefault(w["detector"], A.normalize_target(w["detector"], w.get("target_type")))
        print(f"assay {A.name}; {len(run['wells'])} wells; format {run['meta'].get('format')}")
        print("\ndetector -> family / subtype / kind")
        for d, (fam, sub, kind) in dets.items():
            print(f"  {d!r:32s} -> {fam} / {sub} / {kind}")
        names = collections.Counter()
        for w in run["wells"]:
            s = (w["sample"] or "").strip()
            if s:
                names["control" if A.is_control(s, w.get("task")) else "sample"] += 0
                names[(s, "control" if A.is_control(s, w.get("task")) else "sample")] += 1
        print("\nsample name -> role (wells)")
        for k, n in names.items():
            if isinstance(k, tuple):
                print(f"  {k[0]!r:32s} -> {k[1]} ({n})")
        return 0
    for n in packaged_assays():
        A = load_assay(n)
        print(f"{n:10s} reference={A.reference_name}; targets: {', '.join(A.target_names) or 'any detector'}")
        print(f"{'':10s} {A.cfg.get('description', '')}")
    return 0


def _convert(argv=None):
    ap = argparse.ArgumentParser(prog="qpcrpredict convert",
                                 description="Convert a run file (.eds) to the open RDML format.")
    ap.add_argument("--run", required=True, help="input run file")
    ap.add_argument("--out", required=True, help="output .rdml file")
    ap.add_argument("--assay", default=None, help="assay configuration, used to mark the reference target")
    a = ap.parse_args(argv)
    from .assay import load_assay
    from .io import load_run
    from .rdml import write_rdml
    A = load_assay(a.assay)
    run = load_run(a.run, A)
    refs = {w["detector"] for w in run["wells"]
            if A.normalize_target(w["detector"], w.get("target_type"))[2] == "reference"}
    write_rdml(run, a.out, reference_detectors=refs)
    print(f"wrote {a.out} ({len(run['wells'])} reactions)")
    return 0


_COMMANDS = {
    "predict": "score a run (.eds or .rdml) for a target with a trained model",
    "train": "train a model from run files and a labels table",
    "assay": "list, print or check assay configurations",
    "convert": "convert a run file to RDML",
    "info": "show package and model information",
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="qpcrpredict",
        description="Trained positive/negative calls from raw real-time PCR run files (.eds, .rdml). "
                    "Part of the LeukoPredict tools.")
    parser.add_argument("--version", action="version", version=f"qpcrpredict {__version__}")
    sub = parser.add_subparsers(dest="cmd")
    for c, h in _COMMANDS.items():
        sub.add_parser(c, add_help=False, help=h)

    if not argv:
        parser.print_help()
        return 1
    if argv[0] in ("-h", "--help", "--version"):
        parser.parse_args(argv)
        return 0

    cmd, rest = argv[0], argv[1:]
    if cmd == "predict":
        from .predict import main as m
        return m(rest)
    if cmd == "train":
        from .train import main as m
        return m(rest)
    if cmd == "assay":
        return _assay(rest)
    if cmd == "convert":
        return _convert(rest)
    if cmd == "info":
        return _info(rest)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
