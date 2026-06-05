# Integrating Distributional Lexical Contrast into Word Embeddings for Antonym-Synonym Distinction

**Paper**: Nguyen, Schulte im Walde, Vu (2016), ACL. [arXiv 1605.07766](https://arxiv.org/abs/1605.07766) · sidecar to `antonym_synonym_2016.pdf`

## Summary

The paper tackles a well-known failure of distributional semantics: **antonyms and synonyms have similar embeddings** because both occur in similar contexts (the distributional hypothesis coalesces "similarity" and "association"), so plain word vectors cannot tell `big↔small` from `big↔large`. The authors add a lexical-contrast objective to the skip-gram model - distributional contrast pulled from thesaurus antonym/synonym pairs - and learn embeddings that separate antonyms from synonyms, outperforming prior methods on the antonym-synonym distinction task.

## Why it matters to our grounder

This is the theoretical justification for two of our decisions. First, it explains *why* round-2's substitution-distance feature was a null: surface lexical overlap (and naive embeddings) cannot distinguish a synonym restatement (supported) from an antonymic fact-edit (refuted), because the two are distributionally close. Second, it justifies our use of **explicit WordNet antonym lists** (`wn_antonym_flip`) rather than a distributional similarity - WordNet encodes the opposition relation directly, sidestepping the conflation this paper documents. It also frames why the remaining residual is hard for any purely lexical method.

## Scope

**Out of scope (method)** - the technique trains specialised embeddings, which our lightweight pure-lexical classifier defers for latency. Cited as the *why-behind* the WordNet choice and the round-2 null; not used directly.
