"""Guard the toolchain preflight gate that every plugin ships.

## Why this file exists

A `kolomolo/sales/proposals` session ran `svg-infographics validate --svg …`
against a library 26 releases behind the plugin and got
`error: unrecognized arguments: --svg` on all seven deliverables - validation
silently never ran. The preflight gate was present and reported success:

    python3 -c "import stellars_claude_code_plugins" || pip install --upgrade …
    → "pre-flight done"        # `||` short-circuits, pip NEVER ran
    svg-infographics --help && echo "CLI OK"
    → "CLI OK"                 # --help exits 0 on ancient CLIs

Two green lights, zero version assertions. The correct unconditional-upgrade
form already existed - in exactly ONE file, against 23 broken sites in 20
files. The majority idiom won.

These tests make that drift impossible to reintroduce:

- static guards: no short-circuit idiom anywhere, every upgrade paired with a
  version assertion, no false-premise compatibility prose, version single-sourced
- behavioural: the SHIPPED gate lines are executed against fixture versions
- realism: real recorded `claude -p` responses prove the gate text actually
  makes an agent treat a `STALE:` line as a hazard (and, crucially, that it
  does NOT cry wolf when versions match)

Cassettes replay in CI; re-record with `uv run python tests/record_claude_cassettes.py`.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from _cassette_prompts import (
    GATE_RULES,
    build_gate_matched_prompt,
    build_gate_stale_prompt,
)

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = (
    "autobuild",
    "datascience",
    "devils-advocate",
    "document-processing",
    "journal",
    "svg-infographics",
)

# The exact defect: `||` makes the install conditional on the import FAILING,
# so any importable version - however old - skips the upgrade entirely.
SHORT_CIRCUIT = 'import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install'
UPGRADE_LINE = "pip install --user --upgrade stellars-claude-code-plugins"
STALE_ASSERTION = "STALE: library $LIB != plugin $PLUG"

# Retired claim: plugin and library versions are synced at RELEASE time, which
# says nothing about what is INSTALLED on the machine running the skill.
FALSE_PREMISE_FRAGMENTS = (
    "same version, so any installed library",
    "ship same version",
    "share a version",
)


def _plugin_markdown() -> list[Path]:
    return sorted(p for name in PLUGINS for p in (ROOT / name).rglob("*.md"))


# --- Static guards --------------------------------------------------------


def test_no_short_circuit_preflight_anywhere():
    """The `import || install` idiom must not exist in any shipped plugin doc."""
    offenders = [
        str(p.relative_to(ROOT))
        for p in _plugin_markdown()
        if SHORT_CIRCUIT in p.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        "short-circuiting preflight reintroduced - `||` skips the upgrade for "
        f"any importable version, however stale: {offenders}"
    )


def test_every_upgrade_is_paired_with_a_version_assertion():
    """An upgrade that is never verified is how a stale CLI survives.

    `--help` exiting 0 proves nothing; only comparing the installed library
    against the plugin's own version does.
    """
    unguarded = [
        str(p.relative_to(ROOT))
        for p in _plugin_markdown()
        if UPGRADE_LINE in (t := p.read_text(encoding="utf-8")) and STALE_ASSERTION not in t
    ]
    assert not unguarded, (
        f"files upgrade the toolkit but never assert the version landed: {unguarded}"
    )


def test_gate_compares_against_the_plugins_own_manifest():
    """The comparison must read the plugin's real manifest, not a hardcoded
    number that would rot on the next release."""
    gated = [p for p in _plugin_markdown() if STALE_ASSERTION in p.read_text(encoding="utf-8")]
    assert gated, "no plugin doc carries the version gate at all"
    for p in gated:
        assert "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" in p.read_text(
            encoding="utf-8"
        ), f"{p.relative_to(ROOT)} asserts a version without reading the plugin manifest"


def test_no_false_premise_compatibility_prose():
    """Docs must not tell an agent a failed upgrade is harmless."""
    offenders = [
        f"{p.relative_to(ROOT)}: {frag!r}"
        for p in _plugin_markdown()
        for frag in FALSE_PREMISE_FRAGMENTS
        if frag in p.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        "false-premise prose reintroduced - release-time version sync says "
        f"nothing about the INSTALLED library: {offenders}"
    )


def test_version_is_single_sourced():
    """`__version__` sat at 0.8.43 while the project shipped 1.6.31. Any
    hardcoded literal drifts; metadata cannot."""
    init = (ROOT / "src" / "stellars_claude_code_plugins" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "importlib.metadata" in init, "__version__ must derive from package metadata"

    import stellars_claude_code_plugins as pkg

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = next(
        line.split('"')[1] for line in pyproject.splitlines() if line.startswith("version")
    )
    assert pkg.__version__ == declared, (
        f"__version__ {pkg.__version__} != pyproject {declared} - the editable "
        "install is stale; run `make install`"
    )


def test_frozen_gate_prompt_matches_shipped_text():
    """The cassette prompt quotes the gate. Cassettes are content-addressed, so
    the quote is a frozen copy - this guards it against silent divergence."""
    shipped = (ROOT / "svg-infographics" / "skills" / "svg-designer" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    for line in (UPGRADE_LINE, STALE_ASSERTION):
        assert line in shipped, f"shipped gate lost {line!r}"
        assert line in GATE_RULES, f"frozen cassette prompt lost {line!r}"


# --- Behavioural: execute the SHIPPED gate lines ---------------------------


def _shipped_comparison_lines() -> str:
    """Extract the PLUG-assignment and comparison from a shipped gate block.

    Running the doc's own text (rather than a retyped copy) is the point: a
    typo introduced into the markdown fails these tests.
    """
    body = (ROOT / "svg-infographics" / "commands" / "validate.md").read_text(encoding="utf-8")
    lines = [
        ln.strip()
        for ln in body.splitlines()
        if ln.strip().startswith(("PLUG=", '[ -n "$PLUG" ]'))
    ]
    assert len(lines) >= 2, "could not extract the shipped comparison lines"
    return "\n".join(lines[:2])


def _run_gate(tmp_path: Path, lib_version: str, plugin_version: str | None) -> str:
    """Run the shipped comparison with a fixture library/plugin version pair.

    The `pip install` line is omitted deliberately - the test asserts the
    verification logic, and must not mutate the machine or need a network.
    """
    env = {"PATH": "/usr/bin:/bin"}
    if plugin_version is not None:
        manifest = tmp_path / ".claude-plugin"
        manifest.mkdir(parents=True, exist_ok=True)
        (manifest / "plugin.json").write_text(
            f'{{\n  "name": "svg-infographics",\n  "version": "{plugin_version}"\n}}\n'
        )
        env["CLAUDE_PLUGIN_ROOT"] = str(tmp_path)

    script = f'LIB="{lib_version}"\n' + _shipped_comparison_lines()
    return subprocess.run(  # noqa: S603 - fixed argv, no shell injection surface
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    ).stdout.strip()


def test_gate_flags_mismatch_as_stale(tmp_path):
    """The exact proposals-session condition: plugin ahead of the library."""
    out = _run_gate(tmp_path, lib_version="1.5.5", plugin_version="1.6.31")
    assert out.startswith("STALE:"), out
    assert "1.5.5" in out and "1.6.31" in out, "both versions must be named"


def test_gate_passes_on_parity(tmp_path):
    out = _run_gate(tmp_path, lib_version="1.6.31", plugin_version="1.6.31")
    assert out == "toolkit 1.6.31", out


def test_gate_does_not_cry_wolf_without_a_plugin_root(tmp_path):
    """Outside a plugin install (dev checkout, bare shell) there is nothing to
    compare against - the gate must stay quiet, not emit a bogus STALE."""
    out = _run_gate(tmp_path, lib_version="1.6.31", plugin_version=None)
    assert out == "toolkit 1.6.31", out
    assert "STALE" not in out


# --- Realism: real recorded `claude -p` responses --------------------------


def _spawn_claude(prompt: str) -> str:
    """Spawn site the cassette intercepts. Mirrors the recorder's flags."""
    return subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "text",
            "--dangerously-skip-permissions",
            "--max-turns",
            "3",
            "--no-session-persistence",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    ).stdout


def _verdict(response: str) -> str:
    """First PROCEED/BLOCKED token in the response, uppercased.

    Tolerates leading noise - a `claude -p` run inherits the user's global
    CLAUDE.md, which may prepend a timestamp or markdown emphasis.
    """
    for token in response.replace("*", "").split():
        cleaned = token.strip(":.,`").upper()
        if cleaned in {"PROCEED", "BLOCKED"}:
            return cleaned
    pytest.fail(f"no PROCEED/BLOCKED verdict in response: {response[:300]!r}")


class TestGateComprehensionRealism:
    """Does the gate's wording actually change an agent's behaviour?

    The static tests prove the text is present; only a real model response
    proves it is *understood*. The old wording produced `CLI OK` and the agent
    sailed on into `unrecognized arguments`.
    """

    def test_stale_output_blocks_the_run(self, claude_p_cassette, monkeypatch):
        monkeypatch.setattr(subprocess, "run", claude_p_cassette)
        assert _verdict(_spawn_claude(build_gate_stale_prompt())) == "BLOCKED"

    def test_matched_output_allows_the_run(self, claude_p_cassette, monkeypatch):
        """Discriminator - without this, an always-BLOCKED model would pass the
        test above while telling us nothing about the gate."""
        monkeypatch.setattr(subprocess, "run", claude_p_cassette)
        assert _verdict(_spawn_claude(build_gate_matched_prompt())) == "PROCEED"
