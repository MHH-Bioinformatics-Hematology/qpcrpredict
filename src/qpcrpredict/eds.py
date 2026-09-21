"""Parse an Applied Biosystems .eds project file (a ZIP archive) -> run metadata + per-well records.

Per well: well, sample, detector, task, ct, avg_ct, ct_sd, qty, avg_qty, qty_sd, rn, drn.
All extraction is local; nothing is transmitted.
"""
import zipfile
import re
import datetime


def parse_eds(path):
    """Return {'path', 'meta': {...}, 'wells': [ {well, sample, detector, task, ct, qty, rn, drn}, ... ]}."""
    out = {"path": path, "wells": [], "meta": {"format": "eds"}}
    with zipfile.ZipFile(path) as z:
        # ---- experiment.xml: date, operator, name
        try:
            xml = z.read("apldbio/sds/experiment.xml").decode("utf-8", "replace")

            def tag(t):
                m = re.search(rf"<{t}>(.*?)</{t}>", xml, re.S)
                return m.group(1).strip() if m else None

            for k in ("Name", "Operator", "RunStartTime", "RunEndTime", "ModifiedTime", "FileName"):
                out["meta"][k] = tag(k)
            rs = out["meta"].get("RunStartTime")
            if rs and rs.isdigit():
                out["meta"]["run_date"] = datetime.datetime.utcfromtimestamp(
                    int(rs) / 1000
                ).strftime("%Y-%m-%d")
        except KeyError:
            pass
        # ---- analysis_result.txt: per-well table + Rn / DeltaRn curves
        try:
            txt = z.read("apldbio/sds/analysis_result.txt").decode("utf-8", "replace")
        except KeyError:
            return out

    header = None
    cur = None
    for ln in txt.split("\n"):
        parts = ln.rstrip("\r").split("\t")
        if parts and parts[0] == "Well" and "Detector" in parts:
            header = {name: i for i, name in enumerate(parts)}
            continue
        if header is None:
            continue
        c0 = parts[0].strip()
        if c0.isdigit():  # a well data row

            def g(name):
                i = header.get(name)
                return parts[i].strip() if i is not None and i < len(parts) else ""

            cur = {
                "well": c0,
                "sample": g("Sample Name"),
                "detector": g("Detector"),
                "task": g("Task"),
                "ct": g("Ct"),
                "avg_ct": g("Avg Ct"),
                "ct_sd": g("Ct SD"),
                "qty": g("Qty"),
                "avg_qty": g("Avg Qty"),
                "qty_sd": g("Qty SD"),
                "rn": None,
                "drn": None,
            }
            out["wells"].append(cur)
        elif cur is not None and parts[0].strip() == "Rn values":
            cur["rn"] = [x for x in parts[1:] if x != ""]
        elif cur is not None and parts[0].strip() == "Delta Rn values":
            cur["drn"] = [x for x in parts[1:] if x != ""]
    return out
