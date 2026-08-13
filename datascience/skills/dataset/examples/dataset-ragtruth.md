# RAGTruth

The only corpus where domain, negative construction and licence are all correct at once. Negatives are the error distribution a production RAG grounder actually meets, not a synthetic approximation of it.

- **Source** - `wandb/RAGTruth-processed` on HuggingFace
- **Licence** - MIT
- **Size** - 17,790 responses - 15,090 train / 2,700 test
- **Languages** - English
- **How negatives were made** - Naturally occurring LLM hallucinations - 6 models (Llama-2 7/13/70B, Mistral-7B, GPT-3.5, GPT-4) answering real retrieval prompts; no perturbation
- **How labels were made** - Human expert span annotation
- **Mapping onto our task** - response span -> claim; retrieved passage -> evidence; any hallucinated span in a sentence -> that claim is unsupported

## Caveats

English only. Retrieval contexts derive from MS MARCO / CNN-DM / Yelp, so the documents are public-web register rather than business documents.

## Provenance

Admitted against the gate: a licence permitting commercial use, source documents shipping
alongside the claims, and a task shape that maps onto (claim, evidence) → supported. Corpora
rejected on the licence filter alone: TrueTeacher (CC-BY-NC, 1.38M), HaluBench (CC-BY-NC),
MS MARCO (non-commercial), ANLI (CC-BY-NC), MEMERAG (card forbids training).

Fetched by `scripts/fetch_grounding_datasets.py`. The archive `dataset-ragtruth.zip` is
gitignored; this sidecar is tracked.
