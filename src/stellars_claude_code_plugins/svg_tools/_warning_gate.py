"""Stop-and-think warning-acknowledgement gate shared by every svg-tool CLI.

Every warning a tool emits blocks its primary output until the caller
acknowledges it with a deterministic token and a terse reason. The token is
``hash(canonical_input, warning_text)`` so reruns with the same input produce
the same token and no server-side memory is needed.

Workflow from the caller's point of view:

1. Run the tool. If any warning fires, the tool prints a BLOCKED block with
   one token per warning and exits 2.
2. Fix the input so the warning no longer fires, OR rerun with
   ``--ack-warning TOKEN='reason'`` for each warning. Reasoning is mandatory -
   acks without a reason are rejected, otherwise the mechanism degrades into
   a silent bypass.
3. Tool prints the acked list (audit trail on stderr) and proceeds to output.

There is no bulk override. One ``--ack-warning`` flag per warning; each ack
includes its own reason. The token changes whenever the input OR the warning
text changes, so a stale ack cannot silently pass a different warning.

Public API (four functions):

- ``compute_warning_token(input_key, warning_text)`` - deterministic token.
- ``parse_ack_warning_args(ack_values)`` - TOKEN=reason parser.
- ``enforce_warning_acks(warnings, argv, ack_values)`` - the gate itself.
- ``add_ack_warning_arg(parser)`` - adds the ``--ack-warning`` argparse flag
  with standardised help text so every tool has identical UX.
"""

from __future__ import annotations

import hashlib
import sys
from typing import Iterable, Sequence

_ACK_WARNING_HELP = (
    "Acknowledge a warning (stop-and-think gate). Every warning the tool "
    "emits blocks output until it is consciously acknowledged with this "
    "flag. Format: TOKEN=reason (reasoning MUST be terse - one short "
    "clause). Tokens are deterministic for the invocation - rerun to see "
    "them. One --ack-warning flag per warning - there is no bulk override."
)


def add_ack_warning_arg(parser) -> None:
    """Register the standard ``--ack-warning`` flag on an argparse parser.

    Every gated tool calls this instead of defining its own flag, so the
    help text and semantics stay identical across the whole toolbox.
    """
    parser.add_argument(
        "--ack-warning",
        action="append",
        default=[],
        metavar="TOKEN=REASON",
        help=_ACK_WARNING_HELP,
    )


def _canonical_input_key(argv: Sequence[str]) -> str:
    """Hash-stable input identity for a CLI invocation.

    Excludes ``--ack-warning`` arguments so adding acks does not change the
    warning tokens. Normalises whitespace inside each arg so minor quoting
    differences do not flip tokens.
    """
    filtered = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--ack-warning":
            i += 2  # skip flag + value
            continue
        if a.startswith("--ack-warning="):
            i += 1
            continue
        filtered.append(" ".join(str(a).split()))
        i += 1
    return "\0".join(filtered)


def compute_warning_token(input_key: str, warning_text: str) -> str:
    """Deterministic ignore token for a ``(input_key, warning_text)`` pair."""
    h = hashlib.sha256(f"{input_key}\0||\0{warning_text}".encode("utf-8")).hexdigest()
    return f"W-{h[:8]}"


def parse_ack_warning_args(ack_values: Iterable[str] | None) -> dict[str, str]:
    """Parse ``--ack-warning TOKEN=reason`` args into ``{token: reason}``.

    Accepts ``TOKEN=reason`` or ``TOKEN:reason``. Empty reasoning is rejected
    - the point of the mechanism is conscious acknowledgement, not a bypass.
    Raises ``ValueError`` with a guidance message on malformed input.
    """
    result: dict[str, str] = {}
    for val in ack_values or []:
        # Pick the earliest of '=' / ':' as the separator so reasons can
        # legitimately contain the other character.
        sep_idx = -1
        for sep in ("=", ":"):
            idx = val.find(sep)
            if idx > 0 and (sep_idx == -1 or idx < sep_idx):
                sep_idx = idx
        if sep_idx <= 0:
            raise ValueError(
                f"--ack-warning {val!r} invalid: expected TOKEN=reason "
                f"(or TOKEN:reason). Reasoning is mandatory - acks without "
                f"a 'why' defeat the point of the mechanism."
            )
        tok = val[:sep_idx].strip()
        reason = val[sep_idx + 1 :].strip()
        if not tok or not reason:
            raise ValueError(
                f"--ack-warning {val!r} invalid: both TOKEN and reason must be non-empty."
            )
        result[tok] = reason
    return result


def enforce_warning_acks(
    warnings: Iterable[str],
    argv: Sequence[str],
    ack_values: Iterable[str] | None,
) -> None:
    """Gate: exit 2 unless every warning has a matching ack with reasoning.

    Returns normally when all warnings are acked (or none fired). Prints an
    acknowledgement summary to stderr as an audit trail.

    Tokens are deterministic ``hash(canonical_input, warning_text)``, so reruns
    with the same input produce the same tokens - the agent can safely paste
    the ack flags back without guessing.
    """
    # Dedup preserving order - some code paths append the same hint twice.
    seen: set[str] = set()
    uniq: list[str] = []
    for w in warnings or []:
        if w not in seen:
            uniq.append(w)
            seen.add(w)

    try:
        acks = parse_ack_warning_args(ack_values)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    if not uniq and not acks:
        return

    input_key = _canonical_input_key(argv)
    warning_tokens = [(compute_warning_token(input_key, w), w) for w in uniq]
    provided = set(acks.keys())
    expected = {tok for tok, _ in warning_tokens}

    unacked = [(tok, w) for tok, w in warning_tokens if tok not in provided]
    acked = [(tok, w, acks[tok]) for tok, w in warning_tokens if tok in provided]
    dead_acks = sorted(provided - expected)

    if unacked:
        print("", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
        print(
            f"BLOCKED: {len(unacked)} unacknowledged warning(s).",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print(
            "Every warning must be consciously acknowledged with a reasoning.",
            file=sys.stderr,
        )
        print(
            "Fix the input so the warning no longer fires, OR rerun the tool",
            file=sys.stderr,
        )
        print(
            "passing --ack-warning TOKEN='reason' for each warning below.",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print(
            "Tokens are deterministic for this input; reruns reproduce them.",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        for tok, w in unacked:
            print(f"  [{tok}]  {w}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Paste one of these per warning (with a real reason):", file=sys.stderr)
        for tok, _w in unacked:
            print(f"  --ack-warning {tok}='<why this is safe to ignore>'", file=sys.stderr)
        if dead_acks:
            print("", file=sys.stderr)
            print(
                f"Also: {len(dead_acks)} --ack-warning token(s) matched no "
                f"current warning (stale or mistyped):",
                file=sys.stderr,
            )
            for tok in dead_acks:
                print(f"  [{tok}] = {acks[tok]!r}", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
        sys.exit(2)

    # All acked - print audit trail to stderr.
    if acked:
        print("", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
        print(
            f"Acknowledged {len(acked)} warning(s) with reasoning:",
            file=sys.stderr,
        )
        for tok, w, reason in acked:
            print(f"  [{tok}] {w}", file=sys.stderr)
            print(f"           reason: {reason}", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
    if dead_acks:
        print("", file=sys.stderr)
        print(
            f"NOTE: {len(dead_acks)} --ack-warning token(s) matched no current warning:",
            file=sys.stderr,
        )
        for tok in dead_acks:
            print(f"  [{tok}] = {acks[tok]!r}", file=sys.stderr)
