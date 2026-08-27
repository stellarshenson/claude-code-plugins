"""Guard the toolchain preflight gate that every plugin ships.

A downstream session ran `svg-infographics validate --svg …` against a library
26 releases behind the plugin docs and got `unrecognized arguments: --svg` on
all seven deliverables - validation silently never ran, while the preflight
printed success. `import X || pip install --upgrade X` short-circuits whenever
any version imports, so pip never ran, and `--help` exits 0 on an ancient CLI,
so the verify step was a second false green. The correct unconditional-upgrade
form already existed - in exactly one file, against 21 sites in 20 others.

Cassettes replay in CI; re-record with `uv run python tests/record_claude_cassettes.py`.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
from _cassette_prompts import (
    GATE_BULLETS,
    GATE_FENCE,
    build_gate_matched_prompt,
    build_gate_stale_prompt,
)

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins"
PLUGINS = (
    "autobuild",
    "datascience",
    "devils-advocate",
    "document-processing",
    "journal",
    "project-management",
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
    return sorted(p for name in PLUGINS for p in (PLUGIN_ROOT / name).rglob("*.md"))


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


def _can_run_shell(body: str) -> bool:
    """Whether an entry point's own frontmatter lets it execute the gate.

    A file restricted to Read/Write/Edit/Glob/Grep cannot invoke any toolkit CLI,
    so there is nothing for a gate to protect - and shipping one there would be an
    instruction the agent has no tool to follow. Anything it delegates CLI work to
    is itself a gated entry point. No `allowed-tools` key at all means unrestricted.
    """
    if not body.startswith("---\n"):
        return True
    end = body.find("\n---\n", 4)
    if end == -1:
        return True
    for line in body[4:end].splitlines():
        stripped = line.strip()
        if stripped.startswith(("allowed-tools:", "tools:")):
            value = stripped.split(":", 1)[1]
            return "Bash" in value or "*" in value
    return True


def test_every_cli_entry_point_is_gated():
    """Every entry point that CAN run a CLI carries the gate - and only those.

    The earlier form guarded only files that named a CLI, so a skill could reach
    the toolkit indirectly, or gain a CLI call later, and never check the version.
    The contract is now biconditional: shell-capable means gated, and gated means
    shell-capable, so neither a silent hole nor an unrunnable instruction ships.

    Entry points are `SKILL.md` and `commands/*.md`. References, rules, READMEs
    and examples stay exempt - they are loaded BY a gated entry point.
    """
    ungated, undeliverable = [], []
    for p in _plugin_markdown():
        if p.name != "SKILL.md" and p.parent.name != "commands":
            continue
        body = p.read_text(encoding="utf-8")
        gated = STALE_ASSERTION in body
        if gated != _can_run_shell(body):
            (ungated if not gated else undeliverable).append(str(p.relative_to(ROOT)))
    assert not ungated, (
        "shell-capable entry points missing the toolchain gate - each can drive a "
        f"toolkit CLI and would do so unchecked: {ungated}"
    )
    assert not undeliverable, (
        "entry points carry a gate their own `allowed-tools` forbids them from "
        f"running, so the instruction is dead text: {undeliverable}"
    )


def test_shipped_gate_still_carries_its_normative_lines():
    """Cheap, deterministic guard on the LIVE gate the cassettes quote.

    The realism pair below needs the `claude` binary to re-record, so it cannot
    be what protects the gate from deletion - in replay it can only report a
    hash miss. This test is the protection: it fails loudly and is fixable
    without any binary. It must read the shipped file, not the frozen snapshot,
    or it proves only that a constant equals itself.
    """
    live = (
        PLUGIN_ROOT / "svg-infographics" / "skills" / "svg-designer" / "SKILL.md"
    ).read_text(encoding="utf-8")
    for required in (UPGRADE_LINE, STALE_ASSERTION):
        assert required in live, f"shipped gate lost its {required!r} line"
    assert "The version compare is the real gate" in live, (
        "the gate lost the rule that a green `--help` proves nothing - the "
        "exact false green that let a 26-release-stale CLI through"
    )
    for name, snapshot in (("GATE_FENCE", GATE_FENCE), ("GATE_BULLETS", GATE_BULLETS)):
        assert snapshot in live, (
            f"the shipped gate no longer matches the frozen {name} snapshot in "
            "tests/_cassette_prompts.py - the recorded cassettes were built from the "
            f"old text. Update {name} and re-record with "
            "`uv run python tests/record_claude_cassettes.py` (needs the `claude` binary)."
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


# --- Behavioural: execute the SHIPPED gate lines ---------------------------


def _shipped_comparison_lines() -> str:
    """Extract the PLUG-assignment and comparison from a shipped gate block.

    Running the doc's own text (rather than a retyped copy) is the point: a
    typo introduced into the markdown fails these tests.
    """
    body = (PLUGIN_ROOT / "svg-infographics" / "commands" / "validate.md").read_text(encoding="utf-8")
    lines = [
        ln.strip()
        for ln in body.splitlines()
        if ln.strip().startswith(("PLUG=", '[ -n "$PLUG" ]', 'echo "toolkit'))
    ]
    assert len(lines) >= 3, "could not extract the shipped comparison lines"
    return "\n".join(lines[:3])


def _run_gate(
    tmp_path: Path, lib_version: str, plugin_version: str | None
) -> subprocess.CompletedProcess:
    """Run the shipped comparison with a fixture library/plugin version pair.

    The `pip install` line is omitted deliberately - the test asserts the
    verification logic, and must not mutate the machine or need a network.
    Returns the whole result: the EXIT CODE is the contract, not just the text.
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
    )


def test_gate_blocks_on_mismatch(tmp_path):
    """The exact proposals-session condition: plugin ahead of the library.

    A non-zero exit is the whole point. Printing STALE and continuing is what
    let a session drive a 26-release-old CLI while believing it was checked.
    """
    r = _run_gate(tmp_path, lib_version="1.5.5", plugin_version="1.6.31")
    assert r.returncode != 0, f"a mismatched gate must BLOCK, got exit 0: {r.stdout}"
    assert r.stdout.strip().startswith("STALE:"), r.stdout
    assert "1.5.5" in r.stdout and "1.6.31" in r.stdout, "both versions must be named"
    assert "toolkit" not in r.stdout, "must not also print the success line"


def test_gate_passes_on_parity(tmp_path):
    r = _run_gate(tmp_path, lib_version="1.6.31", plugin_version="1.6.31")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "toolkit 1.6.31", r.stdout


def test_gate_does_not_cry_wolf_without_a_plugin_root(tmp_path):
    """Outside a plugin install (dev checkout, bare shell) there is nothing to
    compare against - the gate must stay quiet and pass, not block on a bogus
    STALE. Blocking here would make every dev-tree invocation unrunnable."""
    r = _run_gate(tmp_path, lib_version="1.6.31", plugin_version=None)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "toolkit 1.6.31", r.stdout
    assert "STALE" not in r.stdout


def test_every_shipped_gate_blocks_rather_than_warns():
    """All 21 sites, not just the one the behavioural test runs. A gate that
    echoes STALE and falls through is the defect; it must exit non-zero."""
    soft = []
    # Scoped to the shipped plugins: an unscoped rglob also walks `.venv` and the
    # journal, where entry 286 quotes a STALE line as prose and would fail this
    # test on a reword.
    for plugin in PLUGINS:
        for path in (ROOT / plugin).rglob("*.md"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "STALE: library" not in line:
                    continue
                if "exit 1" not in line:
                    soft.append(f"{path.relative_to(ROOT)}: {line.strip()}")
    assert not soft, "gate sites that warn instead of blocking:\n" + "\n".join(soft)


# --- Realism: real recorded `claude -p` responses --------------------------


def _spawn_claude(prompt: str) -> str:
    """Spawn site the cassette intercepts.

    Must mirror `tests/record_claude_cassettes.py::spawn` - including stripping
    CLAUDECODE from the env, or a `--record-cassettes` run here would capture a
    different response than the recorder does (claude -p hangs with it set).
    """
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
        env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
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

    The static tests prove the text is present; a real model response shows the
    guidance drives the verdict - inverting it to "a STALE line is NOT a
    blocker" flips the recorded answer from BLOCKED to PROCEED.

    The prompt quotes only the gate's commands and rules, not its prose, so
    tidying wording costs nothing and changing an instruction demands a
    re-record. Deletion is caught by the static guards above, which need no
    binary; these add the evidence that the rules are understood.
    """

    def test_stale_output_blocks_the_run(self, claude_p_cassette, monkeypatch):
        monkeypatch.setattr(subprocess, "run", claude_p_cassette)
        assert _verdict(_spawn_claude(build_gate_stale_prompt())) == "BLOCKED"

    def test_matched_output_allows_the_run(self, claude_p_cassette, monkeypatch):
        """Discriminator - without this, an always-BLOCKED model would pass the
        test above while telling us nothing about the gate."""
        monkeypatch.setattr(subprocess, "run", claude_p_cassette)
        assert _verdict(_spawn_claude(build_gate_matched_prompt())) == "PROCEED"
