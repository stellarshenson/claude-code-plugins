"""Document processing tools: source grounding, compliance checks, validation.

The grounding engine itself lives in the standalone :mod:`groundrails` package
(a PyPI dependency). This package provides the document-reading layer (PDF /
DOCX / OCR, which groundrails does not cover), the multi-document ``validate``
orchestration, and the ``document-processing`` CLI that drives groundrails.

The core grounding API is re-exported from groundrails for convenience.
"""

try:
    from groundrails import (
        GroundingMatch,
        Location,
        ground,
        ground_batch,
    )
except ModuleNotFoundError as exc:  # pragma: no cover
    # groundrails is 3.12-only, so it installs under an environment marker and is
    # simply absent everywhere else in the toolkit's 3.11+ band - where the bare
    # "No module named 'groundrails'" gives no hint why. Narrow to groundrails
    # itself so a broken transitive dep keeps its own name.
    if exc.name != "groundrails":
        raise
    raise ModuleNotFoundError(
        "document-processing requires the 'groundrails' engine, which is not "
        "installed. It supports Python 3.12 only, so it is absent by design on "
        "every other interpreter; on 3.12 reinstall the toolkit. Every "
        "subcommand needs it; the other toolkit CLIs are unaffected."
    ) from exc

__all__ = ["GroundingMatch", "Location", "ground", "ground_batch"]
