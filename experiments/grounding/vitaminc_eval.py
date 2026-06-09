"""Run the deployed lexical grounder on VitaminC to see how the method transfers.

This is NOT cross-corpus transfer (A4 fit-on-VitaminC, apply-to-gold). Here we
build the SAME lexical feature set the gold uses (the e2e.py FEATS + specificity)
on VitaminC records and evaluate the logistic IN-CORPUS via stratified out-of-fold
CV. VitaminC is monolingual English single-sentence evidence, so MT never fires;
this isolates the lexical recall + claim-intrinsic mechanism on a contrastive
fact-verification set where REFUTES claims share heavy lexical overlap with the
evidence (the known weakness of recall-only grounding).

Two label mappings:
  - primary   SUPPORTS=1 vs REFUTES=0          (drop NEI; the clean supported-vs-contradicted task)
  - secondary SUPPORTS=1 vs {REFUTES,NEI}=0    (NEI counted as not-supported)
"""

from __future__ import annotations

import json
import sys

import numpy as np
from rapidfuzz import fuzz
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, ".")
import harness as H  # noqa: E402
import lab  # noqa: E402

FEATS = [
    "r1_direct",
    "r1_mt",
    "r1_best",
    "charng",
    "fuzzy",
    "anchor",
    "anchor_mm",
    "oracle",
    "top3",
    "same_lang",
    "is_en",
    "specificity",
]


def build_vitaminc_lex(per_label: int = 400, refresh: bool = False) -> list[dict]:
    """Lexical feature rows for VitaminC dev, balanced across the 3 native labels."""
    fp = lab.CACHE / "vitaminc_lex.json"
    if fp.exists() and not refresh:
        return json.loads(fp.read_text())
    from huggingface_hub import hf_hub_download

    p = hf_hub_download("tals/vitaminc", "dev.jsonl", repo_type="dataset")
    want = {"SUPPORTS": per_label, "REFUTES": per_label, "NOT ENOUGH INFO": per_label}
    rows = []
    for line in open(p, encoding="utf-8"):
        rec = json.loads(line)
        nat = rec.get("label")
        if nat not in want or want[nat] <= 0:
            continue
        want[nat] -= 1
        claim, ev = rec["claim"], rec["evidence"]
        chunks = H.chunk_text(ev, *H.CHUNK)
        # English-only: claim_en == claim, MT never fires, is_en=1
        rd, ad, best = lab.chunk_recalls(claim, chunks, H.an_word, bg_idf_fn=H.bg_idf, bg_lang="en")
        r1 = rd[ad] if rd else 0.0
        charng = H.idf_best_chunk_recall(claim, chunks, H.an_charngram)
        fz = fuzz.partial_ratio(claim.lower(), best.lower()) / 100.0 if best else 0.0
        oracle = max(rd) if rd else 0.0
        top = sorted(rd, reverse=True)
        top3 = top[1] if len(top) >= 2 else (top[0] if top else 0.0)
        ents = H.list_claim_entities(claim)
        absent = set(H.find_absent_entities(claim, ev))
        num_rec, num_mm = H.number_recall(claim, ev)
        aden = len(ents) + (1 if num_rec >= 0 else 0)
        ahit = sum(1 for e in ents if e not in absent) + (num_rec if num_rec >= 0 else 0)
        anchor = (ahit / aden) if aden else 0.0
        nmm, emm = H.find_mismatches(claim, best) if best else ([], [])
        amm = 1 if (nmm or emm or num_mm) else 0
        clang = lab._lingua_lang(claim)
        chunk_lang = lab._lingua_lang(best) if best else "und"
        same_lang = int(clang != "und" and chunk_lang == clang)
        spec, _ = lab.claim_intrinsic(claim)
        # contradiction features (English-only; overlap-gated on fuzzy, since IDF
        # recall r1 degenerates to ~0 on VitaminC's single-sentence evidence)
        conflict_n, conflict_flag, num_edit_mag = lab.conflict_feats(claim, best)
        wn_flip = int(lab.wn_antonym_flip(claim, best) and fz > 0.5)
        conflict_any = int(conflict_flag or wn_flip)
        semantic_candidate = int(fz >= 0.5 and conflict_any)
        unmatched_rarity, max_unmatched = lab.gap_rarity(claim, best)
        rows.append(
            dict(
                nat=nat,
                r1_direct=round(r1, 4),
                r1_mt=round(r1, 4),
                r1_best=round(r1, 4),
                charng=round(charng, 4),
                fuzzy=round(fz, 4),
                anchor=round(anchor, 4),
                anchor_mm=amm,
                oracle=round(oracle, 4),
                top3=round(top3, 4),
                same_lang=same_lang,
                is_en=1,
                specificity=round(spec, 4),
                conflict_n=round(conflict_n, 4),
                conflict_flag=conflict_flag,
                num_edit_mag=round(num_edit_mag, 4),
                wn_antonym_flip=wn_flip,
                r1_x_conflict=round(r1 * conflict_any, 4),
                unmatched_rarity=round(unmatched_rarity, 4),
                max_unmatched=round(max_unmatched, 4),
                semantic_candidate=semantic_candidate,
            )
        )
        if all(v <= 0 for v in want.values()):
            break
    fp.write_text(json.dumps(rows))
    return rows


def _oof_cv(rows, k: int = 5):
    """Stratified k-fold out-of-fold predictions; threshold tuned on each train split."""
    y = np.array([r["label"] for r in rows])
    idx = np.arange(len(rows))
    rng = np.array([i % k for i in range(len(rows))])  # deterministic round-robin per class
    fold = np.empty(len(rows), dtype=int)
    for cls in (0, 1):
        ci = idx[y == cls]
        fold[ci] = rng[: len(ci)]
    yt, yp, nats = [], [], []
    for f in range(k):
        tr = idx[fold != f]
        te = idx[fold == f]
        if len({rows[i]["label"] for i in tr}) < 2 or not len(te):
            continue
        Xtr = np.array([[rows[i][c] for c in FEATS] for i in tr], dtype=float)
        ytr = y[tr]
        m = LogisticRegression(max_iter=1000, class_weight="balanced").fit(Xtr, ytr)
        ptr = m.predict_proba(Xtr)[:, 1]
        thr, best = 0.5, -1.0
        for t in np.linspace(0.2, 0.8, 13):
            s = lab._mf1(ytr.tolist(), (ptr >= t).astype(int).tolist())
            if s > best:
                best, thr = s, t
        Xte = np.array([[rows[i][c] for c in FEATS] for i in te], dtype=float)
        pte = m.predict_proba(Xte)[:, 1]
        yp += list((pte >= thr).astype(int))
        yt += [rows[i]["label"] for i in te]
        nats += [rows[i]["nat"] for i in te]
    return yt, yp, nats


def _report(title, rows):
    yt, yp, nats = _oof_cv(rows)
    s = H.score_verdicts(yt, yp)
    print(f"\n{title}  (n={len(yt)}, supported={sum(yt)}, neg={len(yt) - sum(yt)})")
    print(
        f"  macroF1 {s['f1_macro']:.3f}  hal-F1 {s['f1_hal']:.2f}  "
        f"sup-F1 {s['f1_sup']:.2f}  acc {s['acc']:.3f}  "
        f"sup-rec {s['rec_sup']:.2f}  hal-rec {s['rec_hal']:.2f}"
    )
    # per native-label: how often the model called it "supported"
    by = {}
    for t, p, nat in zip(yt, yp, nats):
        d = by.setdefault(nat, [0, 0])
        d[0] += 1
        d[1] += p
    for nat in ("SUPPORTS", "REFUTES", "NOT ENOUGH INFO"):
        if nat in by:
            n, pos = by[nat]
            print(f"    {nat:16}: predicted-supported {pos}/{n} = {pos / n:.0%}")


def main(per_label: int = 400) -> None:
    rows = build_vitaminc_lex(per_label)
    print(f"=== Deployed lexical grounder on VitaminC dev (balanced {per_label}/label) ===")
    print(f"features: {FEATS}")
    print("English-only: MT never fires (is_en=1); isolates lexical recall + specificity")

    # primary: SUPPORTS vs REFUTES (drop NEI)
    sr = [
        dict(r, label=1 if r["nat"] == "SUPPORTS" else 0)
        for r in rows
        if r["nat"] in ("SUPPORTS", "REFUTES")
    ]
    _report("PRIMARY  SUPPORTS=1 vs REFUTES=0", sr)

    # secondary: SUPPORTS vs {REFUTES, NEI}
    allr = [dict(r, label=1 if r["nat"] == "SUPPORTS" else 0) for r in rows]
    _report("SECONDARY  SUPPORTS=1 vs {REFUTES,NEI}=0", allr)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    main(n)
