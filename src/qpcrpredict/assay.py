"""Assay configuration: everything that is specific to a laboratory's qPCR assay.

Nothing about targets, reference genes, control names, label vocabulary, cycle number or
thresholds is written into the code. It all comes from an assay configuration (JSON). Two
configurations ship with the package: ``aml_mrd`` (the default, matching the packaged model) and
``generic`` (a template for any standard-curve qPCR assay).
"""
import copy
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_ASSAY_DIR = os.path.join(_HERE, "data", "assays")
DEFAULT_ASSAY = "aml_mrd"

_REQUIRED = ("name", "n_cycles", "references", "targets", "controls", "standards", "labels", "qc")


def _clean(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower().replace("ã¤", "ä")


def _key(s):
    return re.sub(r"[^a-z0-9]+", "", _clean(s))


def packaged_assays():
    """Names of the assay configurations that ship with the package."""
    return sorted(f[:-5] for f in os.listdir(_ASSAY_DIR) if f.endswith(".json"))


class Assay:
    """A loaded assay configuration with the name-resolution logic that uses it."""

    def __init__(self, cfg):
        missing = [k for k in _REQUIRED if k not in cfg]
        if missing:
            raise ValueError(f"assay configuration lacks the keys: {', '.join(missing)}")
        if not cfg["references"]:
            raise ValueError("assay configuration needs at least one reference")
        self.cfg = copy.deepcopy(cfg)
        self.name = cfg["name"]
        self.n_cycles = int(cfg["n_cycles"])
        self.baseline_cycles = tuple(cfg.get("baseline_cycles") or (3, 15))
        self.ct_cap = float(cfg.get("ct_cap", 50))
        self.ratio_scale = float(cfg.get("ratio_scale", 10000))
        self.texts = dict(cfg.get("texts") or {})
        self.qc = dict(cfg["qc"])
        self._refs = [(r["family"], r.get("name", r["family"]), [re.compile(p) for p in r["patterns"]])
                      for r in cfg["references"]]
        self._noise = [re.compile(p) for p in cfg.get("noise_patterns") or []]
        self._targets = []
        for t in cfg["targets"]:
            self._targets.append(dict(
                name=t["name"], family=t["family"],
                aliases={_key(a) for a in t.get("aliases", [])} | {_key(t["name"]), _key(t["family"])},
                patterns=[re.compile(p) for p in t["patterns"]],
                subtypes=[(re.compile(s["pattern"]), s["subtype"]) for s in t.get("subtypes", [])],
                default_subtype=t.get("default_subtype") or t["family"]))
        self._unknown_family = cfg.get("unknown_target_family")
        c = cfg["controls"]
        self._ctrl_exact = {x.lower() for x in c.get("exact", [])}
        self._ctrl_prefix = tuple(x.lower() for x in c.get("prefixes", []))
        self._ctrl_contains = tuple(x.lower() for x in c.get("contains", []))
        self._ctrl_tasks = {x.upper() for x in c.get("tasks", [])}
        s = cfg["standards"]
        self._std_tasks = {x.upper() for x in s.get("tasks", [])}
        self._std_prefix = tuple(x.upper() for x in s.get("sample_prefixes", []))
        self.std_ct_max = float(s.get("ct_max", 45))
        strip = cfg.get("group_id_strip")
        self._group_strip = re.compile(strip) if strip else None

    # ------------------------------------------------------------------ references / targets
    @property
    def reference_family(self):
        """Family code of the primary reference (the first one listed)."""
        return self._refs[0][0]

    @property
    def reference_name(self):
        return self._refs[0][1]

    @property
    def target_names(self):
        return [t["name"] for t in self._targets]

    def normalize_target(self, name, target_type=None):
        """Raw detector name -> (family, subtype, kind); kind is one of reference, target,
        target_other, noise, empty. ``target_type`` is the type stored in the run file, if any
        ('ref' marks a reference in RDML)."""
        s = _clean(name)
        if not s:
            return (None, None, "empty")
        for fam, _nm, pats in self._refs:
            if any(p.search(s) for p in pats):
                return (fam, fam, "reference")
        if any(p.search(s) for p in self._noise):
            return (None, None, "noise")
        for t in self._targets:
            if any(p.search(s) for p in t["patterns"]):
                sub = t["default_subtype"]
                for rx, tmpl in t["subtypes"]:
                    m = rx.search(s)
                    if m:
                        sub = tmpl
                        for i, g in enumerate(m.groups(), 1):
                            sub = sub.replace("{%d}" % i, (g or "").upper())
                        break
                return (t["family"], sub, "target")
        if target_type == "ref":
            return (self.reference_family, self.reference_family, "reference")
        slug = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        if self._unknown_family:
            return (self._unknown_family, slug[:20], "target_other")
        return (slug.upper(), slug.upper(), "target_other")

    def resolve_target(self, token):
        """User token (public name, alias or raw detector name) -> family code."""
        for t in self._targets:
            if token == t["name"]:
                return t["family"]
        k = _key(token)
        for t in self._targets:
            if k in t["aliases"]:
                return t["family"]
        fam, _sub, kind = self.normalize_target(token)
        if kind in ("target", "target_other") and fam:
            return fam
        known = ", ".join(self.target_names) or "any detector name on the plate"
        raise ValueError(f"unrecognised target '{token}' for assay '{self.name}'. Known: {known}.")

    # ------------------------------------------------------------------ wells / samples
    def is_control(self, sample, task=None):
        s = (sample or "").strip().lower()
        if task and task.strip().upper() in self._ctrl_tasks:
            return True
        if s in self._ctrl_exact:
            return True
        if self._ctrl_prefix and s.startswith(self._ctrl_prefix):
            return True
        return any(w in s for w in self._ctrl_contains)

    def is_standard(self, well):
        if (well.get("task") or "").strip().upper() in self._std_tasks:
            return True
        return bool(self._std_prefix) and (well.get("sample") or "").upper().startswith(self._std_prefix)

    def group_id(self, sample):
        """Identifier used to keep repeated measurements of one sample in one CV fold."""
        s = str(sample).upper().strip()
        return self._group_strip.sub("", s) if self._group_strip else s

    # ------------------------------------------------------------------ labels
    def normalize_label(self, v):
        s = _clean(v)
        if not s:
            return None
        for cls in ("pos", "neg", "na"):
            spec = self.cfg["labels"].get(cls) or {}
            if s in {x.lower() for x in spec.get("exact", [])}:
                return cls
        for cls in ("pos", "neg", "na"):
            pre = tuple(x.lower() for x in (self.cfg["labels"].get(cls) or {}).get("prefixes", []))
            if pre and s.startswith(pre):
                return cls
        return None

    def to_dict(self):
        return copy.deepcopy(self.cfg)


def load_assay(spec=None):
    """``spec``: None (default assay), the name of a packaged assay, a path to a JSON file, a
    dict, or an ``Assay``."""
    if isinstance(spec, Assay):
        return spec
    if isinstance(spec, dict):
        return Assay(spec)
    spec = spec or DEFAULT_ASSAY
    path = spec if os.path.exists(spec) else os.path.join(_ASSAY_DIR, f"{spec}.json")
    if not os.path.exists(path):
        raise ValueError(f"assay '{spec}' is neither a file nor one of: {', '.join(packaged_assays())}")
    with open(path, encoding="utf-8") as f:
        return Assay(json.load(f))
