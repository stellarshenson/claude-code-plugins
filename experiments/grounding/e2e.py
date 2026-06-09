"""End-to-end performance of the lexical-only grounder (lexical + MT, NO semantic).

Reports both quality (macro-F1 / hal-F1 under LOLO + LOSO) and throughput
(per-stage latency, ms/claim, MT-only timing). Uses the torch-free mt.py
(CTranslate2 + wtpsplit SaT). MT runs only for heterogeneous claims (non-English
claim vs English source).
"""

from __future__ import annotations

import sys
import time

from rapidfuzz import fuzz
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, ".")
import harness as H  # noqa: E402
import lab  # noqa: E402
import mt  # noqa: E402

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
    "conflict_n",
    "conflict_flag",
    "num_edit_mag",
    "wn_antonym_flip",
]


def main() -> None:
    recs = H.load_gold()
    n = len(recs)

    # cold start: load SaT + one MT model, measured separately
    t = time.time()
    mt.translate("Prueba de arranque del modelo.", "es")
    cold = time.time() - t

    timing = {"mt": 0.0, "recall": 0.0, "anchor": 0.0, "intrinsic": 0.0, "lang": 0.0}
    n_mt = 0
    src_ids: dict = {}
    rows = []
    t_all = time.time()
    for r in recs:
        sid = src_ids.setdefault(r.source[:120], len(src_ids))
        chunks = H.chunk_text(r.source, *H.CHUNK)
        claim = r.claim
        if r.det_lang not in ("en", "und", ""):  # heterogeneous -> translate
            t = time.time()
            claim = mt.translate(r.claim, r.det_lang)
            timing["mt"] += time.time() - t
            n_mt += 1
        t = time.time()
        rd, ad, bd = lab.chunk_recalls(r.claim, chunks, H.an_word)
        rt, at, bt = lab.chunk_recalls(claim, chunks, H.an_word)
        r1_direct = rd[ad] if rd else 0.0
        r1_mt = rt[at] if rt else 0.0
        charng = H.idf_best_chunk_recall(claim, chunks, H.an_charngram)
        fz = fuzz.partial_ratio(claim.lower(), bt.lower()) / 100.0 if bt else 0.0
        oracle = max(rt) if rt else 0.0
        top = sorted(rt, reverse=True)
        top3 = top[1] if len(top) >= 2 else (top[0] if top else 0.0)
        timing["recall"] += time.time() - t
        t = time.time()
        ents = H.list_claim_entities(r.claim)
        absent = set(H.find_absent_entities(r.claim, r.source))
        num_rec, num_mm = H.number_recall(r.claim, r.source)
        aden = len(ents) + (1 if num_rec >= 0 else 0)
        ahit = sum(1 for e in ents if e not in absent) + (num_rec if num_rec >= 0 else 0)
        anchor = (ahit / aden) if aden else 0.0
        nmm, emm = H.find_mismatches(r.claim, bt) if bt else ([], [])
        amm = 1 if (nmm or emm or num_mm) else 0
        timing["anchor"] += time.time() - t
        t = time.time()
        spec, _ = lab.claim_intrinsic(r.claim)
        clang = lab._lingua_lang(r.claim)
        chunk_lang = lab._lingua_lang(bd) if bd else "und"
        same_lang = int(clang != "und" and chunk_lang == clang)
        # contradiction layer: aligned value-conflict + WordNet antonym flip; both
        # fuzzy-gated so they stay inert on private RAG's absent-content negatives
        conflict_n, conflict_flag, num_edit_mag = lab.conflict_feats(r.claim, bt)
        wn_flip = int(lab.wn_antonym_flip(claim, bt) and fz > 0.5)
        semantic_candidate = int(fz >= 0.5 and (conflict_flag or wn_flip))
        timing["intrinsic"] += time.time() - t
        rows.append(
            dict(
                label=r.label,
                det_lang=r.det_lang,
                src=sid,
                is_en=int(r.det_lang == "en"),
                same_lang=same_lang,
                r1_direct=r1_direct,
                r1_mt=r1_mt,
                r1_best=max(r1_direct, r1_mt),
                charng=charng,
                fuzzy=fz,
                anchor=anchor,
                anchor_mm=amm,
                oracle=oracle,
                top3=top3,
                specificity=spec,
                conflict_n=conflict_n,
                conflict_flag=conflict_flag,
                num_edit_mag=num_edit_mag,
                wn_antonym_flip=wn_flip,
                semantic_candidate=semantic_candidate,
            )
        )
    feat_wall = time.time() - t_all

    def LR():
        return LogisticRegression(max_iter=1000, class_weight="balanced")

    t = time.time()
    lolo = lab.group_model(rows, FEATS, LR, "det_lang")
    loso = lab.group_model(rows, FEATS, LR, "src")
    eval_wall = time.time() - t

    print("\n=== END-TO-END LEXICAL GROUNDER (lexical + MT, NO semantic) ===\n")
    print(
        f"records: {n} | translated (heterogeneous claim vs en source): {n_mt} "
        f"({100 * n_mt / n:.0f}%)\n"
    )
    print("QUALITY (logistic over lexical features + specificity)")
    print(
        f"  LOLO  macroF1 {lolo['f1_macro']:.3f}  hal-F1 {lolo['f1_hal']:.2f}  "
        f"sup-F1 {lolo['f1_sup']:.2f}  acc {lolo['acc']:.3f}"
    )
    print(
        f"  LOSO  macroF1 {loso['f1_macro']:.3f}  hal-F1 {loso['f1_hal']:.2f}  "
        f"sup-F1 {loso['f1_sup']:.2f}  acc {loso['acc']:.3f}\n"
    )
    print("THROUGHPUT")
    print(f"  cold start (load SaT + 1 MT model): {cold:.1f}s (one-time)")
    print(
        f"  feature build wall:                 {feat_wall:.1f}s  ({1000 * feat_wall / n:.1f} ms/claim)"
    )
    for k, v in timing.items():
        print(f"    {k:10}: {v:6.1f}s total  | {1000 * v / n:5.2f} ms/claim avg")
    if n_mt:
        print(f"  MT per translated claim:            {1000 * timing['mt'] / n_mt:.1f} ms")
    print(f"  classifier fit+score (LOLO+LOSO):   {eval_wall:.1f}s (negligible at inference)")
    n_sc = sum(r["semantic_candidate"] for r in rows)
    print(
        f"\nTRIAGE  semantic_candidate flagged: {n_sc}/{n} = {100 * n_sc / n:.0f}% "
        "(contradiction region routed to a future semantic stage)"
    )


if __name__ == "__main__":
    main()
