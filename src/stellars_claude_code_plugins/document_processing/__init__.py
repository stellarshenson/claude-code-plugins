"""Document processing tools for source grounding, compliance checks, and validation.

Core exports (zero heavy deps): :func:`ground`, :func:`ground_batch`,
:class:`GroundingMatch`, :class:`Location`.

Optional semantic grounding (ModernBERT + FAISS) lives in
:mod:`.semantic` and requires ``stellars-claude-code-plugins[semantic]``.
It is lazy-imported — ``import stellars_claude_code_plugins.document_processing``
does NOT load torch, transformers, or faiss.
"""

from stellars_claude_code_plugins.document_processing.grounding import (
    GroundingMatch,
    Location,
    ground,
    ground_batch,
)

__all__ = ["GroundingMatch", "Location", "ground", "ground_batch"]
