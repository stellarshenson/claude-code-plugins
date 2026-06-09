"""Retrain the three shipped lexical manifolds on the joint private RAG + VitaminC
gold with short-source augmentation, using the SHIPPED lexical pipeline, and
write them non-destructively into config_document_processing.yaml (preserving
all comments - replaces only the trailing lexical_manifolds: block).

One-off ship tool. Run from experiments/grounding:  uv run python retrain_manifolds.py
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from stellars_claude_code_plugins.document_processing import lexical as L

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "src/stellars_claude_code_plugins/config_document_processing.yaml"
PRIVATE_RAG = Path(__file__).parent / "private-rag-forensics/gold/golden_grounding_evidence_verified.parquet"


def _extract_one(args: tuple) -> dict:
    """Worker: extract HIGH features for one (claim, source, label). HIGH is a
    superset of every tier, so one extraction feeds all three manifolds. det_lang
    is left None so lingua detects exactly as the grounder does at inference."""
    claim, source, label = args
    f = L.extract_lexical_features(str(claim), [str(source)], effort="high", det_lang=None)
    f["label"] = int(label)
    return f


def _private_rag_rows() -> list[dict]:
    import pandas as pd

    df = pd.read_parquet(PRIVATE_RAG, columns=["claim", "source_text", "label", "lang"])
    return [
        {"claim": r["claim"], "source_text": r["source_text"],
         "label": int(r["label"]), "lang": (r.get("lang") or None)}
        for r in df.to_dict("records")
    ]


def _vitaminc_rows(per_label: int = 400) -> list[dict]:
    from huggingface_hub import hf_hub_download

    p = hf_hub_download("tals/vitaminc", "dev.jsonl", repo_type="dataset")
    want = {"SUPPORTS": per_label, "REFUTES": per_label}
    out = []
    for line in open(p, encoding="utf-8"):
        rec = json.loads(line)
        nat = rec.get("label")
        if nat not in want or want[nat] <= 0:
            continue
        want[nat] -= 1
        out.append({"claim": rec["claim"], "source_text": rec["evidence"],
                    "label": 1 if nat == "SUPPORTS" else 0, "lang": "en"})
    return out


def main() -> None:
    raw = _private_rag_rows() + _vitaminc_rows()
    aug = L.short_source_augment(raw)
    rows = raw + aug
    print(f"rows: {len(raw)} gold + {len(aug)} short-source aug = {len(rows)}", flush=True)

    import os
    import time
    from multiprocessing import Pool

    # The 413-chunk char-ngram BM25 on these 45k-char sources is ~1s/row, so
    # extract in parallel across the box (independent per row, pure CPU). HIGH is a
    # superset of every tier -> one extraction per row feeds all three manifolds.
    workers = min(24, os.cpu_count() or 8)
    args = [(r["claim"], r["source_text"], r["label"]) for r in rows]
    t0 = time.time()
    with Pool(processes=workers) as pool:
        feat_rows = pool.map(_extract_one, args, chunksize=16)
    print(f"  extracted {len(feat_rows)} rows on {workers} workers [{time.time() - t0:.0f}s]", flush=True)

    manifolds = {}
    for effort in L.EFFORT_TIERS:
        manifolds[effort] = L.fit_lexical_manifold(feat_rows, effort=effort)
        m = manifolds[effort]
        print(f"  {effort}: {len(m['feature_order'])} feats, thr {m['threshold']:.2f}, "
              f"unmatched_rarity {m['weights'].get('unmatched_rarity', 0):+.2f}", flush=True)

    # Non-destructive write: keep everything up to the trailing lexical_manifolds:
    # block, replace that block (it is the last key in the file).
    text = CONFIG.read_text(encoding="utf-8")
    marker = "  lexical_manifolds:"
    head = text[: text.index(marker)]
    block = yaml.safe_dump({"lexical_manifolds": manifolds}, sort_keys=False, default_flow_style=False)
    block = "\n".join(("  " + ln if ln.strip() else ln) for ln in block.splitlines())
    CONFIG.write_text(head + block + "\n", encoding="utf-8")
    print(f"wrote {CONFIG}")


if __name__ == "__main__":
    main()
