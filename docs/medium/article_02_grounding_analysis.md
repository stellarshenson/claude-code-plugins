# Grounding analysis: `article_02_summary.md` vs `article_02_svg-infographics.md`

End-to-end test of the new `document-processing ground-many` CLI on a
hand-written summary of the "Stop Fixing Your AI's SVGs" article. Eleven
claims were fed in: 9 derived from the source, 2 deliberately fabricated
as negative controls.

## Command

```bash
document-processing ground-many \
  --claims /tmp/grounding-demo/claims.json \
  --source docs/medium/article_02_svg-infographics.md \
  --output /tmp/grounding-demo/report.md \
  --threshold 0.85 \
  --bm25-threshold 0.4
```

Full report at `/tmp/grounding-demo/report.md`. Runtime: well under one second (semantic layer disabled — three-layer lexical only).

## Headline numbers

| Layer | Claims grounded |
|-------|-----------------|
| Exact (regex) | 2 |
| Fuzzy (Levenshtein) | 3 |
| BM25 (topical) | 4 |
| Unconfirmed | 2 |
| **Total** | **11** |

**Grounding score: 9/11 = 81.8%.** Both "unconfirmed" claims are the fabricated ones — perfect separation.

## Per-claim breakdown

### Exact matches (verbatim quotes)

| # | Claim | Layer score | Location |
|---|-------|-------------|----------|
| 4 | "snapping, smart connectors, alignment guides, a colour swatch, and a layer panel" | exact 1.000 | L53:C72 ¶15 |
| 7 | "eighteen shape primitives" | exact 1.000 | L107:C3 ¶37 |

Both quoted the source byte-for-byte (case-insensitive in #7). The tool pinpointed line + column + paragraph, so the grounding agent can cite directly — no re-read.

### Fuzzy matches (close paraphrases)

| # | Claim | Fuzzy | BM25 | Location |
|---|-------|-------|------|----------|
| 2 | "When you ask an LLM to 'draw an SVG infographic'…" | 0.965 | 1.000 | L51:C1 ¶14 |
| 5 | "3-6 hours of hand-editing with zero creative value" | 0.960 | 1.000 | L75:C1 ¶26 |
| 8 | "contrast - WCAG 2.1 for text AND objects in both light and dark mode" | 0.956 | 1.000 | L99:C8 ¶35 |

All three are very close to verbatim — the difference is single-character punctuation or formatting (smart quotes, asterisks around bold markers, leading dash). Levenshtein caught them at 95%+ similarity.

### BM25 topical matches (same terms, different wording)

| # | Claim | Fuzzy | BM25 | Location |
|---|-------|-------|------|----------|
| 1 | "snap-to-grid placement, smart connectors, alignment guides, and a quality gate" | 0.692 | 0.667 | L55 ¶16 |
| 3 | "Every number is a token prediction, nothing snaps" | 0.796 | 0.875 | L51 ¶14 |
| 6 | "twelve tools via the svg-infographics CLI, split into six design tools and six validators" | 0.663 | 0.615 | L81 ¶29 |
| 9 | "paraphrase of design philosophy: tools handle coordinates so agent focuses on where and what" | 0.533 | 0.500 | L85 ¶31 |

These are the interesting cases. Fuzzy didn't clear its 0.85 threshold — the wording differs enough that character-level distance is high. But BM25 sees the shared key terms ("snap", "grid", "connector", "alignment", "twelve", "tools", "CLI", "design", "validators") and correctly points at the right passage. This is exactly what BM25 is for: **finding where a claim is supported even when the exact wording diverges**.

Claim 9 is the most distant paraphrase — BM25 score 0.500 is just above the 0.4 threshold. The winning passage ("the agent says *where* and *what*, the tools handle exact coordinates") semantically matches the claim even though the wording is inverted.

### Unconfirmed (the negative controls)

| # | Claim | Best score | Outcome |
|---|-------|-----------|---------|
| 10 | "The plugin requires a GPU with at least 16GB of VRAM" | fuzzy 0.500, bm25 0.273 | UNCONFIRMED ✓ |
| 11 | "Kubernetes orchestration runs on 42 nodes" | fuzzy 0.512, bm25 0.167 | UNCONFIRMED ✓ |

Both fabricated claims fell below every threshold. The tool reported the best-available weak matches for diagnostics (fuzzy caught spurious character overlap; BM25 token recall was 27% / 17%) so a reviewer can see exactly why the claim failed — no lexical signal in the source for any of the distinctive terms (`GPU`, `VRAM`, `Kubernetes`, `orchestration`, `42 nodes`).

## What the output gave the agent (without re-reading)

For every confirmed claim the agent receives:

- **Three scores** (`exact_score`, `fuzzy_score`, `bm25_score`) — disagreement across layers is itself a signal (high fuzzy + low BM25 = character overlap without semantic match; low fuzzy + high BM25 = paraphrase with same terms)
- **Winning passage quoted** — paste-ready into a citation block
- **Location metadata** — `L<line>:C<column> ¶<paragraph>` (and `pg<n>` for PDFs) to cite precisely
- **Context before/after** — a line of surrounding prose for verification

The agent never needs a second read of the source to produce a grounding report — that directly saves tokens, which was the stated design goal.

## Cross-layer signal patterns

Observing patterns across the 9 confirmed claims:

- **All three at 1.000** (exact + fuzzy + bm25): verbatim quote. Claims #4, #7.
- **High fuzzy + 1.000 BM25**: near-verbatim with punctuation drift. Claims #2, #5, #8.
- **Low fuzzy + high BM25**: same terms reordered or paraphrased. Claim #3 (similar shape but "number" vs "coordinate"), #6, #1.
- **All three low but BM25 ≥ threshold**: distant paraphrase, topic-matched. Claim #9 — risk flag for the reviewer.

Unconfirmed claims had ALL three signals consistently low, which is the cleanest negative-signal pattern: no character match, no fuzzy alignment, no shared terminology.

## Design verdict

The three-layer design did what the user asked: each layer fires on a different kind of grounding, and the claim is classified by the strongest signal. The agent gets precise locations so it can cite without re-reading, and the fabricated claims separated cleanly from the real ones.

The semantic (ModernBERT + FAISS) layer was not run here — the three lexical layers were sufficient for this summary, which stays close to the source wording. Semantic would earn its keep on longer, more abstract claims that share meaning without sharing vocabulary (a position paper vs a hearing transcript, for example).

## Token cost comparison (measured)

Measured with `tiktoken` (`cl100k_base`) for this run: 11 claims against the 3,031-token source article.

| Approach | Input tokens | Output tokens | Total |
|----------|-------------:|--------------:|------:|
| Generative, one call per claim (naive) | 38,995 | 2,200 | **41,195** |
| Generative, one batched call | 3,687 | 2,200 | **5,887** |
| CLI grounding (this run) | 0 | 2,117 | **2,117** |

Savings: **64% vs batched generative**, **95% vs naive per-claim**. Report includes full quoted passages + locations + context; a `--json`-only mode would roughly halve the output. Scale is linear in source size — a 30-page source would save ~16K tokens per grounding pass vs the batched generative alternative.

Caveats: prompt caching on a static source tips batched generative back up somewhat; CLI wins cleanly on fresh-source workflows and grows its lead as source size or claim count grows.

## Follow-ups worth trying

- Re-run with `--semantic on` once a user has installed `[semantic]` extras — see whether any of the paraphrased claims move from "BM25 topical" up to "semantic" with higher confidence.
- Try the same pipeline against a longer article where paragraphs are split across pages via form-feed — verify `page` field populates.
- Feed a deliberately fabricated claim close in wording to the source (e.g. "six-image article" → "four-image article") to confirm fuzzy + BM25 agree on the number mismatch.
