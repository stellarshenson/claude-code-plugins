"""Build the combined grounding evaluation dataset -> data/processed/.

Unions the three evaluation corpora into one parquet with the full HIGH-tier
lexical feature set and the shipped manifold probability per row, so batch-level
threshold experiments (max-gap / Jenks) run on precomputed columns:

- private_rag - 2,752 verified gold claims (parquet, gitignored client data)
- vitaminc    - 800 dev claims (HF tals/vitaminc, SUPPORTS/REFUTES balanced)
- articles    - 42 Liu/Han/Ye fixture claims (references/grounding-results/data)

Importable module (multiprocessing workers need top-level functions); driven by
notebooks/03-kj-H12-maxgap-batch-experiment.ipynb. Output is gitignored - the parquet
embeds private client text and must never be committed.
"""

from __future__ import annotations

import json
from multiprocessing import Pool, cpu_count
from pathlib import Path

from stellars_claude_code_plugins.document_processing import calibration as C
from stellars_claude_code_plugins.document_processing import lexical as L

REPO = Path(__file__).resolve().parents[2]
PRIVATE_RAG = Path(__file__).parent / "private-rag-forensics/gold/golden_grounding_evidence_verified.parquet"
ARTICLES = REPO / "references/grounding-results/data"
OUT_PARQUET = REPO / "data/processed/grounding_combined.parquet"
OUT_SIDECAR = REPO / "data/processed/grounding_combined.md"

ARTICLE_SOURCES = {"liu": "liu2023.txt", "han": "han2024.txt", "ye": "ye2024.txt"}


def _extract_one(args: tuple) -> dict:
    """Worker: HIGH-tier features for one row dict; passes identity through."""
    row = args
    f = L.extract_lexical_features(
        str(row["claim"]), [str(row["source_text"])], effort="high", det_lang=None
    )
    out = dict(row)
    out.update(f)
    return out


def _private_rag_rows() -> list[dict]:
    import pandas as pd

    df = pd.read_parquet(PRIVATE_RAG)
    return [
        {
            "corpus": "private_rag",
            "claim_id": f"pr{i:04d}",
            "group_id": str(r["trace_id"]),
            "claim": r["claim"],
            "source_text": r["source_text"],
            "label": int(r["label"]),
            "lang": r.get("lang") or "",
        }
        for i, r in enumerate(df.to_dict("records"))
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
        out.append(
            {
                "corpus": "vitaminc",
                "claim_id": f"vc{len(out):04d}",
                "group_id": "vitaminc",
                "claim": rec["claim"],
                "source_text": rec["evidence"],
                "label": 1 if nat == "SUPPORTS" else 0,
                "lang": "en",
            }
        )
    return out


def _article_rows() -> list[dict]:
    out = []
    for name, src_file in ARTICLE_SOURCES.items():
        claims = json.loads((ARTICLES / f"{name}_claims.json").read_text(encoding="utf-8"))
        source = (ARTICLES / src_file).read_text(encoding="utf-8", errors="replace")
        rejected = {claims[-2]["id"], claims[-1]["id"]}  # *13, *14 fabrications
        for c in claims:
            out.append(
                {
                    "corpus": "articles",
                    "claim_id": c["id"],
                    "group_id": name,
                    "claim": c["claim"],
                    "source_text": source,
                    "label": 0 if c["id"] in rejected else 1,
                    "lang": "en",
                }
            )
    return out


def shipped_manifold(effort: str = "high") -> L.LexicalVerdict:
    """The shipped frozen-weight manifold from the bundled config."""
    block = C.load_calibration_from_config()
    lv = L.LexicalVerdict.from_config(block, effort)
    if lv is None:
        raise RuntimeError(f"no shipped {effort} manifold in bundled config")
    return lv


def build(refresh: bool = False, workers: int | None = None) -> "pd.DataFrame":  # noqa: F821
    """Build (or load cached) combined parquet with features + p_high."""
    import pandas as pd

    if OUT_PARQUET.is_file() and not refresh:
        return pd.read_parquet(OUT_PARQUET)

    rows = _private_rag_rows() + _vitaminc_rows() + _article_rows()
    n = workers or min(24, cpu_count())
    with Pool(n) as pool:
        feat_rows = pool.map(_extract_one, rows, chunksize=16)

    lv = shipped_manifold("high")
    for r in feat_rows:
        r["p_high"] = lv.predict_proba(r)

    df = pd.DataFrame(feat_rows)
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    _write_sidecar(df, lv)
    return df


def _write_sidecar(df, lv) -> None:
    import datetime

    by_corpus = df.groupby("corpus")["label"].agg(["count", "sum"])
    lines = [
        "# grounding_combined.parquet",
        "",
        "Combined grounding evaluation dataset - one row per (claim, source) pair with",
        "the full HIGH-tier lexical feature set and the shipped manifold probability.",
        "Built by `experiments/grounding/build_combined.py`; driven from",
        "`notebooks/03-kj-H12-maxgap-batch-experiment.ipynb`. GITIGNORED - embeds private",
        "client text, never commit.",
        "",
        f"- **Built**: {datetime.date.today().isoformat()}, shipped high manifold threshold {lv.threshold}",
        f"- **Rows**: {len(df)}",
    ]
    for corpus, r in by_corpus.iterrows():
        lines.append(
            f"- **{corpus}**: {int(r['count'])} rows, {int(r['sum'])} supported / "
            f"{int(r['count'] - r['sum'])} hallucination"
        )
    lines += [
        "",
        "## Columns",
        "",
        "- `corpus` - private_rag | vitaminc | articles (the batch key)",
        "- `claim_id`, `group_id` - identity; group_id = trace_id / 'vitaminc' / article name",
        "- `claim`, `source_text`, `label` (1 supported / 0 hallucination), `lang`",
        f"- HIGH-tier features: {', '.join(L.TIER_FEATURES['high'])}",
        "- `p_high` - shipped high-manifold probability (frozen weights, bundled config)",
        "",
        "Rebuild: `build_combined.build(refresh=True)` (~6 min on 24 workers).",
    ]
    OUT_SIDECAR.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    frame = build(refresh=True)
    print(frame.groupby("corpus").size())
    print(f"wrote {OUT_PARQUET}")
