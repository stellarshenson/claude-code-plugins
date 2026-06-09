# VitaminC - Robust Fact Verification with Contrastive Evidence

**Paper**: Schuster, Fisch, Barzilay (2021), NAACL. [arXiv 2103.08541](https://arxiv.org/abs/2103.08541) · sidecar to `vitaminc_2021.pdf`

## Summary

VitaminC is a fact-verification benchmark built from over 100,000 Wikipedia revisions that modify an underlying fact, plus synthetic pairs - ~400k claim-evidence pairs in total. Its defining property is **contrastive evidence**: two evidence sentences are nearly identical in language and content, but one *supports* a claim and the other *refutes* it. The discriminating change is a single localized edit - a number/quantity, a named entity, a date, a negation, or an antonym. Training on this design makes verifiers sensitive to minimal factual changes and improves robustness (+10% on adversarial fact verification, +6% on adversarial NLI). The benchmark also defines auxiliary tasks: word-level rationale tagging, factual-revision detection, and factually-consistent generation.

## Why it matters to our grounder

This is the **second corpus** in our joint hold-vs-collapse test and the diagnostic that exposed the No Free Lunch boundary: the lexical grounder collapses to macro-F1 0.586 (≈ coin-flip) on VitaminC vs 0.837 on private RAG. The cause is exactly VitaminC's construction - its negatives are *present-but-contradicted* (recall stays high, the lexical stack is blind), whereas private RAG's negatives are *absent/fabricated* (recall drops, the lexical stack catches them). The "minimal localized edit" insight is what drove every contradiction feature we built: aligned value-conflict (number/entity edits), WordNet antonym-flip, and the round-3 structural candidates (role reversal, scoped negation, quantifier mismatch).

## Scope

**In scope** - used as the contrastive test corpus (`tals/vitaminc` dev) and the mechanism reference. We never train on its test fold; it is the held-out second domain that any new feature must lift without degrading private RAG.
