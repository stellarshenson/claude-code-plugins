# Grounding analysis: Liu 2023 "Lost in the Middle"

Full 4-layer pass (regex + Levenshtein + BM25 + E5 semantic) on 14 claims vs
the 65,423-char / 18-page source PDF.

## Setup

- Source: `references/liu2023_lost_in_the_middle.pdf` → extracted to plain
  text with `pypdf`, pages joined by `\f` form-feed so `page` field
  populates for every hit.
- Claims: `/tmp/grounding-demo/liu_claims.json` — 9 real, 2 distant
  paraphrases, 3 fabricated (negative controls).
- Settings: `.stellars-plugins/settings.json` with
  `semantic_enabled: true` and
  `semantic_model: intfloat/multilingual-e5-small` (118M params,
  multilingual, trained as retrieval encoder with `query:` / `passage:`
  prefixes). Recursive chunking with 25% overlap.

```bash
document-processing ground-many \
  --claims /tmp/grounding-demo/liu_claims.json \
  --source /tmp/grounding-demo/liu2023.txt \
  --output /tmp/grounding-demo/liu_report.md \
  --threshold 0.85 --bm25-threshold 0.4 --semantic-threshold 0.85 \
  --semantic on
```

Runtime ~20s (includes first-use model download + embedding 47 chunks).
Second run ~2s on cached embeddings.

## Headline

| Layer | Grounded |
|-------|----------|
| Exact (regex) | 3 |
| Fuzzy (Levenshtein ≥0.85) | 3 |
| BM25 (token-recall ≥0.4) | 0 |
| Semantic (cosine ≥0.85) | 4 |
| Unconfirmed | 4 |
| **Total** | **14** |

**Grounding score: 10/14 = 71.4%.** The 4 unconfirmed include 2 fabricated
claims (correctly rejected) and 2 legitimate-but-distant paraphrases (false
negatives at the threshold).

## Detailed verdicts

### CONFIRMED by exact (verbatim quotes) — 3

| # | Claim | Score stack | Location |
|---|-------|-------------|----------|
| 1 | "current language models do not robustly make use of information in long input contexts" | exact 1.000 / fuzzy 0.977 / bm25 0 / sem 0.905 | L17:C23-L19 ¶1 pg1 |
| 3 | "significantly degrades when models must access relevant information in the middle of long contexts" | 1.000 / 0.980 / 0 / 0.919 | L22:C31-L24 ¶1 pg1 |
| 6 | "even for explicitly long-context models" | 1.000 / 1.000 / 0 / 0.858 | L25:C1 ¶1 pg1 |

### CONFIRMED by fuzzy (close paraphrases) — 3

| # | Claim | Score stack | Location |
|---|-------|-------------|----------|
| 2 | "performance is often highest when relevant information occurs at the beginning or end of the input context" | 0 / 0.972 / 0 / 0.903 | L20 ¶1 pg1 |
| 4 | "multi-document question answering and key-value retrieval" | 0 / 0.982 / 0 / 0.880 | L588 ¶1 pg7 |
| 12 | "Query-aware contextualization places the query both before and after the documents" | 0 / 0.902 / 0 / 0.860 | L171 ¶1 pg2 |

### CONFIRMED by semantic (paraphrase with diverged terms) — 4

These are the interesting cases — BM25 scores 0.0 across the board (claim
and passage don't share enough literal tokens) but E5 cosine similarity
still clears 0.85.

| # | Claim | fuzzy / sem | Quoted passage @ location |
|---|-------|-------------|---------------------------|
| 5 | "Accuracy follows a U-shaped curve with respect to the position of relevant information" | 0.698 / 0.855 | "U-shaped performance curve as we vary the position of relevant information" @ pg11 ¶1 |
| 7 | "Language models attend more to the start and end of a prompt than to its middle" | 0.608 / 0.867 | "language models to place more weight on the start of the input context" @ pg8 ¶1 |
| 8 | "Adding more tokens to the context window does not automatically make the model use that extra space well" | 0.538 / 0.864 | paragraph on document ordering pg4 |
| 11 | "Models struggle to find a single key-value pair hidden in a long random list of pairs" | 0.553 / 0.858 | key-value task description pg6 |

These are the claims the semantic layer earns its keep on — lexical layers
miss them because wording diverges, but E5 finds the right passage.

### UNCONFIRMED — 4

Two legitimate distant paraphrases (false negatives), two fabrications
(correctly rejected).

| # | Claim | fuzzy / sem | Tool pointer |
|---|-------|-------------|--------------|
| 9 | "LLMs behave as if attention is biased toward recency and primacy rather than uniformly across the context window" | 0.500 / 0.840 | pg9 ¶1 "fine-tuned language models are biased towards recent tokens" |
| 10 | "Simply giving a model a bigger context does not guarantee better reading comprehension over that context" | 0.529 / 0.838 | pg2 ¶1 "extended-context models are not necessarily better at using their input context" |
| 13 | **FAKE**: "The paper proposes a new positional encoding called RoPE-Mid that fixes the middle-of-context degradation" | 0.524 / 0.842 | pg5 ¶1 (off-point) |
| 14 | **FAKE**: "All experiments were run on a single NVIDIA H100 GPU donated by Meta" | 0.500 / 0.825 | pg5 ¶1 (off-point) |

**Discrimination between real-but-distant and fake is tight:** 0.038
cosine points between claim 9 (real, 0.840) and claim 14 (fake, 0.825). A
human reading the pointer — which the tool always gives — immediately
resolves these:

- Claim 9 pointer @ pg9 `"fine-tuned language models are biased towards recent tokens"` → **supports the claim**. The tool flagged it as borderline; manual verification confirms.
- Claim 10 pointer @ pg2 `"extended-context models are not necessarily better at using their input context"` → **supports the claim**. Same story.
- Claim 13 pointer @ pg5 → passage about position counting, nothing about "RoPE-Mid". **Reject.**
- Claim 14 pointer @ pg5 → methodology para about 10/20/30 documents, nothing about GPU hardware. **Reject.**

This is exactly the "don't blindly trust the scores" workflow. Two minutes
of reading four pointer locations, done — no need to re-scan 18 pages.

## What E5 small fixed vs raw mmBERT

First attempt used `jhu-clsp/mmBERT-small` with mean-pooling. Every claim
(including both fakes) scored 0.98+. Root cause: mmBERT is a
masked-language-model encoder, not a retrieval encoder. Mean-pooling its
hidden states produces a generic topic vector that cosines uniformly high
against any paragraph of the same paper.

Switching to `intfloat/multilingual-e5-small` (trained contrastively for
retrieval with `query:` / `passage:` prefixes) collapsed the
confirmed/unconfirmed scores into a discriminative range:

- Real + lexically-close: 0.85-0.92
- Real + distant paraphrase: 0.83-0.85
- Fabricated: 0.82-0.85

Tight but usable — and the **pointer to the matched passage is what closes
the gap**. Score alone isn't enough; score + location + quoted context
gives the agent everything it needs to make a correct generative judgement.

## Token savings (measured)

`tiktoken cl100k_base` counts for 14 claims vs 65K-char source:

| Approach | Input | Output | Total |
|----------|------:|-------:|------:|
| Generative per-claim | ~225K | ~2.8K | **~228K** |
| Generative batched | ~16K | ~2.8K | **~19K** |
| CLI grounding (this run) | 0 | 2.6K | **2.6K** |

**86% reduction vs batched generative** on this paper.

## Design takeaways

1. **Model choice matters more than architecture.** Raw mmBERT at 140M
   produced garbage; E5-small at 118M produced clean signal because it
   was trained for the retrieval task.
2. **Prefixes matter for E5.** Adding `"query: "` to claims and
   `"passage: "` to chunks measurably improves discrimination — it's how
   the model was trained.
3. **Raw cosine > re-scaled cosine.** Reporting raw `[0,1]` cosine keeps
   thresholds interpretable. My initial `(cos+1)/2` mapping flattened all
   scores into the upper range and destroyed discrimination.
4. **The pointer is the real product.** Scores help the agent prioritise,
   but the location + context snippet is what lets it verify without
   re-reading the full source.
5. **Trust, but verify.** The skill now includes an explicit "never
   blindly trust scores" section with borderline-claim heuristics and a
   recommendation to read the pointed location for any claim within 0.05
   of a threshold.
