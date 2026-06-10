#!/usr/bin/env python
"""Benchmark: numeric + entity mismatch recall.

Walks the 10-seed fixture in ``tests/fixtures/numeric_mismatch/``, runs
``ground`` on each claim against its paired source, counts how many land
with ``match_type == "contradicted"``. Emits ``count / 10`` on stdout.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from stellars_claude_code_plugins.document_processing.grounding import ground

FIXTURE_DIR = Path("tests/fixtures/numeric_mismatch")


def main() -> int:
    claims_json = FIXTURE_DIR / "claims.json"
    if not claims_json.is_file():
        print("ERROR: numeric_mismatch fixture not found", file=sys.stderr)
        return 2

    items = json.loads(claims_json.read_text(encoding="utf-8"))
    correct = 0
    total = len(items)
    for item in items:
        src_path = FIXTURE_DIR / item["source"]
        if not src_path.is_file():
            print(f"MISSING source: {src_path}", file=sys.stderr)
            continue
        source_text = src_path.read_text(encoding="utf-8", errors="replace")
        m = ground(item["claim"], [(str(src_path), source_text)])
        if m.match_type == item["expected"]:
            correct += 1
        else:
            print(
                f"MISS {item['id']}: expected {item['expected']} got {m.match_type}"
                f" | num_mm={m.numeric_mismatches} ent_mm={m.entity_mismatches}",
                file=sys.stderr,
            )

    print(f"{correct / total:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
