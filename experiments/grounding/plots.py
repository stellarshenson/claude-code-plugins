"""Optimisation plots for the cross-lingual grounding experiment.

Reuses the harness signals; writes PNGs to ``plots/``. Aggregate metrics only,
no client text. Run: ``python plots.py`` (featurizes twice, ~90s incl MT).
"""
# ruff: noqa: E702  (dense plotting code uses compact one-line statements)

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import harness as H
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).parent / "plots"
OUT.mkdir(exist_ok=True)

CY, OR, GREY = "#0096d1", "#da8230", "#888888"


def main() -> None:
    recs = H.load_gold()
    labels = [r.label for r in recs]
    print("featurizing (lexical)...")
    rows_lex = H.featurize(recs, *H.CHUNK, use_mt=False)
    print("featurizing (MT)...")
    rows_mt = H.featurize(recs, *H.CHUNK, use_mt=True)

    # --- Plot 1: recall-threshold sweep (accuracy + balanced vs tau) ----------
    taus = np.linspace(0.05, 0.95, 19)
    def curve(rows):
        acc, bal = [], []
        for tau in taus:
            pred = [int(r["r1"] >= tau) for r in rows]
            s = H.score_verdicts(labels, pred)
            acc.append(s["acc"]); bal.append(s["bal"])
        return acc, bal
    acc_mt, bal_mt = curve(rows_mt)
    acc_lex, bal_lex = curve(rows_lex)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(taus, acc_mt, "-o", color=CY, label="accuracy (+MT)", ms=4)
    ax.plot(taus, bal_mt, "-s", color=OR, label="balanced (+MT)", ms=4)
    ax.plot(taus, acc_lex, "--o", color=CY, alpha=0.45, label="accuracy (lexical)", ms=3)
    ax.plot(taus, bal_lex, "--s", color=OR, alpha=0.45, label="balanced (lexical)", ms=3)
    ax.axhline(0.771, color=GREY, ls=":", lw=1, label="majority acc 0.771")
    ax.axhline(0.75, color="#3a7", ls=":", lw=1, label="balanced target 0.75")
    ax.set_xlabel("recall threshold $\\tau$")
    ax.set_ylabel("score over 375 (fixed-prior)")
    ax.set_title("Recall-threshold sweep: accuracy vs balanced, MT vs lexical")
    ax.set_ylim(0.45, 0.85); ax.grid(alpha=0.3); ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "01_threshold_sweep.png", dpi=150); plt.close(fig)

    # --- Plot 2: per-language accuracy, lexical vs +MT (recall_only tau=0.4) ---
    order = ["en", "no", "fr", "sv", "it", "es", "pt"]
    def lang_acc(rows, tau=0.4):
        out = {}
        for L in order:
            idx = [i for i, r in enumerate(recs) if rows[i]["det_lang"] == L]
            if not idx:
                out[L] = (np.nan, 0); continue
            corr = sum(1 for i in idx if int(rows[i]["r1"] >= tau) == labels[i])
            out[L] = (corr / len(idx), len(idx))
        return out
    la_lex, la_mt = lang_acc(rows_lex), lang_acc(rows_mt)
    x = np.arange(len(order)); w = 0.38
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(x - w / 2, [la_lex[L][0] for L in order], w, color=GREY, label="lexical")
    ax.bar(x + w / 2, [la_mt[L][0] for L in order], w, color=CY, label="+MT")
    for i, L in enumerate(order):
        ax.text(i, 1.02, f"n={la_mt[L][1]}", ha="center", fontsize=7, color="#555")
    ax.set_xticks(x); ax.set_xticklabels(order)
    ax.set_ylabel("accuracy (recall $\\tau$=0.4)")
    ax.set_title("Per-language accuracy: MT bridge closes the cross-lingual gap")
    ax.set_ylim(0, 1.12); ax.grid(axis="y", alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(OUT / "02_per_language_mt.png", dpi=150); plt.close(fig)

    # --- Plot 3: abstain curve (coverage vs balanced-on-covered) --------------
    lo = 0.30
    his = np.linspace(0.35, 0.80, 19)
    cov, bal_cov = [], []
    for hi in his:
        c = [(int(r["r1"] >= hi), r["label"]) for r in rows_mt if not (lo <= r["r1"] < hi)]
        cov.append(len(c) / len(rows_mt))
        bal_cov.append(H.score_verdicts([y for _, y in c], [p for p, _ in c])["bal"] if c else np.nan)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(cov, bal_cov, "-o", color=OR, ms=4)
    for hi, cv, bc in zip(his[::3], cov[::3], bal_cov[::3]):
        ax.annotate(f"hi={hi:.2f}", (cv, bc), fontsize=6, color="#555",
                    textcoords="offset points", xytext=(3, 4))
    ax.set_xlabel("coverage (fraction of claims verdicted)")
    ax.set_ylabel("balanced accuracy on covered set")
    ax.set_title("Abstain band: precision/coverage trade (+MT, lo=0.30)")
    ax.grid(alpha=0.3); ax.invert_xaxis()
    fig.tight_layout(); fig.savefig(OUT / "03_abstain_curve.png", dpi=150); plt.close(fig)

    # --- Plot 4: chunk sweep (AUC of recall separation vs chunk size) ---------
    sizes = [150, 300, 600, 1200, 10**9]  # last = whole-doc
    labelsz = ["150", "300", "600", "1200", "whole"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for strat, col in [("recursive", CY), ("sentence", OR), ("char", "#3a7")]:
        aucs = []
        for sz in sizes:
            scores = [
                H.idf_best_chunk_recall(r.claim, H.chunk_text(r.source, sz, 0.1, strat), H.an_word)
                for r in recs
            ]
            aucs.append(H.auc(scores, labels))
        ax.plot(range(len(sizes)), aucs, "-o", color=col, label=strat, ms=5)
    ax.axhline(0.5, color=GREY, ls=":", lw=1, label="no separation")
    ax.set_xticks(range(len(sizes))); ax.set_xticklabels(labelsz)
    ax.set_xlabel("chunk size (chars)"); ax.set_ylabel("AUC of recall separation")
    ax.set_title("Chunk-size optimisation: small chunks separate, whole-doc is blind")
    ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(OUT / "04_chunk_sweep.png", dpi=150); plt.close(fig)

    print("wrote:", *(p.name for p in sorted(OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
