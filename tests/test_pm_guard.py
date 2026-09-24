"""The project-management plugin hooks: pm-tools is the only writer of a tracker file.

The hook script runs as Claude Code runs it - a subprocess fed the hook's JSON on
stdin - so each test asserts on what Claude would receive, not on internal state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

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


@pytest.fixture(autouse=True)
def own_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard remembers what it denied in the temp dir; each test gets its own."""
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("TMPDIR", str(state))


@pytest.fixture
def tracker(tmp_path: Path) -> Path:
    f = tmp_path / "docs" / "defects-app.md"
    f.parent.mkdir()
    f.write_text("# Defects - App\n", encoding="utf-8")
    return f


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
def test_a_hand_edit_of_a_tracker_is_denied_with_the_way_out(tracker: Path, tool: str) -> None:
    reply = hook("pre-tool-use", edit(tracker, tool))
    assert denied(reply), f"{tool} on a tracker must be denied"
    reason = reply["hookSpecificOutput"]["permissionDecisionReason"]
    assert "pm-tools" in reason and "project-management" in reason
    assert "same call again" in reason, "the deny says how a justified edit gets through"


def test_the_same_edit_sent_again_passes_and_a_new_one_is_asked_again(tracker: Path) -> None:
    """The first deny asks Claude to reconsider; repeating the exact call is the decision."""
    assert denied(hook("pre-tool-use", edit(tracker)))
    assert hook("pre-tool-use", edit(tracker)) is None, "the repeat passes"
    assert denied(hook("pre-tool-use", edit(tracker, new="c"))), "a different edit is asked again"
    other = edit(tracker) | {"session_id": "s2"}
    assert denied(hook("pre-tool-use", other)), "another session starts over"


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
def test_an_in_place_shell_write_to_a_tracker_is_denied(tracker: Path, command: str) -> None:
    assert denied(hook("pre-tool-use", bash(command, tracker.parents[1])))
    assert hook("pre-tool-use", bash(command, tracker.parents[1])) is None, "the repeat passes"


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
