"""Every plugin command must have a same-named skill that owns its procedure.

A procedure that lives only in a command file has no skill of its own. That bit
in practice: this repo's own CLAUDE.md mandates journal writes go through
`/journal:update`, and `update` was a command with no skill behind it. 27 of 42
commands were in that state.

The fix is the router pattern: `skills/<name>/SKILL.md` owns the procedure and
`commands/<name>.md` routes into it. One source of truth, both surfaces live.
The command names the skill's file, not the skill's name: the two share one
name and the Skill tool resolves it to the command (DEF-SKILLC-76).
This test pins the parity - the skill exists, is addressable, and the command
points at it rather than standing alone as the only copy of the procedure. It
deliberately does NOT cap the command's length: several commands legitimately
carry mode dispatch above the skill they call, and enforcing a router shape on
them would be a refactor nobody asked for.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins"

COMMANDS = sorted(PLUGIN_ROOT.glob("*/commands/*.md"))

def _ids(paths: list[Path]) -> list[str]:
    return [f"{p.parents[1].name}:{p.stem}" for p in paths]


def _body(text: str) -> str:
    match = re.match(r"^---\n.*?\n---\n(.*)$", text, re.S)
    return (match.group(1) if match else text).strip()


def test_commands_were_found() -> None:
    """Guard the glob itself - an empty sweep would make every test below vacuous."""
    assert len(COMMANDS) > 30, f"only {len(COMMANDS)} commands found; the glob is wrong"


@pytest.mark.parametrize("command", COMMANDS, ids=_ids(COMMANDS))
def test_command_has_a_same_named_skill(command: Path) -> None:
    plugin = command.parents[1]
    skill = plugin / "skills" / command.stem / "SKILL.md"
    assert skill.is_file(), (
        f"{plugin.name}:{command.stem} is a command with no skill at "
        f"{skill.relative_to(ROOT)} - an agent cannot invoke it"
    )


@pytest.mark.parametrize("command", COMMANDS, ids=_ids(COMMANDS))
def test_command_points_at_its_skill(command: Path) -> None:
    """DEF-SKILLC-76. A command and its skill share one name, and the Skill tool
    resolves that name to the command. A command that sends the reader to "the
    `journal:update` skill" hands back itself and the procedure never loads: a
    galaxahub session filed a defect before it read the project-management rules.
    The command names the skill's file instead, which one Read opens from either
    entry point."""
    plugin = command.parents[1]
    body = _body(command.read_text())
    path = f"this plugin's skill file `skills/{command.stem}/SKILL.md`"
    assert path in body, f"{plugin.name}:{command.stem} does not name {path}"
    by_name = rf"(?:Invoke|Read) (?:the )?`{plugin.name}:{command.stem}` skill"
    assert not re.search(by_name, body), (
        f"{plugin.name}:{command.stem} points at its skill by the name the Skill tool "
        "resolves to this command"
    )


@pytest.mark.parametrize("command", COMMANDS, ids=_ids(COMMANDS))
def test_skill_declares_its_name_and_description(command: Path) -> None:
    skill = command.parents[1] / "skills" / command.stem / "SKILL.md"
    if not skill.is_file():
        pytest.skip("covered by test_command_has_a_same_named_skill")
    front = re.match(r"^---\n(.*?)\n---\n", skill.read_text(), re.S)
    assert front, f"{skill.relative_to(ROOT)} has no frontmatter"
    fields = front.group(1)
    assert re.search(r"^name:\s*\S", fields, re.M), f"{skill.relative_to(ROOT)} has no name"
    assert re.search(r"^description:\s*\S", fields, re.M), (
        f"{skill.relative_to(ROOT)} has no description - it is what Claude matches on"
    )
    declared = re.search(r"^name:\s*(\S+)", fields, re.M).group(1)
    assert declared == command.stem, (
        f"{skill.relative_to(ROOT)} declares name '{declared}' but sits in "
        f"skills/{command.stem}/ - the directory is what makes it addressable"
    )


def test_no_frontmatter_description_carries_angle_brackets() -> None:
    """skill-creator's frontmatter gate refuses `<` and `>` in a description, so a
    skill shipped with `ACC-<CAT>-<N>` or `analyze -> draft` in its description
    fails validation downstream. Commands are held to the same rule: several share
    their description with their skill verbatim, and a divergence here would put
    the pair on opposite sides of the gate."""
    fronts = sorted(PLUGIN_ROOT.glob("*/skills/*/SKILL.md")) + COMMANDS
    assert len(fronts) > 80, f"only {len(fronts)} files swept; the glob is wrong"
    offenders = []
    for path in fronts:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("description:") and ("<" in line or ">" in line):
                offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"angle brackets in a description: {offenders}"
