# Concept Draft Example - End-of-Increment Slide Deck

Reference for the **concept-drafting phase**: the plain-text spec an agent writes and gets
approved *before* any SVG is generated. Each ```svg-infographics``` block below is a content
spec, not markup - it names the canvas, the theme, every band, the concrete facts each band
carries, and the data source behind those facts. Approve the specs first; the SVGs are built
only after.

What makes this a good draft:

- **Narrative arc stated up front** - the deck tells one story across its slides; each slide's
  job is named before any card is placed
- **One theme, reused** - canvas size, palette and CSS skeleton are fixed once and referenced,
  not re-invented per slide
- **Concrete facts, not lorem** - every card, hero value and fact strip carries the real number
  it will show (29%, 80% → 92%, ~165 ms), so the layout is sized against real content
- **A graphic asked for as a graphic** - Slide 2 Panel 3 specifies a chunk-tile visual and says
  "no paragraph", so the builder knows the takeaway is carried visually
- **Sources cited per slide** - each number traces to where it came from, so review can verify
- **Open questions surfaced** - unresolved choices are listed for the reviewer, not guessed

Below: a three-slide deck for a fictional retrieval assistant ("Atlas Assistant", "Meridian"
theme). Slide 1 states two measured issues, slide 2 shows the reranker fixing retrieval, slide 3
shows the grounder detecting hallucination.

---

Three end-of-increment slides for the Atlas Assistant work. Each slide is a 16:9 SVG infographic
that replaces the placeholder text below it. The `svg-infographics` code blocks are the content
specs - read them first; the SVGs are generated only after these are approved.

Narrative arc: slide 1 states the two measured issues (hallucination and inadequate retrieval),
slide 2 shows the reranker fixing retrieval, slide 3 shows the grounder detecting hallucination.
Theme reuses the Meridian palette and skeleton already approved in the executive-summary deck
(title strip, card band, fact strip, italic strap; blue = structure/problem, red/amber = issue,
green = win; dual light/dark CSS).

Open questions for review:
- Slide 3 is speced on the **lexical** grounder (deterministic, torch-free, no NLI/LLM). The
  original brief said "NLI / entailment" - that is the separate semantic track. Confirm lexical,
  or ask to swap to the NLI semantic grounder
- English vs multilingual on slide 3 currently mixes metrics (English F1 0.81 vs non-English
  TNR 0.78 = share of hallucinations caught). Decide whether to align both to one metric
- Three slides / three SVGs assumed (the brief wavered between two and three)

---

## Slide 1 - Atlas Assistant: the two issues

```svg-infographics
canvas:  1280x720 (16:9). Meridian theme - reuse palette + CSS skeleton from the approved
         executive-summary deck. Blue structure, red/amber for the issues.

title strip (top-left):
  title:    "THE ISSUES"  (small-caps, navy)
  subtitle: "Atlas Assistant - what sits behind perceived hallucination. Two failure
             modes, both measured on production data: fabricated content, and retrieval
             that hands the model the wrong passages."

main band - TWO large issue cards (not four), problem accents:

  CARD A - Hallucination        (red accent header)
    headline value:  29%
    label:           OF STATEMENTS CONTAIN A HALLUCINATION
    sub:             786 of 2,752 labelled statements
    root cause:
      - the answer is never checked against its own retrieved evidence
      - invented facts surface when the retrieved material is thin
      - no answer-vs-evidence verification stage exists

  CARD B - Inadequate retrieval (amber accent header)
    headline value:  >20%
    label:           OF RETRIEVED CHUNKS ARE IRRELEVANT
    sub:             retrieval precision ~80% before reranking
    root cause:
      - passages are handed to the model in raw vector-search order
      - relevance is never scored - closest vector is not most useful
      - no filtering by machine model, so wrong-model docs reach the answer

fact strip (golden dataset, measured):
  639 real conversations | 9 languages | 2,752 labelled statements |
  29% contain hallucination | labelled by 2 independent AI judges

strap (italic):
  "The two issues this increment attacks - retrieval quality and hallucination detection -
   each confirmed by measurement, not anecdote."
```

---

## Slide 2 - The reranker: smarter retrieval

```svg-infographics
canvas:  1280x720 (16:9). Meridian theme, GREEN win accents (matches the solutions slide).

title strip (top-left):
  title:    "THE RERANKER"
  subtitle: "A quantized cross-encoder that re-scores every retrieved chunk by true
             relevance to the question, then reorders so the best passages lead - the
             single change that lifted retrieval quality."

hero band - the headline result, large:
  retrieval quality   80%  →  92%
  irrelevant chunks   >20% →  <8%     (about 1-in-5 down to under 1-in-12)

three panels below the hero:

  PANEL 1 - What it does
    bge-reranker-v2-m3 reads each (question, chunk) pair and scores real relevance, replacing
    raw vector-search order. It picks the best chunks from what retrieval returned.

  PANEL 2 - How we shipped it
    - int8 quantized (NNCF) - holds 98% of FP16 quality (score parity pearson 0.9976 vs fp32)
    - 571 MB int8 IR - fits a serverless Lambda container
    - CPU-only, OpenVINO single runtime - no GPU
    - tuned inference: LATENCY compile hint (~2x), rank-ordered early-exit
    - warm: ~1 s to rerank a query against its retrieved content

  PANEL 3 - Why it matters (GRAPHIC, not prose)
    a small chunk-tile visual showing irrelevant context shrinking, then feeding downstream:
      - BEFORE row: 10 chunk tiles, ~2 tinted red (irrelevant)  → caption ">20% irrelevant"
      - arrow (reranker) →
      - AFTER row:  12 chunk tiles, <1 tinted red               → caption "<8% irrelevant"
      - a short down-arrow from the AFTER row into a single "downstream stages" chip
        (grounding + answer) → caption "cleaner context feeds every downstream stage"
    takeaway carried by the graphic (no paragraph): fewer irrelevant chunks in = less
    spurious material to hallucinate from; the reranker is the retrieval-quality lever

fact strip:
  80% → 92% retrieval quality | <8% irrelevant | int8 571 MB |
  98% of FP16 quality | ~1 s warm/query | CPU serverless Lambda

strap (italic):
  "One quantized model, CPU-only - retrieval quality up 12 points, irrelevant context more
   than halved."
```

---

## Slide 3 - Grounding: cross-lingual hallucination detection

```svg-infographics
canvas:  1280x720 (16:9). Meridian theme, green win accents.

title strip (top-left):
  title:    "GROUNDING"
  subtitle: "The outcome of extensive, hypothesis-driven research - engineered for two goals
             at once: maximum hallucination detection and minimum latency tax. A novel,
             LLM-less detector that checks every statement against the retrieved knowledge.
             Deterministic, torch-free, cross-lingual, sub-second."

FRAMING - present the slide as the two research goals side by side (label the two blocks):
  LEFT  block = MAXIMUM DETECTION      (the hero split below)
  RIGHT block = MINIMUM LATENCY TAX    (the latency band below)
  a small provenance badge/chip near the title: "dozens of hypothesis-driven experiment
  rounds" - the detection + latency numbers are the tuned end state, not a first attempt
  (e.g. cross-lingual detection was driven 0% → 78% over successive research rounds)

hero split - EN vs MULTILINGUAL, under the MAXIMUM DETECTION label (the two-column ask):
  ENGLISH        F1 0.81         hallucination detection on English claims
  MULTILINGUAL   78% caught      non-English hallucinations (TNR 0.78), 9 languages
  callout arc:   non-English detection went from 0% → 78% caught after the cross-lingual
                 synthetic-negative research (English detection went up, not down)

method panel (how it works, no LLM):
  - lexical signals: IDF-weighted BM25 recall, char-ngram recall, fuzzy match, anchor
    recall (numbers / IDs, language-invariant), claim specificity, distinctive-content coverage
  - cross-lingual MT bridge: argos CTranslate2 int8 + OpenVINO-INT8 SaT segmenter (torch-free)
    - translate-then-recall on the ~23% of claims whose language differs from the source
  - contradiction layer: aligned value-conflict + WordNet antonym-flip - catches
    present-but-flipped facts (100 VAC vs 240 VAC), not just missing content
  - verdict: one class-balanced logistic - NO LLM, NO NLI model, NO neural verdict head
  - generalises per language: TNR es 0.80 / sv 0.93 / fr 0.71 / nb 0.71 / pt 0.65

latency band - under the MINIMUM LATENCY TAX label:
  ~165 ms per claim (single-thread CPU) | well under 1 s | 5 s one-time cold start |
  torch-free, CPU-only

strap (italic):
  "The tuned end state of extensive research - maximum hallucination detection at minimum
   latency tax: every statement checked against its evidence, in nine languages, under a
   fifth of a second, with no language model in the loop."
```

---

## Sources

Each slide's numbers trace to a source - the discipline the draft demonstrates, not the
specific documents:

- Golden dataset / issue numbers: `slide_1_problem.svg` from the executive-summary deck plus
  the internal SOTA benchmark report (2,752 statements, 29% hallucinated, 639 conversations,
  9 languages)
- Reranker: product-team retrieval-quality deltas (80% → 92%, >20% → <8%) plus the reranker
  experiment log (bge-reranker-v2-m3 int8, pearson 0.9976, 571 MB)
- Grounding: the grounder experiment log (English F1 0.810, non-English TNR 0.78, per-language
  TNR, ~165 ms/claim, torch-free CPU)
