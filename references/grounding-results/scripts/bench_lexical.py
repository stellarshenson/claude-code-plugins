#!/usr/bin/env python
"""Benchmark: lexical grounder on the Liu / Han / Ye claim fixtures.

Runs ``ground_batch`` under the bundled default config (lexical mode,
``lexical_effort`` as shipped - high) over each corpus and scores the
verdict against the archived expectations:

- claims 01-12 per corpus: expect CONFIRMED (match_type is a layer label)
- claims 13-14 per corpus: expect REJECTED (match_type none/contradicted)

Scoring: per-corpus accuracy = correct / 14, plus confirmed-recall
(true CONFIRMED rate over 12) and rejected-recall (true REJECTED rate
over 2). Emits a table on stderr and the mean accuracy across the three
corpora as a single float in ``[0, 1]`` on stdout.

No fixtures setup needed - reads ``../data/`` relative to this script.
Requires no extras (lexical tier is core-only).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from stellars_claude_code_plugins.document_processing.grounding import ground_batch

DATA = Path(__file__).resolve().parent.parent / "data"
CORPORA = {"liu": "liu2023.txt", "han": "han2024.txt", "ye": "ye2024.txt"}
CONFIRMED_TYPES = {"exact", "fuzzy", "bm25", "semantic"}


def main() -> int:
    accuracies = []
    print(
        f"{'corpus':<6} {'acc':>6} {'conf_recall':>12} {'rej_recall':>11}  errors",
        file=sys.stderr,
    )
    for name, src_file in CORPORA.items():
        claims_raw = json.loads((DATA / f"{name}_claims.json").read_text(encoding="utf-8"))
        ids = [c["id"] for c in claims_raw]
        claims = [c["claim"] for c in claims_raw]
        source_text = (DATA / src_file).read_text(encoding="utf-8", errors="replace")
        expected_rejected = {ids[-2], ids[-1]}  # *13, *14 are fabrications

        matches = ground_batch(claims, [(src_file, source_text)])

        correct = conf_ok = rej_ok = 0
        errors = []
        for cid, m in zip(ids, matches):
            confirmed = m.match_type in CONFIRMED_TYPES
            if cid in expected_rejected:
                rej_ok += not confirmed
                correct += not confirmed
            else:
                conf_ok += confirmed
                correct += confirmed
            if (cid in expected_rejected) == confirmed:
                errors.append(f"{cid}:{m.match_type}")
        acc = correct / len(ids)
        accuracies.append(acc)
        print(
            f"{name:<6} {acc:>6.4f} {conf_ok / 12:>12.4f} {rej_ok / 2:>11.4f}  {', '.join(errors) or '-'}",
            file=sys.stderr,
        )

    print(f"{sum(accuracies) / len(accuracies):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
