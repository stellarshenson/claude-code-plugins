"""Round 8 mechanism experiments: diagnostics + candidate mechanisms.

Three pre-registered hypotheses (see HYPOTHESIS.md "Round 8"):
  A1 - SaT multilingual claim extraction (front door)
  A2 - atomic-fact scoring through the frozen manifold
  H-B - alignment-profile features (r1_union / dispersion / max_run)
  H-C - negation-scope mismatch feature

Stage 1 diagnostics run first; a hypothesis whose gate fails is closed
without building its mechanism. Importable module (multiprocessing needs
top-level functions); the notebook drives it.

Private data: the gold parquet and the trace cache live outside the repo
or in the gitignored forensics stash. The trace-cache location is read
from ``private-rag-forensics/trace_cache.path`` (gitignored) so no client
path enters tracked code.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from stellars_claude_code_plugins.document_processing.extract import (
    _looks_like_claim,
    _split_document,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FORENSICS = HERE / "private-rag-forensics"
GOLD = FORENSICS / "gold" / "golden_grounding_evidence_verified.parquet"
COMBINED = REPO / "data" / "processed" / "grounding_combined.parquet"

# trailing "### <link emoji>" references block in assistant answers
_REF_BLOCK = re.compile(r"#+\s*\U0001f517")

# high-tier manifold decision threshold (config_document_processing.yaml)
P_HIGH_THRESHOLD = 0.40

# multilingual negation cues (lifted from harness._NEG_CUES)
NEG_CUES = {
    "ikke", "ingen", "aldri", "inte", "aldrig", "pas", "non", "aucun",
    "aucune", "jamais", "nessun", "nessuna", "mai", "no", "nunca",
    "ningun", "ningún", "não", "nao", "nenhum", "not", "never",
    "cannot", "n't", "without",
}
_TOKEN_RE = re.compile(r"[\w']+")

_SAT = None


def _sat():
    global _SAT
    if _SAT is None:
        from stellars_claude_code_plugins.document_processing.sat import SaTSegmenter

        _SAT = SaTSegmenter()
    return _SAT


def is_negated(text: str) -> bool:
    return bool(set(_TOKEN_RE.findall(text.lower())) & NEG_CUES)


def _trace_cache() -> Path:
    return Path((FORENSICS / "trace_cache.path").read_text().strip())


def _answer_text(trace_id: str) -> str | None:
    f = _trace_cache() / f"{trace_id}.json"
    if not f.exists():
        return None
    tr = json.loads(f.read_text())
    raw = (tr.get("output") or {}).get("value", "") or ""
    return _REF_BLOCK.split(raw)[0] if raw else None


# --------------------------------------------------------------------------
# Stage 1 diagnostics
# --------------------------------------------------------------------------


def diag_a1() -> pd.DataFrame:
    """A1 gate: verb-gate rejection rate per sentence language on raw answers.

    Gold claims came FROM extract_claims (survivorship bias), so gold-recall
    is circular. The honest measurement: on the original answer documents,
    what fraction of length-passing candidate sentences does the English
    verb gate reject, per language? Anglocentric defect = non-English
    rejection rate far above English.
    """
    from stellars_claude_code_plugins.document_processing.lexical import _lingua_lang

    gold = pd.read_parquet(GOLD, columns=["trace_id"])
    rows, missing = [], 0
    for tid in gold["trace_id"].unique():
        prose = _answer_text(str(tid))
        if not prose:
            missing += 1
            continue
        for _line, sent in _split_document(prose):
            if len(sent) < 20:
                continue  # length gate is language-neutral; not the target
            rows.append(
                {
                    "trace_id": tid,
                    "lang": _lingua_lang(sent),
                    "sent": sent,
                    "accepted": _looks_like_claim(sent),
                }
            )
    df = pd.DataFrame(rows)
    print(f"traces: {gold['trace_id'].nunique()}, missing from cache: {missing}")
    out = (
        df.groupby("lang")
        .agg(n=("accepted", "size"), accept_rate=("accepted", "mean"))
        .sort_values("n", ascending=False)
    )
    out["reject_rate"] = 1.0 - out["accept_rate"]
    return out


def sat_sentence_count(claim: str) -> int:
    return len([s for s in _sat().split(claim) if s.strip()])


def diag_a2(corpus: str = "private_rag") -> dict:
    """A2/H-B gate: do errors concentrate in multi-sentence claims?

    Pre-registered: >=30% of errors multi-sentence AND multi-sentence error
    rate > 1.5x single-sentence, else kill.
    """
    df = pd.read_parquet(COMBINED)
    df = df[df["corpus"] == corpus].copy()
    df["pred"] = (df["p_high"] >= P_HIGH_THRESHOLD).astype(int)
    df["error"] = (df["pred"] != df["label"]).astype(int)
    df["n_sents"] = [sat_sentence_count(c) for c in df["claim"]]
    df["multi"] = df["n_sents"] >= 2

    errors = df[df["error"] == 1]
    res = {
        "corpus": corpus,
        "n": len(df),
        "n_errors": len(errors),
        "share_claims_multi": float(df["multi"].mean()),
        "share_errors_multi": float(errors["multi"].mean()) if len(errors) else 0.0,
        "err_rate_multi": float(df[df["multi"]]["error"].mean()) if df["multi"].any() else 0.0,
        "err_rate_single": float(df[~df["multi"]]["error"].mean()),
        "sent_count_distribution": df["n_sents"].value_counts().sort_index().to_dict(),
    }
    res["err_rate_ratio"] = (
        res["err_rate_multi"] / res["err_rate_single"] if res["err_rate_single"] else float("inf")
    )
    res["gate_pass"] = res["share_errors_multi"] >= 0.30 and res["err_rate_ratio"] > 1.5
    return res


def diag_c() -> dict:
    """H-C gate: negation-cue asymmetry in VitaminC errors vs non-errors.

    Pre-registered: asymmetry in >=25% of errors AND non-error asymmetry
    rate < half the error rate, else kill.
    """
    df = pd.read_parquet(COMBINED)
    df = df[df["corpus"] == "vitaminc"].copy()
    df["pred"] = (df["p_high"] >= P_HIGH_THRESHOLD).astype(int)
    df["error"] = (df["pred"] != df["label"]).astype(int)
    df["asym"] = [
        is_negated(c) != is_negated(s) for c, s in zip(df["claim"], df["source_text"])
    ]
    err, ok = df[df["error"] == 1], df[df["error"] == 0]
    res = {
        "n": len(df),
        "n_errors": len(err),
        "asym_rate_errors": float(err["asym"].mean()) if len(err) else 0.0,
        "asym_rate_non_errors": float(ok["asym"].mean()),
        # error direction context: false accepts (label 0, pred 1) vs false rejects
        "false_accepts": int(((df.label == 0) & (df.pred == 1)).sum()),
        "false_rejects": int(((df.label == 1) & (df.pred == 0)).sum()),
    }
    res["gate_pass"] = (
        res["asym_rate_errors"] >= 0.25
        and res["asym_rate_non_errors"] < res["asym_rate_errors"] / 2
    )
    return res


# --------------------------------------------------------------------------
# Stage 2: A1 mechanism - SaT extraction variants
# --------------------------------------------------------------------------


def _lang_agnostic_gate(candidate: str) -> bool:
    """Length + token-count gate, no English morphology. Drops noun-phrase
    headers ('Key Features') by token count instead of verb shape."""
    return len(candidate) >= 20 and len(_TOKEN_RE.findall(candidate)) >= 4


def _split_paragraphs(text: str) -> list[tuple[int, str]]:
    """Markdown-aware paragraph assembly (same walk as extract._split_document
    but stopping at paragraph granularity so the splitter is pluggable)."""
    from stellars_claude_code_plugins.document_processing.extract import (
        _strip_markdown_noise,
    )

    out: list[tuple[int, str]] = []
    para: list[tuple[int, str]] = []

    def flush() -> None:
        if para:
            txt = " ".join(line for _, line in para).strip()
            if txt:
                out.append((para[0][0], txt))
            para.clear()

    for idx, raw in enumerate(text.splitlines(), start=1):
        stripped = _strip_markdown_noise(raw)
        if not stripped:
            flush()
            continue
        para.append((idx, stripped))
    flush()
    return out


_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def extract_claims_variant(text: str, splitter: str, gate: str) -> list[str]:
    """Extraction variants for the A1 ablation.

    splitter: 'regex' (shipped boundary) | 'sat' (SaT OpenVINO)
    gate:     'verb' (shipped English gate) | 'agnostic' (length + tokens)
    shipped behaviour == ('regex', 'verb').
    """
    gate_fn = _looks_like_claim if gate == "verb" else _lang_agnostic_gate
    claims: list[str] = []
    for _line, para in _split_paragraphs(text):
        if splitter == "sat":
            sents = [s.strip() for s in _sat().split(para) if s.strip()]
        else:
            sents = [s.strip() for s in _SENT_SPLIT_RE.split(para) if s.strip()]
        claims.extend(s for s in sents if gate_fn(s))
    return claims


def eval_a1(fuzzy_min: float = 90.0) -> dict:
    """A1 head-to-head: shipped vs gate-only vs SaT+gate on the 639 answer docs.

    Per variant: claims/doc (inflation), per-language claim counts, and gold
    coverage (fraction of gold claims fuzzy-recovered, partial_ratio >= 90 -
    circular for shipped by construction, regression check for the others).
    """
    from rapidfuzz import fuzz

    from stellars_claude_code_plugins.document_processing.lexical import _lingua_lang

    gold = pd.read_parquet(GOLD, columns=["trace_id", "claim", "lang"])
    variants = {
        "shipped": ("regex", "verb"),
        "gate_only": ("regex", "agnostic"),
        "sat_gate": ("sat", "agnostic"),
    }
    stats = {
        v: {"n_claims": 0, "covered": 0, "gold_n": 0, "lang_counts": {}, "cov_by_lang": {}}
        for v in variants
    }
    n_docs = 0
    for tid, grp in gold.groupby("trace_id"):
        prose = _answer_text(str(tid))
        if not prose:
            continue
        n_docs += 1
        for name, (splitter, gate) in variants.items():
            claims = extract_claims_variant(prose, splitter, gate)
            s = stats[name]
            s["n_claims"] += len(claims)
            for c in claims:
                lang = _lingua_lang(c)
                s["lang_counts"][lang] = s["lang_counts"].get(lang, 0) + 1
            for gclaim, glang in zip(grp["claim"], grp["lang"]):
                hit = any(
                    fuzz.partial_ratio(str(gclaim).lower(), c.lower()) >= fuzzy_min
                    for c in claims
                )
                s["gold_n"] += 1
                s["covered"] += int(hit)
                cb = s["cov_by_lang"].setdefault(glang or "und", [0, 0])
                cb[0] += int(hit)
                cb[1] += 1
    out: dict = {"n_docs": n_docs}
    base = None
    for name, s in stats.items():
        per_doc = s["n_claims"] / n_docs if n_docs else 0.0
        if name == "shipped":
            base = per_doc
        out[name] = {
            "claims_per_doc": round(per_doc, 2),
            "inflation_vs_shipped": round(per_doc / base, 2) if base else None,
            "gold_coverage": round(s["covered"] / s["gold_n"], 4) if s["gold_n"] else None,
            "cov_by_lang": {
                k: round(a / b, 3) for k, (a, b) in sorted(s["cov_by_lang"].items())
            },
            "top_langs": dict(
                sorted(s["lang_counts"].items(), key=lambda kv: -kv[1])[:8]
            ),
        }
    return out


if __name__ == "__main__":
    import sys

    if "--eval-a1" in sys.argv:
        print("=== A1 head-to-head: shipped vs gate-only vs SaT+gate ===")
        print(json.dumps(eval_a1(), indent=2))
    else:
        print("=== A1: verb-gate rejection by language ===")
        print(diag_a1().to_string())
        print("\n=== A2/H-B: multi-sentence error concentration (private_rag) ===")
        print(json.dumps(diag_a2(), indent=2, default=str))
        print("\n=== H-C: negation asymmetry (vitaminc) ===")
        print(json.dumps(diag_c(), indent=2))
