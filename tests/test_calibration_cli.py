"""CLI tests for `document-processing calibrate` and `config` (no network).

Semantic stays off so no retrieval model downloads; PyMC draws are tiny.
"""

from __future__ import annotations

import json
import warnings

import pytest
import yaml

from stellars_claude_code_plugins.document_processing import cli

warnings.filterwarnings("ignore")

DRAWS = ["--draws", "100", "--tune", "100"]

EVIDENCE = [
    {
        "claim": "the estate has three walled gardens",
        "source_text": "The estate has three walled gardens and an orchard.",
        "label": 1,
        "lang": "en",
    },
    {
        "claim": "the estate employs twelve gardeners",
        "source_text": "The estate has three walled gardens and an orchard.",
        "label": 0,
        "lang": "en",
    },
    {
        "claim": "annual rainfall averages 800 mm",
        "source_text": "Rainfall in the region averages 800 mm per year.",
        "label": 1,
        "lang": "en",
    },
    {
        "claim": "a fleet of tractors patrols the vineyard",
        "source_text": "Rainfall in the region averages 800 mm per year.",
        "label": 0,
        "lang": "en",
    },
]


def _write_evidence(tmp_path):
    p = tmp_path / "evidence.json"
    p.write_text(json.dumps(EVIDENCE), encoding="utf-8")
    return p


class TestCalibrateCLI:
    def test_init_writes_profile(self, tmp_path):
        prof = tmp_path / "cal.json"
        rc = cli.main(["calibrate", "--action", "init", "--profile", str(prof), *DRAWS])
        assert rc == 0 and prof.is_file()

    def test_update_show_eval(self, tmp_path, capsys):
        ev = _write_evidence(tmp_path)
        prof = tmp_path / "cal.json"
        assert (
            cli.main(
                [
                    "calibrate",
                    "--action",
                    "update",
                    "--evidence",
                    str(ev),
                    "--profile",
                    str(prof),
                    *DRAWS,
                ]
            )
            == 0
        )
        assert prof.is_file()

        assert cli.main(["calibrate", "--action", "show", "--profile", str(prof)]) == 0
        assert "Intercept" in capsys.readouterr().out

        assert (
            cli.main(
                ["calibrate", "--action", "eval", "--evidence", str(ev), "--profile", str(prof)]
            )
            == 0
        )

    def test_update_requires_evidence(self):
        with pytest.raises(SystemExit):
            cli.main(["calibrate", "--action", "update", "--profile", "/tmp/none.json", *DRAWS])


class TestConfigCLI:
    def test_set_calibrator_writes_block_and_show(self, tmp_path, monkeypatch, capsys):
        prof = tmp_path / "cal.json"
        assert cli.main(["calibrate", "--action", "init", "--profile", str(prof), *DRAWS]) == 0

        monkeypatch.chdir(tmp_path)
        assert cli.main(["config", "set-calibrator", "--profile", str(prof)]) == 0
        cfg = tmp_path / ".stellars-plugins" / "config_document_processing.yaml"
        block = yaml.safe_load(cfg.read_text())["calibration"]
        assert block["engine"] == "calibrated"
        assert set(block["weights"])  # non-empty learned weights

        assert cli.main(["config", "show"]) == 0
        assert "calibration" in capsys.readouterr().out


class TestTrainLexicalCLI:
    """Smoke test for `document-processing train-lexical` (argument parser + the
    feature-extract -> sklearn fit -> config-write path) on the cheap LOW tier
    with a synthetic dataset that just clears the enforced training floor."""

    @staticmethod
    def _synthetic_jsonl(path):
        """200 rows (100 supported / 100 hallucination) - the exact training floor."""
        rows = []
        for i in range(100):
            src = (
                f"The manor number {i} was built in {1800 + i} and restored in "
                f"{1900 + i}. The estate has {i % 7 + 2} walled gardens and an "
                f"orchard of {i % 11 + 3} apple trees."
            )
            rows.append(
                {
                    "claim": f"the manor number {i} was built in {1800 + i}",
                    "source_text": src,
                    "label": 1,
                    "lang": "en",
                }
            )
            rows.append(
                {
                    "claim": f"submarine fleet {i} patrols trench {i * 3} at dawn",
                    "source_text": src,
                    "label": 0,
                    "lang": "en",
                }
            )
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return path

    def test_train_lexical_smoke(self, tmp_path, monkeypatch):
        from stellars_claude_code_plugins.document_processing import lexical as L

        data = self._synthetic_jsonl(tmp_path / "train.jsonl")
        monkeypatch.chdir(tmp_path)
        assert cli.main(["train-lexical", "--effort", "low", "--data", str(data)]) == 0

        cfg = tmp_path / ".stellars-plugins" / "config_document_processing.yaml"
        assert cfg.is_file()
        full = yaml.safe_load(cfg.read_text())
        block = full["calibration"]
        assert block["mode"] == "lexical"
        m = block["lexical_manifolds"]["low"]
        # the written manifold matches the low-tier feature contract
        assert m["feature_order"] == L.TIER_FEATURES["low"]
        assert "Intercept" in m["weights"]
        assert set(m["weights"]) == {"Intercept", *L.TIER_FEATURES["low"]}
        assert 0.0 < m["threshold"] < 1.0
        assert full["lexical_effort"] == "low"

    def test_train_lexical_rejects_undersized_dataset(self, tmp_path, monkeypatch):
        small = tmp_path / "small.jsonl"
        small.write_text(
            "\n".join(
                json.dumps({"claim": f"c{i}", "source_text": f"s{i}", "label": i % 2})
                for i in range(10)
            ),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            cli.main(["train-lexical", "--effort", "low", "--data", str(small)])
