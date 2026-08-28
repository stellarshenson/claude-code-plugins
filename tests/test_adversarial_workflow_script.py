"""Guardrails for the canonical adversarial-review workflow script.

The script IS the loop protocol - plugins/devils-advocate ships it so the
control flow (forced adjudication, computed verdict, pinned confirms, fanout
and round caps) is versioned code instead of orchestrator context. These tests
pin the gates so an edit cannot silently drop one.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parent.parent
    / "plugins/devils-advocate/skills/adversarial-review/workflows/adversarial-loop.js"
)


def text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_script_exists_with_pure_literal_meta():
    t = text()
    assert t.startswith("export const meta = {")
    meta = t[: t.index("\n}") + 2]
    for banned in ("${", "Date.", "Math.random", "...'"):
        assert banned not in meta


def test_no_runtime_banned_calls():
    t = text()
    assert "Date.now(" not in t and "Math.random(" not in t and "new Date(" not in t
    assert not re.search(r":\s*string\b|:\s*number\b|interface ", t)  # plain JS, not TS


def test_mandatory_args_throw():
    assert re.search(r"args\.target.*args\.bar.*args\.lenses.*mandatory", text(), re.S)


def test_verdict_is_computed_from_severities():
    t = text()
    assert re.search(r"blockingOf.*CRITICAL.*MAJOR", t, re.S)
    assert "computed" in t.lower() and "prose" in t.lower()


def test_gates_present():
    t = text()
    assert "'STOP'" in t and "FANOUT_STOP" in t and "ROUND_CAP" in t and "FIX_FAILED" in t
    assert "highFanoutStreak >= 2" in t and "> 0.5" in t  # two consecutive rounds over half
    assert "cleanStreak >= CLEAN_REQUIRED" in t
    assert "devils-advocate:adjudicator" in t and "devils-advocate:adversarial-reviewer" in t


def test_confirm_round_is_pinned():
    t = text()
    assert "CONFIRMING round, pinned" in t and "CLOSURES:" in t and "FIX DELTA:" in t
    assert "do not review code the fixes did not touch" in t


def test_phase_labels_match_meta():
    t = text()
    titles = re.findall(r"title: '([^']+)'", t[: t.index("\n}") + 2])
    assert titles == ["Discover", "Adjudicate", "Fix", "Confirm"]
    for title in titles:
        assert f"'{title}'" in t[t.index("\n}") + 2 :]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_script_parses_as_workflow_body():
    """The runtime runs the body inside an async function (top-level return and
    await are legal); AsyncFunction reproduces that parse exactly."""
    body = text().replace("export const meta", "const meta", 1)
    check = (
        "const fs = require('fs');"
        "const body = fs.readFileSync(0, 'utf8');"
        "const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;"
        "new AsyncFunction('args','budget','agent','parallel','pipeline','phase','log','workflow', body);"
        "console.log('PARSE-OK');"
    )
    r = subprocess.run(
        ["node", "-e", check], input=body, capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0 and "PARSE-OK" in r.stdout, r.stderr
