"""Common configuration access interface for every plugin.

One shared module exposing per-plugin schemas (dataclasses) and a
generic yaml loader. **Yaml is the single source of truth** for every
tunable value; the dataclasses here are typed schemas (no defaults)
that describe the expected shape.

File layout (same ``config_<plugin>.yaml`` filename in every location):

- Bundled default (ships with the package):
  ``stellars_claude_code_plugins/config_<plugin>.yaml``.
- Project-local override:
  ``./.stellars-plugins/config_<plugin>.yaml``.
- User-level override:
  ``~/.stellars-plugins/config_<plugin>.yaml``.

Resolution order for every plugin, first match wins:

1. Explicit ``path`` argument passed to the plugin's load function.
2. ``./.stellars-plugins/config_<plugin>.yaml`` project-local override.
3. ``~/.stellars-plugins/config_<plugin>.yaml`` user-level override.
4. Bundled default at ``<package>/config_<plugin>.yaml``.

Layer 2 beats layer 3 intentionally: a committed project-local override
is an explicit project choice; user-level tuning only applies when no
project override exists.

Any missing required field raises :class:`ConfigError` - no hardcoded
fallbacks. Unknown yaml keys are ignored (forward compatibility). Invalid
yaml syntax raises :class:`ConfigError` wrapping the parser exception.

Add a new plugin by:

1. Declare a ``@dataclass`` with type-annotated (no-default) fields here.
2. Ship the bundled default at
   ``stellars_claude_code_plugins/config_<plugin>.yaml``.
3. Add a ``load_<plugin>_config(path=None) -> <schema>`` wrapper that
   calls :func:`_load_typed_config`.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Literal, Type, TypeVar

import yaml

PACKAGE_ROOT = Path(__file__).parent
PROJECT_OVERRIDE_DIR = Path(".stellars-plugins")
USER_OVERRIDE_DIR_NAME = ".stellars-plugins"


def _user_override_dir() -> Path:
    """Resolve the user-level override directory at call time.

    Using ``Path.home()`` at call time (rather than at import) lets tests
    monkeypatch ``HOME`` or ``Path.home`` to redirect user config to a
    temp directory.
    """
    return Path.home() / USER_OVERRIDE_DIR_NAME


class ConfigError(RuntimeError):
    """Raised when a subsystem configuration cannot be resolved.

    Common causes: missing yaml, missing required field in yaml, invalid
    yaml syntax, yaml that isn't a top-level mapping. Deliberately loud
    because running with partial or hallucinated defaults would produce
    wrong results silently.
    """


# --- document-processing schema -------------------------------------------


@dataclass
class GroundingConfig:
    """Tunable parameters for the document-processing grounding pipeline.

    Every field is type-annotated with no default - values are sourced
    from ``config_document_processing.yaml``. Add a new field here and a
    matching entry in the yaml together; never one without the other.
    """

    # ── match_type thresholds ────────────────────────────────────────────
    fuzzy_threshold: float
    """Levenshtein partial-ratio in [0, 1] above which match_type=fuzzy."""

    bm25_threshold: float
    """BM25 token-recall in [0, 1] above which match_type=bm25."""

    semantic_threshold: float
    """Absolute cosine above which match_type=semantic (pre-percentile)."""

    semantic_threshold_percentile: float
    """Top fraction of random chunk-pair distribution for semantic match."""

    agreement_threshold: float
    """Minimum agreement_score for the agreement-fallback classifier."""

    # ── percentile safety floor ──────────────────────────────────────────
    percentile_floor: float
    """Min value SemanticGrounder.percentile_threshold can return."""

    # ── agreement_score per-layer weights (raw sum, should total 1.0) ───
    agreement_weight_exact: float
    agreement_weight_fuzzy: float
    agreement_weight_bm25: float
    agreement_weight_semantic: float

    # ── agreement_score per-layer ramps (low..high -> v_layer in [0,1]) ─
    fuzzy_ramp_low: float
    fuzzy_ramp_high: float
    bm25_ramp_low: float
    bm25_ramp_high: float
    semantic_abs_ramp_low: float
    semantic_abs_ramp_high: float
    semantic_ratio_ramp_low: float
    semantic_ratio_ramp_high: float

    # ── voter thresholds ────────────────────────────────────────────────
    voter_exact: float
    voter_fuzzy: float
    voter_bm25: float
    voter_semantic_abs: float
    voter_semantic_ratio: float
    voter_semantic_mode: Literal["or", "and", "abs_only", "ratio_only"]
    """How the semantic voter combines absolute score and ratio."""

    voter_bonus_2: float
    voter_bonus_3_plus: float

    # ── entity-presence penalty ─────────────────────────────────────────
    entity_penalty_factor: float
    """Max fraction of agreement_score removed when 100% of claim entities absent from source."""

    # ── semantic / chunking ─────────────────────────────────────────────
    chunk_max_chars: int
    chunk_overlap_ratio: float
    percentile_sample_n: int

    # ── sentence-split fallback ─────────────────────────────────────────
    min_passage_chars: int
    single_passage_fallback_length: int

    # ── classifier mode (H11) ───────────────────────────────────────────
    classifier_mode: Literal["absolute", "adaptive_gap"]
    """``absolute`` = use agreement_threshold. ``adaptive_gap`` = batch-mode rank-based."""

    adaptive_gap_min_claims: int

    # ── misc ────────────────────────────────────────────────────────────
    context_chars: int
    semantic_top_k: int

    def overlay(self, **overrides) -> GroundingConfig:
        """Return a copy with the given fields overridden.

        Used by ``ground`` / ``ground_many`` to let explicit keyword
        arguments win over the loaded config. ``None`` values are
        ignored ("no override for this field"), so callers can pass
        their full signature through without special-casing.
        """
        current = {f.name: getattr(self, f.name) for f in fields(self)}
        for k, v in overrides.items():
            if v is not None:
                current[k] = v
        return GroundingConfig(**current)


# --- generic loader --------------------------------------------------------


T = TypeVar("T")


def _resolve_config_path(plugin_name: str, explicit_path: Path | str | None) -> Path:
    """Walk the 4-layer precedence order and return the first file that exists.

    Falls back to the bundled default path even if the file does not
    exist there - the caller's ``is_file()`` check will produce the
    loud ``ConfigError``.

    Same ``config_<plugin>.yaml`` filename in all three locations;
    only the directory changes.
    """
    if explicit_path is not None:
        return Path(explicit_path)
    filename = f"config_{plugin_name}.yaml"
    project = PROJECT_OVERRIDE_DIR / filename
    if project.is_file():
        return project
    user = _user_override_dir() / filename
    if user.is_file():
        return user
    return PACKAGE_ROOT / filename


def _load_typed_config(
    schema: Type[T],
    plugin_name: str,
    path: Path | str | None = None,
) -> T:
    """Load ``<plugin_name>`` config from disk and instantiate ``schema``.

    See module docstring for resolution order. Raises :class:`ConfigError`
    on any problem (missing file, bad yaml, missing required fields).
    """
    effective_path = _resolve_config_path(plugin_name, path)

    if not effective_path.is_file():
        raise ConfigError(
            f"config yaml not found at {effective_path}; ship "
            f"config_{plugin_name}.yaml with the package or create "
            f".stellars-plugins/config_{plugin_name}.yaml to override"
        )

    try:
        raw = yaml.safe_load(effective_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"failed to parse {effective_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"{effective_path} must contain a yaml mapping at top level")

    required = {f.name for f in fields(schema)}
    missing = required - set(raw.keys())
    if missing:
        raise ConfigError(
            f"{effective_path} is missing required fields: {sorted(missing)}. "
            "Every schema field must be declared in the yaml - there are no "
            "hardcoded defaults."
        )

    filtered = {k: raw[k] for k in required}
    return schema(**filtered)


# --- per-subsystem load helpers -------------------------------------------


def load_document_processing_config(
    path: Path | str | None = None,
) -> GroundingConfig:
    """Load the document-processing grounding config from yaml.

    Looks for ``config_document_processing.yaml`` in order:

    - ``./.stellars-plugins/config_document_processing.yaml`` (project)
    - ``~/.stellars-plugins/config_document_processing.yaml`` (user)
    - ``stellars_claude_code_plugins/config_document_processing.yaml`` (bundled)
    """
    return _load_typed_config(GroundingConfig, "document_processing", path=path)


# --- backward-compatible aliases ------------------------------------------
#
# ``load_config`` was the Iter 5 name when config lived inside
# ``document_processing/``. Keep it as an alias so existing callers (and
# the archived scripts under ``references/grounding-optimisation/``)
# continue to work.

load_config = load_document_processing_config


__all__ = [
    "GroundingConfig",
    "ConfigError",
    "load_document_processing_config",
    "load_config",
    "PACKAGE_ROOT",
    "PROJECT_OVERRIDE_DIR",
]
