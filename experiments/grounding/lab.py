"""Experiment lab: next-gen grounding hypotheses (interactions, wildcards).

Builds a cached per-record feature table (incl NLI, oracle-chunk, anchors) once,
then runs hypotheses under leave-one-language-out with learned models that are
NEVER fit to the held-out language. Aggregate metrics only; feature cache is
git-ignored. Number to beat: macro-F1 0.755, hallucination-F1 0.64.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
from rank_bm25 import BM25Okapi

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import harness as H  # noqa: E402

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)


def chunk_recalls(claim: str, chunks: list[str], analyzer, bg_idf_fn=None, bg_lang: str = "en"):
    """IDF-weighted claim recall against EACH chunk (shared corpus IDF).

    Returns (recalls_per_chunk, bm25_argmax_index, best_chunk_text). Decouples
    'which chunk' (bm25 argmax = r1) from 'best possible chunk' (max recall =
    oracle), so the retrieval-vs-scoring gap is measurable. ``bg_idf_fn`` (word
    analyzer only) soft-floors the in-context IDF with length-robust background
    rarity so recall stays honest on a single-chunk source.
    """
    cl = analyzer(claim)
    if not cl:
        return [], None, ""
    pairs = [(c, a) for c in chunks if (a := analyzer(c))]
    if not pairs:
        return [], None, ""
    raw = [c for c, _ in pairs]
    corpus = [a for _, a in pairs]
    bm = BM25Okapi(corpus)
    scores = np.maximum(bm.get_scores(cl), 0.0)
    idf = bm.idf
    max_idf = max(idf.values()) if idf else 1.0
    claim_set = set(cl)
    w = H._blend_weight(idf, max_idf, bg_idf_fn, bg_lang)

    den = sum(w(t) for t in claim_set) or 1.0
    recalls = [sum(w(t) for t in claim_set if t in set(doc)) / den for doc in corpus]
    arg = int(scores.argmax()) if float(scores.max()) > 0 else 0
    return recalls, arg, raw[arg]


def build_features(use_mt: bool = True, refresh: bool = False) -> list[dict]:
    fp = CACHE / (f"features_{'mt' if use_mt else 'lex'}.json")
    if fp.exists() and not refresh:
        return json.loads(fp.read_text())
    from stellars_claude_code_plugins.document_processing.nli import NLIGrounder

    nli = NLIGrounder()
    recs = H.load_gold()
    rows: list[dict] = []
    for r in recs:
        chunks = H.chunk_text(r.source, *H.CHUNK)
        claim = r.claim
        if use_mt and r.det_lang not in ("en", "und", ""):
            claim = H.mt_to_english(r.claim, r.det_lang)
        recalls, arg, best = chunk_recalls(claim, chunks, H.an_word)
        r1 = recalls[arg] if recalls else 0.0
        oracle = max(recalls) if recalls else 0.0
        top = sorted(recalls, reverse=True)
        top3_med = top[1] if len(top) >= 2 else (top[0] if top else 0.0)
        r2 = H.idf_best_chunk_recall(claim, chunks, H.an_charngram)
        sc = nli.scores(best, r.claim) if best else {}
        ne, nc, nn = (
            sc.get("entailment", 0.0),
            sc.get("contradiction", 0.0),
            sc.get("neutral", 0.0),
        )
        nmm, emm = H.find_mismatches(r.claim, best) if best else ([], [])
        num_rec, num_mismatch = H.number_recall(r.claim, r.source)
        veto = 1 if (nmm or num_mismatch) else 0
        ents = H.list_claim_entities(r.claim)
        absent = set(H.find_absent_entities(r.claim, r.source))
        aden = len(ents) + (1 if num_rec >= 0 else 0)
        ahit = sum(1 for e in ents if e not in absent) + (num_rec if num_rec >= 0 else 0)
        anchor = (ahit / aden) if aden else 0.0
        rows.append(
            dict(
                label=r.label,
                lang=r.lang,
                det_lang=r.det_lang,
                is_en=int(r.det_lang == "en"),
                r1=round(r1, 4),
                r2=round(r2, 4),
                oracle=round(oracle, 4),
                top3_med=round(top3_med, 4),
                anchor=round(anchor, 4),
                nli_e=round(ne, 4),
                nli_c=round(nc, 4),
                nli_n=round(nn, 4),
                veto=veto,
            )
        )
    fp.write_text(json.dumps(rows))
    return rows


# --- LOLO evaluation of a learned model (never fit on the held-out language) --
def _mf1(yt, yp) -> float:
    return H.score_verdicts(list(yt), list(yp))["f1_macro"]


def lolo_model(rows, feat_cols, model_factory, tune_thresh: bool = True) -> dict:
    langs = sorted({r["det_lang"] for r in rows})
    yt, yp = [], []
    for L in langs:
        tr = [r for r in rows if r["det_lang"] != L]
        te = [r for r in rows if r["det_lang"] == L]
        if len({r["label"] for r in tr}) < 2 or not te:
            continue
        Xtr = np.array([[r[c] for c in feat_cols] for r in tr], dtype=float)
        ytr = np.array([r["label"] for r in tr])
        m = model_factory()
        m.fit(Xtr, ytr)
        Xte = np.array([[r[c] for c in feat_cols] for r in te], dtype=float)
        ptr = m.predict_proba(Xtr)[:, 1]
        thr = 0.5
        if tune_thresh:
            best = -1.0
            for t in np.linspace(0.2, 0.8, 13):
                f = _mf1(ytr, (ptr >= t).astype(int))
                if f > best:
                    best, thr = f, t
        pte = m.predict_proba(Xte)[:, 1]
        yp += list((pte >= thr).astype(int))
        yt += [r["label"] for r in te]
    return H.score_verdicts(yt, yp)


def _add_interactions(rows):
    for r in rows:
        r["isen_r1"] = r["is_en"] * r["r1"]
        r["nonen_nlie"] = (1 - r["is_en"]) * r["nli_e"]
        r["r1_x_nlic"] = r["r1"] * r["nli_c"]


# --- B1: claim decomposition -------------------------------------------------
import re  # noqa: E402

_CONN = re.compile(
    r"\b(?:and|but|og|men|samt|et|mais|ainsi que|y|e|ed|pero|sino|ma|och|mas|oder|und)\b|[;:]",
    re.I,
)


def split_clauses(text: str, min_len: int = 40) -> list[str]:
    parts = [p.strip() for p in _CONN.split(text) if p and p.strip()]
    merged: list[str] = []
    for p in parts:
        if merged and len(p) < min_len:
            merged[-1] = merged[-1] + " " + p
        else:
            merged.append(p)
    return merged or [text]


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()] or [text]


def build_decomp(use_mt: bool = True, refresh: bool = False) -> list[dict]:
    """Per-record min-clause-recall + any-mismatch for whole/sentence/clause units."""
    fp = CACHE / "decomp.json"
    if fp.exists() and not refresh:
        return json.loads(fp.read_text())
    recs = H.load_gold()
    rows = []
    for r in recs:
        chunks = H.chunk_text(r.source, *H.CHUNK)
        claim = r.claim
        if use_mt and r.det_lang not in ("en", "und", ""):
            claim = H.mt_to_english(r.claim, r.det_lang)
        row = {"label": r.label, "lang": r.lang, "det_lang": r.det_lang}
        for key, units in (
            ("whole", [claim]),
            ("sent", split_sentences(claim)),
            ("clause", split_clauses(claim)),
        ):
            r1s, mm = [], 0
            for u in units:
                recalls, arg, best = chunk_recalls(u, chunks, H.an_word)
                r1s.append(recalls[arg] if recalls else 0.0)
                nmm, _ = H.find_mismatches(u, best) if best else ([], [])
                _, num_mm = H.number_recall(u, r.source)
                if nmm or num_mm:
                    mm = 1
            r1s = r1s or [0.0]
            row[f"{key}_min"] = round(min(r1s), 4)
            row[f"{key}_n"] = len(units)
            row[f"{key}_nge"] = r1s  # per-clause recalls for k-of-n
            row[f"{key}_mm"] = mm
        rows.append(row)
    fp.write_text(json.dumps(rows))
    return rows


def lolo_decomp(rows, key, agg="any") -> dict:
    """Tune the recall bar per-fold (LOLO); aggregate clause verdicts to claim verdict."""

    def verdict(r, bar):
        if r[f"{key}_mm"]:
            return 0
        rs = r[f"{key}_nge"]
        if agg == "any":  # all clauses must clear the bar (weakest-link)
            return int(min(rs) >= bar)
        # k-of-n: all but one
        return int(sum(1 for x in rs if x >= bar) >= max(1, len(rs) - 1))

    langs = sorted({r["det_lang"] for r in rows})
    yt, yp = [], []
    for L in langs:
        tr = [r for r in rows if r["det_lang"] != L]
        te = [r for r in rows if r["det_lang"] == L]
        if len({r["label"] for r in tr}) < 2 or not te:
            continue
        best_bar, best = 0.4, -1.0
        for bar in np.linspace(0.2, 0.7, 11):
            f = _mf1([r["label"] for r in tr], [verdict(r, bar) for r in tr])
            if f > best:
                best, best_bar = f, bar
        yp += [verdict(r, best_bar) for r in te]
        yt += [r["label"] for r in te]
    return H.score_verdicts(yt, yp)


def run_b1() -> None:
    rows = build_decomp(use_mt=True)
    nclause = sum(1 for r in rows if r["clause_n"] > 1)
    out = [
        "## Lab B1 - claim decomposition (LOLO, recall bar tuned out-of-fold)\n",
        f"claims split into >1 clause: {nclause}/{len(rows)}\n",
        "| unit / aggregation | macroF1 | hal-F1 | sup-F1 | acc |",
        "|---|---|---|---|---|",
    ]
    for key, agg, name in [
        ("whole", "any", "whole-claim"),
        ("sent", "any", "sentence-split"),
        ("clause", "any", "clause-split (any-contradicted)"),
        ("clause", "kofn", "clause-split (k-of-n)"),
    ]:
        s = lolo_decomp(rows, key, agg)
        out.append(
            f"| {name} | **{s['f1_macro']:.3f}** | {s['f1_hal']:.2f} | "
            f"{s['f1_sup']:.2f} | {s['acc']:.3f} |"
        )
    report = "\n".join(out) + "\n"
    print(report)
    (Path(__file__).parent / "logs" / "lab_b1.md").write_text(report)


# --- A4: cross-corpus calibrator transfer (fit on VitaminC, freeze) ----------
def build_vitaminc(per_label: int = 130, refresh: bool = False) -> list[dict]:
    fp = CACHE / "vitaminc.json"
    if fp.exists() and not refresh:
        return json.loads(fp.read_text())
    import itertools

    from huggingface_hub import hf_hub_download

    from stellars_claude_code_plugins.document_processing.nli import NLIGrounder

    nli = NLIGrounder()
    p = hf_hub_download("tals/vitaminc", "dev.jsonl", repo_type="dataset")
    want = {"SUPPORTS": per_label, "REFUTES": per_label, "NOT ENOUGH INFO": per_label}
    rows = []
    for line in open(p, encoding="utf-8"):
        rec = json.loads(line)
        lab = rec.get("label")
        if lab not in want or want[lab] <= 0:
            continue
        want[lab] -= 1
        claim, ev = rec["claim"], rec["evidence"]
        recalls, arg, best = chunk_recalls(claim, [ev], H.an_word)
        r1 = recalls[arg] if recalls else 0.0
        sc = nli.scores(ev, claim)
        rows.append(
            dict(
                label=1 if lab == "SUPPORTS" else 0,
                r1=round(r1, 4),
                nli_e=round(sc.get("entailment", 0.0), 4),
                nli_c=round(sc.get("contradiction", 0.0), 4),
            )
        )
        if all(v <= 0 for v in want.values()):
            break
    _ = itertools  # keep import used if loop empty
    fp.write_text(json.dumps(rows))
    return rows


def run_a4() -> None:
    from sklearn.linear_model import LogisticRegression

    vit = build_vitaminc()
    gold = build_features(use_mt=True)
    cols = ["r1", "nli_e", "nli_c"]
    Xv = np.array([[r[c] for c in cols] for r in vit], dtype=float)
    yv = np.array([r["label"] for r in vit])
    m = LogisticRegression(max_iter=1000, class_weight="balanced").fit(Xv, yv)
    Xg = np.array([[r[c] for c in cols] for r in gold], dtype=float)
    yg = [r["label"] for r in gold]
    out = [
        "## Lab A4 - VitaminC-frozen calibrator transfer (zero gold fit)\n",
        f"VitaminC train: {len(vit)} records; coefficients {dict(zip(cols, m.coef_[0].round(2)))} "
        f"intercept {m.intercept_[0]:.2f}\n",
        "| rule | macroF1 | hal-F1 | sup-F1 | acc |",
        "|---|---|---|---|---|",
    ]
    for thr in (0.5, 0.4):
        pred = (m.predict_proba(Xg)[:, 1] >= thr).astype(int)
        s = H.score_verdicts(yg, list(pred))
        out.append(
            f"| VitaminC-frozen @{thr} | **{s['f1_macro']:.3f}** | {s['f1_hal']:.2f} | "
            f"{s['f1_sup']:.2f} | {s['acc']:.3f} |"
        )
    report = "\n".join(out) + "\n"
    print(report)
    (Path(__file__).parent / "logs" / "lab_a4.md").write_text(report)


# --- A6 capacity ceiling + C8 diversity -------------------------------------
def _infold(rows, cols, factory) -> float:
    X = np.array([[r[c] for c in cols] for r in rows], dtype=float)
    y = [r["label"] for r in rows]
    m = factory().fit(X, y)
    p = m.predict_proba(X)[:, 1]
    best = -1.0
    for t in np.linspace(0.2, 0.8, 13):
        f = _mf1(y, (p >= t).astype(int))
        best = max(best, f)
    return best


def run_final() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression

    rows = build_features(use_mt=True)
    _add_interactions(rows)

    def LR():
        return LogisticRegression(max_iter=1000, class_weight="balanced")

    def GBT(d, seed=0):
        return lambda: GradientBoostingClassifier(
            max_depth=d, n_estimators=40, learning_rate=0.1, random_state=seed
        )

    cont = ["r1", "r2", "oracle", "top3_med", "anchor", "nli_e", "nli_c"]
    ladder = [
        ("LR[r1]", ["r1"], LR, 1),
        ("LR[r1,nli]", ["r1", "nli_e", "nli_c"], LR, 3),
        (
            "LR+interactions",
            ["r1", "nli_e", "nli_c", "is_en", "isen_r1", "nonen_nlie", "r1_x_nlic"],
            LR,
            7,
        ),
        ("GBT d2", cont, GBT(2), 12),
        ("GBT d4", cont, GBT(4), 30),
    ]
    names, lolo, infold, fulls = [], [], [], []
    for name, cols, fac, _cap in ladder:
        names.append(name)
        s = lolo_model(rows, cols, fac)
        fulls.append(s)
        lolo.append(s["f1_macro"])
        infold.append(_infold(rows, cols, fac))

    out = [
        "## A6 capacity ceiling (LOLO out-of-fold vs in-fold)\n",
        "| model | LOLO macroF1 | hal-F1 | sup-F1 | acc | in-fold | overfit gap |",
        "|---|---|---|---|---|---|---|",
    ]
    for n, s, inf in zip(names, fulls, infold):
        out.append(
            f"| {n} | **{s['f1_macro']:.3f}** | {s['f1_hal']:.2f} | {s['f1_sup']:.2f} | "
            f"{s['acc']:.3f} | {inf:.3f} | {inf - s['f1_macro']:+.3f} |"
        )
    # GBT d2 is stochastic on 86 negatives - report mean +/- std over 5 seeds
    seeds = [lolo_model(rows, cont, GBT(2, sd))["f1_macro"] for sd in range(5)]
    out.append(
        f"\nGBT d2 over 5 seeds: mean {np.mean(seeds):.3f} +/- {np.std(seeds):.3f} "
        f"(min {min(seeds):.3f}, max {max(seeds):.3f}) - vs recall_split 0.755\n"
    )

    # C8 diversity: per-channel error correlation + ensembles
    R1 = [int(r["r1"] >= 0.4) for r in rows]
    NLI = [1 if r["nli_e"] >= max(r["nli_c"], r["nli_n"]) else 0 for r in rows]
    ANC = [int(r["anchor"] >= 0.5) for r in rows]
    y = [r["label"] for r in rows]
    eR1 = np.array([int(a != b) for a, b in zip(R1, y)])
    eN = np.array([int(a != b) for a, b in zip(NLI, y)])
    eA = np.array([int(a != b) for a, b in zip(ANC, y)])

    def phi(a, b):
        return float(np.corrcoef(a, b)[0, 1])

    out += [
        "\n## C8 ensemble diversity (error-correlation phi)\n",
        f"phi(R1,NLI)={phi(eR1, eN):.2f}  phi(R1,ANC)={phi(eR1, eA):.2f}  "
        f"phi(NLI,ANC)={phi(eN, eA):.2f}\n",
        "| ensemble | macroF1 |",
        "|---|---|",
    ]
    orr = [int(a or b) for a, b in zip(R1, NLI)]
    maj = [int(a + b + c >= 2) for a, b, c in zip(R1, NLI, ANC)]
    out.append(f"| R1 | {_mf1(y, R1):.3f} |")
    out.append(f"| R1 OR NLI | {_mf1(y, orr):.3f} |")
    out.append(f"| R1+NLI+ANC majority | {_mf1(y, maj):.3f} |")

    report = "\n".join(out) + "\n"
    print(report)
    (Path(__file__).parent / "logs" / "lab_final.md").write_text(report)

    # capacity scissors plot
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(names))
    ax.plot(x, infold, "-o", color="#da8230", label="in-fold (optimistic)")
    ax.plot(x, lolo, "-o", color="#0096d1", label="LOLO (out-of-fold)")
    ax.axhline(0.755, color="#3a7", ls=":", lw=1, label="recall_split 0.755")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("macro-F1")
    ax.set_ylim(0.6, 1.0)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    ax.set_title(
        "Capacity ceiling: out-of-fold peaks at depth-2, in-fold memorises (86 negatives)"
    )
    fig.tight_layout()
    fig.savefig(Path(__file__).parent / "plots" / "05_capacity_ceiling.png", dpi=150)
    plt.close(fig)
    print("wrote plots/05_capacity_ceiling.png")


# --- lexical-only, language-routed feature build (NO NLI) --------------------
_LING = {}


def _lingua_lang(text: str, min_len: int = 25) -> str:
    if len(text.strip()) < min_len:
        return "und"
    if "det" not in _LING:
        from lingua import LanguageDetectorBuilder

        _LING["det"] = LanguageDetectorBuilder.from_all_languages().build()
    lg = _LING["det"].detect_language_of(text)
    return lg.iso_code_639_1.name.lower() if lg else "und"


# --- mechanism-general feature helpers (H1 rarity, H2 span, H3 claim-intrinsic) ---
from difflib import SequenceMatcher  # noqa: E402
import math  # noqa: E402

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

_HEDGE = set(
    (
        "typically usually generally often may might could probably possibly likely "
        "vanligvis kanskje muligens generelt ofte sannsynligvis "
        "typiquement generalement peut souvent probablement "
        "tipicamente generalmente forse spesso probabilmente "
        "normalmente quizas geralmente talvez provavelmente vanligen kanske"
    ).split()
)


def _bg_idf(tok: str, lang: str = "en") -> float:
    return H.bg_idf(tok, lang)  # single source of truth (harness.bg_idf)


def gap_rarity(claim_en: str, best: str) -> tuple[float, float]:
    """H1: population-rarity-weighted fraction of claim content ABSENT from best chunk."""
    toks = {t for t in _TOKEN_RE.findall(claim_en.lower()) if len(t) > 1}
    if not toks:
        return 0.0, 0.0
    chunk = set(_TOKEN_RE.findall(best.lower())) if best else set()
    idfs = {t: _bg_idf(t) for t in toks}
    tot = sum(idfs.values()) or 1.0
    absent = [v for t, v in idfs.items() if t not in chunk]
    return (sum(absent) / tot, (max(absent) / 9.0) if absent else 0.0)


def span_feats(claim_en: str, best: str) -> tuple[float, int]:
    """H2: longest contiguous claim substring present in best chunk (verbatim restatement)."""
    if not best:
        return 0.0, 0
    a, b = claim_en.lower(), best.lower()
    m = SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return (m.size / max(1, len(a)), int(m.size >= 40))


def claim_intrinsic(claim: str) -> tuple[float, float]:
    """H3: evidence-independent specificity + hedging (cannot memorise the documents)."""
    toks = _TOKEN_RE.findall(claim.lower())
    n = len(toks) or 1
    nums = len(re.findall(r"\d+", claim))
    spec = (len(H.list_claim_entities(claim)) + nums) / n
    hedge = sum(1 for t in toks if t in _HEDGE) / n
    return spec, hedge


# --- contradiction features (aligned value-conflict + WordNet antonym flip) ---
# Both overlap-gated: they only fire on high-overlap restatements, so they stay
# inert on private RAG's absent-content negatives and active on contrastive (VitaminC)
# negatives where one fact is flipped. WordNet (below) replaced an earlier curated
# antonym lexicon - broader coverage at equal precision (REFUTES 32% vs SUPPORTS 3%).
def conflict_feats(claim: str, best: str) -> tuple[float, int, float]:
    """H1: aligned value-conflict (numeric + entity) from find_mismatches, graded.

    Returns (conflict_n, conflict_flag, num_edit_mag). Inherently overlap-gated:
    a mismatch only exists when a claim anchor ALIGNS with the chunk but disagrees
    in value, so on absent-content negatives (private RAG) nothing aligns -> all zero.
    """
    if not best:
        return 0.0, 0, 0.0
    nmm, emm = H.find_mismatches(claim, best)
    cnt = len(nmm) + len(emm)
    ents = H.list_claim_entities(claim)
    bl = best.lower()
    aligned_ent = sum(1 for e in ents if e.lower() in bl)
    nrec, _ = H.number_recall(claim, best)
    aligned_num = 1 if (nrec is not None and nrec > 0) else 0
    denom = aligned_ent + aligned_num + cnt
    conflict_n = cnt / denom if denom else 0.0
    mag = 0.0
    for a, b in nmm:
        try:
            fa, fb = float(a.replace(",", "")), float(b.replace(",", ""))
            d = max(abs(fa), abs(fb))
            mag = max(mag, abs(fa - fb) / d) if d else mag
        except ValueError:
            mag = max(mag, 1.0)
    return conflict_n, int(cnt > 0), mag


# WordNet-broadened lexical opposition (replaced an earlier curated antonym list).
# WordNet antonyms are a deterministic
# population lexicon at word-sense level; broader coverage than the curated list
# (probe: fires on 70% of VitaminC REFUTES vs 8% SUPPORTS, vs curated 62%/6%).
_WN: dict = {}


def _wn_antonyms(w: str) -> set:
    if "mod" not in _WN:
        import nltk
        from nltk.corpus import wordnet as wn

        try:
            wn.synsets("test")
        except LookupError:
            nltk.download("wordnet", quiet=True)
        _WN["mod"], _WN["cache"] = wn, {}
    cache = _WN["cache"]
    if w not in cache:
        ant = set()
        for s in _WN["mod"].synsets(w):
            for lemma in s.lemmas():
                for a in lemma.antonyms():
                    ant.add(a.name().replace("_", " ").lower())
        cache[w] = ant
    return cache[w]


def wn_antonym_flip(claim_en: str, best: str) -> int:
    """R2-H3: a claim content-token whose WordNet antonym is present in the best
    chunk while the token itself is absent (broader than the curated direction list)."""
    if not best:
        return 0
    bset = set(_TOKEN_RE.findall(best.lower()))
    for t in _TOKEN_RE.findall(claim_en.lower()):
        if len(t) < 3 or t in bset:
            continue
        if _wn_antonyms(t) & bset:
            return 1
    return 0


def build_lex(refresh: bool = False) -> list[dict]:
    """Lexical-only features with claim+chunk language detection (no NLI)."""
    fp = CACHE / "lex.json"
    if fp.exists() and not refresh:
        return json.loads(fp.read_text())
    from rapidfuzz import fuzz

    recs = H.load_gold()
    src_ids = {}
    rows = []
    for r in recs:
        sid = src_ids.setdefault(r.source[:120], len(src_ids))
        chunks = H.chunk_text(r.source, *H.CHUNK)
        clang = _lingua_lang(r.claim)
        # direct (original claim) recall + best-chunk language
        dlang = r.det_lang if r.det_lang not in ("und", "") else "en"
        rd, ad, best_d = chunk_recalls(r.claim, chunks, H.an_word, bg_idf_fn=H.bg_idf, bg_lang=dlang)
        r1_direct = rd[ad] if rd else 0.0
        chunk_lang = _lingua_lang(best_d) if best_d else "und"
        same_lang = int(clang != "und" and chunk_lang == clang)
        # translated recall (claim -> English)
        claim_en = r.claim
        if r.det_lang not in ("en", "und", ""):
            claim_en = H.mt_to_english(r.claim, r.det_lang)
        rt, at, best_t = chunk_recalls(claim_en, chunks, H.an_word, bg_idf_fn=H.bg_idf, bg_lang="en")
        r1_mt = rt[at] if rt else 0.0
        r1_best = max(r1_direct, r1_mt)
        charng = H.idf_best_chunk_recall(claim_en, chunks, H.an_charngram)
        fz = fuzz.partial_ratio(claim_en.lower(), best_t.lower()) / 100.0 if best_t else 0.0
        oracle = max(rt) if rt else 0.0
        top = sorted(rt, reverse=True)
        top3 = top[1] if len(top) >= 2 else (top[0] if top else 0.0)
        # anchors (language-invariant), on the original claim
        ents = H.list_claim_entities(r.claim)
        absent = set(H.find_absent_entities(r.claim, r.source))
        num_rec, num_mm = H.number_recall(r.claim, r.source)
        aden = len(ents) + (1 if num_rec >= 0 else 0)
        ahit = sum(1 for e in ents if e not in absent) + (num_rec if num_rec >= 0 else 0)
        anchor = (ahit / aden) if aden else 0.0
        nmm, emm = H.find_mismatches(r.claim, best_t) if best_t else ([], [])
        amm = 1 if (nmm or emm or num_mm) else 0
        # mechanism-general features
        unmatched_rarity, max_unmatched = gap_rarity(claim_en, best_t)
        span_lcs, quote_flag = span_feats(claim_en, best_t)
        spec, hedge = claim_intrinsic(r.claim)
        # contradiction features (overlap-gated on fuzzy - live on single-chunk
        # evidence, unlike IDF recall which degenerates to ~0 on a 1-chunk corpus)
        conflict_n, conflict_flag, num_edit_mag = conflict_feats(r.claim, best_t)
        wn_flip = int(wn_antonym_flip(claim_en, best_t) and fz > 0.5)
        conflict_any = int(conflict_flag or wn_flip)
        semantic_candidate = int(fz >= 0.5 and conflict_any)
        rows.append(
            dict(
                label=r.label,
                lang=r.lang,
                det_lang=r.det_lang,
                src=sid,
                is_en=int(r.det_lang == "en"),
                same_lang=same_lang,
                r1_direct=round(r1_direct, 4),
                r1_mt=round(r1_mt, 4),
                r1_best=round(r1_best, 4),
                charng=round(charng, 4),
                fuzzy=round(fz, 4),
                anchor=round(anchor, 4),
                anchor_mm=amm,
                oracle=round(oracle, 4),
                top3=round(top3, 4),
                unmatched_rarity=round(unmatched_rarity, 4),
                max_unmatched=round(max_unmatched, 4),
                span_lcs=round(span_lcs, 4),
                quote_flag=quote_flag,
                specificity=round(spec, 4),
                hedge=round(hedge, 4),
                conflict_n=round(conflict_n, 4),
                conflict_flag=conflict_flag,
                num_edit_mag=round(num_edit_mag, 4),
                wn_antonym_flip=wn_flip,
                r1_x_conflict=round(r1_best * conflict_any, 4),
                semantic_candidate=semantic_candidate,
            )
        )
    fp.write_text(json.dumps(rows))
    return rows


def group_model(rows, cols, factory, group, balanced=False, tune=True) -> dict:
    """Generic leave-one-GROUP-out (group='det_lang' for LOLO, 'src' for LOSO)."""
    groups = sorted({r[group] for r in rows})
    yt, yp = [], []
    for g in groups:
        tr = [r for r in rows if r[group] != g]
        te = [r for r in rows if r[group] == g]
        if len({r["label"] for r in tr}) < 2 or not te:
            continue
        Xtr = np.array([[r[c] for c in cols] for r in tr], dtype=float)
        ytr = np.array([r["label"] for r in tr])
        m = factory()
        if balanced:
            n0, n1 = (ytr == 0).sum(), (ytr == 1).sum()
            w = np.where(ytr == 1, len(ytr) / (2 * max(1, n1)), len(ytr) / (2 * max(1, n0)))
            m.fit(Xtr, ytr, sample_weight=w)
        else:
            m.fit(Xtr, ytr)
        ptr = m.predict_proba(Xtr)[:, 1]
        thr = 0.5
        if tune:
            best = -1.0
            for t in np.linspace(0.2, 0.8, 13):
                f = _mf1(ytr.tolist(), (ptr >= t).astype(int).tolist())
                if f > best:
                    best, thr = f, t
        pte = m.predict_proba(np.array([[r[c] for c in cols] for r in te], dtype=float))[:, 1]
        yp += list((pte >= thr).astype(int))
        yt += [r["label"] for r in te]
    return H.score_verdicts(yt, yp)


def run_lexgbm() -> None:
    from lightgbm import LGBMClassifier
    from sklearn.linear_model import LogisticRegression

    rows = build_lex()
    # H6 same-language coverage per language
    cov = {}
    for L in sorted({r["det_lang"] for r in rows}):
        sub = [r for r in rows if r["det_lang"] == L]
        cov[L] = (sum(r["same_lang"] for r in sub), len(sub))
    for r in rows:  # interaction columns for the linear model
        r["sl_rd"] = r["same_lang"] * r["r1_direct"]
        r["nsl_rmt"] = (1 - r["same_lang"]) * r["r1_mt"]

    base = [
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
    ]
    H1 = ["unmatched_rarity", "max_unmatched"]  # gap specificity (unsupported mechanism)
    H2 = ["span_lcs", "quote_flag"]  # verbatim restatement (precision-1 supported)
    H3 = ["specificity", "hedge"]  # claim-intrinsic (generalisation guard)

    def LR():
        return LogisticRegression(max_iter=1000, class_weight="balanced")

    def GBT(d):
        return lambda: LGBMClassifier(
            max_depth=d,
            num_leaves=2**d,
            n_estimators=200,
            learning_rate=0.05,
            class_weight="balanced",
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=0,
            n_jobs=1,
            verbose=-1,
        )

    out = [
        "## Lexical-only + mechanism features (1260 gold, NO NLI) - LR ablation\n",
        "same-language coverage: "
        + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in cov.items())
        + "\n",
        "| model | LOLO macroF1 | LOLO hal-F1 | LOSO macroF1 | LOSO hal-F1 |",
        "|---|---|---|---|---|",
    ]

    def row(name, cols, fac=LR, bal=False):
        lo = group_model(rows, cols, fac, "det_lang", balanced=bal)
        so = group_model(rows, cols, fac, "src", balanced=bal)
        out.append(
            f"| {name} | **{lo['f1_macro']:.3f}** | {lo['f1_hal']:.2f} | "
            f"{so['f1_macro']:.3f} | {so['f1_hal']:.2f} |"
        )

    row("base (lexical)", base)
    row("base + H1 rarity", base + H1)
    row("base + H2 span", base + H2)
    row("base + H3 claim-intrinsic", base + H3)
    row("base + all (H1+H2+H3)", base + H1 + H2 + H3)
    row("LGBM d2 (base, control)", base, GBT(2))

    # H2 acceptance: quote_flag precision for supported
    q = [r for r in rows if r["quote_flag"] == 1]
    qp = sum(r["label"] for r in q) / max(1, len(q))
    out.append(
        f"\nH2 quote_flag==1: n={len(q)}, supported precision {qp:.3f} (base rate "
        f"{sum(r['label'] for r in rows) / len(rows):.3f})"
    )

    # H1/H3 standardized LR coefficients (do the new features get used?)
    from sklearn.preprocessing import StandardScaler

    allf = base + H1 + H2 + H3
    X = np.array([[r[c] for c in allf] for r in rows], dtype=float)
    y = np.array([r["label"] for r in rows])
    Xs = StandardScaler().fit_transform(X)
    coef = LR().fit(Xs, y).coef_[0]
    new = {c: round(float(coef[allf.index(c)]), 2) for c in H1 + H2 + H3}
    out.append(f"new-feature standardized coefficients: {new}\n")

    report = "\n".join(out) + "\n"
    print(report)
    (Path(__file__).parent / "logs" / "lab_lexgbm.md").write_text(report)


def run_seg() -> None:
    """Claim-segmentation competition scored by OUR metric (macro-F1, LOLO + LOSO).

    whole-claim vs regex clause-split (current) vs SaT (wtpsplit). Ground each unit,
    aggregate any-contradicted / min-recall, tune the recall bar per fold. Uses the
    torch-free mt.py for translation and SaT.
    """
    import mt

    sat = mt._sat()
    fp = CACHE / "seg.json"
    if fp.exists():
        rows = json.loads(fp.read_text())
    else:
        recs = H.load_gold()
        src_ids: dict = {}
        rows = []
        for r in recs:
            sid = src_ids.setdefault(r.source[:120], len(src_ids))
            chunks = H.chunk_text(r.source, *H.CHUNK)
            claim = r.claim
            if r.det_lang not in ("en", "und", ""):
                claim = mt.translate(r.claim, r.det_lang)
            methods = {
                "whole": [claim],
                "clause": split_clauses(claim),
                "sat": sat.split(claim) or [claim],
            }
            row = {"label": r.label, "det_lang": r.det_lang, "src": sid}
            for k, units in methods.items():
                r1s, mm = [], 0
                for u in units:
                    u = u.strip()
                    if not u:
                        continue
                    recalls, arg, best = chunk_recalls(u, chunks, H.an_word)
                    r1s.append(recalls[arg] if recalls else 0.0)
                    nmm, _ = H.find_mismatches(u, best) if best else ([], [])
                    _, num_mm = H.number_recall(u, r.source)
                    if nmm or num_mm:
                        mm = 1
                r1s = r1s or [0.0]
                row[f"{k}_min"] = round(min(r1s), 4)
                row[f"{k}_n"] = len([u for u in units if u.strip()])
                row[f"{k}_mm"] = mm
            rows.append(row)
        fp.write_text(json.dumps(rows))

    def evaluate(method, group):
        def verdict(r, bar):
            return 0 if r[f"{method}_mm"] else int(r[f"{method}_min"] >= bar)

        groups = sorted({r[group] for r in rows})
        yt, yp = [], []
        for g in groups:
            tr = [r for r in rows if r[group] != g]
            te = [r for r in rows if r[group] == g]
            if len({r["label"] for r in tr}) < 2 or not te:
                continue
            best, bar = -1.0, 0.4
            for b in np.linspace(0.2, 0.7, 11):
                f = _mf1([r["label"] for r in tr], [verdict(r, b) for r in tr])
                if f > best:
                    best, bar = f, b
            yp += [verdict(r, bar) for r in te]
            yt += [r["label"] for r in te]
        return H.score_verdicts(yt, yp)

    avg_units = {
        m: round(np.mean([r[f"{m}_n"] for r in rows]), 2) for m in ("whole", "clause", "sat")
    }
    out = [
        "## Claim-segmentation competition - macro-F1 (1260 gold, min-recall + any-contra)\n",
        f"mean units/claim: {avg_units}\n",
        "| segmentation | LOLO macroF1 | LOLO hal-F1 | LOSO macroF1 | LOSO hal-F1 |",
        "|---|---|---|---|---|",
    ]
    for m, name in [
        ("whole", "whole-claim (no split)"),
        ("clause", "regex clause-split (current)"),
        ("sat", "SaT (wtpsplit)"),
    ]:
        lo, so = evaluate(m, "det_lang"), evaluate(m, "src")
        out.append(
            f"| {name} | **{lo['f1_macro']:.3f}** | {lo['f1_hal']:.2f} | "
            f"{so['f1_macro']:.3f} | {so['f1_hal']:.2f} |"
        )
    report = "\n".join(out) + "\n"
    print(report)
    (Path(__file__).parent / "logs" / "lab_seg.md").write_text(report)


def run_bayes() -> None:
    """Production Bayesian calibrator (bambi/PyMC logistic) under LOLO - a hyperplane."""
    import pandas as pd

    from stellars_claude_code_plugins.document_processing.calibration import (
        PREDICTORS,
        fit_calibrator,
    )

    rows = build_features(use_mt=True)

    def to_df(rs):
        d = {p: [0.0] * len(rs) for p in PREDICTORS}
        d["bm25_recall"] = [r["r1"] for r in rs]
        d["nli_entail"] = [r["nli_e"] for r in rs]
        d["nli_contra"] = [r["nli_c"] for r in rs]
        d["grounded"] = [float(r["label"]) for r in rs]
        return pd.DataFrame(d)

    langs = sorted({r["det_lang"] for r in rows})
    yt, yp = [], []
    for L in langs:
        tr = [r for r in rows if r["det_lang"] != L]
        te = [r for r in rows if r["det_lang"] == L]
        if len({r["label"] for r in tr}) < 2 or not te:
            continue
        cal = fit_calibrator(
            to_df(tr), balance="balanced", draws=300, tune=300, chains=2, random_seed=0
        )
        ptr = np.asarray(cal.predict_proba(to_df(tr)[PREDICTORS]))
        thr, best = 0.5, -1.0
        for t in np.linspace(0.2, 0.8, 13):
            f = _mf1([r["label"] for r in tr], (ptr >= t).astype(int))
            if f > best:
                best, thr = f, t
        pte = np.asarray(cal.predict_proba(to_df(te)[PREDICTORS]))
        yp += list((pte >= thr).astype(int))
        yt += [r["label"] for r in te]
    s = H.score_verdicts(yt, yp)
    line = (
        f"Bayesian calibrator (bambi/PyMC logistic) LOLO: "
        f"macroF1 {s['f1_macro']:.3f} | hal-F1 {s['f1_hal']:.2f} | "
        f"sup-F1 {s['f1_sup']:.2f} | acc {s['acc']:.3f}"
    )
    print(line)
    (Path(__file__).parent / "logs" / "lab_bayes.md").write_text(line + "\n")


def main() -> None:
    from sklearn.linear_model import LogisticRegression

    rows = build_features(use_mt=True)
    _add_interactions(rows)
    labels = [r["label"] for r in rows]
    print(f"feature table: {len(rows)} records | beat macro-F1 0.755 / hal-F1 0.64\n")

    def LR():
        return LogisticRegression(max_iter=1000, class_weight="balanced")

    out = [
        "## Lab batch 1 - interactions + wildcards (LOLO, macro-F1)\n",
        "| hypothesis | macroF1 | hal-F1 | sup-F1 | acc | note |",
        "|---|---|---|---|---|---|",
    ]

    def row(name, s, note=""):
        out.append(
            f"| {name} | **{s['f1_macro']:.3f}** | {s['f1_hal']:.2f} | "
            f"{s['f1_sup']:.2f} | {s['acc']:.3f} | {note} |"
        )

    # floor: logistic on r1 alone
    row("floor: LR[r1]", lolo_model(rows, ["r1"], LR))
    # A1 language x recall
    row(
        "A1 +is_en,isen_r1,nonen_nlie",
        lolo_model(rows, ["r1", "nli_e", "nli_c", "is_en", "isen_r1", "nonen_nlie"], LR),
        "language x recall interaction",
    )
    row(
        "A1 twin (no interactions)",
        lolo_model(rows, ["r1", "nli_e", "nli_c", "is_en"], LR),
        "ablation: main effects only",
    )
    # A3 carved region
    row(
        "A3 +r1_x_nlic product",
        lolo_model(rows, ["r1", "nli_e", "nli_c", "r1_x_nlic"], LR),
        "right-topic-wrong-fact",
    )
    row("A3 twin (no product)", lolo_model(rows, ["r1", "nli_e", "nli_c"], LR), "ablation")
    # A5 continuous NLI
    row(
        "A5 LR[r1,nli_e,nli_c]",
        lolo_model(rows, ["r1", "nli_e", "nli_c"], LR),
        "continuous NLI balance",
    )
    # A3 diagnostic: 2x2 enrichment
    hi = [r for r in rows if r["r1"] >= 0.4 and r["nli_c"] >= 0.5]
    halrate = sum(1 for r in hi if r["label"] == 0) / max(1, len(hi))
    out.append(
        f"\nA3 diagnostic: high-r1 & high-nli_c cell n={len(hi)}, "
        f"hallucination rate {halrate:.2f} (base 0.23)\n"
    )
    # C1 oracle vs r1 (1-feature LR)
    r1s = lolo_model(rows, ["r1"], LR)["f1_macro"]
    ors = lolo_model(rows, ["oracle"], LR)["f1_macro"]
    out.append(
        f"C1 oracle-chunk: LR[r1]={r1s:.3f} -> LR[oracle]={ors:.3f}; "
        f"retrieval loss {ors - r1s:+.3f}\n"
    )
    # C6 anchor-as-veto (parameter-free override on fixed-prior recall tau=0.4)
    rec = [int(r["r1"] >= 0.4) for r in rows]
    vetoed = [0 if r["veto"] else p for r, p in zip(rows, rec)]
    fv = sum(1 for r, p, v in zip(rows, rec, vetoed) if r["label"] == 1 and p == 1 and v == 0)
    row("C6 recall+veto (fixed tau0.4)", H.score_verdicts(labels, vetoed), f"false-veto={fv}")
    row("C6 recall-only (fixed tau0.4)", H.score_verdicts(labels, rec), "no veto")

    report = "\n".join(out) + "\n"
    print(report)
    (Path(__file__).parent / "logs").mkdir(exist_ok=True)
    (Path(__file__).parent / "logs" / "lab_batch1.md").write_text(report)


# --- joint private RAG + VitaminC: one model, scored per corpus (hold or collapse) ---
_JOINT_BASE = [
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
_JOINT_H1 = ["conflict_n", "conflict_flag", "num_edit_mag"]  # aligned value-conflict
_JOINT_H2 = ["wn_antonym_flip"]  # WordNet antonym flip (replaced curated direction)
_JOINT_H3 = ["r1_x_conflict"]  # conflict x overlap interaction
_JOINT_CUR = _JOINT_BASE + _JOINT_H1 + _JOINT_H2 + _JOINT_H3  # shipped contradiction layer
_JOINT_RARITY = ["unmatched_rarity", "max_unmatched"]  # Phase B distinctive-content coverage


def _cur_cols() -> list[str]:
    """Shipped feature set, optionally + Phase-B rarity features (env ADD_RARITY=1)."""
    import os

    cols = list(_JOINT_CUR)
    if os.environ.get("ADD_RARITY") == "1":
        cols += _JOINT_RARITY
    return cols


def build_joint(per_label: int = 400, refresh: bool = False) -> list[dict]:
    """Tagged union of private RAG gold + VitaminC (primary: SUPPORTS vs REFUTES, drop NEI)."""
    import vitaminc_eval as V

    dela = build_lex(refresh=refresh)
    out = []
    for r in dela:
        rr = dict(r, corpus="private_rag", grp=f"d{r['src']}")
        out.append(rr)
    vit = V.build_vitaminc_lex(per_label, refresh=refresh)
    keep = [r for r in vit if r["nat"] in ("SUPPORTS", "REFUTES")]
    for i, r in enumerate(keep):
        rr = dict(r, label=1 if r["nat"] == "SUPPORTS" else 0, corpus="vitaminc", grp=f"v{i % 10}")
        out.append(rr)
    return out


def _tune_thr(yy, pp):
    if len(set(yy.tolist())) < 2:
        return 0.5
    best, thr = -1.0, 0.5
    for t in np.linspace(0.2, 0.8, 13):
        s = _mf1(yy.tolist(), (pp >= t).astype(int).tolist())
        if s > best:
            best, thr = s, t
    return thr


def _joint_oof(rows, cols):
    """One logistic, leave-one-group-out. Two operating points per row:
    pred_shared (threshold tuned on the whole joint train fold) and pred_pc
    (threshold tuned per corpus on the train fold) - same model, domain-calibrated
    operating point. Returns (corpus, label, pred_shared, pred_pc)."""
    from sklearn.linear_model import LogisticRegression

    rec = []
    for g in sorted({r["grp"] for r in rows}):
        tr = [r for r in rows if r["grp"] != g]
        te = [r for r in rows if r["grp"] == g]
        if len({r["label"] for r in tr}) < 2 or not te:
            continue
        Xtr = np.array([[r[c] for c in cols] for r in tr], dtype=float)
        ytr = np.array([r["label"] for r in tr])
        corp = np.array([r["corpus"] for r in tr])
        m = LogisticRegression(max_iter=1000, class_weight="balanced").fit(Xtr, ytr)
        ptr = m.predict_proba(Xtr)[:, 1]
        thr_all = _tune_thr(ytr, ptr)
        thr = {
            "private_rag": _tune_thr(ytr[corp == "private_rag"], ptr[corp == "private_rag"]),
            "vitaminc": _tune_thr(ytr[corp == "vitaminc"], ptr[corp == "vitaminc"]),
        }
        pte = m.predict_proba(np.array([[r[c] for c in cols] for r in te], dtype=float))[:, 1]
        for r, pp in zip(te, pte):
            rec.append(
                (r["corpus"], r["label"], int(pp >= thr_all),
                 int(pp >= thr.get(r["corpus"], thr_all)), r)
            )
    return rec


def _corpus_score(rec, corpus=None, idx=2):
    yy = [(t[1], t[idx]) for t in rec if corpus is None or t[0] == corpus]
    return H.score_verdicts([y for y, _ in yy], [p for _, p in yy])


def run_joint(per_label: int = 400, refresh: bool = False) -> None:
    rows = build_joint(per_label, refresh=refresh)
    nd = sum(1 for r in rows if r["corpus"] == "private_rag")
    nv = len(rows) - nd
    out = [
        "## Joint private RAG + VitaminC - one logistic, scored per corpus\n",
        f"rows: {nd} private_rag + {nv} vitaminc (SUPPORTS vs REFUTES); "
        "grouped CV (private_rag by src, vitaminc round-robin)\n",
        "macro-F1 per corpus; **pc** = per-corpus-tuned threshold (one model, "
        "domain-calibrated operating point), **sh** = single shared threshold\n",
        "| features | private RAG pc | private RAG sh | VitaminC pc | VitaminC sh | pooled sh |",
        "|---|---|---|---|---|---|",
    ]
    sets = [("base (lexical)", _JOINT_BASE), ("shipped (conflict + wn-antonym)", _cur_cols())]
    base_rec = None
    for name, cols in sets:
        rec = _joint_oof(rows, cols)
        if name.startswith("shipped"):
            base_rec = rec
        dpc, dsh = _corpus_score(rec, "private_rag", 3), _corpus_score(rec, "private_rag", 2)
        vpc, vsh = _corpus_score(rec, "vitaminc", 3), _corpus_score(rec, "vitaminc", 2)
        psh = _corpus_score(rec, None, 2)
        out.append(
            f"| {name} | **{dpc['f1_macro']:.3f}** | {dsh['f1_macro']:.3f} | "
            f"**{vpc['f1_macro']:.3f}** | {vsh['f1_macro']:.3f} | {psh['f1_macro']:.3f} |"
        )

    # triage flag: does semantic_candidate concentrate VitaminC REFUTES + lexical FPs?
    vit = [r for r in rows if r["corpus"] == "vitaminc"]
    flagged = [r for r in vit if r["semantic_candidate"]]
    ref_in = sum(1 for r in flagged if r["label"] == 0)
    ref_all = sum(1 for r in vit if r["label"] == 0)
    base_rate = ref_all / len(vit)
    prec = (ref_in / len(flagged)) if flagged else 0.0
    # base-model false positives (missed hallucinations, shared-threshold) concentration
    fp_rows = [t[4] for t in base_rec if t[1] == 0 and t[2] == 1]
    fp_flag = sum(1 for r in fp_rows if r["semantic_candidate"])
    flag_rate = sum(1 for r in rows if r["semantic_candidate"]) / len(rows)
    out.append(
        f"\n### semantic_candidate triage flag\n"
        f"- VitaminC coverage: {len(flagged)}/{len(vit)} = {len(flagged) / len(vit):.0%} flagged; "
        f"REFUTES inside flag {ref_in}/{len(flagged)} = {prec:.0%} (base rate {base_rate:.0%})\n"
        f"- base-model missed-hallucinations (FP) inside flag: {fp_flag}/{len(fp_rows)} = "
        f"{(fp_flag / len(fp_rows)) if fp_rows else 0:.0%} (overall flag rate {flag_rate:.0%})\n"
    )
    report = "\n".join(out) + "\n"
    print(report)
    (Path(__file__).parent / "logs").mkdir(exist_ok=True)
    (Path(__file__).parent / "logs" / "lab_joint.md").write_text(report)


# --- short-source probe (measurement only; never trains, never enters CV) -----
# Tiny 1-line-source pairs that expose the degenerate-IDF failure mode. Each is
# (claim, source, label) with label 1=supported / 0=hallucination. Spans
# distinctive-present (should confirm) and distinctive-absent (should reject).
_PROBE: list[tuple[str, str, int]] = [
    # false-negative regime: distinctive token IS in the 1-line source -> supported
    ("there is an orchard on the estate", "The estate has three walled gardens and an orchard.", 1),
    ("the estate has three walled gardens", "The estate has three walled gardens and an orchard.", 1),
    ("a trout stream runs along the boundary", "A trout stream runs along the eastern boundary.", 1),
    ("the manor was restored in 1998", "The manor was built in 1820 and restored in 1998.", 1),
    ("rainfall averages 800 millimetres", "Rainfall in the region averages 800 millimetres per year.", 1),
    # false-positive regime: distinctive token ABSENT -> hallucination
    ("quantum physics", "Only about horticulture.", 0),
    ("the estate runs a commercial brewery", "The estate has three walled gardens and an orchard.", 0),
    ("the estate has a helicopter landing pad", "The estate has three walled gardens and an orchard.", 0),
    ("a private airport serves the estate", "The estate has three walled gardens and an orchard.", 0),
    ("tropical island paradise", "The quick brown fox jumps over the lazy dog.", 0),
    ("the vineyard covers fifty hectares", "The vineyard covers twelve hectares on the south slope.", 0),
    ("the manor was built in 1650", "The manor was built in 1820 and restored in 1998.", 0),
]


def _probe_feats(claim: str, source: str) -> dict:
    """_JOINT_CUR features for one English short-source pair (mirrors build_lex;
    is_en=same_lang=1, no MT). Honours the active BG_BLEND_LAMBDA via chunk_recalls."""
    from rapidfuzz import fuzz

    chunks = H.chunk_text(source, *H.CHUNK)
    rt, at, best = chunk_recalls(claim, chunks, H.an_word, bg_idf_fn=H.bg_idf, bg_lang="en")
    r1 = rt[at] if rt else 0.0
    charng = H.idf_best_chunk_recall(claim, chunks, H.an_charngram)
    fz = fuzz.partial_ratio(claim.lower(), best.lower()) / 100.0 if best else 0.0
    oracle = max(rt) if rt else 0.0
    top = sorted(rt, reverse=True)
    top3 = top[1] if len(top) >= 2 else (top[0] if top else 0.0)
    ents = H.list_claim_entities(claim)
    absent = set(H.find_absent_entities(claim, source))
    num_rec, num_mm = H.number_recall(claim, source)
    aden = len(ents) + (1 if num_rec >= 0 else 0)
    ahit = sum(1 for e in ents if e not in absent) + (num_rec if num_rec >= 0 else 0)
    anchor = (ahit / aden) if aden else 0.0
    nmm, emm = H.find_mismatches(claim, best) if best else ([], [])
    amm = 1 if (nmm or emm or num_mm) else 0
    unmatched_rarity, max_unmatched = gap_rarity(claim, best)
    spec, _hedge = claim_intrinsic(claim)
    conflict_n, conflict_flag, num_edit_mag = conflict_feats(claim, best)
    wn_flip = int(wn_antonym_flip(claim, best) and fz > 0.5)
    conflict_any = int(conflict_flag or wn_flip)
    return dict(
        r1_direct=r1, r1_mt=r1, r1_best=r1, charng=charng, fuzzy=fz, anchor=anchor,
        anchor_mm=amm, oracle=oracle, top3=top3, same_lang=1, is_en=1, specificity=spec,
        conflict_n=conflict_n, conflict_flag=conflict_flag, num_edit_mag=num_edit_mag,
        wn_antonym_flip=wn_flip, r1_x_conflict=r1 * conflict_any,
        unmatched_rarity=unmatched_rarity, max_unmatched=max_unmatched,
    )


def run_probe(per_label: int = 400, refresh: bool = False) -> None:
    """Score the short-source probe through the shipped (_JOINT_CUR) joint manifold.
    Measurement only: the probe never trains and never enters the benchmark CV."""
    from sklearn.linear_model import LogisticRegression

    cols = _cur_cols()
    rows = build_joint(per_label, refresh=refresh)
    Xtr = np.array([[r[c] for c in cols] for r in rows], dtype=float)
    ytr = np.array([r["label"] for r in rows])
    m = LogisticRegression(max_iter=1000, class_weight="balanced").fit(Xtr, ytr)
    thr = _tune_thr(ytr, m.predict_proba(Xtr)[:, 1])
    out = [
        f"## Short-source probe (BG_BLEND_LAMBDA={H.BG_BLEND_LAMBDA}, thr={thr:.2f})\n",
        "| ok | lab | pred | proba | r1 | fuzzy | unmatched | claim |",
        "|---|---|---|---|---|---|---|---|",
    ]
    correct = 0
    for claim, source, lab in _PROBE:
        f = _probe_feats(claim, source)
        proba = float(m.predict_proba(np.array([[f[c] for c in cols]], dtype=float))[0, 1])
        pred = int(proba >= thr)
        ok = pred == lab
        correct += ok
        out.append(
            f"| {'Y' if ok else 'N'} | {lab} | {pred} | {proba:.3f} | {f['r1_best']:.3f} | "
            f"{f['fuzzy']:.3f} | {f['unmatched_rarity']:.3f} | {claim[:38]} |"
        )
    out.append(f"\n**probe accuracy: {correct}/{len(_PROBE)} = {correct / len(_PROBE):.0%}**\n")
    report = "\n".join(out) + "\n"
    print(report)
    (Path(__file__).parent / "logs").mkdir(exist_ok=True)
    (Path(__file__).parent / "logs" / "lab_probe.md").write_text(report)


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _augment_rows(n_per_class: int = 200) -> list[dict]:
    """Truncation-derived short-source regime rows from English gold.

    Positives keep the max-overlap (evidence) source sentence; negatives keep the
    MIN-overlap sentence (still unsupported). Label inherited from gold; only the
    source LENGTH changes - the axis of the failure mode. Tagged corpus='aug' with
    its own CV group so it is held out as a unit (no benchmark contamination)."""
    gold = H.load_gold()
    eng = [r for r in gold if r.det_lang == "en"]
    pos = [r for r in eng if r.label == 1][:n_per_class]
    neg = [r for r in eng if r.label == 0][:n_per_class]
    out = []
    for k, r in enumerate(pos + neg):
        sents = [s.strip() for s in _SENT_SPLIT.split(r.source) if len(s.strip()) > 10]
        if len(sents) < 2:
            continue
        ctoks = set(H.an_word(r.claim))
        ov = lambda s: len(ctoks & set(H.an_word(s)))  # noqa: E731
        sent = max(sents, key=ov) if r.label == 1 else min(sents, key=ov)
        f = _probe_feats(r.claim, sent)
        out.append(dict(f, label=r.label, corpus="aug", grp=f"aug{k % 10}", src=-1))
    return out


def run_aug(per_label: int = 400, n_aug: int = 200, refresh: bool = False) -> None:
    """Research: does truncation augmentation un-stick the short-source regime?
    Trains on benchmark + aug (aug in own CV group), scores the disjoint probe,
    and reports the benchmark hold (grouped CV) + standardized coefficients."""
    from sklearn.linear_model import LogisticRegression

    cols = _cur_cols()
    base = build_joint(per_label, refresh=refresh)
    aug = _augment_rows(n_aug)
    rows = base + aug
    X = np.array([[r[c] for c in cols] for r in rows], float)
    y = np.array([r["label"] for r in rows])
    m = LogisticRegression(max_iter=1000, class_weight="balanced").fit(X, y)
    thr = _tune_thr(y, m.predict_proba(X)[:, 1])
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
    cd = dict(zip(cols, LogisticRegression(max_iter=1000, class_weight="balanced").fit(Xs, y).coef_[0]))
    # Gate A: grouped-CV on the benchmark rows only (aug held out by its own grp)
    rec = _joint_oof(rows, cols)
    dpc = _corpus_score(rec, "private_rag", 3)["f1_macro"]
    vpc = _corpus_score(rec, "vitaminc", 3)["f1_macro"]
    # Gate B: disjoint probe
    correct, lines = 0, []
    for claim, source, lab_ in _PROBE:
        f = _probe_feats(claim, source)
        p = float(m.predict_proba(np.array([[f[c] for c in cols]], dtype=float))[0, 1])
        pred = int(p >= thr)
        ok = pred == lab_
        correct += ok
        lines.append(f"| {'Y' if ok else 'N'} | {lab_} | {pred} | {p:.3f} | {f['r1_best']:.3f} | "
                     f"{f['unmatched_rarity']:.3f} | {claim[:34]} |")
    print(f"\n## Augmentation research (lambda={H.BG_BLEND_LAMBDA}, aug={len(aug)}, thr={thr:.2f})")
    print(f"Gate A (benchmark hold): private RAG pc {dpc:.3f} | VitaminC pc {vpc:.3f}  "
          f"(baseline 0.825 / 0.661)")
    print(f"coef: top3 {cd.get('top3', 0):+.2f} | unmatched_rarity {cd.get('unmatched_rarity', 0):+.2f} "
          f"| max_unmatched {cd.get('max_unmatched', 0):+.2f} | fuzzy {cd.get('fuzzy', 0):+.2f}")
    print(f"Gate B probe: **{correct}/{len(_PROBE)}**")
    print("| ok | lab | pred | proba | r1 | unmatched | claim |\n|---|---|---|---|---|---|---|")
    print("\n".join(lines))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "batch1"
    if cmd == "joint":
        run_joint(refresh="--refresh" in sys.argv)
    elif cmd == "probe":
        run_probe(refresh="--refresh" in sys.argv)
    elif cmd == "aug":
        run_aug(refresh="--refresh" in sys.argv)
    else:
        {
            "b1": run_b1,
            "a4": run_a4,
            "final": run_final,
            "bayes": run_bayes,
            "lexgbm": run_lexgbm,
            "seg": run_seg,
            "batch1": main,
        }.get(cmd, main)()
