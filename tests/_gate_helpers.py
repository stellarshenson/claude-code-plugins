"""Shared helper for tests that invoke gated svg-tools CLIs.

The stop-and-think warning-ack gate (see ``svg_tools/_warning_gate.py``) exits
2 on any warning and lists deterministic tokens in stderr. Tests that only
care about a CLI's primary output - not the gate's own contract - use
``run_gated_cli`` below to auto-discover tokens and rerun with
``--ack-warning TOKEN=reason`` per warning.

The explicit gate-contract tests (``TestWarningAckGate``) do NOT use this
helper - they drive the gate directly so the contract under test stays
visible.
"""

from __future__ import annotations

import re
import subprocess

_TOKEN_RE = re.compile(r"W-[0-9a-f]{8}")


def run_gated_cli(
    argv_prefix: list[str],
    *args: str,
    reason: str = "test fixture",
    extra_ack_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a gated CLI. If the gate blocks with exit 2, discover the tokens
    from the BLOCKED block in stderr, rerun with
    ``--ack-warning TOKEN=<reason>`` per unique token, and return the
    second invocation.

    Parameters
    ----------
    argv_prefix
        Fixed command prefix, e.g.
        ``[sys.executable, str(TOOLS_DIR / "calc_connector.py")]`` or
        ``[sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli", "connector"]``.
    args
        Additional CLI arguments passed after ``argv_prefix``.
    reason
        Reasoning string used for every auto-ack. Tests passing this helper
        are asserting that the CLI path works; the reason is a stable
        placeholder, not under test.
    extra_ack_args
        Optional extra argv entries to include on the second invocation
        (e.g. to assert behaviour when acks are combined with other flags).

    Returns
    -------
    CompletedProcess
        Either the original invocation (gate did not fire) or the rerun
        with all tokens acked.
    """
    cmd = [*argv_prefix, *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 2 or "BLOCKED" not in proc.stderr:
        return proc
    tokens: list[str] = []
    seen: set[str] = set()
    for tok in _TOKEN_RE.findall(proc.stderr):
        if tok not in seen:
            tokens.append(tok)
            seen.add(tok)
    ack_flags: list[str] = []
    for tok in tokens:
        ack_flags += ["--ack-warning", f"{tok}={reason}"]
    if extra_ack_args:
        ack_flags += list(extra_ack_args)
    return subprocess.run([*cmd, *ack_flags], capture_output=True, text=True)
