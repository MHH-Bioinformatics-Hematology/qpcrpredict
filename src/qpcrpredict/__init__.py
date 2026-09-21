"""qpcrpredict - trained positive/negative calls from raw real-time PCR run files.

Part of the LeukoPredict tools, developed for leukemia diagnostics at Hannover Medical School.

Features are derived only from the run file (amplification curves, Ct and quantities). A trained
classifier gives the probability of a positive call; a quality and review gate turns runs that
cannot be evaluated into an explicit 'na' (repeat) and ambiguous calls into 'review'. Targets,
reference gene, control names and thresholds are defined in an assay configuration.
"""
__version__ = "1"

from .assay import Assay, load_assay, packaged_assays
from .eds import parse_eds
from .rdml import parse_rdml, write_rdml
from .io import load_run
from .genes import normalize_target, resolve_gene, GENE_CHOICES
from .qc import QCThresholds, assess

__all__ = [
    "__version__", "Assay", "load_assay", "packaged_assays", "parse_eds", "parse_rdml",
    "write_rdml", "load_run", "normalize_target", "resolve_gene", "GENE_CHOICES",
    "QCThresholds", "assess",
]
