"""Shared prompt builders for cassette recording + replay.

Both `tests/record_claude_cassettes.py` and
`tests/test_claude_cassette_realism.py` import from here so the prompt
text is content-identical across record and replay. Drift between the
two (even a single whitespace change) would invalidate the cassette
hash and break replay.

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


def build_pass_evaluation_prompt() -> str:
    """Hand-crafted PASS/FAIL prompt as used by `_claude_evaluate`."""
    return textwrap.dedent("""\
        Respond with PASS or FAIL on the first line, then a one-line
        justification.

        Question: Does 2 + 2 equal 4?

        Respond ONLY in this format:
          PASS|FAIL: justification
    """).strip()
