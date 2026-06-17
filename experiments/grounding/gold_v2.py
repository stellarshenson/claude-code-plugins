"""Gold v2: rebuild the private RAG gold through the Round 8 (H13) extraction
front door, removing the v1 extractor's survivorship bias.

Protocol (mirrors the original golden_dataset/golden_verify flow):
  1. units  - per trace: SaT + language-agnostic gate extraction over the raw
              answer; claims fuzzy-matching a v1 gold claim (partial_ratio >= 90)
              INHERIT the verified label; the rest become judge units
  2. judge  - per-trace batched `claude -p` judging of new claims against the
              trace evidence, labels SUPPORTED / UNSUPPORTED / NOT_A_CLAIM;
              run once with --model haiku and once with --model sonnet
  3. build  - keep dual-agreed labels, assemble
              gold/golden_grounding_evidence_v2.parquet (gitignored stash);
              NOT_A_CLAIM agreements are excluded from gold but reported as the
              extraction-precision number

Run from experiments/grounding:
  uv run python gold_v2.py units
  uv run python gold_v2.py judge --model haiku   [--workers 12]
  uv run python gold_v2.py judge --model sonnet  [--workers 12]
  uv run python gold_v2.py build
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mechanisms import GOLD, _answer_text, extract_claims_variant  # noqa: E402

FORENSICS = Path(__file__).resolve().parent / "private-rag-forensics"
V2_DIR = FORENSICS / "gold" / "v2"
UNITS = V2_DIR / "units.json"
RESULTS = V2_DIR / "judge_{model}.json"
GOLD_V2 = FORENSICS / "gold" / "golden_grounding_evidence_v2.parquet"

FUZZY_MIN = 90.0

_JUDGE_PROMPT = """You are a strict grounding judge for a technical support assistant.
Evidence below is the ONLY source of truth. For each numbered claim decide:

- SUPPORTED: the evidence explicitly supports the claim (translation across languages is fine)
- UNSUPPORTED: the claim asserts something the evidence does not contain or contradicts
- NOT_A_CLAIM: the sentence is not a checkable factual assertion (greeting, offer to help,
  question, navigation/connective text, pure formatting fragment)

Evidence:
<<<EVIDENCE
{evidence}
EVIDENCE>>>

There are exactly {n} claims, numbered 1 to {n}. Judge ONLY these numbered claims,
ignore any numbering inside the evidence text.

Claims:
{claims}

Reply with ONLY a JSON array with exactly {n} objects, idx 1 to {n}, no prose:
[{{"idx": 1, "label": "SUPPORTED"}}, ...]"""


def _evidence(trace_id: str) -> str:
    """Relaxed evidence: all tool/rag span outputs of the cached trace,
    stripped of markup, deduped, joined (golden_verify's relaxed filter)."""
    import re

    cache = Path((FORENSICS / "trace_cache.path").read_text().strip())
    tr = json.loads((cache / f"{trace_id}.json").read_text())
    out, seen = [], set()
    for sp in tr.get("spans", []):
        if sp.get("type") not in ("tool", "rag"):
            continue
        o = sp.get("output")
        raw = o.get("value") if isinstance(o, dict) else o
        if not isinstance(raw, str):
            raw = json.dumps(raw) if raw else ""
        txt = re.sub(r"<[^>]+>", " ", raw)
        txt = re.sub(r"\s+", " ", txt).strip()
        if len(txt) > 80 and hash(txt) not in seen:
            seen.add(hash(txt))
            out.append(txt)
    return "\n\n".join(out)


def cmd_units() -> None:
    from rapidfuzz import fuzz

    gold = pd.read_parquet(GOLD)
    units, n_inh, n_new = [], 0, 0
    for tid, grp in gold.groupby("trace_id"):
        prose = _answer_text(str(tid))
        if not prose:
            continue
        claims = extract_claims_variant(prose, "sat", "agnostic")
        v1 = list(zip(grp["claim"], grp["label"], grp["lang"]))
        inherited, new = [], []
        for c in claims:
            best = max(
                v1, key=lambda r: fuzz.partial_ratio(str(r[0]).lower(), c.lower()), default=None
            )
            if best and fuzz.partial_ratio(str(best[0]).lower(), c.lower()) >= FUZZY_MIN:
                inherited.append({"claim": c, "label": int(best[1]), "lang": best[2]})
            else:
                new.append(c)
        n_inh += len(inherited)
        n_new += len(new)
        units.append(
            {
                "trace_id": str(tid),
                "source_text": grp["source_text"].iloc[0],
                "inherited": inherited,
                "new": new,
            }
        )
    V2_DIR.mkdir(parents=True, exist_ok=True)
    UNITS.write_text(json.dumps(units, ensure_ascii=False))
    print(f"traces {len(units)}  inherited {n_inh}  new-to-judge {n_new}")


# max claims per claude -p call - bounds the work so huge units (one trace has
# 621 extracted claims) don't time out; the unit is judged in chunks and merged
CHUNK = 25


def _judge_chunk(evidence: str, claims: list[str], model: str, env: dict) -> list[dict] | None:
    numbered = "\n".join(f"{i}. {c}" for i, c in enumerate(claims, 1))
    prompt = _JUDGE_PROMPT.format(evidence=evidence[:60000], claims=numbered, n=len(claims))
    try:
        r = subprocess.run(
            ["claude", "-p", "--model", model, prompt],
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        txt = r.stdout.strip()
        start, end = txt.find("["), txt.rfind("]")
        labels = json.loads(txt[start : end + 1])
        ok = {"SUPPORTED", "UNSUPPORTED", "NOT_A_CLAIM"}
        keep = [
            rec for rec in labels if rec.get("label") in ok and 1 <= rec.get("idx", 0) <= len(claims)
        ]
        if sorted(rec["idx"] for rec in keep) != list(range(1, len(claims) + 1)):
            return None
        return keep
    except Exception:
        return None


def _judge_one(unit: dict, model: str) -> tuple[str, list[dict] | None]:
    claims = unit["new"]
    if not claims:
        return unit["trace_id"], []
    env = {
        k: v
        for k, v in os.environ.items()
        if not (k.startswith("ANTHROPIC") or k.startswith("CLAUDE"))
    }
    evidence = _evidence(unit["trace_id"])
    merged: list[dict] = []
    for off in range(0, len(claims), CHUNK):
        sub = claims[off : off + CHUNK]
        res = _judge_chunk(evidence, sub, model, env)
        if res is None:
            return unit["trace_id"], None  # whole unit retried next pass
        merged.extend({"idx": off + r["idx"], "label": r["label"]} for r in res)
    return unit["trace_id"], merged


def cmd_judge(model: str, workers: int) -> None:
    units = json.loads(UNITS.read_text())
    out_path = Path(str(RESULTS).format(model=model))
    done: dict = json.loads(out_path.read_text()) if out_path.exists() else {}
    todo = [u for u in units if u["trace_id"] not in done and u["new"]]
    print(f"{model}: {len(todo)} units to judge ({len(done)} cached)")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_judge_one, u, model): u for u in todo}
        for i, f in enumerate(as_completed(futs), 1):
            tid, labels = f.result()
            if labels is not None:
                done[tid] = labels
            if i % 20 == 0 or i == len(todo):
                out_path.write_text(json.dumps(done))
                print(f"  {i}/{len(todo)} judged, {len(done)} stored", flush=True)
    out_path.write_text(json.dumps(done))
    failed = len(todo) - sum(1 for u in todo if u["trace_id"] in done)
    print(f"done: {len(done)} units stored, {failed} failed (re-run to retry)")


def cmd_build() -> None:
    units = json.loads(UNITS.read_text())
    haiku = json.loads(Path(str(RESULTS).format(model="haiku")).read_text())
    sonnet = json.loads(Path(str(RESULTS).format(model="sonnet")).read_text())
    from stellars_claude_code_plugins.document_processing.lexical import _lingua_lang

    rows, stats = [], {"inherited": 0, "agreed": 0, "disagreed": 0, "not_a_claim": 0, "unjudged": 0}
    for u in units:
        tid, src = u["trace_id"], u["source_text"]
        for rec in u["inherited"]:
            rows.append(
                {"claim": rec["claim"], "source_text": src, "label": rec["label"],
                 "lang": rec["lang"], "trace_id": tid, "origin": "inherited"}
            )
            stats["inherited"] += 1
        h, s = haiku.get(tid), sonnet.get(tid)
        if h is None or s is None:
            stats["unjudged"] += len(u["new"])
            continue
        hmap = {r["idx"]: r["label"] for r in h}
        smap = {r["idx"]: r["label"] for r in s}
        for i, claim in enumerate(u["new"], 1):
            hl, sl = hmap.get(i), smap.get(i)
            if hl is None or sl is None or hl != sl:
                stats["disagreed"] += 1
                continue
            if hl == "NOT_A_CLAIM":
                stats["not_a_claim"] += 1
                continue
            rows.append(
                {"claim": claim, "source_text": src, "label": 1 if hl == "SUPPORTED" else 0,
                 "lang": _lingua_lang(claim), "trace_id": tid, "origin": "judged"}
            )
            stats["agreed"] += 1
    df = pd.DataFrame(rows)
    df.to_parquet(GOLD_V2, index=False)
    new_total = stats["agreed"] + stats["not_a_claim"] + stats["disagreed"]
    print(json.dumps(stats, indent=2))
    if new_total:
        print(f"extraction precision of new admissions (agreed claims / judged): "
              f"{(stats['agreed']) / new_total:.3f}  (NOT_A_CLAIM rate {stats['not_a_claim'] / new_total:.3f})")
    print(f"gold v2: {len(df)} rows -> {GOLD_V2}")
    print(df.groupby(["origin", "label"]).size())


def _feat_worker(args):
    claim, source, effort = args
    from stellars_claude_code_plugins.document_processing import lexical as L
    return L.extract_lexical_features(str(claim), [str(source)], effort=effort, det_lang=None)


def cmd_bench() -> None:
    """Benchmark the shipped HIGH manifold on gold v2, split inherited vs judged."""
    from concurrent.futures import ProcessPoolExecutor
    from sklearn.metrics import f1_score
    from build_combined import shipped_manifold

    verdict = shipped_manifold("high")

    df = pd.read_parquet(GOLD_V2)
    args = [(r.claim, r.source_text, "high") for r in df.itertuples()]
    print(f"extracting high features for {len(args)} rows...")
    with ProcessPoolExecutor(max_workers=20) as ex:
        feats = list(ex.map(_feat_worker, args, chunksize=16))
    df["p_high"] = [verdict.predict_proba(f) for f in feats]
    df["pred"] = (df["p_high"] >= verdict.threshold).astype(int)

    def macro(sub):
        return round(f1_score(sub["label"], sub["pred"], average="macro"), 4) if len(sub) else None

    print(f"\ngold v2 macro-F1 (n={len(df)}): {macro(df)}")
    print(f"  inherited (n={(df.origin=='inherited').sum()}): {macro(df[df.origin=='inherited'])}")
    print(f"  judged-new (n={(df.origin=='judged').sum()}): {macro(df[df.origin=='judged'])}")
    en = df[df.lang == "en"]
    non_en = df[df.lang != "en"]
    print(f"  english (n={len(en)}): {macro(en)}")
    print(f"  non-english (n={len(non_en)}): {macro(non_en)}")
    print("\n  per-language (n>=30):")
    for lang, g in df.groupby("lang"):
        if len(g) >= 30:
            print(f"    {lang:6s} n={len(g):4d}  macro-F1 {macro(g)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["units", "judge", "build", "bench"])
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    if a.cmd == "units":
        cmd_units()
    elif a.cmd == "judge":
        cmd_judge(a.model, a.workers)
    elif a.cmd == "bench":
        cmd_bench()
    else:
        cmd_build()
