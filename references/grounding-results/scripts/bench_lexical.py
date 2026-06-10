#!/usr/bin/env python
"""Benchmark: lexical grounder on the Liu / Han / Ye claim fixtures.

Runs ``ground_batch`` under the bundled default config (lexical mode,
``lexical_effort`` as shipped - high) over each corpus and scores the
verdict against the archived expectations:

- claims 01-12 per corpus: expect CONFIRMED (match_type is a layer label)
- claims 13-14 per corpus: expect REJECTED (match_type none/contradicted)

Scoring: per-corpus macro-F1 over the two classes (F1 of CONFIRMED
and F1 of REJECTED, averaged), with accuracy shown for reference.
Emits a table on stderr and the mean macro-F1 across the three corpora
as a single float in ``[0, 1]`` on stdout.

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


def _f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def main() -> int:
    macro_f1s = []
    print(
        f"{'corpus':<6} {'macroF1':>8} {'f1_conf':>8} {'f1_rej':>7} {'acc':>6}  errors",
        file=sys.stderr,
    )
    for name, src_file in CORPORA.items():
        claims_raw = json.loads((DATA / f"{name}_claims.json").read_text(encoding="utf-8"))
        ids = [c["id"] for c in claims_raw]
        claims = [c["claim"] for c in claims_raw]
        source_text = (DATA / src_file).read_text(encoding="utf-8", errors="replace")
        expected_rejected = {ids[-2], ids[-1]}  # *13, *14 are fabrications

        matches = ground_batch(claims, [(src_file, source_text)])

        tp_c = fp_c = fn_c = tp_r = 0
        errors = []
        for cid, m in zip(ids, matches):
            confirmed = m.match_type in CONFIRMED_TYPES
            if cid in expected_rejected:
                if confirmed:
                    fp_c += 1
                    errors.append(f"{cid}:{m.match_type}")
                else:
                    tp_r += 1
            else:
                if confirmed:
                    tp_c += 1
                else:
                    fn_c += 1
                    errors.append(f"{cid}:{m.match_type}")
        # rejected-class FP/FN mirror the confirmed-class FN/FP
        f1_conf = _f1(tp_c, fp_c, fn_c)
        f1_rej = _f1(tp_r, fn_c, fp_c)
        macro = (f1_conf + f1_rej) / 2
        acc = (tp_c + tp_r) / len(ids)
        macro_f1s.append(macro)
        print(
            f"{name:<6} {macro:>8.4f} {f1_conf:>8.4f} {f1_rej:>7.4f} {acc:>6.4f}  {', '.join(errors) or '-'}",
            file=sys.stderr,
        )

    print(f"{sum(macro_f1s) / len(macro_f1s):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
