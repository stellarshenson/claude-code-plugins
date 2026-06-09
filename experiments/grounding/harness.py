"""Rival deterministic grounder tournament on the private RAG cross-lingual gold.

Read-only experiment harness. Loads the git-ignored verified gold
(``private-rag-forensics/gold/golden_grounding_evidence_verified.parquet``:
``{claim, source_text, label, lang}``, grew 375 → 1260 → 2631 records),
computes rival deterministic grounding signals, and scores them under a hard
anti-overfit protocol (50/50 held-out, leave-one-language-out, fixed-prior).
No learner is fit to the test fold - thresholds come from held-out folds or
fixed priors only.

Signals (each a per-record scalar in [0,1] unless noted):
  R1  word IDF best-chunk recall            (Gap A: same-language)
  R2  char n-gram IDF best-chunk recall     (cognate-robust, language-agnostic)
  R3  phonetic-skeleton IDF best-chunk recall
  X1  anchor recall + anchor mismatch       (language-invariant; contradiction)
  X2  lexicon-canonicalised recall          (curated NO/SV/.. -> EN)
  X3  cognate/orthographic fuzzy recall
  creative: number-format containment, negation flip, meta-claim inversion,
            co-location bonus, MT bridge (optional), function-word lang id.

Usage:
  python harness.py --profile              # language/anchor profile of the gold
  python harness.py --baselines            # majority + recall baselines
  python harness.py --sweep R1             # chunk size/overlap/strategy sweep by AUC
  python harness.py --tournament           # full LOLO tournament (todo pass 2)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np
from rank_bm25 import BM25Okapi

# prefer the dev source tree (has nli.py + latest grounding) over the installed pkg
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# --- reuse production primitives ---------------------------------------------
from stellars_claude_code_plugins.document_processing.chunking import recursive_chunk
from stellars_claude_code_plugins.document_processing.entity_check import (
    find_absent_entities,
    find_mismatches,
    list_claim_entities,
)
from stellars_claude_code_plugins.document_processing.grounding import _tokenize

GOLD = Path(__file__).parent / "private-rag-forensics/gold/golden_grounding_evidence_verified.parquet"

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


# --- data --------------------------------------------------------------------
@dataclass
class Record:
    claim: str
    source: str
    label: int  # 1 supported, 0 hallucination
    lang: str  # gold field (noisy)
    det_lang: str = ""  # re-derived


def load_gold(path: Path = GOLD) -> list[Record]:
    if path.suffix == ".parquet":
        import pandas as pd

        raw = pd.read_parquet(path, columns=["claim", "source_text", "label", "lang"]).to_dict(
            "records"
        )
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))
    recs = [
        Record(
            claim=r["claim"],
            source=r["source_text"],
            label=int(r["label"]),
            lang=str(r.get("lang") or "und"),
        )
        for r in raw
    ]
    _detect_languages(recs)
    return recs


DETECTOR = "langdetect"  # or "lingua" (exp#6); set via --lingua


def _detect_languages(recs: list[Record]) -> None:
    """Re-derive claim language (gold ``lang`` is noisy: sv-SE rows are English)."""
    if DETECTOR == "lingua":
        try:
            from lingua import LanguageDetectorBuilder

            det = LanguageDetectorBuilder.from_all_languages().build()
            for r in recs:
                lg = det.detect_language_of(r.claim)
                r.det_lang = lg.iso_code_639_1.name.lower() if lg else "und"
            return
        except Exception:
            pass
    from langdetect import DetectorFactory, detect

    DetectorFactory.seed = 0
    for r in recs:
        try:
            r.det_lang = detect(r.claim)
        except Exception:
            r.det_lang = "und"


# --- text normalisation ------------------------------------------------------
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


# --- chunkers: (text, size, overlap, strategy) -> list[str] -------------------
def chunk_text(text: str, size: int, overlap: float, strategy: str) -> list[str]:
    if size <= 0 or size >= len(text):  # whole-doc
        return [text] if text.strip() else []
    if strategy == "recursive":
        return [
            c.text
            for c in recursive_chunk(text, max_chars=size, overlap_ratio=overlap)
            if c.text.strip()
        ]
    if strategy == "char":  # blind sliding char window
        step = max(1, int(size * (1.0 - overlap)))
        out = [text[i : i + size] for i in range(0, len(text), step)]
        return [c for c in out if c.strip()]
    if strategy == "sentence":
        sents = re.split(r"(?<=[.!?])\s+", text)
        out, buf = [], ""
        for s in sents:
            if len(buf) + len(s) <= size:
                buf = (buf + " " + s).strip()
            else:
                if buf:
                    out.append(buf)
                buf = s
        if buf:
            out.append(buf)
        return [c for c in out if c.strip()]
    raise ValueError(f"unknown strategy {strategy!r}")


# --- analyzers: text -> list[token] ------------------------------------------
def an_word(text: str) -> list[str]:
    return _tokenize(text)


def an_charngram(text: str, lo: int = 3, hi: int = 5) -> list[str]:
    s = strip_accents(text.lower())
    grams: list[str] = []
    for tok in _TOKEN_RE.findall(s):
        t = f"#{tok}#"
        for n in range(lo, hi + 1):
            grams.extend(t[i : i + n] for i in range(len(t) - n + 1))
    return grams


_VOWELS = set("aeiou")


def _skeleton(tok: str) -> str:
    t = strip_accents(tok.lower())
    out: list[str] = []
    for i, c in enumerate(t):
        if i == 0:
            out.append(c)
            continue
        if c in _VOWELS:
            continue
        if out and out[-1] == c:
            continue
        out.append(c)
    return "".join(out)


def an_phonetic(text: str) -> list[str]:
    return [k for t in _TOKEN_RE.findall(text.lower()) if (k := _skeleton(t))]


ANALYZERS = {"word": an_word, "charngram": an_charngram, "phonetic": an_phonetic}


# --- background (population) token rarity -------------------------------------
# In-context BM25 IDF degenerates on a 1-chunk source (N=1 -> every token floors
# to the same weight), so recall cannot tell distinctive content from filler in
# that regime. A length-robust background IDF from wordfreq does not collapse;
# blending it as a soft floor (max of in-context and lambda*background) only
# bites when the in-context weight has collapsed - on normal multi-chunk sources
# the in-context weight for a distinctive token already exceeds the floor.
import os as _os

BG_BLEND_LAMBDA = float(_os.environ.get("BG_LAMBDA", "0.0"))  # 0 = off; tuned on probe


def bg_idf(tok: str, lang: str = "en") -> float:
    """Background (population) IDF of a token: -log10(wordfreq). Unknown -> 9.0.

    Length-robust: independent of the source being grounded, so it does not
    collapse on a single-chunk source the way in-context BM25 IDF does."""
    from wordfreq import word_frequency

    f = word_frequency(tok, lang)
    return -math.log10(f) if f > 0 else 9.0


def _blend_weight(idf: dict, max_idf: float, bg_idf_fn, bg_lang: str):
    """Token-weight closure: in-context IDF, soft-floored by lambda*background IDF
    when ``bg_idf_fn`` is given (word analyzer only; never char n-grams)."""
    if bg_idf_fn is None or BG_BLEND_LAMBDA <= 0.0:
        return lambda t: max(0.0, idf.get(t, max_idf))
    return lambda t: max(0.0, idf.get(t, max_idf), BG_BLEND_LAMBDA * bg_idf_fn(t, bg_lang))


# --- IDF best-chunk recall (the protagonist; generalises _bm25_match) ---------
def idf_best_chunk_recall(
    claim: str,
    chunks: list[str],
    analyzer,
    return_best: bool = False,
    bg_idf_fn=None,
    bg_lang: str = "en",
):
    """IDF-weighted fraction of claim tokens present in the BM25-best chunk.

    Asymmetric, claim-anchored, peak-over-chunks. Out-of-corpus claim tokens
    get max IDF (a claim whose distinctive terms are absent cannot score high).
    Mirrors ``grounding._bm25_match`` token_recall, analyzer-pluggable.
    With ``return_best`` also returns the raw text of the BM25-best chunk.
    ``bg_idf_fn`` (word analyzer only) soft-floors the in-context IDF with a
    length-robust background rarity so recall stays honest on 1-chunk sources.
    """
    cl = analyzer(claim)
    if not cl:
        return (0.0, "") if return_best else 0.0
    pairs = [(c, a) for c in chunks if (a := analyzer(c))]
    if not pairs:
        return (0.0, "") if return_best else 0.0
    raw_chunks = [c for c, _ in pairs]
    corpus = [a for _, a in pairs]
    bm = BM25Okapi(corpus)
    scores = np.maximum(bm.get_scores(cl), 0.0)
    if float(scores.max()) == 0.0:
        return (0.0, raw_chunks[0]) if return_best else 0.0
    bi = int(scores.argmax())
    best = set(corpus[bi])
    claim_set = set(cl)
    idf = bm.idf
    max_idf = max(idf.values()) if idf else 1.0
    w = _blend_weight(idf, max_idf, bg_idf_fn, bg_lang)

    den = sum(w(t) for t in claim_set)
    if den > 0:
        recall = sum(w(t) for t in claim_set if t in best) / den
    else:
        recall = len(claim_set & best) / len(claim_set)
    return (recall, raw_chunks[bi]) if return_best else recall


# --- creative deterministic signals ------------------------------------------
_NUM_RE = re.compile(r"\d[\d.,   ]*\d|\d")


def _num_variants(s: str) -> set[str]:
    base = s.strip(" .,  ")
    return {
        v
        for v in {
            base,
            base.replace(",", "."),
            base.replace(".", ","),
            re.sub(r"[.,   ]", "", base),
        }
        if v
    }


def _numbers(text: str) -> set[str]:
    out: set[str] = set()
    for m in _NUM_RE.finditer(text):
        out |= _num_variants(m.group())
    return out


def number_recall(claim: str, source: str) -> tuple[float, bool]:
    """Locale-robust number containment + mismatch (decimal-comma aware)."""
    cn = [m.group() for m in _NUM_RE.finditer(claim)]
    if not cn:
        return (-1.0, False)  # no numeric anchors
    src = _numbers(source)
    present = sum(1 for n in cn if _num_variants(n) & src)
    return (present / len(cn), present < len(cn))


_NEG_CUES = {
    "ikke",
    "ingen",
    "aldri",
    "inte",
    "aldrig",
    "pas",
    "non",
    "aucun",
    "aucune",
    "jamais",
    "nessun",
    "nessuna",
    "mai",
    "no",
    "nunca",
    "ningun",
    "ningún",
    "não",
    "nao",
    "nenhum",
    "not",
    "never",
    "cannot",
    "n't",
    "without",
}
_META_RE = re.compile(
    r"fant ikke|jeg fant|finner ikke|kunne ikke|ingen informasjon|hittade inte|"
    r"not specified|does not specify|do(es)? not (contain|mention|provide)|"
    r"no information|not found|unable to|cannot find|no menci|no se especifica|"
    r"no encontr|não encontr|nao encontr|non ho trovato|non è specificat|"
    r"je n'ai pas|aucune information|n'est pas",
    re.I,
)


def _is_negated(text: str) -> bool:
    toks = set(_TOKEN_RE.findall(text.lower()))
    return bool(toks & _NEG_CUES)


def is_meta_claim(claim: str) -> bool:
    return bool(_META_RE.search(claim))


# --- optional MT bridge (frozen pre-trained translator; flagged + timed) ------
_MT = {}
_OPUS: dict = {}
MT_ENGINE = "argos"  # or "opus" (exp#3); set via --mt-engine
# langdetect ISO -> argos model code (argos uses 'nb' for Norwegian Bokmal)
_ISO_MT = {"no": "nb", "nn": "nb"}


def _opus_translate(text: str) -> str:
    """exp#3: OPUS-MT multilingual->English (one Helsinki-NLP/opus-mt-mul-en model)."""
    if "model" not in _OPUS:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        name = "Helsinki-NLP/opus-mt-mul-en"
        _OPUS["tok"] = AutoTokenizer.from_pretrained(name)
        _OPUS["model"] = AutoModelForSeq2SeqLM.from_pretrained(name)
        _OPUS["torch"] = torch
    tok, m, torch = _OPUS["tok"], _OPUS["model"], _OPUS["torch"]
    enc = tok([text], return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        gen = m.generate(**enc, max_length=256, num_beams=1)
    return tok.decode(gen[0], skip_special_tokens=True)


def mt_to_english(text: str, src_iso2: str) -> str:
    """Translate via a frozen offline engine (argos default, opus optional)."""
    if src_iso2 in ("en", "und", ""):
        return text
    if MT_ENGINE == "opus":
        try:
            return _opus_translate(text)
        except Exception:
            return text
    code = _ISO_MT.get(src_iso2, src_iso2)
    if code not in _MT:
        try:
            import argostranslate.translate as at
        except Exception:
            return text
        langs = {lg.code: lg for lg in at.get_installed_languages()}
        src = langs.get(code) or langs.get(code.split("-")[0])
        en = langs.get("en")
        _MT[code] = src.get_translation(en) if src and en else None
    tr = _MT[code]
    try:
        return tr.translate(text) if tr else text
    except Exception:
        return text


# --- featurization (computed once per chunk operating point, cached) ----------
def featurize(
    recs: list[Record], size: int, overlap: float, strategy: str, use_mt: bool = False
) -> list[dict]:
    rows = []
    for r in recs:
        chunks = chunk_text(r.source, size, overlap, strategy)
        claim = r.claim
        if use_mt and r.det_lang not in ("en", "und", ""):
            claim = mt_to_english(claim, r.det_lang)
        r1, best = idf_best_chunk_recall(claim, chunks, an_word, return_best=True)
        r2 = idf_best_chunk_recall(claim, chunks, an_charngram)
        r3 = idf_best_chunk_recall(claim, chunks, an_phonetic)
        # anchors: entities + numbers present in full source
        ents = list_claim_entities(r.claim)
        absent = set(find_absent_entities(r.claim, r.source))
        n_ent = len(ents)
        ent_present = sum(1 for e in ents if e not in absent)
        num_rec, num_mismatch = number_recall(r.claim, r.source)
        anchor_den = n_ent + (1 if num_rec >= 0 else 0)
        anchor_hit = ent_present + (num_rec if num_rec >= 0 else 0)
        anchor_recall = (anchor_hit / anchor_den) if anchor_den else -1.0
        # contradiction: numeric/entity mismatch vs best chunk, or negation flip
        num_mm, ent_mm = find_mismatches(r.claim, best)
        neg_flip = _is_negated(r.claim) != _is_negated(best) and r1 > 0.15
        contra = 1 if (num_mm or ent_mm or num_mismatch or neg_flip) else 0
        rows.append(
            {
                "label": r.label,
                "lang": r.lang,
                "det_lang": r.det_lang,
                "is_en": int(r.det_lang == "en"),
                "r1": r1,
                "r2": r2,
                "r3": r3,
                "anchor_recall": anchor_recall,
                "bridge": max(r2, anchor_recall if anchor_recall >= 0 else 0.0),
                "contra": contra,
                "meta": int(is_meta_claim(r.claim)),
            }
        )
    return rows


# --- combiners (no fit): f, thresholds -> {0,1} -------------------------------
def v_global(f: dict, t: dict) -> int:
    if f["contra"]:
        return 0
    if f["meta"]:
        return 1 if (f["anchor_recall"] < 0 or f["anchor_recall"] < t["meta"]) else 0
    if f["r1"] >= t["rec"]:
        return 1
    if f["bridge"] >= t["bridge"]:
        return 1
    return 0


def v_routed(f: dict, t: dict) -> int:
    if f["contra"]:
        return 0
    if f["meta"]:
        return 1 if (f["anchor_recall"] < 0 or f["anchor_recall"] < t["meta"]) else 0
    if f["is_en"]:
        return 1 if f["r1"] >= t["rec_en"] else 0
    if f["bridge"] >= t["bridge"]:
        return 1
    if f["r1"] >= t["rec_x"]:
        return 1
    return 0


def v_weighted(f: dict, t: dict) -> int:
    # hand-set prior weights (no fit); only the bias threshold may move on dev
    z = (
        -2.0
        + 3.5 * f["r1"]
        + 1.5 * f["r2"]
        + 1.5 * (f["anchor_recall"] if f["anchor_recall"] >= 0 else 0.0)
        - 3.0 * f["contra"]
    )
    if f["meta"]:
        z = 2.0 - 4.0 * (f["anchor_recall"] if f["anchor_recall"] >= 0 else 0.0)
    p = 1.0 / (1.0 + np.exp(-z))
    return int(p >= t["thr"])


def v_tree(f: dict, t: dict) -> int:
    if f["contra"]:
        return 0
    if f["meta"]:
        return 1 if (f["anchor_recall"] < 0 or f["anchor_recall"] < t["meta"]) else 0
    if f["r1"] >= t["hi"]:
        return 1
    if f["r1"] >= t["lo"] and f["bridge"] >= t["bridge"]:
        return 1
    return 0


def v_recall_only(f: dict, t: dict) -> int:  # ablation rung 1 (the null model)
    return int(f["r1"] >= t["rec"])


def v_recall_contra(f: dict, t: dict) -> int:  # ablation rung 2
    return 0 if f["contra"] else int(f["r1"] >= t["rec"])


def v_recall_split(f: dict, t: dict) -> int:  # exp#1: separate native-en vs translated bar
    thr = t["rec_en"] if f["is_en"] else t["rec_x"]
    return int(f["r1"] >= thr)


COMBINERS = {
    "global": (v_global, {"rec": "R", "bridge": "R", "meta": "M"}),
    "routed": (v_routed, {"rec_en": "R", "rec_x": "R", "bridge": "R", "meta": "M"}),
    "weighted": (v_weighted, {"thr": "P"}),
    "tree": (v_tree, {"hi": "R", "lo": "R", "bridge": "R", "meta": "M"}),
    "recall_only": (v_recall_only, {"rec": "R"}),
    "recall_contra": (v_recall_contra, {"rec": "R"}),
    "recall_split": (v_recall_split, {"rec_en": "R", "rec_x": "R"}),
}
_GRID = {
    "R": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],  # recall/bridge thresholds
    "M": [0.2, 0.3, 0.5],  # meta anchor-absence cutoff
    "P": [0.3, 0.4, 0.5, 0.6, 0.7],  # logistic prob threshold
}


def _grids(spec: dict):
    import itertools

    keys = list(spec)
    for combo in itertools.product(*[_GRID[spec[k]] for k in keys]):
        yield dict(zip(keys, combo))


def tune(rows: list[dict], combiner_name: str) -> dict:
    """Pick thresholds maximising macro-F1 on the fold (imbalance-robust)."""
    fn, spec = COMBINERS[combiner_name]
    y = [r["label"] for r in rows]
    best_t, best_b = None, -1.0
    for t in _grids(spec):
        pred = [fn(r, t) for r in rows]
        b = score_verdicts(y, pred)["f1_macro"]
        if b > best_b:
            best_b, best_t = b, t
    return best_t


# --- split regimes -----------------------------------------------------------
def run_lolo(rows: list[dict], combiner_name: str) -> dict:
    fn, _ = COMBINERS[combiner_name]
    langs = sorted({r["det_lang"] for r in rows})
    y_true, y_pred = [], []
    for L in langs:
        train = [r for r in rows if r["det_lang"] != L]
        test = [r for r in rows if r["det_lang"] == L]
        if len({r["label"] for r in train}) < 2:
            continue
        t = tune(train, combiner_name)
        for r in test:
            y_pred.append(fn(r, t))
            y_true.append(r["label"])
    return score_verdicts(y_true, y_pred)


def run_heldout(rows: list[dict], combiner_name: str, seed: int = 0) -> dict:
    fn, _ = COMBINERS[combiner_name]
    rng = np.random.default_rng(seed)
    # stratified by (label, lang)
    from collections import defaultdict

    buckets = defaultdict(list)
    for i, r in enumerate(rows):
        buckets[(r["label"], r["lang"])].append(i)
    dev, test = [], []
    for b in buckets.values():
        b = list(b)
        rng.shuffle(b)
        dev += b[: len(b) // 2]
        test += b[len(b) // 2 :]
    t = tune([rows[i] for i in dev], combiner_name)
    yp = [fn(rows[i], t) for i in test]
    yt = [rows[i]["label"] for i in test]
    return score_verdicts(yt, yp)


# --- metrics -----------------------------------------------------------------
def cohens_d(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return 0.0
    p, n = np.array(pos), np.array(neg)
    psd = np.sqrt(((p.var() * len(p)) + (n.var() * len(n))) / (len(p) + len(n)))
    return float((p.mean() - n.mean()) / psd) if psd > 0 else 0.0


def auc(scores: list[float], labels: list[int]) -> float:
    from sklearn.metrics import roc_auc_score

    if len(set(labels)) < 2:
        return float("nan")
    return float(roc_auc_score(labels, scores))


def score_verdicts(y_true: list[int], y_pred: list[int]) -> dict:
    from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    acc = (tp + tn) / max(1, len(y_true))
    bal = balanced_accuracy_score(y_true, y_pred)
    rec_pos = tp / max(1, tp + fn)
    rec_neg = tn / max(1, tn + fp)
    # F1 (imbalance-robust headline): macro = mean of supported-F1 and hallucination-F1
    f1_sup = f1_score(y_true, y_pred, pos_label=1, zero_division=0)
    f1_hal = f1_score(y_true, y_pred, pos_label=0, zero_division=0)
    return {
        "acc": acc,
        "bal": bal,
        "f1_macro": (f1_sup + f1_hal) / 2,
        "f1_sup": f1_sup,
        "f1_hal": f1_hal,
        "rec_sup": rec_pos,
        "rec_hal": rec_neg,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
    }


# --- reports -----------------------------------------------------------------
def cmd_profile(recs: list[Record]) -> None:
    from collections import Counter

    print(
        f"records: {len(recs)}  supported: {sum(r.label for r in recs)}  "
        f"hallucination: {sum(1 for r in recs if r.label == 0)}"
    )
    gold = Counter(r.lang for r in recs)
    det = Counter(r.det_lang for r in recs)
    print(f"gold lang : {dict(gold.most_common())}")
    print(f"detected  : {dict(det.most_common())}")
    mism = sum(1 for r in recs if r.lang.split("-")[0] != r.det_lang)
    print(f"gold-vs-detected mismatch: {mism}/{len(recs)}")


def cmd_sweep(recs: list[Record], signal: str) -> None:
    """Chunk size/overlap/strategy sweep, ranked by AUC of peak recall (no threshold)."""
    analyzer = ANALYZERS[signal]
    sizes = [150, 300, 600, 1200, 0]  # 0 = whole-doc
    overlaps = [0.0, 0.1, 0.25]
    strategies = ["recursive", "sentence", "char"]
    labels = [r.label for r in recs]
    rows = []
    for strat in strategies:
        for size in sizes:
            for ov in overlaps:
                if size == 0 and ov != 0.0:
                    continue  # overlap meaningless for whole-doc
                scores = [
                    idf_best_chunk_recall(r.claim, chunk_text(r.source, size, ov, strat), analyzer)
                    for r in recs
                ]
                a = auc(scores, labels)
                pos = [s for s, lab in zip(scores, labels) if lab == 1]
                neg = [s for s, lab in zip(scores, labels) if lab == 0]
                rows.append((a, cohens_d(pos, neg), strat, size, ov))
    rows.sort(key=lambda x: (-(x[0] if x[0] == x[0] else 0), -x[1]))
    print(f"\nchunk sweep for signal {signal!r} (ranked by AUC of peak recall)\n")
    print(f"{'AUC':>6} {'d':>6}  {'strategy':<10} {'size':>6} {'overlap':>7}")
    for a, d, strat, size, ov in rows:
        sz = "whole" if size == 0 else str(size)
        print(f"{a:6.3f} {d:6.2f}  {strat:<10} {sz:>6} {ov:>7.2f}")


def cmd_baselines(recs: list[Record]) -> None:
    labels = [r.label for r in recs]
    # majority: always grounded
    maj = score_verdicts(labels, [1] * len(recs))
    print(f"majority(always-1) : acc={maj['acc']:.3f} bal={maj['bal']:.3f}")
    # recall signals at a default operating point (recursive 300/0.1), threshold-free AUC
    for sig, an in ANALYZERS.items():
        scores = [
            idf_best_chunk_recall(r.claim, chunk_text(r.source, 300, 0.1, "recursive"), an)
            for r in recs
        ]
        a = auc(scores, labels)
        pos = [s for s, lab in zip(scores, labels) if lab == 1]
        neg = [s for s, lab in zip(scores, labels) if lab == 0]
        print(
            f"{sig:>10} recall : AUC={a:.3f}  d={cohens_d(pos, neg):.2f}  "
            f"mean_sup={np.mean(pos):.3f} mean_hal={np.mean(neg):.3f}"
        )


def per_language_lolo(rows: list[dict], combiner_name: str) -> dict:
    """LOLO recall per held-out language (each language scored out-of-fold)."""
    fn, _ = COMBINERS[combiner_name]
    out = {}
    langs = sorted({r["det_lang"] for r in rows})
    for L in langs:
        train = [r for r in rows if r["det_lang"] != L]
        test = [r for r in rows if r["det_lang"] == L]
        if len({r["label"] for r in train}) < 2 or not test:
            continue
        t = tune(train, combiner_name)
        correct = sum(1 for r in test if fn(r, t) == r["label"])
        out[L] = (correct / len(test), len(test))
    return out


# point chosen from the sweep; recursive 300/0.1 validated as a strong operating point
CHUNK = (300, 0.1, "recursive")


def cmd_tournament(recs: list[Record], use_mt: bool = False) -> str:
    import time

    t0 = time.time()
    rows = featurize(recs, *CHUNK, use_mt=use_mt)
    feat_s = time.time() - t0
    ms_claim = 1000 * feat_s / len(recs)
    labels = [r.label for r in recs]
    maj = score_verdicts(labels, [1] * len(recs))

    order = [
        "recall_only", "recall_split", "recall_contra",
        "tree", "global", "routed", "weighted",
    ]
    results = []
    for name in order:
        lolo = run_lolo(rows, name)
        test = run_heldout(rows, name)
        results.append((name, lolo, test))
    results.sort(key=lambda x: -x[1]["f1_macro"])

    lines = []
    lines.append("# Tournament results - private RAG gold (375 records)\n")
    lines.append(
        f"Chunk operating point: {CHUNK[2]} size={CHUNK[0]} overlap={CHUNK[1]}  "
        f"| MT bridge: {'on' if use_mt else 'off'}  | featurize {feat_s:.1f}s "
        f"(~{ms_claim:.0f} ms/claim)\n"
    )
    lines.append(
        "Headline = **macro-F1** (imbalance-robust) under leave-one-language-out; "
        "every record scored out-of-fold. TEST = stratified 50/50. No combiner fit to the 375.\n"
    )
    lines.append(
        f"Reference: majority-always-grounded macroF1={maj['f1_macro']:.3f} "
        f"(sup-F1={maj['f1_sup']:.3f} hal-F1={maj['f1_hal']:.3f}) acc={maj['acc']:.3f}\n"
    )
    lines.append("| combiner | LOLO macroF1 | sup-F1 | hal-F1 | LOLO acc | TEST macroF1 | TEST acc |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, lo, te in results:
        lines.append(
            f"| {name} | **{lo['f1_macro']:.3f}** | {lo['f1_sup']:.2f} | {lo['f1_hal']:.2f} | "
            f"{lo['acc']:.3f} | {te['f1_macro']:.3f} | {te['acc']:.3f} |"
        )
    # per-language LOLO for the winner
    win = results[0][0]
    pl = per_language_lolo(rows, win)
    lines.append(f"\nPer-language LOLO accuracy for winner ({win}):\n")
    lines.append("| lang | acc | n |")
    lines.append("|---|---|---|")
    for L, (a, n) in sorted(pl.items(), key=lambda x: -x[1][1]):
        lines.append(f"| {L} | {a:.2f} | {n} |")

    # exp#7: fixed-prior - no tuning at all, score all 375 at a principled threshold
    lines.append("\n## Fixed-prior (zero tuning, all 375) - the 'ships untouched' bound\n")
    lines.append("| rule | threshold | macroF1 | acc | bal |")
    lines.append("|---|---|---|---|---|")
    for tau in (0.4, 0.5, 0.6):
        pred = [int(r["r1"] >= tau) for r in rows]
        s = score_verdicts(labels, pred)
        lines.append(f"| recall_only | {tau:.2f} | {s['f1_macro']:.3f} | {s['acc']:.3f} | {s['bal']:.3f} |")

    # exp#8: abstain band - three-way verdict, fixed band, report coverage + covered F1
    lines.append("\n## Abstain band (fixed lo=0.30 hi=0.55) - precision/coverage trade\n")
    lo_b, hi_b = 0.30, 0.55
    cov = [(int(r["r1"] >= hi_b), r["label"]) for r in rows if not (lo_b <= r["r1"] < hi_b)]
    coverage = len(cov) / len(rows)
    if cov:
        cs = score_verdicts([y for _, y in cov], [p for p, _ in cov])
        lines.append(f"coverage {coverage:.2f} ({len(cov)}/{len(rows)}), "
                     f"macroF1-on-covered {cs['f1_macro']:.3f}, "
                     f"balanced-on-covered {cs['bal']:.3f}\n")
    report = "\n".join(lines) + "\n"
    print(report)
    return report


def cmd_ablation(recs: list[Record], use_mt: bool = False) -> str:
    rows = featurize(recs, *CHUNK, use_mt=use_mt)
    ladder = ["recall_only", "recall_contra", "global", "weighted"]
    lines = [
        "\n## Ablation ladder (LOLO macro-F1)\n",
        "| rung | LOLO macroF1 | delta |",
        "|---|---|---|",
    ]
    prev = None
    for name in ladder:
        b = run_lolo(rows, name)["f1_macro"]
        d = "-" if prev is None else f"{b - prev:+.3f}"
        lines.append(f"| {name} | {b:.3f} | {d} |")
        prev = b
    report = "\n".join(lines) + "\n"
    print(report)
    return report


def cmd_residual(recs: list[Record], use_mt: bool = True) -> str:
    """exp#4/#5: NLI entailment on the residual the recall stack misses.

    NLI is parameter-free (argmax of entailment/neutral/contradiction), so it is
    scored directly on all 375 - no fold, no overfitting. Premise = best English
    chunk (selected via the translated claim); hypothesis = original claim
    (mDeBERTa NLI is multilingual). Ensemble = recall(MT, fixed tau) OR NLI-entail.
    """
    from stellars_claude_code_plugins.document_processing.nli import NLIGrounder

    nli = NLIGrounder()
    labels = [r.label for r in recs]
    rows = featurize(recs, *CHUNK, use_mt=use_mt)
    nli_pred, ens_pred = [], []
    for r, row in zip(recs, rows):
        chunks = chunk_text(r.source, *CHUNK)
        translated = r.claim
        if use_mt and r.det_lang not in ("en", "und", ""):
            translated = mt_to_english(r.claim, r.det_lang)
        _, best = idf_best_chunk_recall(translated, chunks, an_word, return_best=True)
        sc = nli.scores(best, r.claim)
        g = 1 if sc.get("entailment", 0) >= max(sc.get("neutral", 0), sc.get("contradiction", 0)) else 0
        nli_pred.append(g)
        ens_pred.append(1 if (row["r1"] >= 0.4 or g == 1) else 0)
    rec_pred = [int(row["r1"] >= 0.4) for row in rows]
    lines = ["## NLI residual (#4/#5) - parameter-free (argmax), all 375\n"]
    lines.append("| rule | macroF1 | sup-F1 | hal-F1 | acc | bal |")
    lines.append("|---|---|---|---|---|---|")
    for name, pred in [("recall_only τ0.4", rec_pred), ("NLI-alone", nli_pred),
                       ("recall OR NLI", ens_pred)]:
        s = score_verdicts(labels, pred)
        lines.append(f"| {name} | **{s['f1_macro']:.3f}** | {s['f1_sup']:.2f} | "
                     f"{s['f1_hal']:.2f} | {s['acc']:.3f} | {s['bal']:.3f} |")
    lines.append("\nPer-language accuracy (tail focus):\n")
    lines.append("| lang | n | recall | NLI | ensemble |")
    lines.append("|---|---|---|---|---|")
    for L in sorted({r.det_lang for r in recs}):
        idx = [i for i, r in enumerate(recs) if r.det_lang == L]
        if len(idx) < 3:
            continue
        ra = sum(1 for i in idx if rec_pred[i] == labels[i]) / len(idx)
        na = sum(1 for i in idx if nli_pred[i] == labels[i]) / len(idx)
        ea = sum(1 for i in idx if ens_pred[i] == labels[i]) / len(idx)
        lines.append(f"| {L} | {len(idx)} | {ra:.2f} | {na:.2f} | {ea:.2f} |")
    report = "\n".join(lines) + "\n"
    print(report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--baselines", action="store_true")
    ap.add_argument("--sweep", metavar="SIGNAL", choices=list(ANALYZERS))
    ap.add_argument("--tournament", action="store_true")
    ap.add_argument("--ablation", action="store_true")
    ap.add_argument("--residual", action="store_true", help="NLI residual (#4/#5)")
    ap.add_argument("--mt", action="store_true", help="enable the MT bridge (timed)")
    ap.add_argument("--mt-engine", choices=["argos", "opus"], default="argos")
    ap.add_argument("--lingua", action="store_true", help="use lingua-py for language ID")
    ap.add_argument("--write", action="store_true", help="write RESULTS.md")
    args = ap.parse_args()

    if args.lingua:
        global DETECTOR
        DETECTOR = "lingua"
    if args.mt_engine == "opus":
        global MT_ENGINE
        MT_ENGINE = "opus"
    recs = load_gold()
    out = []
    if args.profile:
        cmd_profile(recs)
    if args.baselines:
        cmd_baselines(recs)
    if args.sweep:
        cmd_sweep(recs, args.sweep)
    if args.tournament:
        out.append(cmd_tournament(recs, use_mt=args.mt))
    if args.ablation:
        out.append(cmd_ablation(recs, use_mt=args.mt))
    if args.residual:
        out.append(cmd_residual(recs, use_mt=args.mt))
    if args.write and out:
        (Path(__file__).parent / "RESULTS.md").write_text("\n".join(out), encoding="utf-8")
        print("wrote RESULTS.md")
    if not any([args.profile, args.baselines, args.sweep, args.tournament,
                args.ablation, args.residual]):
        ap.print_help()


if __name__ == "__main__":
    main()
