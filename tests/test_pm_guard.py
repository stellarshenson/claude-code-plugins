"""The project-management plugin hooks: pm-tools is the only writer of a tracker file.

The hook script runs as Claude Code runs it - a subprocess fed the hook's JSON on
stdin - so each test asserts on what Claude would receive, not on internal state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from stellars_claude_code_plugins.project_management.pm_tools import main as pm_tools

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "project-management"
GUARD = PLUGIN / "hooks" / "pm_guard.py"


def hook(event: str, payload: dict, **env: str) -> dict | None:
    """Run the guard; return its JSON reply, or None when it stays silent."""
    run_env = {k: v for k, v in os.environ.items() if k != "PM_TOOLS_HAND_EDIT"} | env
    r = subprocess.run(
        [sys.executable, str(GUARD), event],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=run_env,
        check=True,
    )
    return json.loads(r.stdout) if r.stdout.strip() else None


def denied(reply: dict | None) -> bool:
    return bool(reply) and reply["hookSpecificOutput"]["permissionDecision"] == "deny"


def pm(*args: str) -> int:
    return pm_tools(["pm-tools", *args])


@pytest.fixture
def tracker(tmp_path: Path) -> Path:
    f = tmp_path / "docs" / "defects-app.md"
    f.parent.mkdir()
    f.write_text("# Defects - App\n", encoding="utf-8")
    assert pm("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen") == 0
    return f


def token_of(tracker: Path, capsys: pytest.CaptureFixture) -> str:
    """The token pm-tools prints for the tracker as it is now - the only source of it."""
    capsys.readouterr()
    before = tracker.read_bytes()
    assert pm("ack", str(tracker)) == 0
    assert tracker.read_bytes() == before, "asking for a token writes nothing"
    return re.search(r"--token (\w+)", capsys.readouterr().out).group(1)


def ack(tracker: Path, token: str, reason: str = "repair a line two merges broke") -> int:
    return pm("ack", str(tracker), "--token", token, "--author", "@kj", "--reason", reason)


def edit(path: Path, tool: str = "Edit", new: str = "b") -> dict:
    args = {"file_path": str(path), "old_string": "a", "new_string": new}
    return {"session_id": "s1", "tool_name": tool, "tool_input": args, "cwd": str(path.parent)}


def bash(command: str, cwd: Path) -> dict:
    return {
        "session_id": "s1",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd),
    }


def test_hooks_json_wires_the_guard_for_both_events() -> None:
    cfg = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    pre = cfg["PreToolUse"][0]
    assert set(pre["matcher"].split("|")) == {"Edit", "Write", "MultiEdit", "Bash"}
    assert pre["hooks"][0]["command"].endswith('/hooks/pm_guard.py" pre-tool-use')
    assert cfg["UserPromptSubmit"][0]["hooks"][0]["command"].endswith('/hooks/pm_guard.py" prompt')
    assert "${CLAUDE_PLUGIN_ROOT}" in pre["hooks"][0]["command"]


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_a_hand_edit_of_a_tracker_is_denied_with_the_way_out(
    tracker: Path, tool: str, capsys: pytest.CaptureFixture
) -> None:
    reply = hook("pre-tool-use", edit(tracker, tool))
    assert denied(reply), f"{tool} on a tracker must be denied"
    reason = reply["hookSpecificOutput"]["permissionDecisionReason"]
    assert "pm-tools" in reason and "project-management" in reason
    assert f"pm-tools ack {tracker}" in reason, "the deny names the command that logs why"
    assert token_of(tracker, capsys) not in reason, "only pm-tools gives the token"


def test_sending_the_same_edit_again_is_not_a_justification(tracker: Path) -> None:
    """DEF-PMGT-77. The ask-once guard passed the identical call on its second try and
    recorded nothing, and its key hashed the Bash description too, so a reworded
    description was denied twice. Repeating a call now proves nothing."""
    assert denied(hook("pre-tool-use", edit(tracker)))
    assert denied(hook("pre-tool-use", edit(tracker))), "the repeat is denied too"


def test_an_acknowledged_hand_edit_passes_for_that_state_of_the_file(
    tracker: Path, capsys: pytest.CaptureFixture
) -> None:
    """DEF-PMGT-77. pm-tools derives the token from the file, prints it on request and
    logs the reason beside the tracker; the guard then lets a hand edit through until
    the file changes, and the next hand edit needs a token of its own."""
    assert denied(hook("pre-tool-use", edit(tracker)))
    token = token_of(tracker, capsys)
    assert not (tracker.parent / "pm-hand-edits.md").exists(), "no token was acknowledged yet"
    assert ack(tracker, token) == 0
    log = (tracker.parent / "pm-hand-edits.md").read_text(encoding="utf-8")
    assert f" @kj defects-app.md {token} sha256:" in log
    assert log.startswith("- "), "one markdown list item per acknowledged edit"
    assert log.rstrip().endswith(": repair a line two merges broke")
    assert hook("pre-tool-use", edit(tracker)) is None, "the acknowledged edit passes"
    tracker.write_text(tracker.read_text(encoding="utf-8") + "- edited\n", encoding="utf-8")
    assert denied(hook("pre-tool-use", edit(tracker))), "a new state needs a new token"
    assert token_of(tracker, capsys) != token


def test_ack_refuses_what_it_cannot_log(tracker: Path, capsys: pytest.CaptureFixture) -> None:
    """The token must be the file's current one, the author a well-formed handle, the reason
    given and short, and the file a tracker; each refusal leaves the log unwritten."""
    token = token_of(tracker, capsys)
    with pytest.raises(SystemExit, match="not the token"):
        ack(tracker, "0" * 8)
    with pytest.raises(SystemExit, match="--reason"):
        pm("ack", str(tracker), "--token", token, "--author", "@kj")
    with pytest.raises(SystemExit, match="bad handle"):
        pm("ack", str(tracker), "--token", token, "--author", "@1x", "--reason", "r")
    with pytest.raises(SystemExit, match="limit is 50"):
        ack(tracker, token, " ".join(["word"] * 51))
    notes = tracker.parent / "notes.md"
    notes.write_text("x\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="not a tracker"):
        pm("ack", str(notes))
    assert not (tracker.parent / "pm-hand-edits.md").exists()


def test_ack_works_when_the_roster_is_unreadable(
    tracker: Path, capsys: pytest.CaptureFixture
) -> None:
    """An unclosed code fence above ## Authors hides the roster from pm-tools; that is a
    repair only a hand edit can make, so ack must not depend on reading the roster."""
    head, rest = tracker.read_text(encoding="utf-8").split("\n", 1)
    tracker.write_text(f"{head}\n```\n{rest}", encoding="utf-8")
    assert ack(tracker, token_of(tracker, capsys)) == 0


def test_other_files_and_new_trackers_pass(tracker: Path) -> None:
    assert hook("pre-tool-use", edit(tracker.parent / "notes.md")) is None
    assert hook("pre-tool-use", edit(tracker.parent / "my-defects.md")) is None
    new = tracker.parent / "acc-crit-app.md"
    assert hook("pre-tool-use", edit(new, "Write")) is None, "pm-tools needs a file to write into"
    assert denied(hook("pre-tool-use", edit(new, "Edit"))) is False


def test_a_tracker_in_a_merge_conflict_may_be_hand_edited(tracker: Path) -> None:
    tracker.write_text("<<<<<<< HEAD\n- [ ] a\n=======\n- [ ] b\n>>>>>>> side\n", encoding="utf-8")
    assert hook("pre-tool-use", edit(tracker)) is None


def test_the_user_override_lets_a_hand_edit_through(tracker: Path) -> None:
    assert hook("pre-tool-use", edit(tracker), PM_TOOLS_HAND_EDIT="1") is None


@pytest.mark.parametrize(
    "command",
    [
        "sed -i 's/MAJOR/MINOR/' docs/defects-app.md",
        "echo '- [ ] x' >> docs/defects-app.md",
        "printf x | tee docs/defects-app.md",
        "python3 - <<'EOF'\nfrom pathlib import Path\np = Path('docs/defects-app.md')\n"
        "p.write_text(p.read_text().replace('a', 'b'))\nEOF",
        "cp /tmp/x.md docs/defects-app.md",
        "grep -c x docs/defects-app.md && sed -i 's/a/b/' docs/defects-app.md",
    ],
)
def test_an_in_place_shell_write_to_a_tracker_is_denied(
    tracker: Path, command: str, capsys: pytest.CaptureFixture
) -> None:
    assert denied(hook("pre-tool-use", bash(command, tracker.parents[1])))
    assert denied(hook("pre-tool-use", bash(command, tracker.parents[1]))), "so is the repeat"
    assert ack(tracker, token_of(tracker, capsys)) == 0
    assert hook("pre-tool-use", bash(command, tracker.parents[1])) is None, "acknowledged"


@pytest.mark.parametrize(
    "command",
    [
        "grep -n DEF-LNCH-1 docs/defects-app.md",
        "sed -n 1,20p docs/defects-app.md",
        "cp docs/defects-app.md /tmp/backup.md",
        "pm-tools log docs/defects-app.md --id DEF-LNCH-1 --author @kj --event 'sed -i broke it'",
        "uv run --extra dev pm-tools check docs > /tmp/check.txt",
        "sed -i 's/a/b/' notes.md",
    ],
)
def test_reads_pm_tools_and_other_files_pass(tracker: Path, command: str) -> None:
    assert hook("pre-tool-use", bash(command, tracker.parents[1])) is None


@pytest.mark.parametrize(
    "prompt",
    [
        "add acc crit for the login screen",
        "update the acceptance criteria",
        "file a defect for the crash",
        "DEF-LNCH-3 is back",
        "is ACC-AUTH-102 done?",
        "what is on the bug tracker",
    ],
)
def test_a_tracker_prompt_is_told_to_load_the_skill(prompt: str) -> None:
    reply = hook("prompt", {"prompt": prompt})
    assert reply and "project-management" in reply["hookSpecificOutput"]["additionalContext"]


def test_an_unrelated_prompt_gets_nothing() -> None:
    assert hook("prompt", {"prompt": "refactor the parser and fix the failing test"}) is None
