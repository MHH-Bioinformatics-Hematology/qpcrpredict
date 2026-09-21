"""Read and write RDML, the vendor-neutral open format for real-time PCR data (www.rdml.org).

An RDML file is a ZIP archive that holds one XML document (``rdml_data.xml``). Only the Python
standard library is used. Versions 1.1 to 1.4 are read. The reader returns the same structure
as :func:`qpcrpredict.eds.parse_eds`, so every downstream step is independent of the file format.
"""
import re
import zipfile
import xml.etree.ElementTree as ET

# RDML sample type -> task name used throughout the package
_TASK = {"unkn": "UNKNOWN", "std": "STANDARD", "ntc": "NTC", "nac": "NAC", "ntp": "NTP",
         "nrt": "NRT", "pos": "POS", "neg": "NEG", "opt": "OPT"}
_TYPE = {v: k for k, v in _TASK.items()}
_TYPE.update({"TARGET": "unkn", "UNKN": "unkn", "": "unkn"})
NS = "http://www.rdml.org"


def _strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _text(el, tag):
    c = el.find(tag) if el is not None else None
    return c.text.strip() if c is not None and c.text else None


def is_rdml(path):
    try:
        with zipfile.ZipFile(path) as z:
            return any(n.lower().endswith("rdml_data.xml") for n in z.namelist())
    except zipfile.BadZipFile:
        return False


def _read_xml(path):
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".xml")]
            pick = [n for n in names if n.lower().endswith("rdml_data.xml")] or names
            if not pick:
                raise ValueError(f"{path}: no XML document inside the RDML archive")
            data = z.read(pick[0])
    except zipfile.BadZipFile:
        with open(path, "rb") as f:          # some tools write the XML uncompressed
            data = f.read()
    return _strip_ns(ET.fromstring(data))


def parse_rdml(path, experiment=None, run=None):
    """Return {'path', 'meta', 'wells'} for one run of an RDML file.

    If the file holds several experiments or runs, ``experiment`` and ``run`` select one by id;
    by default all runs are read and the well id is prefixed with the run id when needed.
    Per well: well, sample, detector, task, ct, avg_ct, ct_sd, qty, avg_qty, qty_sd, rn, drn and
    target_type. RDML stores one fluorescence curve per reaction; it is returned as ``rn``.
    ``drn`` is the background-corrected curve if the file provides one, otherwise None (it is
    then computed by :func:`qpcrpredict.io.complete_run`). ``qty`` is filled for standards only.
    """
    root = _read_xml(path)
    out = {"path": path, "wells": [],
           "meta": {"format": "rdml", "rdml_version": root.get("version"), "run_date": None}}

    samples = {}
    for s in root.findall("sample"):
        types = {}
        for t in s.findall("type"):
            types[t.get("targetId")] = (t.text or "").strip().lower()
        qty = {}
        for q in s.findall("quantity"):
            v = _text(q, "value")
            if v is not None:
                qty[q.get("targetId")] = v
        samples[s.get("id")] = dict(types=types, qty=qty)
    targets = {t.get("id"): (_text(t, "type") or "").lower() for t in root.findall("target")}

    runs = []
    for e in root.findall("experiment"):
        if experiment is not None and e.get("id") != experiment:
            continue
        for r in e.findall("run"):
            if run is not None and r.get("id") != run:
                continue
            runs.append((e.get("id"), r))
    if not runs:
        raise ValueError(f"{path}: no matching experiment/run in the RDML file")
    out["meta"]["runs"] = [f"{e}/{r.get('id')}" for e, r in runs]

    multi = len(runs) > 1
    for eid, r in runs:
        rd = _text(r, "runDate")
        if rd and not out["meta"]["run_date"]:
            out["meta"]["run_date"] = rd[:10]
        for react in r.findall("react"):
            s_el = react.find("sample")
            sid = s_el.get("id") if s_el is not None else ""
            info = samples.get(sid, dict(types={}, qty={}))
            for d in react.findall("data"):
                tar = d.find("tar")
                tid = tar.get("id") if tar is not None else ""
                stype = info["types"].get(tid) or info["types"].get(None) or "unkn"
                task = _TASK.get(stype, stype.upper())
                cq = _text(d, "cq")
                try:
                    if cq is None or float(cq) < 0:      # RDML: -1 = no amplification
                        cq = ""
                except ValueError:
                    cq = ""
                q = info["qty"].get(tid) or info["qty"].get(None) or ""
                adp = sorted(((int(float(_text(a, "cyc"))), _text(a, "fluor"), _text(a, "bgFluor"))
                              for a in d.findall("adp") if _text(a, "cyc") and _text(a, "fluor")),
                             key=lambda x: x[0])
                rn = [a[1] for a in adp] or None
                bg = [a[2] for a in adp]
                drn = None
                if rn and all(b is not None for b in bg):
                    drn = [str(float(f) - float(b)) for f, b in zip(rn, bg)]
                wid = react.get("id") or ""
                out["wells"].append(dict(
                    well=f"{r.get('id')}:{wid}" if multi else wid, sample=sid, detector=tid,
                    task=task, ct=cq, avg_ct="", ct_sd="",
                    qty=q if task == "STANDARD" else "", avg_qty="", qty_sd="",
                    rn=rn, drn=drn, target_type=targets.get(tid) or None,
                    excluded=_text(d, "excl") is not None))
    out["wells"] = [w for w in out["wells"] if not w.pop("excluded")]
    return out


def write_rdml(parsed, path, reference_detectors=()):
    """Write a parsed run as RDML 1.2. Standards keep their quantity; the fluorescence curve
    written is ``rn``. ``reference_detectors`` are marked with the target type 'ref'."""
    root = ET.Element("rdml", {"version": "1.2", "xmlns": NS})
    ET.SubElement(root, "dateMade").text = (parsed["meta"].get("run_date") or "1970-01-01") + "T00:00:00"
    ET.SubElement(root, "id").append(_el("publisher", "qpcrpredict"))
    root.find("id").append(_el("serialNumber", "1"))
    dye = ET.SubElement(root, "dye", {"id": "reporter"})
    seen_s, seen_t = {}, []
    for w in parsed["wells"]:
        s = w["sample"] or "unnamed"
        key = (s, (w.get("task") or "").upper())
        if s not in seen_s:
            seen_s[s] = w
        if w["detector"] not in seen_t:
            seen_t.append(w["detector"])
    for s, w in seen_s.items():
        el = ET.SubElement(root, "sample", {"id": s})
        task = (w.get("task") or "").upper()
        ET.SubElement(el, "type").text = _TYPE.get(task, "unkn")
        if task == "STANDARD" and str(w.get("qty") or "").strip():
            q = ET.SubElement(el, "quantity")
            q.append(_el("value", str(w["qty"])))
            q.append(_el("unit", "cop"))
    refs = set(reference_detectors)
    for t in seen_t:
        el = ET.SubElement(root, "target", {"id": t or "unnamed"})
        ET.SubElement(el, "type").text = "ref" if t in refs else "toi"
        ET.SubElement(el, "dyeId", {"id": "reporter"})
    exp = ET.SubElement(root, "experiment", {"id": "experiment"})
    run = ET.SubElement(exp, "run", {"id": "run"})
    if parsed["meta"].get("run_date"):
        run.append(_el("runDate", parsed["meta"]["run_date"] + "T00:00:00"))
    fmt = ET.SubElement(run, "pcrFormat")
    for k, v in (("rows", "8"), ("columns", "12"), ("rowLabel", "ABC"), ("columnLabel", "123")):
        fmt.append(_el(k, v))
    for w in parsed["wells"]:
        m = re.match(r"\d+", str(w["well"]))
        react = ET.SubElement(run, "react", {"id": str(int(m.group(0)) + 1) if m else "1"})
        ET.SubElement(react, "sample", {"id": w["sample"] or "unnamed"})
        d = ET.SubElement(react, "data")
        ET.SubElement(d, "tar", {"id": w["detector"] or "unnamed"})
        try:
            cq = float(w["ct"])
        except (TypeError, ValueError):
            cq = -1.0
        d.append(_el("cq", repr(cq)))
        for i, f in enumerate(w.get("rn") or [], 1):
            a = ET.SubElement(d, "adp")
            a.append(_el("cyc", str(i)))
            a.append(_el("fluor", str(f)))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("rdml_data.xml", ET.tostring(root, encoding="utf-8", xml_declaration=True))
    return path


def _el(tag, text):
    e = ET.Element(tag)
    e.text = text
    return e
