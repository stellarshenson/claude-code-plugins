"""Real-data grounding validation on a PUBLIC dataset (VitaminC, FEVER-derived).

Closes the real-data validation gate with a public, reproducible corpus instead
of a private one. VitaminC ships (claim, evidence_text, label) inline, fetched
via huggingface_hub (already a core dep) - no `datasets` library needed. Labels
map onto our deterministic verdict:

    SUPPORTS         -> grounded     (exact / fuzzy / bm25)
    REFUTES          -> contradicted
    NOT ENOUGH INFO  -> unconfirmed  (none)

Deterministic engine only (VitaminC is monolingual English); no semantic model.
This measures the SHIPPED grounding against real human-labelled claims with
genuine contradictions and genuinely-unsupported claims.

Run: uv run python notebooks/validate_public_grounding.py [N]
"""

from __future__ import annotations

import collections
import json
import sys
import warnings

from huggingface_hub import hf_hub_download

from stellars_claude_code_plugins.document_processing.grounding import ground

warnings.filterwarnings("ignore")

_GOLD = {"SUPPORTS": "grounded", "REFUTES": "contradicted", "NOT ENOUGH INFO": "unconfirmed"}
_BUCKETS = ["grounded", "contradicted", "unconfirmed"]


def _pred_bucket(match_type: str) -> str:
    if match_type == "contradicted":
        return "contradicted"
    if match_type in ("exact", "fuzzy", "bm25", "semantic"):
        return "grounded"
    return "unconfirmed"


def main(n: int = 600, engine: str = "lexical") -> int:
    path = hf_hub_download("tals/vitaminc", "dev.jsonl", repo_type="dataset")
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]

    # Balanced, deterministic slice across the three labels.
    by_label: dict[str, list] = {k: [] for k in _GOLD}
    for r in rows:
        lab = r.get("label")
        if lab in by_label and r.get("claim") and r.get("evidence"):
            by_label[lab].append(r)
    per = n // 3
    sample = by_label["SUPPORTS"][:per] + by_label["REFUTES"][:per] + by_label["NOT ENOUGH INFO"][:per]

    nli = None
    if engine == "nli":
        from stellars_claude_code_plugins.document_processing.nli import NLIGrounder

        nli = NLIGrounder()  # multilingual cross-encoder, ONNX, cached after first use

    # Both engines run through the integrated ground() pipeline; nli mode just
    # passes the NLI grounder, so this validates the real grounding path.
    conf: collections.Counter = collections.Counter()
    for r in sample:
        m = ground(r["claim"], [(str(r.get("page", "src")), r["evidence"])], nli_grounder=nli)
        conf[(_GOLD[r["label"]], _pred_bucket(m.match_type))] += 1

    print(f"VitaminC dev - n={len(sample)} ({per} per label), {engine} engine\n")
    header = f"{'gold \\ pred':16}" + "".join(f"{b:>14}" for b in _BUCKETS)
    print(header)
    for g in _BUCKETS:
        print(f"{g:16}" + "".join(f"{conf[(g, p)]:>14}" for p in _BUCKETS))

    tp = conf[("grounded", "grounded")]
    fp = sum(conf[(g, "grounded")] for g in _BUCKETS if g != "grounded")
    fn = sum(conf[("grounded", p)] for p in _BUCKETS if p != "grounded")
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0

    cr_tp = conf[("contradicted", "contradicted")]
    cr_fn = sum(conf[("contradicted", p)] for p in _BUCKETS if p != "contradicted")
    cr = cr_tp / (cr_tp + cr_fn) if (cr_tp + cr_fn) else 0.0

    nei_correct = conf[("unconfirmed", "unconfirmed")]
    nei_total = sum(conf[("unconfirmed", p)] for p in _BUCKETS)
    nei_rate = nei_correct / nei_total if nei_total else 0.0

    print(f"\nCONFIRMED  precision={prec:.3f}  recall={rec:.3f}")
    print(f"contradiction recall (REFUTES caught) = {cr:.3f}")
    print(f"NEI correctly left unconfirmed         = {nei_rate:.3f}")
    return 0


if __name__ == "__main__":
    _n = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    _engine = sys.argv[2] if len(sys.argv) > 2 else "lexical"
    raise SystemExit(main(_n, _engine))
