# Research: deterministic cross-lingual claim-grounding toolbox

Survey of installable, CPU-fast, offline, permissively-licensed Python tools for grounding NO/SV/FR/IT/ES/PT claims against English evidence **without** training any model on the target data. Compiled 2026-06-03 from web research. Pairs with `HYPOTHESIS.md` (the experiment) and feeds `harness.py` (the implementation).

## Pick per task

| Task | Tier 1 | Tier 2 | Skip |
|---|---|---|---|
| Offline MT | CTranslate2 + OPUS-MT int8 (~250 ms/sent CPU, <100 MB) | argos-translate (MIT, simpler) | NLLB-200 full (GPU-only) |
| Bilingual lexicon | PanLex snapshot (1.1B pairs, CC-BY-SA) | kaikki.org Wiktionary JSONL (free, weekly) | IATE (sparse for NO/SV) |
| CLIR | query-translate → BM25S | dict-expansion (PanLex) + BM25 | vector fusion (needs embeddings) |
| Cognate / orthographic | rapidfuzz Damerau-Levenshtein (have it) | epitran G2P→IPA + rapidfuzz | abydos (slow, exotic) |
| Compound split (nb/sv) | CharSplit (~95% de, supports NO/SV) | compound-split | SECOS (needs corpus tuning) |
| Negation | per-language cue lists (no package covers these langs) | negspaCy + custom termsets | NegEx research variants |
| Number / unit | Babel locale parse (decimal-comma) + text2num | quantulum3 (units) | pint (only if unit arithmetic) |
| Language ID (short) | lingua-py (~0.95 on short text, Apache-2.0) | fastText lid.176 (faster) | CLD3 (~0.73 short) |
| Faithfulness scoring | token-recall + negation scope + BM25 | BM25 score as confidence | fuzzy token alignment |

## Notes that change the harness

- **Language ID:** swap `langdetect` → **lingua-py** (`lingua-language-detector`); it is the most accurate on the short claims where the gold `lang` field was noisy. Deterministic, all six languages.
- **MT bridge:** **argos-translate** for the simplest offline path (`argos no→en`, `sv→en`, …); **CTranslate2 + OPUS-MT int8** if speed matters. Frozen black box, not fit to the 375 → within the anti-overfit rule, but report it in its own tier (a small model, not pure-lexical). Time it; gate behind a flag.
- **Number normalization:** **Babel** parses locale decimals (`1,5` nb/sv/fr → 1.5) - the decimal-comma fix the catalogue missed; **quantulum3** for unit-bearing quantities.
- **Lexicon (X2):** bootstrap from **kaikki.org** per-language `*-en.jsonl` Wiktionary dumps + private RAG catalogue/manual term pairs. Offline, label-free, leakage-safe.
- **Compound split (nb/sv):** **CharSplit** / **compound-split** to expose cognate sub-parts (`melkeutskiller`→`melke`+`utskiller`).
- **Negation:** no package covers NO/SV/FR/IT/ES/PT - hand cue lists (`ikke/inte/non/pas/não/no/ingen/aucun/kunde inte`).

## Faithfulness methods worth citing

- Token-recall / coverage grounding (the R1 protagonist) - susceptible to negation, hence the negation-flip signal.
- Delexicalization for fact verification (arXiv:1909.09868) - mask lexical tokens, keep structure.
- WiCE (arXiv:2303.01432) - token-level "which claim tokens are unsupported".
- FEVER (arXiv:1803.05355) - retrieve-then-classify; deterministic variant = negation scope + token overlap.

## Install (experiment-only, --user)

```bash
pip install --user lingua-language-detector rapidfuzz bm25s Babel \
  quantulum3 text2num unidecode
# optional / heavier:
pip install --user argos-translate          # MT bridge (flagged, timed)
pip install --user epitran compound-split    # IPA cognate, Germanic compound
```

Licences: OPUS-MT (Apache/CC-BY), CTranslate2/rapidfuzz/epitran/negspaCy/text2num (MIT), lingua-py (Apache-2.0), PanLex/Wiktionary (CC-BY-SA - attribute).
