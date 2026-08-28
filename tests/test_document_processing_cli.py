"""Offline smoke tests for the rewired document-processing CLI.

The CLI now drives the standalone :mod:`groundrails` engine. These tests pin
``--effort low`` and initialise groundrails with ``models="none"`` so the whole
suite runs offline (bundled calibration, no model downloads, no network) - the
guaranteed core-only path. Semantic grounding (the OpenVINO cascade) is opt-in
and not exercised here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

# groundrails installs under a `python_version == '3.12'` marker (it pins ~=3.12.0),
# so off 3.12 the engine - and with it this whole CLI - is absent by design. Gate on
# the interpreter, NOT on `importorskip("groundrails")`: the import-based form cannot
# tell by-design absence from a broken 3.12 install, so a groundrails that failed to
# resolve would skip all six tests and leave the 3.12 leg green with the subsystem
# untested. Here an import failure on 3.12 stays a hard error.
if sys.version_info[:2] != (3, 12):
    pytest.skip("grounding engine is Python 3.12 only", allow_module_level=True)

from stellars_claude_code_plugins.document_processing import cli


@pytest.fixture(scope="module", autouse=True)
def _groundrails_ready(tmp_path_factory):
    """Initialise groundrails once into an isolated, offline home for the module."""
    import groundrails

    home = tmp_path_factory.mktemp("groundrails_home")
    prev = os.environ.get("GROUNDRAILS_HOME")
    os.environ["GROUNDRAILS_HOME"] = str(home)
    groundrails.init(models="none")  # bundled calibration, no downloads
    yield
    if prev is None:
        os.environ.pop("GROUNDRAILS_HOME", None)
    else:
        os.environ["GROUNDRAILS_HOME"] = prev


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_ground_single_exact(tmp_path, capsys):
    src = _write(tmp_path / "src.txt", "The sky is blue today.")
    rc = cli.main(
        ["ground", "--claim", "The sky is blue", "--source", str(src), "--effort", "low"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "EXACT" in out


def test_ground_single_unconfirmed(tmp_path):
    src = _write(tmp_path / "src.txt", "The sky is blue today.")
    rc = cli.main(
        ["ground", "--claim", "Pigs can fly to Mars", "--source", str(src), "--effort", "low"]
    )
    assert rc == 1  # nothing grounds -> exit 1


def test_ground_single_contradicted_exits_one(tmp_path):
    src = _write(tmp_path / "src.txt", "Revenue was 6 million euros in 2024.")
    rc = cli.main(
        [
            "ground",
            "--claim",
            "Revenue was 5 million euros in 2024",
            "--source",
            str(src),
            "--effort",
            "low",
        ]
    )
    assert rc == 1  # a contradicted number is not a grounded claim


def test_ground_manifest_json_report(tmp_path):
    src = _write(tmp_path / "src.txt", "Revenue grew to 45 percent in Q3.")
    claims = _write(
        tmp_path / "claims.json",
        json.dumps(["Revenue grew to 45 percent", "Pigs can fly to Mars"]),
    )
    out_file = tmp_path / "report.json"
    rc = cli.main(
        [
            "ground",
            "--manifest",
            str(claims),
            "--source",
            str(src),
            "--effort",
            "low",
            "--json",
            "--output",
            str(out_file),
        ]
    )
    assert rc in (0, 1)
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == 2


def test_extract_claims(tmp_path, capsys):
    doc = _write(
        tmp_path / "doc.md",
        "# Brief\n\n"
        "The quarterly revenue increased to 45 percent in the third fiscal quarter. "
        "The engineering team expanded to twelve full-time members this year.\n",
    )
    rc = cli.main(["extract-claims", "--document", str(doc)])
    assert rc == 0
    # Verify the CLI -> groundrails.extract wiring + JSON shape; the exact claim
    # count is groundrails' heuristic, not this CLI's contract.
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list)
    assert all("claim" in c for c in payload)


def test_check_consistency(tmp_path):
    doc = _write(
        tmp_path / "doc.md", "Pipeline is dev/test/staging. Later it is dev/staging/prod.\n"
    )
    rc = cli.main(["check-consistency", "--document", str(doc)])
    assert rc in (0, 1)  # 0 = no findings, 1 = divergence found


def test_validate_batch_writes_reports(tmp_path):
    src = _write(tmp_path / "src.txt", "The sky is blue today.")
    doc = _write(tmp_path / "doc.md", "# Brief\n\nThe sky is blue.\n")
    out_dir = tmp_path / "out"
    rc = cli.main(
        [
            "validate",
            "--document",
            str(doc),
            "--source",
            str(src),
            "--effort",
            "low",
            "--output-dir",
            str(out_dir),
        ]
    )
    assert rc in (0, 1)
    assert (out_dir / "doc" / "grounding-report.md").is_file()
    assert (out_dir / "doc" / "consistency-report.md").is_file()
    assert (out_dir / "doc" / "claims.json").is_file()
