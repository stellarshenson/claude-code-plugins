# WMD Document Distance with mmBERT (SOTA)

## Abstract

An embedding-grounded, metric document distance for pipelines that cannot read model logits. Each document is segmented into statements, embedded with mmBERT, isotropy-corrected (all-but-the-top), and compared by exact optimal transport - the Statement Mover's Distance (SMD). It adapts Word Mover's Distance[<sup>ref1</sup>](#ref1) (Kusner et al. 2015, digest in `../references/papers/from-word-embeddings-to-document-distances.md`) by swapping the embedded unit (statement, not word) and the encoder (mmBERT, not word2vec), keeping the transport skeleton verbatim. SMD is a true metric, ranks the executive-summary quality tiers with zero ordering errors (batch E01, [`experiments/wmd-docdistance-experiments.md`](experiments/wmd-docdistance-experiments.md)), and runs CPU-INT8 end-to-end (~5.5 s for two A4 pages on one core). This is the conclusion doc; the experiments log is its evidence.

## Problem

Comparing two documents for shared content is hard when whole-document embeddings are too coarse and model logits are unavailable.

- **Whole-document cosine is too coarse** - two summaries that carry the same claims in different places, in a different order, or with content added or dropped collapse to one bunched cosine score
- **No logits in frontier pipelines** - agentic conversion and extraction run through frontier models that do not expose token-level logits, so KL divergence cannot measure how far an output has drifted from its source
- **A metric is required** - the distance must satisfy the triangle inequality to compose and threshold reliably, and stay interpretable enough to localize what changed

## Solution

Lift the comparison to statements and optimal transport: segment each document, embed and isotropy-correct the statements, and take the exact transport cost between the two clouds.

- **Distance interpretation** - transport cost between the two statement clouds; `0` identical, larger = more divergent content, read as `closeness = 1 − SMD/√2` (1 identical, 0 unrelated)
- **Why and how to use** - flag content drift between two documents when model logits are unavailable; two texts in → one metric distance, a similar/not verdict, and the statement alignment showing what moved, dropped, or was added
- **Deterministic and reproducible** - the same two texts give the same distance every run; the CPU-INT8 production path is bit-exact (segmentation, embedding, the SVD and exact OT are all deterministic), the only non-determinism being the natural floating-point reduction-order variance on GPU - unlike a sampling LLM judge
- **Headline result** - perfect tier ordinality (`0/24` violations), anisotropy removal widens the dynamic range 3.2x, and a 2 × A4 pair compares in ~5.5 s on one CPU core

## Pipeline

Two documents in → one closeness score and a similar/not verdict; the transport plan is the statement-to-statement alignment.

- **Segment** - split each document into statements with `sat-3l-sm`[<sup>ref4</sup>](#ref4) (nb 01); statements are the transport unit, so the comparison is position-invariant
- **Embed** - mmBERT[<sup>ref5</sup>](#ref5), mean-pooled and L2-normalized per statement; quantized encoder (OpenVINO INT8 on CPU, torchao FP8 on GPU)
- **Anisotropy removal** - subtract the dominant principal component from the pooled statement embeddings and re-L2-normalize (all-but-the-top); de-bunches the mmBERT cosines so the cost matrix is not compressed - a standard step, not optional
- **Ground cost** - Euclidean on L2-normalized embeddings `= √(2 − 2cos)`, metric-safe cosine; `1 − cos` and squared-Euclidean are rejected - they rank like cosine but void the triangle inequality
- **Distance** - exact optimal transport between the two clouds, uniform weights `1/n`, solved with POT[<sup>ref6</sup>](#ref6) `ot.emd2`; this scalar is the SMD
- **Lower bounds** - WCD (centroid distance, exactly the whole-document-cosine baseline) and RWMD (one-sided relaxation, greedy nearest-statement alignment) nest as `WCD ≤ RWMD ≤ SMD`; cheap prefetch-and-prune floors
- **Verdict** - closeness `1 − SMD/√2` (1 identical, 0 orthogonal) plus a similar/not call against a threshold set by the gold cluster's own diameter

## Mechanism

The distance is optimal transport between the two statement clouds; the ground cost must be a true metric, the encoder's anisotropy is corrected first so the cost matrix is not compressed, and the transport is solved exactly.

**Why not cosine similarity.** Cosine is a similarity in `[−1, 1]`, not a distance - it peaks at identity, has no zero floor, and obeys no triangle inequality, so it cannot serve as a transport ground cost. Optimal transport needs a genuine metric: non-negative, zero only for identical points, triangle-respecting - and WMD inherits the metric property only when its ground cost is one (Kusner et al. 2015). The cosine-derived costs `1 − cos` and `2 − 2cos` rank pairs identically to cosine but break the triangle inequality, so they would void that guarantee. The Euclidean norm of the difference of L2-normalized vectors does not, and for unit vectors it collapses to a function of cosine:

$$
\lVert \mathbf{x} - \mathbf{y} \rVert_2^{2} = \lVert \mathbf{x} \rVert_2^{2} + \lVert \mathbf{y} \rVert_2^{2} - 2\,\mathbf{x}^{\top}\mathbf{y} = 2 - 2\cos(\mathbf{x}, \mathbf{y})
$$

So the ground cost is the chord length between the two unit vectors - a real metric that ranks exactly like cosine, only as a distance:

$$
c(\mathbf{x}_i, \mathbf{x}_j) = \lVert \mathbf{x}_i - \mathbf{x}_j \rVert_2 = \sqrt{2 - 2\cos(\mathbf{x}_i, \mathbf{x}_j)}
$$

The chord distance spans `[0, 2]` in general - `cos = −1` (antipodal) gives the maximum `2`. mmBERT statement embeddings are non-negatively correlated, though - they occupy a narrow cone, `cos ∈ [0, 1]` - so in practice the cost lives in `[0, √2]`, orthogonal statements (`cos = 0`) sitting at the ceiling `√2`. That practical ceiling is the closeness normalizer: `closeness = 1 − SMD/√2` maps orthogonal clouds to 0 and identical clouds to 1.

**The distance.** With that cost, the Statement Mover's Distance is the minimum-cost plan that moves one cloud's uniform mass onto the other's:

$$
\mathrm{SMD}(A, B) = \min_{T \ge 0} \sum_{i=1}^{n_A} \sum_{j=1}^{n_B} T_{ij}\, c(\mathbf{a}_i, \mathbf{b}_j)
\quad \text{s.t.} \quad
\sum_{j} T_{ij} = \tfrac{1}{n_A}, \;\; \sum_{i} T_{ij} = \tfrac{1}{n_B}
$$

**The solver - exact EMD, not Sinkhorn.** This is a linear program, solved exactly with the network-simplex (POT `ot.emd2`), which returns the true optimal cost and a sparse transport plan. The entropic-regularized alternative, Sinkhorn[<sup>ref3</sup>](#ref3) (Cuturi 2013), trades exactness for speed by adding an entropy term `H(T)` with blur `ε`:

$$
\mathrm{SMD}_{\varepsilon}(A, B) = \min_{T \ge 0} \sum_{i, j} T_{ij}\, c(\mathbf{a}_i, \mathbf{b}_j) \;-\; \varepsilon\, H(T), \qquad H(T) = -\sum_{i,j} T_{ij}\big(\log T_{ij} - 1\big)
$$

Sinkhorn only pays off when the clouds are large; at statement scale (~12 points) exact EMD runs at ~0.08 ms/pair, faster than Sinkhorn and free of the entropic bias, so Sinkhorn is dropped.

**Anisotropy.** mmBERT statement embeddings are anisotropic - a common mean and a few dominant principal directions sway every vector, so pairwise cosines bunch at 0.7-0.9 and the cost matrix is compressed. The dominant directions encode word frequency, not meaning, so removing them is pure signal gain. All-but-the-top postprocessing[<sup>ref2</sup>](#ref2) (Mu & Viswanath, ICLR 2018; digest `../references/papers/all-but-the-top-simple-and-effective-postprocessing-for-word-representations.md`) subtracts the pooled mean and projects away the top D directions (`D ≈ d/100`), then re-L2-normalizes:

$$
\tilde{\mathbf{v}} = \mathbf{v} - \boldsymbol{\mu}, \qquad
\mathbf{v}' = \tilde{\mathbf{v}} - \sum_{i=1}^{D} (\mathbf{u}_i^{\top} \mathbf{v})\, \mathbf{u}_i
$$

- **Effect** - de-bunched cosines, dynamic range up 3.2x (DR 0.057 → 0.180) at zero ordinality violations (E01)
- **Metric preserved** - re-normalized vectors keep Euclidean = metric-safe cosine, so the distance stays a metric
- **Corpus-level step** - the shared direction is estimated from the pooled statements of all documents compared, so it sharpens a batch or corpus; an isolated document pair (~two dozen vectors) is too small to estimate it reliably, so a single pairwise comparison uses raw embeddings, on which the tier ordering is already perfect (`0/24`)

## Performance

Eleven executive summaries of one IBM AI-adoption article, three tiers (7 gold, 2 info-loss, 2 info-noise), scored against the reference gold; full evidence in [batch E01](experiments/wmd-docdistance-experiments.md).

| measure | SMD + anisotropy removal (shipped) | SMD, no postprocessing |
|---|---|---|
| ordinality violations `V` | 0 / 24 | 0 / 24 |
| dynamic range `DR` | 0.180 (3.2x) | 0.057 |
| boundary margin (closeness pts) | +0.92 | +0.79 |
| separation `d'` | 2.34 | 2.70 |
| reference contrast `R` | 1.26x | 1.27x |
| metric | yes | yes |

- **Perfect ordering** - every gold summary is closer to the anchor than every adversarial one, zero crossings, with or without postprocessing
- **Resolution gain ships** - of five levers tested in E01, anisotropy removal is the only one that widens dynamic range and the boundary margin without breaking the order, so it is standard
- **`d'` tradeoff** - the isotropy step spreads the gold band too, so the effect-size separation `d'` drops (2.70 → 2.34); accepted for the 3.2x resolution gain since ordering stays perfect
- **Closeness bands** (no postprocessing) - gold 73-82%, adversarial 68-72%; the two 3-sweep golds nearest
- **What it responds to** - SMD tracks shared statement content; the info-noise tier (kept the source's numbers) lands slightly closer than the info-loss tier (stripped them), so numeric retention correlates with closeness

## Setup

Preparation for the single-core benchmark (run in `notebooks/04-kj-wmd-document-distance.ipynb`, final section).

- **Hardware** - AMD Ryzen Threadripper PRO 7975WX (32 cores / 64 threads); measured on **one core** (OpenVINO `INFERENCE_NUM_THREADS=1`, torch `set_num_threads(1)`)
- **Models** - `sat-3l-sm` segmenter (FP32, CPU) and `mmBERT-base` encoder as OpenVINO INT8 (CPU) - the deployable CPU stack
- **Workload** - two A4-page text blocks (~554 words each, segmenting to ~21 statements each, ~42 total) - the "compare two documents" unit
- **Pipeline timed** - segment → embed → anisotropy removal → exact SMD, the full end-to-end

## Methods of measurement

How each figure is taken; single-stream throughout, so a number is the per-core unit.

- **Single-core** - thread counts pinned to 1, so each figure is one core; multiply by vCPUs for parallel throughput
- **Encoder latency** - one statement, dynamic padding, 50 reps after 5 warmups, mean ms/sentence; tokens/s from the real token count
- **Encoder amortized** - a 55-statement batch (one document), 5 reps, ms/sentence = batch time / count; on a single core batching does not parallelize, so amortized is slightly above single-statement latency (padding to the batch's longest statement)
- **Exact SMD** - 100 reps at 55×55 statements, mean ms/pair
- **End-to-end** - one timed pass per stage over the 2×A4 workload, after a segmentation warmup
- **Caveat** - segmentation is FP32 `sat-3l-sm` on CPU; an INT8 OpenVINO SAT would cut its share

## Throughput and footprint

Single core, full pipeline, AMD Ryzen Threadripper PRO 7975WX.

| stage | single core |
|---|---|
| segment (SAT FP32 CPU) | 2553 ms / 2 docs |
| embed (mmBERT INT8 CPU) | 2998 ms / 2 docs (~30.8 ms/sentence, 32 sent/s/core, ~1300 tok/s) |
| anisotropy (SVD) | 2.7 ms |
| exact SMD | 0.40 ms/pair at 55×55 (0.08 ms at 12×12) |
| **end-to-end (2 × A4)** | **5.55 s** |

- **Per-core unit** - ~0.2 document-pairs/s/core; embedding is 54% of the time, segmentation 46%, the distance negligible
- **AWS Lambda sizing** - ~1 vCPU per 1769 MB, so a ~2 GB function ≈ 1 core ≈ 0.2 pairs/s; scale ~linearly with vCPUs (a 6-vCPU / 10 GB function ≈ ~1.2 pairs/s)
- **GPU contrast** - the encoder reaches ~2588 sentences/s on GPU FP8 (~80× one CPU core, nb03), collapsing the embed stage; the single CPU core is the serverless worst-case floor
- **Footprint** - INT8 encoder IR ~310 MB, SAT ~few hundred MB, so the stack fits a ~1-2 GB Lambda; dependencies `wtpsplit` (SAT), `transformers` / `openvino` (mmBERT), `ot` (POT)

## Limitations

- **Thin boundary margin** - +0.92 closeness points at the gold/adversarial boundary; the ordering is clean, the separation is narrow
- **Intrinsic to the fixture** - all eleven summaries describe one article and share its content, so the margin is genuinely narrow, not a defect of the distance
- **Single source, single degradation design** - a controlled probe, not a benchmark; cross-fixture validation on a second article is pending
- **`d'` lowered by the isotropy step** - anisotropy removal widens the margin and dynamic range but spreads the gold band, lowering the effect-size `d'` (2.70 → 2.34); ordering is unaffected
- **Selection vs grounding not separated** - a symmetric distance cannot tell same-source-different-picks from off-source fabrication; the source-conditioned variant `d(A,B|S)` in [`wmd-wrt-source-docdistance-solution.md`](wmd-wrt-source-docdistance-solution.md) adds that axis

## FAQ

- **Why not KL divergence?** - KL between the model's output token distributions is the natural drift measure, but it needs token-level logits, which frontier models behind agentic pipelines do not expose; KL is also asymmetric (not a metric) and lives over tokens, not document content. SMD is the embedding-grounded, logit-free stand-in that needs only the two texts
- **Why not embeddings + cosine similarity?** - whole-document cosine is exactly the WCD lower bound here, the cheap floor SMD refines; it bunches every document into the anisotropic 0.7-0.9 band, discards statement-level structure (the same claims in different places read as far apart), and cosine is a similarity, not a metric - no triangle inequality, no zero floor
- **Why not a cross-encoder?** - a cross-encoder (e.g. `bge-reranker`) scores relevance between two texts but returns no metric, no zero point, and no alignment, and costs O(n·m) over statement pairs; it is the right tool for the source-conditioned grounding variant `d(A,B|S)`, not for a symmetric metric distance
- **Why not an LLM judge?** - no logits exposed, non-deterministic, slow and costly per call, and not a metric; SMD is deterministic, cheap (sub-ms transport, ~5.5 s/pair full CPU pipeline), and thresholdable
- **Why statements, not words (literal WMD)?** - statements are the unit the use case cares about (a claim moved, dropped, or added), give far fewer points so exact OT stays cheap, and align interpretably; word-level pooling is slower and noisier
- **Why not Sinkhorn (entropic OT)?** - at ~12-55 statements exact EMD is faster and unbiased; Sinkhorn's entropic blur only pays off on large clouds (see Mechanism)
- **Why PCA/SVD for anisotropy removal?** - the anisotropy is a few dominant directions of shared variance across all statement embeddings; PCA - computed by the SVD of the mean-centered matrix - is exactly what finds those top-variance directions, so projecting them out strips the common component the all-but-the-top paper identifies as frequency, not meaning; the SVD is exact, deterministic, and cheap at statement scale, and removing the top-D components (`D ≈ d/100`) needs no training

## Implementation

- **Notebooks** - `notebooks/01-kj-document-segmentation.ipynb` (segment), `notebooks/04-kj-wmd-document-distance.ipynb` (the distance, validated end-to-end)
- **Experiments** - `docs/experiments/wmd-docdistance-experiments.md` (batch E01: five contrast levers, one promoted, four refuted)
- **Functions** - `smd` (`ot.emd2`), `wcd` (centroid norm), `rwmd` (one-sided relaxation), `closeness` (`1 − SMD/√2`), `all_but_the_top` (anisotropy); pairwise verdict threshold is a heuristic closeness cutoff, calibrate per corpus
- **References** - WMD (Kusner et al. 2015) and all-but-the-top postprocessing (Mu & Viswanath, ICLR 2018); digests under `../references/papers/`
- **Library** - shipped as the `docdistance` package: `src/docdistance/distance.py` (pure-numpy OT core), `encoders.py` (SAT + mmBERT INT8 / torch backends), `pipeline.py` (`document_distance`, `source_conditioned_distance`, the reusable `DocDistance` class), and a `docdistance` CLI (`distance`, `distance-wrt-source`, `install`)
- **Library validation** - `notebooks/09-kj-docdistance-api-e2e.ipynb` reproduces the `0/24` ordinality through the public API and confirms openvino-vs-torch backend agreement (Pearson 0.9991)

## Conclusions

A single metric distance with a bounded, interpretable readout, built for pipelines that cannot read model logits.

- **Range** - the ground cost is `[0, 2]` in theory (`cos = −1`, antipodal); for these non-negatively-correlated embeddings it spans `[0, √2]`, so `SMD ∈ [0, √2]` and `closeness = 1 − SMD/√2 ∈ [0, 1]` (1 identical, 0 unrelated)
- **Verdict** - similar when `SMD ≤ τ`, `τ` the gold cluster's own diameter; the transport plan is the statement alignment, so the number arrives with what moved, dropped, or was added
- **Use scenario** - agentic document conversion and extraction through frontier models, where token-level logits are not exposed so KL divergence cannot be computed; SMD is the embedding-grounded stand-in that flags when a converted or extracted output has drifted from its source, and the alignment localizes the drift
- **Operating point** - exact, metric, deterministic, runs CPU-INT8 end-to-end; the transport is ~0.08 ms/pair at statement scale, so a document pair's cost is dominated by encoding, not the distance
- **Performance** - a 2 × A4 document pair compares in ~5.55 s end-to-end on one core of the Threadripper 7975WX (segmentation 46%, embedding 54%, transport negligible); ~0.2 pairs/s/core, so a ~2 GB AWS Lambda ≈ one core and throughput scales ~linearly with vCPUs

## Bibliography

- <span id="ref1">ref1 Kusner, Sun, Kolkin, Weinberger. *From Word Embeddings To Document Distances*. ICML 2015. Digest `../references/papers/from-word-embeddings-to-document-distances.md`</span>
- <span id="ref2">ref2 Mu, Viswanath. *All-but-the-Top: Simple and Effective Postprocessing for Word Representations*. ICLR 2018. Digest `../references/papers/all-but-the-top-simple-and-effective-postprocessing-for-word-representations.md`</span>
- <span id="ref3">ref3 Cuturi. *Sinkhorn Distances: Lightspeed Computation of Optimal Transport*. NeurIPS 2013</span>
- <span id="ref4">ref4 Frohmann et al. *Segment Any Text* (`sat-3l-sm`, wtpsplit). Shipped INT8: `stellars/sat-3l-sm-openvino-int8`</span>
- <span id="ref5">ref5 `mmBERT-base` (`jhu-clsp/mmBERT-base`), a multilingual ModernBERT encoder. Shipped INT8: `stellars/mmBERT-base-openvino-int8`</span>
- <span id="ref6">ref6 Flamary et al. *POT: Python Optimal Transport*. JMLR 2021 (`ot.emd2`)</span>
