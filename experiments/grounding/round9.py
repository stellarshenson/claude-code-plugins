"""Round 9 (H17) - cross-lingual manifold retrain on gold v2.

The shipped HIGH manifold catches 0/139 non-English hallucinations (TNR 0.000) while
English is healthy (TNR 0.710). A probe showed the 18 shipped features already SEPARATE
non-English support from hallucination (r1_mt/r1_best AUC 0.80, unmatched_rarity 0.80
inverted) - so the defect is in the WEIGHTS (trained English-only, r1_mt==r1_direct
collinear), not the features. This module retrains the same frozen 18-feature contract on
gold v2 (the first gold containing non-English negatives) and measures the lift honestly:
5-fold out-of-fold CV (every row gets a held-out prediction) + leave-one-language-out for
generalization.

Writes retrained weights to config_document_processing.experiment.yaml - NEVER the shipped
config. Run from experiments/grounding:  uv run python round9.py <cmd>

Commands:
  features   extract shipped HIGH features for all rows, cache to gitignored parquet
  audit      Stage 1: per-feature + per-language AUC on the non-EN slice, MT firing
  eval       Stage 3: baseline vs retrained (OOF CV) slice metrics + LOLO
  retrain    fit on ALL rows, write config_document_processing.experiment.yaml
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from stellars_claude_code_plugins.document_processing import lexical as L

HERE = Path(__file__).parent
REPO = HERE.resolve().parents[1]
GV2 = HERE / "private-rag-forensics/gold/golden_grounding_evidence_v2.parquet"
CACHE = HERE / "private-rag-forensics/round9_features.parquet"  # gitignored dir
EXP_CONFIG = REPO / "src/stellars_claude_code_plugins/config_document_processing.experiment.yaml"
SHIPPED_CONFIG = REPO / "src/stellars_claude_code_plugins/config_document_processing.yaml"

FEATS = L.HIGH_FEATURES


def _base_lang(code) -> str:
    """Collapse fr-FR / nb-NO / es-ES to base ISO; the grounder re-detects 2-letter at
    inference, so the regional suffix is a gold-v2 artifact."""
    if code is None:
        return "und"
    return str(code).split("-")[0].lower() or "und"


# ----------------------------------------------------------------------------- data
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
                    "label": 1 if nat == "SUPPORTS" else 0, "lang": "en", "slice": "vitaminc",
                    "origin": "vitaminc"})
    return out


def load_rows() -> list[dict]:
    df = pd.read_parquet(GV2)
    rows = []
    for r in df.to_dict("records"):
        bl = _base_lang(r.get("lang"))
        rows.append({"claim": r["claim"], "source_text": r["source_text"],
                     "label": int(r["label"]), "lang": bl,
                     "slice": "gold_en" if bl == "en" else "gold_ne",
                     "origin": r.get("origin", "")})
    vit = _vitaminc_rows()
    raw = rows + vit
    aug = L.short_source_augment(raw)
    for a in aug:
        a["slice"] = "aug"
        a["lang"] = _base_lang(a.get("lang"))
        a["origin"] = "aug"
    return raw + aug


# ------------------------------------------------------------------------- features
def _work(a):
    claim, src = a
    return L.extract_lexical_features(str(claim), [str(src)], effort="high", det_lang=None)


def build_features(force: bool = False) -> pd.DataFrame:
    if CACHE.exists() and not force:
        return pd.read_parquet(CACHE)
    from multiprocessing import Pool

    rows = load_rows()
    print(f"extracting HIGH features for {len(rows)} rows "
          f"(gold_en/gold_ne/vitaminc/aug)", flush=True)
    t0 = time.time()
    with Pool(min(24, os.cpu_count() or 8)) as p:
        feats = p.map(_work, [(r["claim"], r["source_text"]) for r in rows], chunksize=16)
    print(f"  done in {time.time() - t0:.0f}s", flush=True)
    F = pd.DataFrame(feats)
    for k in ("label", "lang", "slice", "origin"):
        F[k] = [r[k] for r in rows]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    F.to_parquet(CACHE)
    print(f"  cached -> {CACHE}", flush=True)
    return F


# --------------------------------------------------------------------------- models
def fit_high(F: pd.DataFrame, oversample_ne: int = 1) -> L.LexicalVerdict:
    """Fit a HIGH manifold on the given feature frame. oversample_ne replicates gold_ne
    rows N times before fit so the cross-lingual regime is not drowned by 77% English."""
    rows = F.to_dict("records")
    if oversample_ne > 1:
        ne = [r for r in rows if r["slice"] == "gold_ne"]
        rows = rows + ne * (oversample_ne - 1)
    block = L.fit_lexical_manifold(rows, effort="high")
    return L.LexicalVerdict(weights=block["weights"], feature_order=block["feature_order"],
                            threshold=block["threshold"]), block


def shipped_high() -> L.LexicalVerdict:
    from build_combined import shipped_manifold

    return shipped_manifold("high")


# ---------------------------------------------------------------------------- metrics
def _preds(v: L.LexicalVerdict, F: pd.DataFrame) -> np.ndarray:
    return np.array([v.confirmed(F.iloc[i].to_dict()) for i in range(len(F))])


def slice_report(y: np.ndarray, pred_supp: np.ndarray, lang: np.ndarray, sl: np.ndarray,
                 label: str) -> dict:
    """TNR = hallucination recall (caught / total negatives); balanced-acc = (TPR+TNR)/2."""
    def m(mask):
        yy, pp = y[mask], pred_supp[mask]
        neg, pos = (yy == 0), (yy == 1)
        tnr = float((~pp[neg]).mean()) if neg.any() else float("nan")
        tpr = float(pp[pos].mean()) if pos.any() else float("nan")
        ba = np.nanmean([tnr, tpr])
        return dict(n=int(mask.sum()), neg=int(neg.sum()), tnr=round(tnr, 3),
                    tpr=round(tpr, 3), bal_acc=round(float(ba), 3))
    out = {
        "label": label,
        "non_EN": m((sl == "gold_ne")),
        "EN": m((sl == "gold_en")),
        "vitaminc": m((sl == "vitaminc")),
    }
    return out


def _print_report(rep: dict) -> None:
    print(f"\n=== {rep['label']} ===")
    for k in ("non_EN", "EN", "vitaminc"):
        s = rep[k]
        print(f"  {k:8s} n={s['n']:5d} neg={s['neg']:4d}  "
              f"TNR={s['tnr']:.3f}  TPR={s['tpr']:.3f}  bal_acc={s['bal_acc']:.3f}")


# ------------------------------------------------------------------------- commands
def cmd_features() -> None:
    build_features(force="--force" in sys.argv)


def cmd_audit() -> None:
    from sklearn.metrics import roc_auc_score

    F = build_features()
    ne = F[F.slice == "gold_ne"].reset_index(drop=True)
    y = ne.label.values
    print(f"non-EN rows {len(ne)}  neg {int((y == 0).sum())}  pos {int((y == 1).sum())}")
    print("\n--- per-feature AUC for catching non-EN hallucination (1.0=perfect) ---")
    for c in FEATS:
        v = ne[c].values
        try:
            a = roc_auc_score(y == 0, -v)
        except Exception:
            a = float("nan")
        print(f"  {c:18s} AUC={a:.3f}  supp={v[y==1].mean():.3f}  halluc={v[y==0].mean():.3f}")
    fire = float((np.abs(ne.r1_mt - ne.r1_direct) > 1e-6).mean())
    print(f"\n--- MT firing fraction (r1_mt != r1_direct): {fire:.3f}")
    print("\n--- per base-language (negatives only langs) ---")
    for lg in ["es", "fr", "pt", "nb", "sv", "it", "nl"]:
        sub = ne[ne.lang == lg]
        if len(sub) == 0:
            continue
        yy = sub.label.values
        nneg = int((yy == 0).sum())
        try:
            a = roc_auc_score(yy == 0, -sub.r1_best.values) if nneg and (yy == 1).any() else float("nan")
        except Exception:
            a = float("nan")
        print(f"  {lg}: n={len(sub):4d} neg={nneg:3d}  r1_best AUC={a:.3f}")


def cmd_eval() -> None:
    from sklearn.model_selection import StratifiedKFold

    F = build_features()
    gold = F[F.slice.isin(["gold_en", "gold_ne"])].reset_index(drop=True)
    extra = F[F.slice.isin(["vitaminc", "aug"])].reset_index(drop=True)
    y = gold.label.values
    lang = gold.lang.values
    sl = gold.slice.values

    # ---- baseline: shipped HIGH on the full gold v2 (reproduction gate) ----
    ship = shipped_high()
    base_pred = _preds(ship, gold)
    _print_report(slice_report(y, base_pred, lang, sl, "BASELINE shipped HIGH (gold v2)"))

    # ---- retrained: 5-fold OOF so every gold row gets a held-out prediction ----
    for osample in (1, 3):
        oof = np.zeros(len(gold), dtype=bool)
        strat = np.array([f"{s}_{l}" for s, l in zip(sl, y)])
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
        for tr, te in skf.split(gold, strat):
            train = pd.concat([gold.iloc[tr], extra], ignore_index=True)
            v, _ = fit_high(train, oversample_ne=osample)
            oof[te] = _preds(v, gold.iloc[te].reset_index(drop=True))
        _print_report(slice_report(y, oof, lang, sl,
                                   f"RETRAINED gold v2 - 5-fold OOF (oversample_ne={osample})"))

    # ---- LOLO: train without a language's negatives entirely ----
    print("\n=== LOLO (leave-one-language-out) held-out non-EN TNR, oversample_ne=3 ===")
    for lg in ["es", "fr", "pt", "nb", "sv"]:
        held = gold[(gold.lang == lg) & (gold.slice == "gold_ne")]
        if (held.label == 0).sum() == 0:
            continue
        train = pd.concat([gold[~((gold.lang == lg) & (gold.slice == "gold_ne"))], extra],
                          ignore_index=True)
        v, _ = fit_high(train, oversample_ne=3)
        hp = _preds(v, held.reset_index(drop=True))
        yy = held.label.values
        neg = yy == 0
        tnr = float((~hp[neg]).mean())
        print(f"  {lg}: held-out neg={int(neg.sum()):3d}  TNR={tnr:.3f}  "
              f"(confirm rate on its {int((yy==1).sum())} pos={float(hp[yy==1].mean()):.3f})")


def _proba(v: L.LexicalVerdict, F: pd.DataFrame) -> np.ndarray:
    return np.array([v.predict_proba(F.iloc[i].to_dict()) for i in range(len(F))])


def cmd_threshold() -> None:
    """Diagnostic: is the non-EN miss a signal problem or an operating-point problem?
    Build OOF probabilities, then sweep a non-EN-specific threshold (English keeps its own).
    A language-conditional threshold is in-contract - is_en is already computed."""
    from sklearn.model_selection import StratifiedKFold

    F = build_features()
    gold = F[F.slice.isin(["gold_en", "gold_ne"])].reset_index(drop=True)
    extra = F[F.slice.isin(["vitaminc", "aug"])].reset_index(drop=True)
    y = gold.label.values
    ne = (gold.slice == "gold_ne").values
    p = np.zeros(len(gold))
    strat = np.array([f"{s}_{l}" for s, l in zip(gold.slice.values, y)])
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    for tr, te in skf.split(gold, strat):
        train = pd.concat([gold.iloc[tr], extra], ignore_index=True)
        v, _ = fit_high(train, oversample_ne=3)
        p[te] = _proba(v, gold.iloc[te].reset_index(drop=True))

    yn = y[ne]
    pn = p[ne]
    neg, pos = (yn == 0), (yn == 1)
    print("=== non-EN threshold sweep (OOF probabilities, 1204 pos / 139 neg) ===")
    print("  thr   TNR(catch)  TPR(confirm)  bal_acc")
    best = None
    for thr in np.linspace(0.30, 0.95, 14):
        tnr = float((pn[neg] < thr).mean())
        tpr = float((pn[pos] >= thr).mean())
        ba = (tnr + tpr) / 2
        star = ""
        if tpr >= 0.90 and (best is None or tnr > best[1]):
            best = (thr, tnr, tpr)
            star = " <- best @TPR>=0.90"
        print(f"  {thr:.2f}   {tnr:.3f}       {tpr:.3f}        {ba:.3f}{star}")
    if best:
        print(f"\nReachable @TPR>=0.90: TNR={best[1]:.3f} at non-EN thr={best[0]:.2f} "
              f"(shipped single thr catches 0.000)")

    # does a language-conditional threshold survive LOLO (unseen language)?
    print("\n=== LOLO at fixed non-EN thresholds (held-out language never in training) ===")
    for THR in (0.65, 0.70):
        print(f"  non-EN threshold = {THR}")
        for lg in ["es", "fr", "pt", "nb", "sv"]:
            held = gold[(gold.lang == lg) & (gold.slice == "gold_ne")]
            if (held.label == 0).sum() == 0:
                continue
            train = pd.concat([gold[~((gold.lang == lg) & (gold.slice == "gold_ne"))], extra],
                              ignore_index=True)
            v, _ = fit_high(train, oversample_ne=3)
            ph = _proba(v, held.reset_index(drop=True))
            yy = held.label.values
            neg, pos = (yy == 0), (yy == 1)
            tnr = float((ph[neg] < THR).mean())
            tpr = float((ph[pos] >= THR).mean()) if pos.any() else float("nan")
            print(f"    {lg}: held neg={int(neg.sum()):3d}  TNR={tnr:.3f}  TPR={tpr:.3f}")


def cmd_retrain() -> None:
    """Fit ALL tiers on the full gold v2 + vitaminc + aug, write the EXPERIMENT yaml."""
    import yaml

    F = build_features()
    train = F[F.slice.isin(["gold_en", "gold_ne", "vitaminc", "aug"])].reset_index(drop=True)
    osample = int(os.environ.get("OVERSAMPLE_NE", "3"))
    rows = train.to_dict("records")
    ne = [r for r in rows if r["slice"] == "gold_ne"]
    rows_os = rows + ne * (osample - 1)
    manifolds = {}
    for effort in L.EFFORT_TIERS:
        manifolds[effort] = L.fit_lexical_manifold(rows_os, effort=effort)
        m = manifolds[effort]
        print(f"  {effort}: thr {m['threshold']:.2f}  r1_mt {m['weights'].get('r1_mt', 0):+.2f}  "
              f"r1_direct {m['weights'].get('r1_direct', 0):+.2f}  "
              f"unmatched_rarity {m['weights'].get('unmatched_rarity', 0):+.2f}", flush=True)
    # mirror the shipped config shape: nest under calibration.lexical_manifolds
    text = SHIPPED_CONFIG.read_text(encoding="utf-8")
    marker = "  lexical_manifolds:"
    head = text[: text.index(marker)]
    block = yaml.safe_dump({"lexical_manifolds": manifolds}, sort_keys=False, default_flow_style=False)
    block = "\n".join(("  " + ln if ln.strip() else ln) for ln in block.splitlines())
    EXP_CONFIG.write_text(head + block + "\n", encoding="utf-8")
    print(f"wrote EXPERIMENT config (oversample_ne={osample}) -> {EXP_CONFIG}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "eval"
    {"features": cmd_features, "audit": cmd_audit, "eval": cmd_eval,
     "threshold": cmd_threshold, "retrain": cmd_retrain}[cmd]()
