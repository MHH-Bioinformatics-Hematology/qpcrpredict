"""Tests that need no patient data: assay configuration, quality gate, features, RDML reader and
writer, quantities from the standard curve, and a train/predict round trip on synthetic runs."""
import json
import os

import numpy as np
import pandas as pd
import pytest

import qpcrpredict
from qpcrpredict import qc, features as F
from qpcrpredict.assay import load_assay, packaged_assays
from qpcrpredict.io import load_run, standard_curve, complete_run
from qpcrpredict.rdml import write_rdml, parse_rdml


def _curve(ct, n=40, top=3.0):
    c = np.arange(1, n + 1)
    if ct == "":                                   # no amplification: flat background
        return list(np.full(n, 0.05))
    return list(0.05 + top / (1 + np.exp(-(c - float(ct)) * 0.7)))


def synthetic_run(positive=True, reference="REFERENCE", target="MYTARGET", n=40, sample="S1"):
    """A parsed run in the common structure: standards for both assays, one sample, one NTC."""
    wells, k = [], 0

    def add(s, det, task, ct, qty=""):
        nonlocal k
        for _ in range(3):
            wells.append(dict(well=str(k), sample=s, detector=det, task=task, ct=str(ct), avg_ct="",
                              ct_sd="", qty=str(qty), avg_qty="", qty_sd="", rn=_curve(ct, n), drn=None))
            k += 1
    for det in (target, reference):
        for q, ct in ((1e5, 20.0), (1e4, 23.32), (1e3, 26.64), (1e2, 29.96)):
            add(f"STD {q:g}", det, "STANDARD", ct, q)
        add("water", det, "NTC", "")
    add(sample, reference, "UNKNOWN", 22.0)
    add(sample, target, "UNKNOWN", 24.0 if positive else "")
    return {"path": "synthetic", "meta": {"run_date": "2020-01-01"}, "wells": wells}


def test_packaged_assays_load():
    assert {"aml_mrd", "generic"} <= set(packaged_assays())
    for n in packaged_assays():
        a = load_assay(n)
        assert a.reference_family and a.n_cycles > 0


def test_default_assay_name_resolution():
    a = load_assay()
    assert a.resolve_target("NPM1") == "NPM1"
    assert a.resolve_target("RUNX1::RUNX1T1") == "AML1_ETO"
    assert a.resolve_target("t(8;21)") == "AML1_ETO"
    assert a.resolve_target("inv16") == "CBFB_MYH11"
    assert a.resolve_target("PML-RARA") == "PML_RARA"
    assert a.normalize_target("NPM1 mut A") == ("NPM1", "NPM1_A", "target")
    assert a.normalize_target("ABL")[2] == "reference"
    assert a.is_control("Neg Ko") and not a.is_control("Sample 12")
    assert a.normalize_label("positiv") == "pos" and a.normalize_label("negative") == "neg"
    assert qpcrpredict.resolve_gene("NPM1") == "NPM1"          # compatibility layer


def test_generic_assay_has_no_fixed_targets():
    a = load_assay("generic")
    assert a.target_names == []
    assert a.resolve_target("My Gene 7") == "MY_GENE_7"
    assert a.normalize_target("reference")[2] == "reference"
    assert a.is_control("anything", task="NTC")


def test_custom_assay_from_dict(tmp_path):
    cfg = load_assay("generic").to_dict()
    cfg["name"] = "custom"
    cfg["references"] = [{"name": "GUSB", "family": "GUSB", "patterns": ["^gusb$"]}]
    p = tmp_path / "a.json"
    p.write_text(json.dumps(cfg))
    a = load_assay(str(p))
    assert a.reference_name == "GUSB" and a.normalize_target("GUSB")[2] == "reference"
    with pytest.raises(ValueError):
        load_assay({"name": "broken"})


def test_qc_decisions():
    ok = dict(ref_qty_mean=50000, r2_target=0.99, r2_ref=0.99, tg_n_wells=3)
    a = qc.assess(dict(ok, tg_n_below_cutoff=3, ratio_calc=12000), classifier_call="pos", classifier_prob=0.99)
    assert a["decision"] == "positive" and a["quality"] == "sufficient"
    b = qc.assess(dict(ok, ref_qty_mean=400, tg_n_below_cutoff=0, ratio_calc=0), reference="GUSB")
    assert b["decision"] == "na" and b["redo"] and "GUSB" in b["reasons"][0]
    c = qc.assess(dict(ok, tg_n_below_cutoff=2, ratio_calc=300), classifier_call="pos", classifier_prob=0.5)
    assert c["decision"] == "review"
    d = qc.assess(dict(ok, tg_n_below_cutoff=3, ratio_calc=300), classifier_prob=0.4,
                  T=qc.QCThresholds(decision_threshold=0.3, review_prob_lo=0.1, review_prob_hi=0.2))
    assert d["decision"] == "positive"


def test_legacy_threshold_names():
    t = qc.QCThresholds.from_dict({"abl_sufficient": 5, "abl_insufficient": 2, "mrd_low_level": 9})
    assert (t.ref_sufficient, t.ref_insufficient, t.low_level_ratio) == (5, 2, 9)


def test_quantities_and_baseline_are_computed_when_missing():
    a = load_assay("generic")
    run = complete_run(synthetic_run(), a)
    sc = standard_curve([w for w in run["wells"] if w["detector"] == "MYTARGET"], a)
    assert sc["r2"] > 0.999 and abs(sc["slope"] + 3.32) < 0.01
    s = [w for w in run["wells"] if w["sample"] == "S1" and w["detector"] == "MYTARGET"][0]
    assert 5e3 < float(s["qty"]) < 8e3            # Ct 24 on this curve is about 6,200 copies
    assert s["drn"] is not None and abs(np.mean(s["drn"][2:15])) < 1e-6


def test_cycle_number_is_not_fixed():
    a = load_assay(dict(load_assay("generic").to_dict(), n_cycles=50))
    run = complete_run(synthetic_run(n=50), a)
    row, curves = F.sample_feature_record(run, "S1", "MYTARGET", a)
    X, names = F.build_features(pd.DataFrame([row]), pd.DataFrame([curves]), "all", a.ct_cap)
    assert X.shape == (1, 26) and sum(k.startswith("tdrn") for k in curves) == 50
    assert row["has_ref"] and row["tg_n_below_cutoff"] == 3


def test_rdml_round_trip(tmp_path):
    a = load_assay("generic")
    run = synthetic_run()
    p = str(tmp_path / "run.rdml")
    write_rdml(run, p, reference_detectors={"REFERENCE"})
    back = parse_rdml(p)
    assert len(back["wells"]) == len(run["wells"])
    assert {w["task"] for w in back["wells"]} == {"STANDARD", "NTC", "UNKNOWN"}
    assert [w for w in back["wells"] if w["detector"] == "REFERENCE"][0]["target_type"] == "ref"
    loaded = load_run(p, a)
    r1, _ = F.sample_feature_record(complete_run(run, a), "S1", "MYTARGET", a)
    r2, _ = F.sample_feature_record(loaded, "S1", "MYTARGET", a)
    assert r1["tg_ct_mean"] == pytest.approx(r2["tg_ct_mean"])
    assert r1["ratio_calc"] == pytest.approx(r2["ratio_calc"], rel=1e-6)


def test_train_and_predict_on_rdml_with_custom_assay(tmp_path):
    from qpcrpredict.train import fit
    from qpcrpredict.predict import predict
    rows = []
    for i in range(12):
        pos = i % 2 == 0
        s = f"P{i}"
        write_rdml(synthetic_run(positive=pos, sample=s), str(tmp_path / f"r{i}.rdml"), {"REFERENCE"})
        rows.append(dict(sample=s, target="MYTARGET", label="positive" if pos else "negative",
                         run_file=f"r{i}.rdml"))
    pd.DataFrame(rows).to_csv(tmp_path / "labels.csv", index=False)
    model = str(tmp_path / "m.pkl")
    fit(str(tmp_path), str(tmp_path / "labels.csv"), model_name="logreg", out=model, cv=False,
        assay="generic", log=lambda *a: None)
    assert os.path.exists(model) and os.path.exists(model[:-4] + ".json")
    res = predict(str(tmp_path / "r0.rdml"), "MYTARGET", model, quiet=True)
    assert list(res["sample"]) == ["P0"] and res["decision"].iloc[0] == "positive"
    res = predict(str(tmp_path / "r1.rdml"), "MYTARGET", model, quiet=True)
    assert res["decision"].iloc[0] == "negative"


def test_packaged_model_predicts():
    from qpcrpredict.bundle import default_model_path, load_bundle, bundle_assay
    if default_model_path() is None:
        pytest.skip("no packaged model")
    b = load_bundle()
    a = bundle_assay(b)
    assert a.name == "aml_mrd"
    run = complete_run(synthetic_run(reference="ABL", target="NPM1 mut A"), a)
    row, curves = F.sample_feature_record(run, "S1", "NPM1", a)
    X, _ = F.build_features(pd.DataFrame([row]), pd.DataFrame([curves]), b["rep"], a.ct_cap)
    p = b["pipeline"].predict_proba(X)[0, 1]
    assert 0.0 <= p <= 1.0
