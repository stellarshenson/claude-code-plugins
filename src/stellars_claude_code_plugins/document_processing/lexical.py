"""Lexical grounding features + frozen-weight verdict for the grounder.

Consolidated lexical feature pipeline and a per-tier frozen-weight logistic head.
Reuses ``grounding._tokenize``, ``chunking.recursive_chunk`` and the
``entity_check`` helpers; no grounding logic is duplicated. Three effort tiers,
each its own ordered feature subset and its own shipped manifold; the grounder
selects the tier from config (``lexical_effort``) and computes only that tier's
features.

- low - monolingual word/char-ngram recall (wordfreq-floored), fuzzy, anchors, specificity, value-conflict, distinctive-content; 13 features, core install only
- medium - low + lingua language detection (is_en, same_lang) + WordNet antonym-flip; 16 features, needs lingua + nltk/WordNet
- high - medium + MT translate-then-recall (r1_mt, r1_best); 18 features, additionally needs the argos/CTranslate2 MT stack

Recall is soft-floored with a wordfreq background rarity so it stays honest on a
single-chunk source (where the in-context BM25 IDF degenerates), and the
distinctive-content features (unmatched_rarity, max_unmatched) isolate whether a
claim's rare tokens are present. Inference is scikit-learn-free: the verdict is a
dot-product + logistic sigmoid over config-stored weights. scikit-learn is
imported only on the training path (:func:`fit_lexical_manifold`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
import math
import re
import unicodedata

logger = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────────────────

CHARNGRAM_LO = 3
CHARNGRAM_HI = 5
CHUNK_MAX_CHARS = 300  # lexical operating point (harness.CHUNK = 300/0.1/recursive)
CHUNK_OVERLAP_RATIO = 0.1  # fit/extraction default; per-manifold value can override

# Background-IDF soft-floor for recall: w(t) = max(in-context, λ·background-rarity).
# In-context BM25 IDF collapses on a single-chunk source (N=1 -> every token one
# weight); the wordfreq background rarity does not, so the floor only bites when
# the in-context weight has degenerated. λ=0.5 validated on the short-source probe.
BG_BLEND_LAMBDA = 0.5

EFFORT_TIERS = ("low", "medium", "high")

# Per-tier ordered feature lists. The ORDER is the documented coefficient/audit
# contract; the config feature_order must match the tier's list exactly.
LOW_FEATURES = [
    "r1_direct",
    "charng",
    "fuzzy",
    "anchor",
    "anchor_mm",
    "oracle",
    "top3",
    "specificity",
    "conflict_n",
    "conflict_flag",
    "num_edit_mag",
    "unmatched_rarity",
    "max_unmatched",
]  # 13 - core install only
MEDIUM_FEATURES = LOW_FEATURES + ["is_en", "same_lang", "wn_antonym_flip"]  # 16 - + lingua + nltk
HIGH_FEATURES = [  # 18 - the e2e FEATS order, + MT recall + distinctive-content
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
    "unmatched_rarity",
    "max_unmatched",
]
TIER_FEATURES = {"low": LOW_FEATURES, "medium": MEDIUM_FEATURES, "high": HIGH_FEATURES}

LEXICAL_MIN_ROWS = 200  # training floor (CLI + tests share)
LEXICAL_MIN_PER_CLASS = 40

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_NUM_RE = re.compile(r"\d[\d.,   ]*\d|\d")

# Lazy caches for the optional-dependency helpers (lingua detector, WordNet).
_LINGUA: dict = {}
_WN: dict = {}
_LANG_CACHE: dict = {}  # text -> ISO code; detection is the per-row hot path


# ── text normalisation + analyzers (reuse grounding/chunking primitives) ─────


def _strip_accents(s: str) -> str:
    """Drop combining marks (NFKD). Port of harness.strip_accents."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _an_word(text: str) -> list[str]:
    """Word analyzer; wraps grounding._tokenize."""
    from stellars_claude_code_plugins.document_processing.grounding import _tokenize

    return _tokenize(text)


def _an_charngram(text: str, lo: int = CHARNGRAM_LO, hi: int = CHARNGRAM_HI) -> list[str]:
    """Accent-stripped char n-gram analyzer. Port of harness.an_charngram."""
    s = _strip_accents(text.lower())
    grams: list[str] = []
    for tok in _TOKEN_RE.findall(s):
        t = f"#{tok}#"
        for n in range(lo, hi + 1):
            grams.extend(t[i : i + n] for i in range(len(t) - n + 1))
    return grams


def _chunk(text: str, max_chars: int, overlap_ratio: float) -> list[str]:
    """Recursive-chunk the text at the lexical operating point; reuse chunking.recursive_chunk."""
    from stellars_claude_code_plugins.document_processing.chunking import recursive_chunk

    if not text:
        return []
    if max_chars <= 0 or max_chars >= len(text):
        return [text] if text.strip() else []
    return [
        c.text
        for c in recursive_chunk(text, max_chars=max_chars, overlap_ratio=overlap_ratio)
        if c.text.strip()
    ]


# ── background (population) token rarity + recall helpers ────────────────────

_BG_CACHE: dict = {}


def _bg_idf(tok: str, lang: str = "en") -> float:
    """Background (population) IDF of a token: -log10(wordfreq). Unknown -> 9.0.

    Length-robust - independent of the source being grounded, so it does not
    collapse on a single-chunk source the way in-context BM25 IDF does. Neutral
    0.0 (no floor) if wordfreq is somehow unimportable (it ships in core)."""
    key = (tok, lang)
    v = _BG_CACHE.get(key)
    if v is None:
        try:
            from wordfreq import word_frequency

            f = word_frequency(tok, lang)
            v = -math.log10(f) if f > 0 else 9.0
        except ImportError:
            logger.warning(
                "wordfreq not importable - recall floor + distinctive-content neutralised; "
                "it ships with the package, so reinstall stellars-claude-code-plugins"
            )
            v = 0.0
        _BG_CACHE[key] = v
    return v


def _chunk_recalls(claim: str, chunks: list[str], analyzer, bg_lang: str | None = None):
    """IDF-weighted claim recall against each chunk. Port of lab.chunk_recalls.

    Returns ``(recalls_per_chunk, bm25_argmax_index, best_chunk_text)``: decouples
    'which chunk' (bm25 argmax) from 'best possible chunk' (max recall = oracle).
    When ``bg_lang`` is given (word analyzer only), the in-context IDF is
    soft-floored with the wordfreq background rarity so recall stays honest on a
    single-chunk source where the in-context IDF degenerates.
    """
    import numpy as np
    from rank_bm25 import BM25Okapi

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

    if bg_lang is None or BG_BLEND_LAMBDA <= 0.0:

        def w(t: str) -> float:
            return max(0.0, idf.get(t, max_idf))
    else:

        def w(t: str) -> float:
            return max(0.0, idf.get(t, max_idf), BG_BLEND_LAMBDA * _bg_idf(t, bg_lang))

    den = sum(w(t) for t in claim_set) or 1.0
    recalls = [sum(w(t) for t in claim_set if t in set(doc)) / den for doc in corpus]
    arg = int(scores.argmax()) if float(scores.max()) > 0 else 0
    return recalls, arg, raw[arg]


def _gap_rarity(claim: str, best: str, lang: str = "en") -> tuple[float, float]:
    """Distinctive-content coverage. Port of lab.gap_rarity.

    Returns ``(unmatched_rarity, max_unmatched)``: the background-rarity-weighted
    fraction of the claim's content tokens absent from the best chunk, and the
    single rarest absent token (normalised). Spikes when a claim's distinctive
    tokens are missing - the signal aggregate recall cannot isolate."""
    toks = {t for t in _TOKEN_RE.findall(claim.lower()) if len(t) > 1}
    if not toks:
        return 0.0, 0.0
    chunk = set(_TOKEN_RE.findall(best.lower())) if best else set()
    idfs = {t: _bg_idf(t, lang) for t in toks}
    tot = sum(idfs.values()) or 1.0
    absent = [v for t, v in idfs.items() if t not in chunk]
    return (sum(absent) / tot, (max(absent) / 9.0) if absent else 0.0)


# ── numeric / anchor / conflict helpers (reuse entity_check) ─────────────────


def _num_variants(s: str) -> set[str]:
    base = s.strip(" .,  ")
    return {
        v
        for v in {
            base,
            base.replace(",", "."),
            base.replace(".", ","),
            re.sub(r"[.,   ]", "", base),
        }
        if v
    }


def _number_recall(claim: str, source: str) -> tuple[float, bool]:
    """Locale-robust number containment + mismatch. Port of harness.number_recall.

    Returns ``(recall, mismatch)``; recall is -1.0 when the claim has no numeric anchors.
    """
    cn = [m.group() for m in _NUM_RE.finditer(claim)]
    if not cn:
        return (-1.0, False)
    src: set[str] = set()
    for m in _NUM_RE.finditer(source):
        src |= _num_variants(m.group())
    present = sum(1 for n in cn if _num_variants(n) & src)
    return (present / len(cn), present < len(cn))


def _anchor(claim: str, full_source: str, best: str) -> tuple[float, float]:
    """Language-invariant anchor recall + anchor-mismatch flag.

    anchor = fraction of claim entities/numbers present in the full source;
    anchor_mm = 1 when the best passage disagrees on a number or tech entity.
    Reuses list_claim_entities, find_absent_entities, find_mismatches.
    """
    from stellars_claude_code_plugins.document_processing.entity_check import (
        find_absent_entities,
        find_mismatches,
        list_claim_entities,
    )

    ents = list_claim_entities(claim)
    absent = set(find_absent_entities(claim, full_source))
    num_rec, _ = _number_recall(claim, full_source)
    aden = len(ents) + (1 if num_rec >= 0 else 0)
    ahit = sum(1 for e in ents if e not in absent) + (num_rec if num_rec >= 0 else 0)
    anchor = (ahit / aden) if aden else 0.0
    nmm, emm = find_mismatches(claim, best) if best else ([], [])
    _, num_mm = _number_recall(claim, best) if best else (-1.0, False)
    anchor_mm = 1.0 if (nmm or emm or num_mm) else 0.0
    return anchor, anchor_mm


def _claim_specificity(claim: str) -> float:
    """Evidence-independent specificity: (claim entities + numbers) / tokens. Port of lab.claim_intrinsic."""
    from stellars_claude_code_plugins.document_processing.entity_check import list_claim_entities

    toks = _TOKEN_RE.findall(claim.lower())
    n = len(toks) or 1
    nums = len(re.findall(r"\d+", claim))
    return (len(list_claim_entities(claim)) + nums) / n


def _conflict_feats(claim: str, best: str) -> tuple[float, float, float]:
    """Aligned value-conflict against the best passage. Port of lab.conflict_feats.

    Returns ``(conflict_n, conflict_flag, num_edit_mag)``; overlap-gated by
    construction (a mismatch needs an aligned anchor), so absent-content
    negatives stay at zero.
    """
    from stellars_claude_code_plugins.document_processing.entity_check import (
        find_mismatches,
        list_claim_entities,
    )

    if not best:
        return 0.0, 0.0, 0.0
    nmm, emm = find_mismatches(claim, best)
    cnt = len(nmm) + len(emm)
    ents = list_claim_entities(claim)
    bl = best.lower()
    aligned_ent = sum(1 for e in ents if e.lower() in bl)
    nrec, _ = _number_recall(claim, best)
    aligned_num = 1 if nrec > 0 else 0
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
    return conflict_n, float(cnt > 0), mag


# ── optional-dependency helpers (lingua language id, WordNet antonyms) ───────


def _lingua_lang(text: str, min_len: int = 25) -> str:
    """Detect the dominant language ISO code; 'und' when too short or detector absent.

    Lazy + cached lingua import. Returns 'und' on missing dependency so MEDIUM/HIGH
    degrade to neutral language features rather than crashing. Port of lab._lingua_lang.
    """
    if len(text.strip()) < min_len:
        return "und"
    cached = _LANG_CACHE.get(text)
    if cached is not None:
        return cached
    if "det" not in _LINGUA:
        try:
            from lingua import LanguageDetectorBuilder

            _LINGUA["det"] = LanguageDetectorBuilder.from_all_languages().build()
        except ImportError:
            _LINGUA["det"] = None
            logger.warning(
                "lingua-language-detector not importable - language features neutralised; "
                "it ships with the package, so reinstall stellars-claude-code-plugins"
            )
    det = _LINGUA["det"]
    if det is None:
        return "und"
    lg = det.detect_language_of(text)
    iso = lg.iso_code_639_1.name.lower() if lg else "und"
    _LANG_CACHE[text] = iso
    return iso


def _wn_antonyms(w: str) -> set:
    """WordNet antonyms of a word; empty set on missing nltk/WordNet. Port of lab._wn_antonyms."""
    if "mod" not in _WN:
        try:
            import nltk
            from nltk.corpus import wordnet as wn

            try:
                wn.synsets("test")
            except LookupError:
                nltk.download("wordnet", quiet=True)
            _WN["mod"], _WN["cache"] = wn, {}
        except ImportError:
            _WN["mod"], _WN["cache"] = None, {}
            logger.warning(
                "nltk not importable - WordNet antonym feature neutralised; "
                "it ships with the package, so reinstall stellars-claude-code-plugins"
            )
    if _WN["mod"] is None:
        return set()
    cache = _WN["cache"]
    if w not in cache:
        ant: set[str] = set()
        for s in _WN["mod"].synsets(w):
            for lemma in s.lemmas():
                for a in lemma.antonyms():
                    ant.add(a.name().replace("_", " ").lower())
        cache[w] = ant
    return cache[w]


def _wn_antonym_flip(claim_en: str, best: str) -> int:
    """1 when a claim content-token's WordNet antonym is present in the best chunk while the token is absent."""
    if not best:
        return 0
    bset = set(_TOKEN_RE.findall(best.lower()))
    for t in _TOKEN_RE.findall(claim_en.lower()):
        if len(t) < 3 or t in bset:
            continue
        if _wn_antonyms(t) & bset:
            return 1
    return 0


# ── public feature extraction ────────────────────────────────────────────────


def extract_lexical_features(
    claim: str,
    sources: Sequence[str | tuple[str, str]],
    *,
    effort: str,
    chunk_max_chars: int = CHUNK_MAX_CHARS,
    chunk_overlap_ratio: float = CHUNK_OVERLAP_RATIO,
    det_lang: str | None = None,
    translate=None,
) -> dict[str, float]:
    """Compute the lexical feature dict for one effort tier.

    Single tier-gated pass over the claim and chunked sources; reuses
    grounding._tokenize, chunking.recursive_chunk and the entity_check helpers,
    computing only the features in ``TIER_FEATURES[effort]``.

    - low - monolingual word/char-ngram recall, fuzzy, anchors, specificity, value-conflict; core install only
    - medium - low + lingua language detection (is_en, same_lang) + WordNet antonym-flip
    - high - medium + MT translate-then-recall (r1_mt, r1_best), the 18-feature stack

    Args:
        claim - claim text
        sources - raw text or (path, text); concatenated for anchors, chunked once for recall
        effort - one of EFFORT_TIERS
        chunk_max_chars / chunk_overlap_ratio - recursive-chunk operating point (300 / 0.1)
        det_lang - optional precomputed claim ISO code; auto-detected (medium/high) when omitted
        translate - HIGH-tier MT callable (text, iso)->str; defaults to lexical_mt.translate

    Returns a dict whose keys are exactly TIER_FEATURES[effort]. A feature whose
    optional dependency is absent takes its neutral value (0.0); the verdict still
    scores. LOW never needs an optional dependency.
    """
    if effort not in TIER_FEATURES:
        raise ValueError(f"effort must be one of {EFFORT_TIERS}, got {effort!r}")
    from rapidfuzz import fuzz

    feats = set(TIER_FEATURES[effort])
    texts = [s[1] if isinstance(s, tuple) else s for s in sources]
    full_source = "\n".join(texts)
    chunks = _chunk(full_source, chunk_max_chars, chunk_overlap_ratio)

    # background-rarity language for the recall floor: the claim's own language
    # (wordfreq is multilingual), defaulting to English when unknown
    recall_lang = det_lang if det_lang not in (None, "und", "") else "en"

    # direct (original-claim) word recall over the chunk corpus (wordfreq-floored)
    rd, ad, best_text = _chunk_recalls(claim, chunks, _an_word, bg_lang=recall_lang)
    r1_direct = rd[ad] if rd and ad is not None else 0.0
    oracle = max(rd) if rd else 0.0
    top = sorted(rd, reverse=True)
    top3 = top[1] if len(top) >= 2 else (top[0] if top else 0.0)

    rc, ac, _ = _chunk_recalls(claim, chunks, _an_charngram)
    charng = rc[ac] if rc and ac is not None else 0.0
    fuzzy = fuzz.partial_ratio(claim.lower(), best_text.lower()) / 100.0 if best_text else 0.0
    anchor, anchor_mm = _anchor(claim, full_source, best_text)
    specificity = _claim_specificity(claim)
    conflict_n, conflict_flag, num_edit_mag = _conflict_feats(claim, best_text)

    out: dict[str, float] = {
        "r1_direct": r1_direct,
        "charng": charng,
        "fuzzy": fuzzy,
        "anchor": anchor,
        "anchor_mm": anchor_mm,
        "oracle": oracle,
        "top3": top3,
        "specificity": specificity,
        "conflict_n": conflict_n,
        "conflict_flag": conflict_flag,
        "num_edit_mag": num_edit_mag,
    }

    # claim language detected once, reused by medium (is_en/same_lang) and high (MT)
    needs_lang = bool(feats & {"is_en", "same_lang", "r1_mt", "r1_best"})
    clang = (det_lang if det_lang is not None else _lingua_lang(claim)) if needs_lang else "und"

    # medium / high: language detection + WordNet antonym-flip
    if "is_en" in feats or "same_lang" in feats or "wn_antonym_flip" in feats:
        out["is_en"] = float(clang == "en")
        chunk_lang = _lingua_lang(best_text) if best_text else "und"
        out["same_lang"] = float(clang != "und" and chunk_lang == clang)
        out["wn_antonym_flip"] = float(_wn_antonym_flip(claim, best_text) and fuzzy > 0.5)

    # distinctive-content coverage scored on the strongest recall view (English
    # post-MT for high when the claim was translated, else the direct claim)
    rarity_claim, rarity_best, rarity_lang = claim, best_text, recall_lang

    # high only: MT translate-then-recall (cross-lingual r1_mt / r1_best)
    if "r1_mt" in feats or "r1_best" in feats:
        r1_mt = r1_direct
        if clang not in ("en", "und", ""):
            tr = translate if translate is not None else _default_translate
            claim_en = tr(claim, clang)
            rt, at, mt_best = _chunk_recalls(claim_en, chunks, _an_word, bg_lang="en")
            r1_mt = rt[at] if rt and at is not None else 0.0
            rarity_claim, rarity_best, rarity_lang = claim_en, mt_best, "en"
        out["r1_mt"] = r1_mt
        out["r1_best"] = max(r1_direct, r1_mt)

    if "unmatched_rarity" in feats or "max_unmatched" in feats:
        ur, mu = _gap_rarity(rarity_claim, rarity_best, rarity_lang)
        out["unmatched_rarity"] = ur
        out["max_unmatched"] = mu

    return {k: out[k] for k in TIER_FEATURES[effort]}


def _default_translate(text: str, src_iso: str) -> str:
    """HIGH-tier MT bridge; lazy import so LOW/MEDIUM never touch the MT stack."""
    try:
        from stellars_claude_code_plugins.document_processing.lexical_mt import translate
    except ImportError as exc:
        raise ImportError(
            "high-tier MT recall needs the MT stack (argostranslate, ctranslate2, "
            "wtpsplit-lite); it ships with the package, so reinstall "
            "stellars-claude-code-plugins"
        ) from exc
    return translate(text, src_iso)


# ── frozen-weight verdict head ───────────────────────────────────────────────


@dataclass
class LexicalVerdict:
    """Frozen-weight logistic verdict over one tier's ordered feature set.

    Inference is dot-product + logistic sigmoid - no scikit-learn, no bambi, no
    sampling. Intercept + per-feature weights + feature order + threshold define
    the manifold; they live in config (calibration.lexical_manifolds.<tier>) and
    transfer verbatim.

    - weights - {"Intercept": b0, feature: w, ...}
    - feature_order - feature names in coefficient order (the config feature_order list)
    - threshold - decision cut on sigmoid(dot) for English (and the default for any claim)
    - threshold_non_en - optional separate cut for non-English claims (is_en < 0.5). The
      shipped weights are trained English-dominant; the cross-lingual recall signal (r1_mt)
      ranks non-English hallucinations below support but their probabilities sit above the
      English cut, so non-English needs its own (higher) threshold. None -> English cut for
      all claims (back-compat; tiers without an is_en feature always take the English cut).
    """

    weights: dict[str, float]
    feature_order: list[str]
    threshold: float = 0.5
    threshold_non_en: float | None = None

    def predict_proba(self, feat: dict[str, float]) -> float:
        """sigmoid(b0 + Σ w_i·feat_i) over the tier's ordered features."""
        z = float(self.weights.get("Intercept", 0.0))
        for name in self.feature_order:
            z += float(self.weights.get(name, 0.0)) * float(feat.get(name, 0.0))
        return 1.0 / (1.0 + math.exp(-z))

    def threshold_for(self, feat: dict[str, float]) -> float:
        """The decision cut for this claim: the non-English cut when one is configured and
        the claim is detected non-English (``is_en`` feature < 0.5), else the English cut.
        Absent ``is_en`` (LOW tier never computes it) -> English cut."""
        if self.threshold_non_en is not None and float(feat.get("is_en", 1.0)) < 0.5:
            return self.threshold_non_en
        return self.threshold

    def confirmed(self, feat: dict[str, float]) -> bool:
        """True when predict_proba >= the (language-conditional) threshold."""
        return self.predict_proba(feat) >= self.threshold_for(feat)

    @classmethod
    def from_config(cls, block: dict, effort: str) -> "LexicalVerdict | None":
        """Build from ``block['lexical_manifolds'][effort]``; None when absent.

        The manifold block carries ``threshold, feature_order, weights,
        chunk_max_chars, chunk_overlap_ratio``. Validates that feature_order
        matches TIER_FEATURES[effort].
        """
        manifolds = (block or {}).get("lexical_manifolds")
        if not manifolds or effort not in manifolds:
            return None
        m = manifolds[effort]
        order = list(m.get("feature_order") or TIER_FEATURES[effort])
        if order != TIER_FEATURES[effort]:
            raise ValueError(
                f"lexical_manifolds.{effort}.feature_order does not match the {effort} tier "
                f"contract; expected {TIER_FEATURES[effort]}, got {order}"
            )
        thr_ne = m.get("threshold_non_en")
        return cls(
            weights={k: float(v) for k, v in (m.get("weights") or {}).items()},
            feature_order=order,
            threshold=float(m.get("threshold", 0.5)),
            threshold_non_en=None if thr_ne is None else float(thr_ne),
        )


# ── fit path (training-only; scikit-learn imported here, never at inference) ──

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def short_source_augment(rows: list[dict], per_class: int | None = None) -> list[dict]:
    """Truncation-derived short-source regime rows for the training set.

    Each eligible source is cut to ONE sentence - the max-overlap evidence
    sentence for a supported claim, a low-overlap one for a hallucination - so the
    label is inherited from gold and only the source LENGTH changes (the axis of
    the single-chunk failure mode). This teaches the manifold to read the
    degenerate in-context-IDF regime (revived recall + distinctive-content) rather
    than a hand-set threshold. Returns new ``{claim, source_text, label, lang}``
    rows to concatenate onto the dataset before feature extraction.
    """
    pos = [r for r in rows if int(r["label"]) == 1]
    neg = [r for r in rows if int(r["label"]) == 0]
    if per_class is None:
        per_class = min(250, len(pos) // 3, len(neg) // 3)
    out: list[dict] = []
    for r in pos[:per_class] + neg[:per_class]:
        sents = [
            s.strip() for s in _SENT_SPLIT_RE.split(str(r["source_text"])) if len(s.strip()) > 10
        ]
        if len(sents) < 2:
            continue
        ctoks = set(_an_word(str(r["claim"])))
        ov = lambda s: len(ctoks & set(_an_word(s)))  # noqa: E731
        sent = max(sents, key=ov) if int(r["label"]) == 1 else min(sents, key=ov)
        out.append(
            {
                "claim": r["claim"],
                "source_text": sent,
                "label": int(r["label"]),
                "lang": r.get("lang"),
            }
        )
    return out


def fit_lexical_manifold(
    rows: list[dict],
    *,
    effort: str,
    threshold: float | None = None,
    chunk_max_chars: int = CHUNK_MAX_CHARS,
    chunk_overlap_ratio: float = CHUNK_OVERLAP_RATIO,
) -> dict:
    """Fit a logistic over ``TIER_FEATURES[effort]``; return the serializable manifold block.

    rows - dicts carrying the tier's feature keys + 'label' (0/1). Fits
    scikit-learn ``LogisticRegression(max_iter=1000, class_weight='balanced')``
    (imported inside the function; training-only). threshold is tuned on the
    training data by macro-F1 over a 0.2..0.8 grid when None.

    Returns ``{feature_order, threshold, weights:{Intercept, ...}, chunk_max_chars,
    chunk_overlap_ratio}`` - the exact shape LexicalVerdict.from_config consumes.
    """
    if effort not in TIER_FEATURES:
        raise ValueError(f"effort must be one of {EFFORT_TIERS}, got {effort!r}")
    import numpy as np
    from sklearn.linear_model import LogisticRegression

    cols = TIER_FEATURES[effort]
    x = np.array([[float(r.get(c, 0.0)) for c in cols] for r in rows], dtype=float)
    y = np.array([int(r["label"]) for r in rows])
    model = LogisticRegression(max_iter=1000, class_weight="balanced").fit(x, y)
    weights = {"Intercept": round(float(model.intercept_[0]), 6)}
    for c, w in zip(cols, model.coef_[0]):
        weights[c] = round(float(w), 6)

    if threshold is None:
        p = model.predict_proba(x)[:, 1]
        best, threshold = -1.0, 0.5
        for t in np.linspace(0.2, 0.8, 13):
            f = _macro_f1(y.tolist(), (p >= t).astype(int).tolist())
            if f > best:
                best, threshold = f, float(round(t, 4))

    return {
        "feature_order": list(cols),
        "threshold": float(threshold),
        "weights": weights,
        "chunk_max_chars": int(chunk_max_chars),
        "chunk_overlap_ratio": float(chunk_overlap_ratio),
    }


def _macro_f1(y_true: list[int], y_pred: list[int]) -> float:
    """Mean of supported-F1 and hallucination-F1; imbalance-robust fit metric."""
    from sklearn.metrics import f1_score

    sup = f1_score(y_true, y_pred, pos_label=1, zero_division=0)
    hal = f1_score(y_true, y_pred, pos_label=0, zero_division=0)
    return (sup + hal) / 2
