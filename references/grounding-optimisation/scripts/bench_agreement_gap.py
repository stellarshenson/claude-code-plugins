#!/usr/bin/env python
"""Benchmark: agreement-score gap between real paraphrases (l09, l10) and
fabrications (l13, l14) on the Liu fixture.

Gap = ``min(agreement_score[l09], agreement_score[l10])
      - max(agreement_score[l13], agreement_score[l14])``

Returns ``min(gap / 0.10, 1.0)`` on stdout.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from stellars_claude_code_plugins.document_processing.grounding import ground_many

CLAIMS_PATH = Path("/tmp/grounding-demo/liu_claims.json")
SOURCE_PATH = Path("/tmp/grounding-demo/liu2023.txt")


def main() -> int:
    if not CLAIMS_PATH.is_file() or not SOURCE_PATH.is_file():
        print("ERROR: Liu fixtures missing at /tmp/grounding-demo/", file=sys.stderr)
        return 2

    claims_raw = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    claims = [c["claim"] for c in claims_raw]
    ids = [c["id"] for c in claims_raw]
    source_text = SOURCE_PATH.read_text(encoding="utf-8", errors="replace")

    from stellars_claude_code_plugins.document_processing.semantic import (
        SemanticGrounder,
        is_available,
    )

    if not is_available():
        print(
            "ERROR: semantic extras missing; benchmark requires them. "
            "Run `make requirements`.",
            file=sys.stderr,
        )
        return 3

    grounder = SemanticGrounder(
        model_name=os.environ.get("BENCH_MODEL", "intfloat/multilingual-e5-small"),
        device="cpu",
        cache_dir=".stellars-plugins/cache",
    )

    matches = ground_many(
        claims,
        [(str(SOURCE_PATH), source_text)],
        semantic_grounder=grounder,
    )

    by_id = dict(zip(ids, matches))
    real = [by_id[k].agreement_score for k in ("l09", "l10") if k in by_id]
    fake = [by_id[k].agreement_score for k in ("l13", "l14") if k in by_id]

    if not real or not fake:
        print("0.0")
        return 1

    gap = min(real) - max(fake)
    attainment = max(0.0, min(1.0, gap / 0.10))
    print(f"{attainment:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
