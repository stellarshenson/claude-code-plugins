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
from pathlib import Path
import re
import subprocess

from _cassette_prompts import (
    GATE_BULLETS,
    build_gate_matched_prompt,
    build_gate_stale_prompt,
)
import pytest

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
STALE_ASSERTION = "STALE: library $LIB older than plugin $PLUG"

# The comparison every gate block ships, verbatim. The library may be NEWER than
# the plugin (a fresh `pip install --upgrade` against a not-yet-updated plugin
# cache is healthy); only a library OLDER than the plugin is the defect - the
# CLI would lack flags the plugin documents. `sort -V` names the older version.
GATE_OLDER_LINE = 'OLDER=$(printf \'%s\\n%s\\n\' "$LIB" "$PLUG" | sort -V | head -1)'
GATE_COMPARE_LINE = (
    '[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && '
    '{ echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an '
    'outdated CLI; re-run the upgrade"; exit 1; }'
)

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


def test_every_gate_ships_the_version_ordered_comparison():
    """All gate sites carry the exact two-line compare: block only when the
    installed library is OLDER than the plugin, never when it is newer."""
    offenders = []
    for p in _plugin_markdown():
        body = p.read_text(encoding="utf-8")
        if "STALE: library" not in body:
            continue
        if GATE_OLDER_LINE not in body or GATE_COMPARE_LINE not in body:
            offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, (
        f"gate sites missing the verbatim version-ordered comparison: {offenders}"
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


_SKILL_REF = re.compile(
    r"/?(?:autobuild|datascience|devils-advocate|document-processing|journal|project-management|svg-infographics):[a-z-]+"
)


def _toolkit_clis() -> list[str]:
    """The console scripts pyproject ships - the only binaries the gate protects."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("[project.scripts]", 1)[1].split("\n[", 1)[0]
    return [ln.split("=", 1)[0].strip() for ln in block.splitlines() if "=" in ln]


def _strip_frontmatter(body: str) -> str:
    """Drop the YAML header - it is menu metadata, not instructions to the agent.

    A router command's `description` may name the CLI its skill runs
    (`Archive older journal entries via journal-tools archive`) while the
    router itself runs nothing. Gating on that text would put a network `pip
    install` in front of a file whose whole body is one Skill invocation.
    """
    if not body.startswith("---\n"):
        return body
    end = body.find("\n---\n", 4)
    return body if end == -1 else body[end + 5 :]


def _names_toolkit_cli(body: str) -> bool:
    """True when the body tells the agent to run a toolkit binary.

    Skill hand-offs (`svg-infographics:svg-designer`, `/journal:update`) are not
    CLI calls - the skill they route into carries its own gate.
    """
    prose = _SKILL_REF.sub("", _strip_frontmatter(body))
    names = "|".join(re.escape(c) for c in _toolkit_clis())
    return re.search(rf"(?<![\w/:-])(?:{names})(?![\w-])", prose) is not None


def test_every_cli_entry_point_is_gated():
    """An entry point carries the gate exactly when it names a toolkit CLI.

    Two contracts have shipped here. The first gated only files that named a
    CLI. The second widened that to every shell-capable file, on the argument
    that a file could reach the toolkit indirectly or gain a CLI call later
    and never check the version. That put 149 words and a network `pip
    install` at the front of 36 files that run nothing - "how do I write a
    footnote" upgraded the toolkit and could hard-exit on `STALE` before the
    agent read a line - for a risk a test catches better than repetition does.

    So the contract is back to the first form, and this test is the guard
    the second form wanted: add a `journal-tools` call to an ungated file and
    it fails here; an indirect reach goes through a skill that is gated
    itself. Gated files must also be shell-capable, or the instruction is
    dead text. Entry points are `SKILL.md` and `commands/*.md`; references,
    rules, READMEs and examples are loaded BY an entry point and stay exempt.
    """
    ungated, needless, undeliverable = [], [], []
    for p in _plugin_markdown():
        if p.name != "SKILL.md" and p.parent.name != "commands":
            continue
        body = p.read_text(encoding="utf-8")
        gated = STALE_ASSERTION in body
        names_cli = _names_toolkit_cli(body)
        rel = str(p.relative_to(ROOT))
        if names_cli and not gated:
            ungated.append(rel)
        elif gated and not names_cli:
            needless.append(rel)
        if gated and not _can_run_shell(body):
            undeliverable.append(rel)
    assert not ungated, (
        "entry points that run a toolkit CLI without the gate - each would drive "
        f"it unchecked: {ungated}"
    )
    assert not needless, (
        "entry points carrying the gate while running no toolkit CLI - standing "
        f"context and a pip upgrade for nothing: {needless}"
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
    live = (PLUGIN_ROOT / "svg-infographics" / "skills" / "svg-designer" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    for required in (UPGRADE_LINE, STALE_ASSERTION, GATE_OLDER_LINE, GATE_COMPARE_LINE):
        assert required in live, f"shipped gate lost its {required!r} line"
    assert "The version compare is the real gate" in live, (
        "the gate lost the rule that a green `--help` proves nothing - the "
        "exact false green that let a 26-release-stale CLI through"
    )
    # GATE_FENCE in tests/_cassette_prompts.py stays frozen on the pre-ordering
    # compare: the cassette key is a SHA-256 of the prompt, and its scenario - a
    # library OLDER than the plugin - still means BLOCKED under the new rule, so
    # the recorded verdicts remain valid. Only the bullets must track the live doc.
    assert GATE_BULLETS in live, (
        "the shipped gate no longer matches the frozen GATE_BULLETS snapshot in "
        "tests/_cassette_prompts.py - the recorded cassettes were built from the "
        "old text. Update GATE_BULLETS and re-record with "
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
    typo introduced into the markdown fails these tests. The block is FOUND
    rather than read from a pinned path - naming one file made this test fail
    the day that file became a router and its gate moved into the skill.
    """
    wanted = ("PLUG=", "OLDER=", '[ -n "$PLUG" ]', 'echo "toolkit')
    for path in _plugin_markdown():
        if STALE_ASSERTION not in (body := path.read_text(encoding="utf-8")):
            continue
        lines = [ln.strip() for ln in body.splitlines() if ln.strip().startswith(wanted)]
        if len(lines) >= 4:
            return "\n".join(lines[:4])
    raise AssertionError(
        "no shipped gate block carries the four comparison lines - the gate was "
        "deleted, or its wording drifted from what this test executes"
    )


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
    assert r.returncode != 0, f"an older library must BLOCK, got exit 0: {r.stdout}"
    assert r.stdout.strip().startswith("STALE:"), r.stdout
    assert "older than" in r.stdout, "the message names the direction that blocks"
    assert "1.5.5" in r.stdout and "1.6.31" in r.stdout, "both versions must be named"
    assert "toolkit" not in r.stdout, "must not also print the success line"


def test_gate_passes_on_parity(tmp_path):
    r = _run_gate(tmp_path, lib_version="1.6.31", plugin_version="1.6.31")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "toolkit 1.6.31", r.stdout


def test_gate_passes_when_the_library_is_newer_than_the_plugin(tmp_path):
    """A fresh `pip install --upgrade` routinely lands a library ahead of a
    not-yet-refreshed plugin cache. That direction is healthy: the CLI carries
    at least the flags the plugin documents, so the gate must not block."""
    r = _run_gate(tmp_path, lib_version="1.7.0", plugin_version="1.6.31")
    assert r.returncode == 0, f"a newer library must pass, got exit {r.returncode}: {r.stdout}"
    assert r.stdout.strip() == "toolkit 1.7.0", r.stdout
    assert "STALE" not in r.stdout


def test_gate_orders_versions_numerically_not_lexicographically(tmp_path):
    """1.7.10 is newer than 1.7.9, but a plain string sort puts "1.7.10" first
    and would block a healthy library. Only this pair separates `sort -V` from
    lexicographic ordering - the newer-library test above cannot, because
    "1.6.31" < "1.7.0" under both orderings."""
    r = _run_gate(tmp_path, lib_version="1.7.10", plugin_version="1.7.9")
    assert r.returncode == 0, f"1.7.10 is newer than 1.7.9, got exit {r.returncode}: {r.stdout}"
    assert r.stdout.strip() == "toolkit 1.7.10", r.stdout
    r = _run_gate(tmp_path, lib_version="1.7.9", plugin_version="1.7.10")
    assert r.returncode != 0, f"1.7.9 is older than 1.7.10, must block: {r.stdout}"
    assert "older than" in r.stdout, r.stdout


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
    soft, walked = [], 0
    # Scoped to the shipped plugins: an unscoped rglob also walks `.venv` and the
    # journal, where entry 286 quotes a STALE line as prose and would fail this
    # test on a reword.
    for plugin in PLUGINS:
        for path in (PLUGIN_ROOT / plugin).rglob("*.md"):
            walked += 1
            for line in path.read_text(encoding="utf-8").splitlines():
                if "STALE: library" not in line:
                    continue
                if "exit 1" not in line:
                    soft.append(f"{path.relative_to(ROOT)}: {line.strip()}")
    assert walked, "walked no plugin files - the guard would pass vacuously"
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
