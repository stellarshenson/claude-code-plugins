"""LLM-as-judge competition: regex clause-split vs SaT for atomic-claim segmentation.

Qualitative companion to the macro-F1 competition (lab.py seg). For each multi-fact
claim, claude -p judges which segmentation is the better atomic decomposition,
A/B order randomised to remove position bias. Aggregate-only output.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter

sys.path.insert(0, ".")
import lab  # noqa: E402
import mt  # noqa: E402

_PROMPT = """You are judging two ways to split a claim into atomic, independently checkable \
sub-claims for fact-checking against source documents.

Claim: "{claim}"

Method A units: {a}
Method B units: {b}

Which split is better for verifying each fact independently? Judge on: grammaticality, \
no dropped or garbled words, and whether each unit is a self-contained checkable proposition.
Reply with ONLY "A", "B", or "tie" on the first line, then one short reason."""


def _judge(claim, a_units, b_units) -> str:
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("ANTHROPIC") or k.startswith("CLAUDE"))}
    p = _PROMPT.format(claim=claim, a=a_units, b=b_units)
    r = subprocess.run(["claude", "-p", p], capture_output=True, text=True, timeout=150, env=env)
    line = next((ln.strip() for ln in r.stdout.splitlines() if ln.strip()), "")
    v = line.upper()
    return "A" if v.startswith("A") else "B" if v.startswith("B") else "tie"


def main(n: int = 16) -> None:
    sat = mt._sat()
    items = []
    for rec in lab.H.load_gold():
        reg = lab.split_clauses(rec.claim)
        st = sat.split(rec.claim) or [rec.claim]
        if max(len(reg), len(st)) >= 2 and reg != st:
            items.append((rec.claim, reg, st))
        if len(items) >= n:
            break

    tally = Counter()
    for i, (claim, reg, st) in enumerate(items):
        regex_is_a = (i % 2 == 0)
        a, b = (reg, st) if regex_is_a else (st, reg)
        v = _judge(claim, a, b)
        if v == "tie":
            w = "tie"
        elif v == "A":
            w = "regex" if regex_is_a else "sat"
        else:
            w = "sat" if regex_is_a else "regex"
        tally[w] += 1
        print(f"[{w:5}] {claim[:70]}")
    print(f"\nLLM-judge tally over {len(items)} multi-fact claims: {dict(tally)}")


if __name__ == "__main__":
    main()
