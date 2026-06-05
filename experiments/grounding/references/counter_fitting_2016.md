# Counter-fitting Word Vectors to Linguistic Constraints

**Paper**: Mrkšić, Ó Séaghdha, Thomson, Gašić, Rojas-Barahona, Su, Vandyke, Wen, Young (2016), NAACL. [arXiv 1603.00892](https://arxiv.org/abs/1603.00892) · resource [github.com/nmrksic/counter-fitting](https://github.com/nmrksic/counter-fitting) · sidecar to `counter_fitting_2016.pdf`

## Summary

Counter-fitting is a post-processing step that injects synonymy and antonymy constraints (from WordNet and PPDB) into pre-trained word vectors: synonym pairs are pulled closer, antonym pairs are pushed apart toward near-zero or negative cosine, while preserving the original neighbourhood structure. It is a gradient-based optimisation over the embedding matrix, run once offline; the output (`counter_fitted_vectors.txt`) is a **static, downloadable lookup table requiring no neural inference at runtime**. Counter-fitted vectors set a new state of the art on SimLex-999 semantic-similarity judgement at publication.

## Why it matters to our grounder

This paper is the documented path *not* taken. Round 2 found that a general single-token-substitution feature is a **null** because it cannot tell a supported synonym restatement from a refuted fact-edit - "separating a synonym from a fact-edit is irreducibly semantic." Counter-fitting is precisely the deterministic resource that would crack that residual: the counter-fitted cosine between a swapped claim token and the evidence token is *high* for a synonym (supported) and *low/negative* for an antonym or unrelated fact (contradiction) - the signal a plain lexical or naive-embedding distance lacks.

## Scope

**Out of scope (by decision)** - although it is a frozen lookup, it is still an embedding table: it carries a tens-of-MB footprint and per-claim vector lookups, and the project's bar is a **lightweight pure-lexical classifier** where embeddings, NLI, and cross-encoders are deferred for latency. Round 3 therefore pursues parser-free structural mechanisms instead. Counter-fitting is the natural first feature to revisit if/when a heavier semantic stage is admitted (it would also power the triage flag's downstream handoff).
