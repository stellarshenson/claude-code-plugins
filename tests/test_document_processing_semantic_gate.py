"""`--semantic` refuses to start when the cascade is incomplete.

From a real incident: a `--semantic` run whose cascade could not execute failed on
all 74 claims, exited 0, and wrote a report scoring 0/74 that read as a genuine
verdict. groundrails isolates the failure per claim rather than refusing, so the
CLI has to check up front.

These run on the same 3.12-only gate as the rest of the document-processing
suite; see `test_document_processing_cli.py` for why.
"""

from __future__ import annotations

import argparse
import re
import sys

import pytest

if sys.version_info[:2] != (3, 12):
    pytest.skip("grounding engine is Python 3.12 only", allow_module_level=True)

from stellars_claude_code_plugins.document_processing import cli


class TestPreflight:
    def test_missing_modules_are_named(self, monkeypatch):
        """The operator must learn WHICH component is absent. groundrails' hint
        lists the cascade's whole requirement set, most of which is core deps that
        cannot be missing - that ambiguity cost hours in the incident."""
        monkeypatch.setattr(
            cli.importlib.util,
            "find_spec",
            lambda name: None if name in {"openvino", "transformers"} else object(),
        )
        assert cli._missing_semantic_components() == ["openvino", "transformers"]

    def test_missing_models_are_named(self, monkeypatch):
        """Modules present but weights never downloaded - the run would start and
        fail on the first claim."""
        monkeypatch.setattr(cli.importlib.util, "find_spec", lambda name: object())
        import huggingface_hub

        monkeypatch.setattr(huggingface_hub, "try_to_load_from_cache", lambda *a, **k: None)

        missing = cli._missing_semantic_components()
        assert missing and all(m.startswith("model ") for m in missing)

    def test_complete_cascade_passes(self, monkeypatch):
        monkeypatch.setattr(cli.importlib.util, "find_spec", lambda name: object())
        import huggingface_hub

        monkeypatch.setattr(huggingface_hub, "try_to_load_from_cache", lambda *a, **k: "/cached")
        assert cli._missing_semantic_components() == []
        cli._preflight_semantic()  # must not raise

    def test_preflight_exits_2_naming_the_component_and_the_remedy(self, monkeypatch, capsys):
        monkeypatch.setattr(
            cli.importlib.util, "find_spec", lambda name: None if name == "openvino" else object()
        )
        with pytest.raises(SystemExit) as exc:
            cli._preflight_semantic()
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "openvino" in err
        # Must point at an extra that resolves the WHOLE cascade; the narrower
        # groundrails extras are each incomplete.
        assert "stellars-claude-code-plugins[semantic]" in err

    def test_probe_targets_the_layer_semantic_actually_runs(self):
        """`ground_batch(semantic=True)` builds `semantic_ov.SemanticCascade`, not
        the legacy ONNX `SemanticGrounder`. An earlier probe checked the ONNX
        layer's modules and weights, so a fully provisioned OpenVINO cascade read
        as missing and `--semantic` could not run at all - while the remedy it
        printed provisioned artifacts the check never looked at."""
        import inspect

        import groundrails.semantic_ov as ov

        # Pin the probed artifact against the loader that reads it, matching the
        # path-join form: `_load` quotes a dozen strings (CPU, config.json, utf-8,
        # …) and a bare or merely-quoted substring test passes for any of them,
        # which then finds nothing in the cache and re-arms the skip below. Only
        # the model load uses `d / "..."`. Couples to groundrails' formatting, which
        # is the price of checking this at all without a provisioned machine.
        assert (
            f'd / "{cli._SEMANTIC_MODEL_FILE}"' in inspect.getsource(ov.SemanticCascade._load)
        )
        # Equality, not subset: a subset passes when an entry is dropped.
        ov_modules = set(re.findall(r'"([a-z_]+)"', inspect.getsource(ov.is_available)))
        assert set(cli._SEMANTIC_MODULES) == ov_modules, (
            "probed modules must be exactly the ones groundrails checks for THIS cascade"
        )

        if not ov.is_available():
            pytest.skip("cascade modules absent on this machine")
        from huggingface_hub import try_to_load_from_cache

        if not all(
            try_to_load_from_cache(r, cli._SEMANTIC_MODEL_FILE) for r in ov.HF_REPOS.values()
        ):
            pytest.skip("cascade models not provisioned on this machine")
        # Provisioned box: groundrails can run the cascade, so we must not block it.
        assert cli._missing_semantic_components() == []

    def test_ensure_ready_preflights_only_for_semantic(self, monkeypatch):
        """Lexical grounding needs no cascade - gating it would break the default
        path for every user who never asked for semantic."""
        calls = []
        monkeypatch.setattr(cli, "_preflight_semantic", lambda **kw: calls.append(1))
        monkeypatch.setattr(cli.gr_settings, "is_ready", lambda: True)

        cli._ensure_ready(semantic=False)
        assert calls == []
        cli._ensure_ready(semantic=True)
        assert calls == [1]


class TestSetupSemantic:
    """`setup --semantic` on an already-initialised home must still provision the
    cascade. The early return swallowed the flag and printed advice to pass the
    very flag that had been passed - the operator followed it and got nothing."""

    def _args(self, **kw):
        return argparse.Namespace(**{"force": False, "semantic": False, **kw})

    def test_semantic_provisions_even_when_already_initialised(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "_preflight_semantic", lambda **kw: None)
        monkeypatch.setattr(cli.gr_settings, "load_config_file", lambda: None)
        monkeypatch.setattr(cli.gr_settings, "is_ready", lambda: True)
        seen = {}

        def _init(models=None):
            seen["models"] = models
            return {"config_file": "x", "calibration": "y", "models": "provisioned"}

        monkeypatch.setattr(cli.groundrails, "init", _init)

        assert cli.cmd_setup(self._args(semantic=True)) == 0
        # models=None is groundrails' "provision the cascade"; "none" means skip it.
        assert seen["models"] is None
        assert "already initialised" not in capsys.readouterr().err

    def test_setup_does_not_preflight_the_models_it_exists_to_fetch(self, monkeypatch):
        """`setup --semantic` downloads the weights, so checking for them here
        would make the command refuse to do the thing that satisfies the check."""
        monkeypatch.setattr(cli.importlib.util, "find_spec", lambda name: object())
        import huggingface_hub

        monkeypatch.setattr(
            huggingface_hub,
            "try_to_load_from_cache",
            lambda *a, **k: pytest.fail("setup must not probe the model cache"),
        )
        monkeypatch.setattr(cli.gr_settings, "load_config_file", lambda: None)
        monkeypatch.setattr(cli.gr_settings, "is_ready", lambda: False)
        monkeypatch.setattr(
            cli.groundrails,
            "init",
            lambda models=None: {"config_file": "x", "calibration": "y", "models": "ok"},
        )
        assert cli.cmd_setup(self._args(semantic=True)) == 0

    def test_plain_setup_still_short_circuits_when_initialised(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.gr_settings, "load_config_file", lambda: None)
        monkeypatch.setattr(cli.gr_settings, "is_ready", lambda: True)

        def _boom(models=None):
            raise AssertionError("must not re-provision for a plain setup")

        monkeypatch.setattr(cli.groundrails, "init", _boom)

        assert cli.cmd_setup(self._args()) == 0
        assert "already initialised" in capsys.readouterr().err
