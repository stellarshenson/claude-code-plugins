"""Tunable configuration for the grounding pipeline.

Every magic number that shapes classification or scoring lives here. The
defaults are calibrated against the BENCHMARK.md reference and can be
overridden via:

1. Explicit keyword argument to the API (``ground`` / ``ground_many``),
2. ``./.stellars-plugins/config.yaml`` in the project root,
3. The bundled default at
   ``stellars_claude_code_plugins/document_processing/config.yaml``.

Use :func:`load_config` to resolve the effective config. Use
``scripts/calibrate.py`` to grid-search values against the benchmark
and find optimal combinations.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Literal

import yaml

CONFIG_MODULE_DEFAULT = Path(__file__).parent / "config.yaml"
CONFIG_PROJECT_OVERRIDE = Path(".stellars-plugins/config.yaml")


@dataclass
class GroundingConfig:
    """All tunable parameters for grounding + semantic + chunking."""

    # ── match_type thresholds ────────────────────────────────────────────
    fuzzy_threshold: float = 0.85
    """Levenshtein partial-ratio in [0, 1] above which match_type=fuzzy."""

    bm25_threshold: float = 0.5
    """BM25 token-recall in [0, 1] above which match_type=bm25."""

    semantic_threshold: float = 0.6
    """Absolute cosine above which match_type=semantic (pre-percentile)."""

    semantic_threshold_percentile: float = 0.02
    """Top fraction of random chunk-pair distribution for semantic match."""

    agreement_threshold: float = 0.45
    """Minimum agreement_score for the agreement-fallback classifier."""

    # ── percentile safety floor ──────────────────────────────────────────
    percentile_floor: float = 0.65
    """Min value SemanticGrounder.percentile_threshold can return."""

    # ── agreement_score per-layer weights (raw sum, should total 1.0) ───
    agreement_weight_exact: float = 0.30
    agreement_weight_fuzzy: float = 0.25
    agreement_weight_bm25: float = 0.20
    agreement_weight_semantic: float = 0.25

    # ── agreement_score per-layer ramps (low..high -> v_layer in [0,1]) ─
    fuzzy_ramp_low: float = 0.5
    fuzzy_ramp_high: float = 1.0
    bm25_ramp_low: float = 0.0
    bm25_ramp_high: float = 0.5
    semantic_abs_ramp_low: float = 0.5
    semantic_abs_ramp_high: float = 1.0
    semantic_ratio_ramp_low: float = 0.80
    semantic_ratio_ramp_high: float = 1.00

    # ── voter thresholds ────────────────────────────────────────────────
    voter_exact: float = 1.0
    voter_fuzzy: float = 0.55
    voter_bm25: float = 0.15
    voter_semantic_abs: float = 0.70
    voter_semantic_ratio: float = 0.90
    voter_semantic_mode: Literal["or", "and", "abs_only", "ratio_only"] = "or"
    """How the semantic voter combines absolute score and ratio."""

    voter_bonus_2: float = 0.20
    voter_bonus_3_plus: float = 0.35

    # ── entity-presence penalty ─────────────────────────────────────────
    entity_penalty_factor: float = 0.15
    """Max fraction of agreement_score removed when 100% of claim entities absent from source."""

    # ── semantic / chunking ─────────────────────────────────────────────
    chunk_max_chars: int = 1500
    chunk_overlap_ratio: float = 0.25
    percentile_sample_n: int = 200

    # ── sentence-split fallback ─────────────────────────────────────────
    min_passage_chars: int = 40
    single_passage_fallback_length: int = 1500

    # ── classifier mode (H11) ───────────────────────────────────────────
    classifier_mode: Literal["absolute", "adaptive_gap"] = "adaptive_gap"
    """``absolute`` = use agreement_threshold. ``adaptive_gap`` = batch-mode rank-based."""

    adaptive_gap_min_claims: int = 4
    """Minimum number of semantic-zone claims before adaptive_gap engages."""

    # ── misc ────────────────────────────────────────────────────────────
    context_chars: int = 80
    semantic_top_k: int = 3

    # ── helpers ─────────────────────────────────────────────────────────
    def overlay(self, **overrides) -> GroundingConfig:
        """Return a copy of self with the given fields overridden.

        Used internally when the API receives explicit keyword arguments
        that should win over the loaded config.
        """
        current = {f.name: getattr(self, f.name) for f in fields(self)}
        for k, v in overrides.items():
            if v is not None:
                current[k] = v
        return GroundingConfig(**current)


def load_config(path: Path | str | None = None) -> GroundingConfig:
    """Resolve the effective GroundingConfig.

    Order of precedence (first found wins):
        1. Explicit ``path`` argument.
        2. ``./.stellars-plugins/config.yaml`` (project-local override).
        3. Bundled default ``<module>/config.yaml``.

    Unknown keys in the YAML are ignored (forward compatibility).
    Missing keys use dataclass defaults.
    """
    if path is not None:
        effective_path = Path(path)
    elif CONFIG_PROJECT_OVERRIDE.is_file():
        effective_path = CONFIG_PROJECT_OVERRIDE
    else:
        effective_path = CONFIG_MODULE_DEFAULT

    if not effective_path.is_file():
        return GroundingConfig()

    raw = yaml.safe_load(effective_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return GroundingConfig()

    valid_field_names = {f.name for f in fields(GroundingConfig)}
    filtered = {k: v for k, v in raw.items() if k in valid_field_names}
    return GroundingConfig(**filtered)


__all__ = [
    "GroundingConfig",
    "load_config",
    "CONFIG_MODULE_DEFAULT",
    "CONFIG_PROJECT_OVERRIDE",
]
