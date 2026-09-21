"""Name resolution for the default assay (kept for backwards compatibility).

All logic lives in :class:`qpcrpredict.assay.Assay`. These functions apply the packaged default assay;
code that works with another assay should call the methods of its own ``Assay`` object.
"""
from .assay import load_assay

_A = load_assay()

GENE_CHOICES = {name: _A.resolve_target(name) for name in _A.target_names}


def normalize_target(name):
    return _A.normalize_target(name)


def resolve_gene(token):
    return _A.resolve_target(token)


def normalize_label(v):
    return _A.normalize_label(v)


def is_control(sid):
    return _A.is_control(sid)
