#!/usr/bin/env python3
"""project-management plugin hooks: pm-tools is the only writer of a tracker file.

pre-tool-use - deny a hand edit of acc-crit*.md or defects*.md, the files pm-tools reads:
an Edit, Write, MultiEdit or in-place shell write is denied with the pm-tools way, because a
hand edit loses the id assignment and the authored log line. A hand edit with a reason gets
through once `pm-tools ack` has logged the reason with the token pm-tools derives from the
file: the log line carries the file's content digest, which this hook matches, so the next
state of the file needs a new token. Three cases pass at once: a tracker that does not exist
yet (pm-tools needs a file to write into), a tracker holding git conflict markers
(references/conflicts.md resolves those by hand), and PM_TOOLS_HAND_EDIT=1 in Claude Code's
own environment.

prompt - when the prompt names acceptance criteria, defects, a tracker or an ACC-/DEF-
id, tell Claude to load the project-management skill before it acts.

Standard library only, so the guard works before the pm-tools library is installed.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys

TRACKER = r"(?:acc-crit|defects)[\w.-]*\.md"  # pm-tools GLOBS: acc-crit*.md, defects*.md
NAME = re.compile(rf"{TRACKER}$")
MENTION = re.compile(rf"(?<![\w.-]){TRACKER}")
WRITES = re.compile(
    r"\bsed\b[^|;&\n]*\s-(?:[A-Za-z]*i|-in-place)"
    r"|\bperl\b[^|;&\n]*\s-[A-Za-z]*i"
    r"|\bawk\s+-i\s+inplace"
    rf"|>>?\s*['\"]?[^\s'\"]*{TRACKER}"
    rf"|\btee\b[^|;&\n]*{TRACKER}"
    r"|write_text\(|\.write\(|open\([^)]*['\"][wa]"
    rf"|\b(?:mv|cp)\b[^|;&\n]*\s['\"]?[^\s'\"]*{TRACKER}['\"]?\s*$"
)
PM_TOOLS = re.compile(
    r"^(?:\w+=\S*\s+)*(?:uvx?\s+(?:run\s+)?(?:-\S+\s+(?:[^-\s]\S*\s+)?)*)?pm-tools\b"
)
PROMPT = re.compile(
    r"\bacc[\s_-]?crits?\b|\bacceptance[\s_-]+criteri(?:a|on)\b|\bdefects?\b"
    r"|\b(?:bug|issue)[\s_-]+(?:tracker|list)\b|\b(?:ACC|DEF)-[A-Z]{2,6}-\d+|\bpm-tools\b",
    re.I,
)
HAND_EDITS = "pm-hand-edits.log"  # beside the tracker; pm-tools ack writes it


def way(path: Path) -> str:
    return (
        "Use pm-tools instead (add, edit, amend, log, close, reject, reopen, relate, "
        "mechanism, root-cause), as the project-management skill describes: a hand edit "
        "loses the id assignment and the authored log line. If a hand edit is really needed "
        f"- a repair pm-tools cannot make - run `pm-tools ack {path}`, which prints a token "
        f"for the file as it is now, then `pm-tools ack {path} --token TOKEN --author @xx "
        '--reason "<why>"` to log why, and send the same call again. The next hand edit '
        "needs a new token. Then run pm-tools check."
    )


def conflicted(path: Path) -> bool:
    try:
        return any(ln.startswith("<<<<<<< ") for ln in path.open(encoding="utf-8"))
    except OSError:
        return False


def guarded(path: Path) -> bool:
    """An existing tracker outside a merge conflict - the files the guard protects."""
    return bool(NAME.fullmatch(path.name)) and path.is_file() and not conflicted(path)


def acknowledged(path: Path) -> bool:
    """True when pm-hand-edits.log beside the tracker has a line `pm-tools ack` wrote for
    the file as it is now. The hook matches the content digest; only pm-tools derives the
    token."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        lines = (path.parent / HAND_EDITS).read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    return any(f" {path.name} " in ln and f" sha256:{digest}: " in ln for ln in lines)


def segments(command: str) -> list[str]:
    """The command split at unquoted `;`, `|` and `&`, so at `&&`, `||` and pipes too.
    An unbalanced quote leaves the rest in one segment, which only widens the check."""
    out, cur, quote, i = [], [], None, 0
    while i < len(command):
        c = command[i]
        if c == "\\" and quote != "'":
            cur.append(command[i : i + 2])
            i += 2
            continue
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c in ";|&":
            out.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    out.append("".join(cur))
    return [s.strip() for s in out if s.strip()]


def shell_target(command: str, cwd: Path) -> Path | None:
    """The unacknowledged tracker a shell command writes to in place, or None."""
    for seg in segments(command):
        if PM_TOOLS.match(seg) or not WRITES.search(seg):
            continue
        for m in MENTION.finditer(seg):
            start = max(seg.rfind(c, 0, m.start()) for c in " \t\n'\"=<>(") + 1
            path = Path(seg[start : m.end()])
            path = path if path.is_absolute() else cwd / path
            if guarded(path) and not acknowledged(path):
                return path
    return None


def deny(reason: str) -> None:
    out = {"hookEventName": "PreToolUse", "permissionDecision": "deny"}
    print(json.dumps({"hookSpecificOutput": out | {"permissionDecisionReason": reason}}))


def pre_tool_use(event: dict) -> None:
    if os.environ.get("PM_TOOLS_HAND_EDIT") == "1":
        return
    tool, args = event.get("tool_name"), event.get("tool_input") or {}
    cwd = Path(event.get("cwd") or ".")
    if tool == "Bash":
        path = shell_target(args.get("command") or "", cwd)
        if path:
            deny(f"This command writes to {path}, a pm-tools tracker. {way(path)}")
    elif args.get("file_path"):
        path = Path(args["file_path"])
        path = path if path.is_absolute() else cwd / path
        if guarded(path) and not acknowledged(path):
            deny(f"{path} is a pm-tools tracker. {way(path)}")


def prompt(event: dict) -> None:
    if PROMPT.search(event.get("prompt") or ""):
        context = (
            "The prompt mentions acceptance criteria, defects or a tracker id. If it concerns "
            "the project's acc-crit or defects tracker, load the project-management skill "
            "before acting: every write goes through pm-tools, and a hook denies a hand edit "
            "of acc-crit*.md or defects*.md until pm-tools ack has logged why."
        )
        out = {"hookEventName": "UserPromptSubmit", "additionalContext": context}
        print(json.dumps({"hookSpecificOutput": out}))


if __name__ == "__main__":
    handler = {"pre-tool-use": pre_tool_use, "prompt": prompt}[sys.argv[1]]
    handler(json.load(sys.stdin))
