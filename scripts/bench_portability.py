#!/usr/bin/env python
"""Benchmark: portability across embedding models.

Runs Liu ``ground_many`` twice, once with the default
``intfloat/multilingual-e5-small`` and once with
``sentence-transformers/paraphrase-multilingual-mpnet-base-v2``, using the
percentile-based semantic threshold (H3) for both. Compares match types
per claim. Emits ``1`` on full agreement, else ``0``.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from stellars_claude_code_plugins.document_processing.grounding import ground_many

CLAIMS_PATH = Path("/tmp/grounding-demo/liu_claims.json")
SOURCE_PATH = Path("/tmp/grounding-demo/liu2023.txt")

MODEL_A = "intfloat/multilingual-e5-small"
MODEL_B = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


def _run(model_name: str, claims: list[str], source_pair: tuple[str, str]):
    from stellars_claude_code_plugins.document_processing.semantic import (
        SemanticGrounder,
        is_available,
    )

    if not is_available():
        raise RuntimeError(
            "semantic extras missing; benchmark requires them. Run `make requirements`."
        )
    grounder = SemanticGrounder(
        model_name=model_name,
        device="cpu",
        cache_dir=".stellars-plugins/cache",
    )
    return ground_many(
        claims,
        [source_pair],
        semantic_grounder=grounder,
        semantic_threshold_percentile=0.02,
    )


def main() -> int:
    if not CLAIMS_PATH.is_file() or not SOURCE_PATH.is_file():
        print("ERROR: Liu fixtures missing", file=sys.stderr)
        return 2

    claims_raw = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    claims = [c["claim"] for c in claims_raw]
    source_text = SOURCE_PATH.read_text(encoding="utf-8", errors="replace")
    source_pair = (str(SOURCE_PATH), source_text)

    a = _run(MODEL_A, claims, source_pair)
    b = _run(MODEL_B, claims, source_pair)

    all_match = all(ma.match_type == mb.match_type for ma, mb in zip(a, b))
    print("1" if all_match else "0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
