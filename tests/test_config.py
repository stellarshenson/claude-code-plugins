"""Tests for :mod:`stellars_claude_code_plugins.config`.

Covers the 4-layer resolution order (explicit path > project > user >
bundled), every failure mode that must raise :class:`ConfigError`, the
backward-compat alias, and the overlay helper on ``GroundingConfig``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from stellars_claude_code_plugins import config as config_mod
from stellars_claude_code_plugins.config import (
    PACKAGE_ROOT,
    ConfigError,
    GroundingConfig,
    load_config,
    load_document_processing_config,
)

BUNDLED_YAML = PACKAGE_ROOT / "config_document_processing.yaml"


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")


def _full_config_dict(**overrides) -> dict:
    """Start from the shipped bundled yaml, apply overrides."""
    base = yaml.safe_load(BUNDLED_YAML.read_text(encoding="utf-8"))
    base.update(overrides)
    return base


# --- happy paths ----------------------------------------------------------


def test_load_document_processing_config_default(tmp_path, monkeypatch):
    """With no explicit override and no .stellars-plugins dirs, load bundled."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    cfg = load_document_processing_config()
    assert isinstance(cfg, GroundingConfig)
    assert cfg.classifier_mode in ("absolute", "adaptive_gap")
    assert 0.0 <= cfg.agreement_threshold <= 1.0
    # spot-check a few types
    assert isinstance(cfg.chunk_max_chars, int)
    assert isinstance(cfg.fuzzy_threshold, float)
    assert isinstance(cfg.voter_semantic_mode, str)


def test_load_document_processing_config_explicit_path(tmp_path):
    """Explicit path argument bypasses the resolution order entirely."""
    yaml_path = tmp_path / "my_override.yaml"
    _write_yaml(yaml_path, _full_config_dict(agreement_threshold=0.99))
    cfg = load_document_processing_config(path=yaml_path)
    assert cfg.agreement_threshold == 0.99


def test_load_config_alias_matches_canonical(tmp_path, monkeypatch):
    """``load_config`` is kept as an alias for backward compatibility."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    canonical = load_document_processing_config()
    aliased = load_config()
    # Same dataclass values because both read the same bundled yaml
    assert canonical == aliased


# --- precedence -----------------------------------------------------------


def test_project_override_wins_over_user_and_bundled(tmp_path, monkeypatch):
    """Project-local .stellars-plugins/config_<plugin>.yaml beats user + bundled."""
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))

    # User-level file: sets agreement_threshold to 0.11
    _write_yaml(
        home / ".stellars-plugins" / "config_document_processing.yaml",
        _full_config_dict(agreement_threshold=0.11),
    )
    # Project-local file: sets agreement_threshold to 0.77 - should win
    _write_yaml(
        tmp_path / ".stellars-plugins" / "config_document_processing.yaml",
        _full_config_dict(agreement_threshold=0.77),
    )

    cfg = load_document_processing_config()
    assert cfg.agreement_threshold == 0.77


def test_user_override_wins_over_bundled(tmp_path, monkeypatch):
    """User-level config beats bundled when no project override is present."""
    monkeypatch.chdir(tmp_path)  # no project-local
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _write_yaml(
        home / ".stellars-plugins" / "config_document_processing.yaml",
        _full_config_dict(agreement_threshold=0.22),
    )
    cfg = load_document_processing_config()
    assert cfg.agreement_threshold == 0.22


# --- failure modes --------------------------------------------------------


def test_missing_required_field_raises_config_error(tmp_path):
    """A yaml missing any required schema field must fail loud, not silently."""
    raw = _full_config_dict()
    del raw["agreement_threshold"]
    yaml_path = tmp_path / "incomplete.yaml"
    _write_yaml(yaml_path, raw)

    with pytest.raises(ConfigError) as excinfo:
        load_document_processing_config(path=yaml_path)
    assert "agreement_threshold" in str(excinfo.value)
    assert "missing required fields" in str(excinfo.value)


def test_invalid_yaml_syntax_raises_config_error(tmp_path):
    """Garbled yaml raises ConfigError wrapping the parser exception."""
    yaml_path = tmp_path / "broken.yaml"
    yaml_path.write_text("key: value:\n  - bad: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError) as excinfo:
        load_document_processing_config(path=yaml_path)
    assert "failed to parse" in str(excinfo.value)


def test_non_dict_top_level_raises_config_error(tmp_path):
    """Top-level must be a mapping; bare list or scalar is rejected."""
    yaml_path = tmp_path / "list.yaml"
    yaml_path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError) as excinfo:
        load_document_processing_config(path=yaml_path)
    assert "yaml mapping" in str(excinfo.value)


def test_missing_bundled_yaml_raises_config_error(tmp_path, monkeypatch):
    """If no overrides AND no bundled yaml, raise loudly, don't silently default."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    # Redirect PACKAGE_ROOT to an empty dir so the bundled lookup misses
    empty_pkg = tmp_path / "empty_pkg"
    empty_pkg.mkdir()
    monkeypatch.setattr(config_mod, "PACKAGE_ROOT", empty_pkg)

    with pytest.raises(ConfigError) as excinfo:
        load_document_processing_config()
    assert "config yaml not found" in str(excinfo.value)


# --- overlay --------------------------------------------------------------


def test_overlay_applies_non_none_values_only(tmp_path, monkeypatch):
    """overlay() preserves original fields when override is None."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    cfg = load_document_processing_config()
    original_classifier = cfg.classifier_mode

    overridden = cfg.overlay(agreement_threshold=0.42, classifier_mode=None)
    assert overridden.agreement_threshold == 0.42
    # None overrides are ignored — original classifier_mode preserved
    assert overridden.classifier_mode == original_classifier
    # Non-overridden fields are copied verbatim
    assert overridden.chunk_max_chars == cfg.chunk_max_chars


def test_overlay_returns_new_instance(tmp_path, monkeypatch):
    """overlay() does not mutate the source config."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    cfg = load_document_processing_config()
    original_agr = cfg.agreement_threshold
    _ = cfg.overlay(agreement_threshold=0.42)
    assert cfg.agreement_threshold == original_agr
