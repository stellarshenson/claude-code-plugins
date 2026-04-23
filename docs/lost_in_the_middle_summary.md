# Summary: Lost in the Middle — How Language Models Use Long Contexts

Liu et al., 2023 (Stanford / UC Berkeley / Samaya AI). Paper at
`references/liu2023_lost_in_the_middle.pdf`.

## Core finding

Current language models do not robustly make use of information in long
input contexts. Performance is often highest when relevant information
occurs at the beginning or end of the input context, and significantly
degrades when models must access relevant information in the middle of long
contexts — even for explicitly long-context models.

## Setup

The authors analyse the performance of language models on two tasks that
require identifying relevant information in the input context:
multi-document question answering and key-value retrieval. They vary both
(a) the total input context length and (b) the position of the relevant
information within that context, and measure how downstream accuracy
changes.

## Key results

1. Accuracy follows a **U-shaped curve** with respect to the position of
   relevant information — highest at the ends, lowest in the middle.
2. This degradation is observed both in open (smaller) and closed
   (frontier) language models.
3. Extending model context length alone does not fix the problem. Explicitly
   long-context models still drop sharply when relevant information sits in
   the middle.
4. In multi-document QA, performance can be more than 20 percentage points
   below the closed-book baseline when relevant information is in the
   middle of long contexts.
5. Query-aware contextualization (placing the query both before and after
   the documents) improves key-value retrieval to near-perfect on some
   models but only marginally affects multi-document QA.

## Paraphrased claims (for the grounding test)

- Language models attend more to the start and end of a prompt than to its
  middle.
- Adding more tokens to the context window does not automatically make the
  model use that extra space well.
- The retrieval degradation persists across both open and closed
  language models.
- Models struggle to find a single key-value pair hidden in a long random
  list of pairs.

## Distant-paraphrase claims (semantic layer target)

- LLMs behave as if attention is biased toward recency and primacy rather
  than uniformly across the context window.
- Simply giving a model a bigger context does not guarantee better reading
  comprehension over that context.

## Claims that should NOT ground

- The paper proposes a new positional encoding called "RoPE-Mid" that fixes
  the middle-of-context degradation.
- All experiments were run on a single NVIDIA H100 GPU donated by Meta.
