# References - lexical cross-lingual grounding

Key papers for the contradiction-feature research strand. PDFs are git-ignored (large binaries); each has a committed `.md` sidecar with a summary, the mechanism relevant to our grounder, and its in/out-of-scope status (the bar is a lightweight pure-lexical classifier - embeddings, NLI, and cross-encoders are deferred for latency).

| Paper | Sidecar | Relevance | Scope |
|---|---|---|---|
| VitaminC - contrastive fact verification (Schuster 2021) | [vitaminc_2021.md](vitaminc_2021.md) | the contrastive second corpus + the minimal-edit insight behind the contradiction features | in - test corpus |
| Counter-fitting word vectors (Mrkšić 2016) | [counter_fitting_2016.md](counter_fitting_2016.md) | the deterministic embedding fix that would crack the synonym-vs-fact-edit residual | out - embedding, deferred for latency |
| Antonym-synonym distinction (Nguyen 2016) | [antonym_synonym_2016.md](antonym_synonym_2016.md) | why surface lexical / naive embeddings conflate antonyms and synonyms - justifies WordNet | out - method, cited as rationale |

Download the PDFs locally with `curl -sL -o <name>.pdf https://arxiv.org/pdf/<id>` (ids in each sidecar).
