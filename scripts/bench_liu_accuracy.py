#!/usr/bin/env python
"""Benchmark: Liu 14-claim accuracy.

Runs ``ground_many`` over Liu claims fixture and compares ``match_type``
to expected classification:

- l01-l08, l11-l12: expect CONFIRMED (any of exact/fuzzy/bm25/semantic)
- l09-l10: expect CONFIRMED (real distant paraphrases)
- l13-l14: expect UNCONFIRMED or CONTRADICTED (fabrications)

Emits a single float in ``[0, 1]`` = correct / 14 on stdout.
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

EXPECTED_CONFIRMED = {
    "l01", "l02", "l03", "l04", "l05", "l06", "l07", "l08",
    "l09", "l10", "l11", "l12",
}
EXPECTED_REJECTED = {"l13", "l14"}
CONFIRMED_TYPES = {"exact", "fuzzy", "bm25", "semantic"}
REJECTED_TYPES = {"none", "contradicted"}


def main() -> int:
    if not CLAIMS_PATH.is_file() or not SOURCE_PATH.is_file():
        print("ERROR: Liu fixtures missing at /tmp/grounding-demo/", file=sys.stderr)
        return 2

    claims_raw = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    claims = [c["claim"] for c in claims_raw]
    ids = [c["id"] for c in claims_raw]
    source_text = SOURCE_PATH.read_text(encoding="utf-8", errors="replace")

    # Semantic grounder: benchmark REQUIRES semantic; fail loud if missing
    from stellars_claude_code_plugins.document_processing.semantic import (
        SemanticGrounder,
        is_available,
    )

    if not is_available():
        print(
            "ERROR: semantic extras missing; benchmark requires them. "
            "Run `make requirements` (Makefile installs all extras).",
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
        semantic_threshold_percentile=0.02,
    )

    correct = 0
    for cid, m in zip(ids, matches):
        if cid in EXPECTED_CONFIRMED and m.match_type in CONFIRMED_TYPES:
            correct += 1
        elif cid in EXPECTED_REJECTED and m.match_type in REJECTED_TYPES:
            correct += 1

    print(f"{correct / len(ids):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
