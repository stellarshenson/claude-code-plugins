"""Shared prompt builders for cassette recording + replay.

`tests/record_claude_cassettes.py` and the tests that replay its output
(`test_claude_cassette_realism.py`, `test_toolchain_gate.py`) all import
from here so the prompt text is content-identical across record and replay.
Any drift between them (even a single whitespace change) would invalidate
the cassette hash and break replay.

Add a builder here when adding a new scenario; reference it from both
the recording script and the consuming test.
"""

from __future__ import annotations

import textwrap

from stellars_claude_code_plugins.journal.journal_tools import (
    parse_journal,
    render_standardize_prompt,
)

HEADER = "# Test Journal\n\nIntro line.\n\n---\n\n"


def _entry_md(num: int, marker: str, body: str, title: str) -> str:
    return (
        f"{num}. **Task{marker} - {title}** (v0.1.0): one-line summary<br>\n"
        f"    **Result**: {body}\n"
    )


def rationale_rich_body() -> str:
    """200-word unmarked body with rationale segments. Used by the
    'standardize-realistic-decision' cassette + matching test."""
    body = textwrap.dedent("""\
        Trigger: tests for the cassette layer needed a real recorded
        response. Why this approach over synthetic mocks: format drift
        in claude's output (stderr leaks, JSON envelope changes,
        model-swap retry messages) silently breaks parsers that test
        against hand-crafted strings. Implementation: spawned via env
        -u CLAUDECODE claude -p with --no-session-persistence so the
        recording does not pollute ~/.claude/projects/. Cause and
        effect: the recorded JSON ships with the repo; CI replays it
        without ever needing the binary. Gotcha: prompt-text changes
        invalidate the cassette - the SHA-256 hash is content-addressed.
    """).strip()
    while len(body.split()) < 200:
        body += " padding-word"
    return body


def padded_body() -> str:
    """500-word boilerplate body. Used by the 'standardize-condense-padded'
    cassette + matching test."""
    return " ".join(["lorem ipsum dolor sit amet"] * 100)


def build_standardize_rationale_rich_prompt() -> str:
    """Render the per-entry standardize prompt for the rationale-rich
    scenario. Both the recording script and the test call this."""
    md = HEADER + _entry_md(
        1,
        "",
        rationale_rich_body(),
        "Cassette layer recording for claude -p subprocess",
    )
    entry = parse_journal(md)[0]
    return render_standardize_prompt(entry)


def build_standardize_padded_prompt() -> str:
    """Render the per-entry standardize prompt for the padded scenario."""
    md = HEADER + _entry_md(
        2,
        "",
        padded_body(),
        "Padded entry that should condense",
    )
    entry = parse_journal(md)[0]
    return render_standardize_prompt(entry)


# --- Toolchain gate ------------------------------------------------------
#
# A FROZEN snapshot of the shipped gate's normative lines (svg-designer's
# SKILL.md, `## Toolchain gate`): the command block plus the bulleted rules.
#
# Frozen, not read live, because the cassette key is a SHA-256 of the prompt. A
# live read couples the fixture identity to doc prose: rewording one bullet
# misses the cassette and fails CI, which has no `claude` binary to re-record
# with. That already happened - two cassettes were re-recorded mid-session for
# verdicts that came back word-identical.
#
# Drift is caught without the binary: `test_shipped_gate_still_carries_its_
# normative_lines` reads the LIVE SKILL.md and compares it against GATE_FENCE and
# GATE_BULLETS below, so any change to the gate's commands OR rules fails loudly.
# Editing either costs an updated snapshot and a re-record; tidying the prose
# AROUND them is free, which is the coupling the freeze exists to break.

GATE_FENCE = """\
```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && echo "STALE: library $LIB != plugin $PLUG - CLI may lack flags this skill uses; re-run the upgrade" || echo "toolkit $LIB"
```"""

GATE_BULLETS = """\
- **The upgrade always runs** - every session reinstalls to the latest so the validators match the current rules; never skip it because the package is already present, that is how a stale checker survives
- **The version compare is the real gate** - `--help` exits 0 on an ancient CLI, so a green `--help` proves nothing. Only `LIB == PLUG` proves the CLI carries the flags this skill documents. A `STALE:` line means treat every CLI failure as a version problem first
- **Refuse to start** only when the library is unavailable after the reinstall attempt - the import still fails, so `svg-infographics --help` still errors. Report the error and stop; there is no fallback, because every rule here assumes the CLI, and a hand-built SVG without the geometry tools and validators is exactly the defect class the toolchain prevents
- A failed *upgrade* is NOT a refusal condition - offline or PyPI unreachable while the CLI still imports means run at the installed version; the reinstall was attempted, which is what matters. An absent library is fatal, a stale one that could not reach PyPI is a hazard to report, not a stop"""


def _shipped_gate_rules() -> str:
    """The frozen gate text the cassette prompts are built from."""
    return f"{GATE_FENCE}\n{GATE_BULLETS}"


# The question must isolate the TOOLCHAIN-VERSION dimension and nothing else.
# An earlier draft asked whether a zero exit code proved the SVG valid; the
# model correctly answered "no" in both arms - exit codes are not findings -
# so the two scenarios did not discriminate. Ask only about toolchain fitness.
_GATE_QUESTION = textwrap.dedent("""\
    The skill now tells you to run this, using a flag documented by the current plugin:

        svg-infographics validate --svg out.svg

    Question: judging ONLY by the gate output above, is the toolchain in a fit state
    to run that command as documented, or must you repair the toolchain first?

    Respond ONLY in this format:
      PROCEED|BLOCKED: one-line justification
    """).strip()


def _build_gate_prompt(gate_output: str) -> str:
    """Assemble the gate-comprehension prompt around one gate stdout line."""
    return (
        _shipped_gate_rules()
        + "\n\nYou ran the gate above inside a plugin whose plugin.json version is 1.6.31.\n"
        + "It printed:\n\n    "
        + gate_output
        + "\n\n"
        + _GATE_QUESTION
    )


def build_gate_stale_prompt() -> str:
    """Gate reported a library/plugin mismatch - the documented `--svg` flag may
    not exist on the installed CLI, so the toolchain needs repair -> BLOCKED."""
    return _build_gate_prompt(
        "STALE: library 1.5.5 != plugin 1.6.31 - CLI may lack flags this skill uses; re-run the upgrade"
    )


def build_gate_matched_prompt() -> str:
    """Gate reported parity. Discriminator for the stale case - a test that only
    ever returns BLOCKED would pass while proving nothing -> PROCEED."""
    return _build_gate_prompt("toolkit 1.6.31")


def build_pass_evaluation_prompt() -> str:
    """Hand-crafted PASS/FAIL prompt as used by `_claude_evaluate`."""
    return textwrap.dedent("""\
        Respond with PASS or FAIL on the first line, then a one-line
        justification.

        Question: Does 2 + 2 equal 4?

        Respond ONLY in this format:
          PASS|FAIL: justification
    """).strip()
