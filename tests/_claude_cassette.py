"""Cassette layer for `claude -p` subprocess calls in the test suite.

CI cannot run the `claude` binary. Tests that exercise the subprocess
spawn path (standardize, autobuild gatekeeper, devils-advocate
standalone) need their `subprocess.run` interception to return real
recorded responses, not synthetic mocks - synthetic strings like
`DECISION: EXTENDED\\n` miss the parser breakage that happens when
claude's actual output format drifts (stderr leaks, JSON envelope
changes, soft-landing model-swap text).

## How it works

The cassette intercepts at `subprocess.run`. The prompt is extracted
from the args (the value following ``-p`` or ``--print``), hashed
with SHA-256 (12-char prefix), and looked up in
``tests/cassettes/claude_p/<hash>.json``. The JSON ships ``stdout``,
``stderr``, and ``returncode`` so the test sees the same
``CompletedProcess``-shaped result it would get from a real call.

## Record vs replay

Default mode is REPLAY. Missing cassettes raise loudly so tests
fail-closed (silent fallback would hide drift).

Record mode is opt-in via ``pytest --record-cassettes``. In that mode
a missing cassette is populated by actually running ``claude``. Tests
that want to record (re-record) must clear stale cassette files first.

The record workflow is intentionally manual: a maintainer with the
``claude`` binary runs ``pytest --record-cassettes`` once, commits the
new JSON files, and CI picks them up. Anyone re-running the same
tests later replays without ever shelling out.

## Cassette file shape

```json
{
  "prompt_hash": "ab12cd34ef56",
  "prompt_preview": "first 200 chars of the prompt for human grep",
  "args": ["claude", "-p", "...", "--max-turns", "3", ...],
  "stdout": "DECISION: EXTENDED\\n",
  "stderr": "",
  "returncode": 0
}
```

``args`` is recorded for debugging only - replay does not match on it.
The hash of the prompt is the sole match key.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess as _real_subprocess
from types import SimpleNamespace
from typing import Any

CASSETTE_DIR = Path(__file__).resolve().parent / "cassettes" / "claude_p"


def _hash_prompt(prompt: str) -> str:
    """SHA-256 of the prompt text, first 12 hex chars. Stable across runs."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


def _extract_prompt(args: list[str]) -> str:
    """Pull the prompt out of a `claude -p <prompt>` arg list."""
    for flag in ("-p", "--print"):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return str(args[idx + 1])
    raise ValueError(
        "claude -p cassette: subprocess args lack -p/--print followed by a prompt"
    )


class ClaudePCassette:
    """Drop-in replacement for ``subprocess.run`` that replays cassettes.

    Use via ``monkeypatch.setattr(<module>.subprocess, "run", cassette)``.
    """

    def __init__(self, record: bool = False) -> None:
        self.record = record
        if record:
            CASSETTE_DIR.mkdir(parents=True, exist_ok=True)

    def __call__(self, args: list[str], **kwargs: Any) -> SimpleNamespace:
        prompt = _extract_prompt(args)
        key = _hash_prompt(prompt)
        path = CASSETTE_DIR / f"{key}.json"

        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return SimpleNamespace(
                stdout=data.get("stdout", ""),
                stderr=data.get("stderr", ""),
                returncode=data.get("returncode", 0),
                args=args,
            )

        if not self.record:
            raise RuntimeError(
                f"claude -p cassette missing for prompt hash {key} "
                f"(expected at {path.relative_to(Path.cwd())}). "
                f"Re-run with `pytest --record-cassettes` to record; "
                f"requires the `claude` binary."
            )

        # Record mode: actually call claude, capture, persist.
        result = _real_subprocess.run(  # noqa: S603 - intentional shell-less spawn
            args,
            **kwargs,
        )
        path.write_text(
            json.dumps(
                {
                    "prompt_hash": key,
                    "prompt_preview": prompt[:200],
                    "args": list(args),
                    "stdout": result.stdout if isinstance(result.stdout, str) else "",
                    "stderr": result.stderr if isinstance(result.stderr, str) else "",
                    "returncode": result.returncode,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return result


def install_cassette_for_test(monkeypatch, module, cassette: ClaudePCassette) -> None:
    """Convenience: replace ``module.subprocess.run`` with the cassette.

    Most spawn sites import ``subprocess`` at module level and call
    ``subprocess.run`` directly; this helper handles the patch in one
    line so individual tests stay terse.
    """
    monkeypatch.setattr(module.subprocess, "run", cassette)
