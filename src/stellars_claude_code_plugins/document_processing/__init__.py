"""Document processing tools: source grounding, compliance checks, validation.

The grounding engine itself lives in the standalone :mod:`groundrails` package
(a PyPI dependency). This package provides the document-reading layer (PDF /
DOCX / OCR, which groundrails does not cover), the multi-document ``validate``
orchestration, and the ``document-processing`` CLI that drives groundrails.

The core grounding API is re-exported from groundrails for convenience.
"""

from groundrails import (
    GroundingMatch,
    Location,
    ground,
    ground_batch,
)

__all__ = ["GroundingMatch", "Location", "ground", "ground_batch"]
