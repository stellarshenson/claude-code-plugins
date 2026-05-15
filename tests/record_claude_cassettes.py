"""Record `claude -p` cassettes for the test suite.

NOT a pytest test - the filename intentionally lacks the `test_` prefix
so pytest does not auto-collect it. Run manually (and rarely):

    uv run python tests/record_claude_cassettes.py

Requires the `claude` binary on PATH. Records real responses for the
canonical prompts the test suite exercises and saves them to
`tests/cassettes/claude_p/<hash>.json`. Tests then replay these
cassettes via `tests/_claude_cassette.py` so CI works without the
binary.

## Why a manual recording script

CI cannot run `claude` and any "auto-record" path would let stale
responses silently regenerate. Keeping recording manual makes it an
explicit maintainer decision: re-run when prompts change, when claude's
output format drifts, or when you want to add a new scenario.

## Adding a scenario

1. Add a `record_<scenario>` function below that builds the prompt
   text and calls `spawn(prompt, model=...)`.
2. Append the function call to `main()`.
3. Run the script once, commit the new JSON.
4. Add a corresponding test in `tests/test_<area>.py` that asserts
   against the recorded response.

## Cassettes are content-addressed

Each cassette is keyed by SHA-256(prompt)[:12]. Changing the prompt
invalidates the cassette - this is intentional, since a prompt change
needs a fresh response.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

from _cassette_prompts import (  # noqa: E402
    build_pass_evaluation_prompt,
    build_standardize_padded_prompt,
    build_standardize_rationale_rich_prompt,
)

CASSETTE_DIR = REPO / "tests" / "cassettes" / "claude_p"
CASSETTE_DIR.mkdir(parents=True, exist_ok=True)


def hash_prompt(prompt: str) -> str:
    """SHA-256 of the prompt text, first 12 hex chars. Stable across runs."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


def spawn(prompt: str, model: str | None = None, timeout: int = 180) -> dict:
    """Spawn `claude -p` with the standardize/orchestrator-style flags and
    capture the response. Returns the cassette payload as a dict.
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    args = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "text",
        "--dangerously-skip-permissions",
        "--max-turns",
        "3",
        "--no-session-persistence",
    ]
    if model:
        args += ["--model", model]
    r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=timeout)
    return {
        "prompt_hash": hash_prompt(prompt),
        "prompt_preview": prompt[:200],
        "args": args,
        "stdout": r.stdout,
        "stderr": r.stderr,
        "returncode": r.returncode,
    }


def save_cassette(payload: dict, label: str) -> Path:
    """Write the cassette payload to `tests/cassettes/claude_p/<hash>.json`.
    Logs a one-line summary so the recording session is self-documenting.
    """
    path = CASSETTE_DIR / f"{payload['prompt_hash']}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    preview = payload["stdout"][:80].replace("\n", " ")
    print(
        f"[{label}] hash={payload['prompt_hash']} "
        f"stdout={len(payload['stdout'])}b first80={preview!r}"
    )
    return path


# --- Scenarios ------------------------------------------------------------
#
# Each scenario imports its prompt from `tests/_cassette_prompts.py` so the
# recording side and the test (replay) side share one source of truth.
# Drift in prompt text between recording and consumption invalidates the
# cassette hash; centralising the builders prevents it.


def record_standardize_rationale_rich() -> None:
    """200-word unmarked body with rationale segments.

    Sonnet 4 typically returns CONDENSE here (the rubric judges the
    rationale segments as not-distinct-enough for the Extended tier).
    The test consumes this cassette to verify the parser handles a
    real CONDENSE+BODY response shape end-to-end.
    """
    prompt = build_standardize_rationale_rich_prompt()
    save_cassette(spawn(prompt, model="claude-sonnet-4-20250514"), "rationale-rich")


def record_standardize_padded() -> None:
    """500-word unmarked boilerplate body -> CONDENSE."""
    prompt = build_standardize_padded_prompt()
    save_cassette(spawn(prompt, model="claude-sonnet-4-20250514"), "padded")


def record_orchestrator_pass_evaluation() -> None:
    """Minimal PASS/FAIL evaluation prompt as used by `_claude_evaluate`."""
    prompt = build_pass_evaluation_prompt()
    save_cassette(spawn(prompt), "pass-eval")


# --- Entrypoint -----------------------------------------------------------


def main() -> int:
    print(f"Cassette dir: {CASSETTE_DIR}")
    record_standardize_rationale_rich()
    record_standardize_padded()
    record_orchestrator_pass_evaluation()
    print(f"done. cassettes in {CASSETTE_DIR.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
