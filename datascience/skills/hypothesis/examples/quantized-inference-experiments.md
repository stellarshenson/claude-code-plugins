# Quantized Transformer Inference - making it truly faster on Ada + Blackwell

**Canonical Experiments Document**

> **Skill example - deliberately truncated.** The source experiments log carried **105 hypotheses across 36 rounds** (~1,888 lines). This copy keeps the document skeleton (overview, problem, executive summary, methodology, setup) and **two full rounds - E12 (llama.cpp) and E13 (vLLM), nine hypotheses** - to show the per-hypothesis-regime shape without overloading the skill. Omitted spans are marked `[... omitted ...]`. Kept hypotheses are verbatim from the real log; nothing was invented for the example. Use it as the reference for the shape where **each hypothesis owns its regime** (its own models / card / harness): overview paragraph → unlabelled lever-detail paragraph → brief `Lever` → the eight bullets with a `<br>`-labelled `Experiment`. For the compact, shared-Setup shape (one-toggle levers, no per-hypothesis Experiment) mirror `wmd-docdistance-experiments.md` instead.

Experiments log for finding when and how quantization actually speeds up transformer-encoder inference on three local GPUs, and when it silently regresses. Executed by the isolated worker [`qbench_worker.py`](../../qbench_worker.py) via [`run_matrix.py`](../../run_matrix.py), one subprocess per config; analysis and charts in [`02-kj-quantized-inference-experiments.ipynb`](../../02-kj-quantized-inference-experiments.ipynb). Literature grounding in [`../quantized-inference-insights.md`](../quantized-inference-insights.md); final design in [`../quantized-inference-sota.md`](../quantized-inference-sota.md).

- **Branch / artefacts** - worker `qbench_worker.py`, orchestrator `run_matrix.py`, per-GPU configs `configs/{P4,P6,A5}.json`, results `results/qbench/*.json`, logs `logs/{P4,P6,A5}.log`
- **Workload** - Dario Amodei essay "The Adolescence of Technology" (`.mhtml`), tokenized to fixed-length chunks, tiled to a fixed batch; real tokens, controlled shape
- **Batch E01** ran 8 methods eager across 3 GPUs; E02-E05 ran the compile/regime/size/arch levers; 50 of 51 configs succeeded, 1 failed (fp8-ft + compile, InductorError)

## Problem overview

FP8 quantization of a 150M encoder (mmBERT-base) ran slower than bf16 in the prior notebook run. The research question: is quantization ever truly faster here, and which lever flips it. Encoders are the workload, throughput and latency the targets.

- **Hardware** - RTX PRO 4000 Blackwell (sm_120, 24 GB), RTX PRO 6000 Blackwell (sm_120, 96 GB), RTX 5000 Ada (sm_89, 32 GB); torch 2.12+cu130, transformers 5.0, torchao 0.17
- **Models** - mmBERT-base (ModernBERT arch, ~150M), bge-m3 (XLM-R-large arch, ~560M) as the larger, non-ModernBERT encoder
- **The paradox** - a quantized matmul only beats bf16 once the GEMM is compute-bound; small models at small batch/seq are memory-bandwidth-bound, so quant/scale overhead dominates and quantization regresses
- **Core difficulty** - the win depends on regime (batch, sequence, model size), on `torch.compile` fusing dequant into the GEMM, and on the quant method matching the regime (weight-only = memory/latency, dynamic-activation = throughput/compute)
- **Not tested** - training/QAT, downstream-task accuracy (only embedding fidelity vs bf16), decoder/generation, multi-GPU

## Executive summary

`torch.compile` is the master lever: 2.08-2.29x over eager bf16 on every GPU, and the precondition for any quant win - eager quantization regresses (worst: int8-dynamic 0.07x). The truly-faster recipe is int8-dynamic (torchao W8A8) + compile, 2.28-2.57x over the eager bf16 default at equal embedding fidelity (cosine ≥ 0.998), fastest faithful config on Blackwell (673k tok/s, mmBERT-150M, PRO 6000). Quantization's extra gain over already-compiled bf16 is Blackwell-only (+13-21%) and vanishes on Ada (+0%); on the larger bge-m3 the winner flips to fp8-dynamic (+33% over compiled bf16).

**Alternative-stack rounds (E12-E16) broke the decode wall.** The sm_120 int4/decode blockade was a torch-ecosystem gap, not a hardware one: llama.cpp's custom CUDA kernels realize the full bandwidth ordering (7B decode Q4_K_M 2.27-2.69x fp16; batched 3,317 tok/s aggregate), and vLLM's Marlin/Machete + fp8 kernels serve every quant format on consumer Blackwell (0.5B: AWQ-int4 bs=1 +33%, fp8 batched +71%; 7B: GPTQ-int4 2.8x bf16 decode; embeddings: fp8 +39%).

| hypothesis | lever | predicted | result | verdict |
|---|---|---|---|---|
| E12-H33 | llama.cpp int4 on sm_120 | custom kernels bypass CUTLASS | 0.5B+7B Q4/Q8/F16 all run, both PRO cards | Confirmed |
| E12-H34 | decode orders Q4 > Q8 > fp16 | bandwidth-bound decode | 7B: 213/164/94 tok/s (Q4 = 2.27x fp16) | Confirmed |
| E12-H35 | one build serves Ada natively | 89-real;120 fatbin | Ada runs, same ordering (contended, lower bound) | Confirmed |
| E12-H36 | batching multiplies the int4 win | parallel slots | Q4 B32 = 3,317 tok/s (14.8x B1); regime step at B16 | Confirmed |
| E13-H37 | vLLM serves sm_120 | production stack | works after nvcc+g+++curand env wiring | Confirmed |
| E13-H38 | vLLM fp8 beats bf16 | on-the-fly W8A8-fp8 | bs1 +21%, batch64 +71% (0.5B) | Confirmed |
| E13-H39 | GPTQ-int4 works on sm_120 | Marlin-family kernels | bs1 470 tok/s (+26%) | Confirmed |
| E13-H40 | AWQ-int4 works on sm_120 | awq_marlin | bs1 495 tok/s (+33%, best) | Confirmed |
| E13-H41 | batching is first-order lever | continuous batching | 31.6x bs1; quant +21-33% on top | Confirmed |

*Research-at-a-glance table truncated to the two rounds kept below; the source log carried all 105 rows.*

**Baseline performance** (mmBERT-150M, b32 s256, eager)

| measure | fp32 (naive floor) | bf16 (reference) |
|---|---|---|
| tokens/s PRO 6000 | 96,971 | 261,642 |
| tokens/s PRO 4000 | 37,853 | 98,098 |
| tokens/s RTX 5000 Ada | 24,082 | 50,764 |
| bf16 speedup vs fp32 | - | 2.11-2.70x |
| fidelity cosine | 1.0000 | 1.0000 (reference) |

## Methodology and metrics

Each config runs one model+method+compile+attn at a fixed (batch, seq) in an isolated subprocess on a pinned GPU (UUID, `CUDA_DEVICE_ORDER=PCI_BUS_ID`). Timing uses CUDA events (pure GPU) after 8 warmup iters; 30 timed passes averaged.

- **Throughput** - tokens/s (primary), `batch × seq / gpu_ms`; higher better
- **Latency** - `gpu_ms_per_batch` (CUDA-event, GPU only); `host_overhead_ms = wall − gpu`
- **Footprint** - `mem_after_load_mib` (weights resident), `peak_vram_mib` (peak during inference)
- **Speedup ×** - method tokens/s ÷ bf16-eager tokens/s, same GPU and shape; "vs cbf16" = ÷ compiled bf16
- **Fidelity guardrail** - cosine of mean-pooled, L2-normed embeddings vs the bf16 model on a fixed 8-chunk probe; must stay ≥ 0.99; all methods passed (min 0.9931, bge int8-dynamic)

**Naive baseline** - fp32, eager, no compile, mmBERT-base at b32 s256: the floor. Practical reference is bf16 eager; speedups reported as × vs bf16 eager, with the fp32 floor noted. Every quant method here is faithful (cosine ≥ 0.99), so verdicts are about speed.

- **Verdict head** - Ships / Promoted / Kept / Refuted / Refuted (null) / Killed-at-gate / Blocked, each with the number that justifies it

## Setup

- **Fixtures** - `results/chunks.json` (essay chunks), tiled to the target batch, padded/truncated to the target seq
- **Methods** - fp32, bf16, fp16, fp8-ft (transformers FineGrainedFP8Config), torchao `quantize_`: ao-int8w, ao-int8dyn, ao-fp8w, ao-fp8dyn; ao-int4w attempted (blocked)
- **Compile** - none, default, reduce-overhead (CUDA graphs), applied after quantization
- **Reproducibility** - `HF_HUB_OFFLINE=1`, `reference_compile=False` on ModernBERT, fixed workload; minor GPU non-determinism
- **Execution vehicle** - `run_matrix.py` per-GPU config lists as three parallel background jobs

`[... rounds E01-E11 (32 hypotheses: precision/quant-method matrix, torch.compile fusion, batch and sequence regime, model size, orthogonal levers, autotune, decoder regime, static-cache decode, size crossover, task accuracy, MSLK int4) omitted from this skill example ...]`

## E12 - llama.cpp custom CUDA kernels (Qwen2.5-0.5B/7B GGUF, all GPUs)

Alternative-stack round 1: llama.cpp's hand-written CUDA int4/int8 kernels (MMQ) do not use CUTLASS, so the sm_120 kernel wall should not apply. Built from source (master 4fc4ec5) for `89-real;120` with `GGML_CUDA_FA_ALL_QUANTS=ON` via pip nvcc 13.3 + conda gcc 13; build recipe in [`../llamacpp-build-recipe.md`](../llamacpp-build-recipe.md).

### E12-H33 llama.cpp int4 runs on sm_120

Opens the alternative-stack arc: the first test of whether llama.cpp's non-CUTLASS int4 kernels clear the sm_120 wall that stopped every torch-based int4 lever in E10/E11. This is the round's go/no-go gate - if the stack will not even initialize on consumer Blackwell, nothing downstream matters.

The whole inference stack is swapped from torch to llama.cpp's ggml CUDA backend and pointed at the same Qwen GGUF checkpoints on the same three cards E10 and E11 used. Because the models, cards, and quant levels are held while only the kernel provenance changes, a clean init here isolates whether the earlier int4 wall was hardware or a torch-side kernel gap.

- **Hypothesis** - llama.cpp Q4_K_M inference works natively on consumer Blackwell (custom kernels bypass the CUTLASS wall that blocks torchao/MSLK int4)
- **Lever** - inference stack (ggml CUDA backend vs torch) at fixed models, cards, and quant levels
- **Mechanism** - the ggml CUDA backend's hand-written MMQ int4/int8 kernels do not use CUTLASS, so the sm_120 kernel wall that blocks torchao/MSLK int4 does not apply - the failing torch code path simply does not exist in this stack
- **Prediction** - loads and generates on both PRO cards without kernel errors
- **Acceptance bar** - both PRO Blackwell cards initialize and generate the full Q4_K_M/Q8_0/F16 suite without CUTLASS kernel errors
- **Experiment** - setup: the ggml CUDA backend built from llama.cpp master 4fc4ec5 (2026-07-01), binary `vendor/llama.cpp/build/bin/llama-bench` compiled GGML_CUDA=ON GGML_CUDA_FA_ALL_QUANTS=ON for CMAKE_CUDA_ARCHITECTURES=89-real;120a via pip CUDA-13 nvcc (~/venvs/cuda13) + conda gcc 13 (env cudabuild), RPATH baked so no runtime env is needed (recipe docs/llamacpp-build-recipe.md)<br>cards: the suite ran on three cards each pinned with CUDA_DEVICE_ORDER=PCI_BUS_ID then CUDA_VISIBLE_DEVICES=<idx> - RTX PRO 6000 Blackwell Max-Q Workstation Edition 96GB (PCI idx 1, log 97886 MiB, cc 12.0), RTX PRO 4000 Blackwell 24GB (PCI idx 0, log 24466 MiB, cc 12.0) and RTX 5000 Ada Generation 32GB (PCI idx 2, log 32759 MiB, cc 8.9)<br>models: Qwen2.5-0.5B-Instruct-GGUF + Qwen2.5-7B-Instruct-GGUF (HF repos Qwen/Qwen2.5-0.5B-Instruct-GGUF and Qwen/Qwen2.5-7B-Instruct-GGUF, official Qwen-team quantizations, Apache-2.0, downloaded pre-quantized not produced locally) in Q4_K_M/Q8_0/F16 at -fa 1 -ngl -1<br>baseline: the torch baseline being escaped is E10/E11 torchao and MSLK int4 which hit the sm_120 CUTLASS kernel wall on the same cards
- **Result** - PRO 6000 (cc 12.0) initializes and runs the full 0.5B + 7B suite in Q4_K_M/Q8_0/F16 without kernel errors; Ada likewise
- **Verdict** - Confirmed; ggml's hand-written MMQ kernels make int4 a first-class citizen on sm_120 - the wall was CUTLASS-library maturity, never the hardware

### E12-H34 quant ordering follows bandwidth in decode

With the stack proven to run, this quantifies the payoff: whether dropping bytes per weight buys decode throughput on Blackwell, and in the memory-bound order the theory predicts. It converts the go/no-go of H33 into a measured quant-selection rule.

The lever is exercised across two sizes of one family so the effect can be read against scale: Qwen2.5-Instruct at 0.5B and 7B, each in three official Qwen-team quantizations of the same weights, swept back-to-back on the PRO 6000 under llama.cpp's own bench harness. Holding model, card, and harness fixed leaves bytes-per-weight as the only moving part, so any decode ordering that emerges is attributable to weight traffic alone.

- **Hypothesis** - bs=1 decode throughput orders Q4_K_M > Q8_0 > fp16 (memory-bound: fewer bytes = more tok/s), the ordering unreachable in torch on this hardware
- **Lever** - GGUF weight quantization level (q4_k_m / q8_0 / fp16) at fixed model, card, and harness
- **Mechanism** - at batch size 1 decode is memory-bandwidth-bound, so a smaller weight footprint moves fewer bytes per token and lifts tok/s - Q4_K_M reads less than Q8_0, which reads less than fp16
- **Prediction** - monotone decode gain with smaller weights
- **Acceptance bar** - monotone bs=1 decode ordering Q4_K_M > Q8_0 > fp16 (smaller weights win) on the PRO 6000
- **Experiment** - setup: RTX PRO 6000 Blackwell Max-Q Workstation Edition 96GB (PCI idx 1, log 97886 MiB, cc 12.0, CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1)<br>models: Qwen2.5-0.5B-Instruct-GGUF q4_k_m/q8_0/fp16 (630,167,424 params; q8_0 on disk 675,710,816 B, fp16 1,260,477,952 B; official Qwen-team quant, Apache-2.0, downloaded); Qwen2.5-7B-Instruct-GGUF q4_k_m (2-part split 3,993,201,344 + 689,872,288 = 4,683,073,632 B on disk), q8_0 (3-part), fp16 (4-part)<br>harness: vendor/llama.cpp/build/bin/llama-bench (master 4fc4ec5), synthetic pp512 prefill + tg128 decode, -fa 1 -ngl -1, 5 samples per point (not the results/chunks.json essay corpus), stamped in results/llamacpp/P6-qwen-bench.json<br>baseline: the in-stack F16 decode is what the ordering is measured against (7B F16 93.6 tok/s)
- **Result** - PRO 6000, tg128: 7B - Q4_K_M 212.8 > Q8_0 163.8 > F16 93.6 tok/s (**Q4 = 2.27x fp16**); 0.5B - Q4 688 ≈ Q8 685 > F16 625 (+10%, launch-bound on the big card)<br>Prefill pp512 inverts or flattens: 0.5B F16 66.0k > Q8 58.2k > Q4 54.6k; 7B Q8 12.8k ≈ Q4 11.9k ≈ F16 11.2k
- **Verdict** - Confirmed; the memory-bound decode win is real and grows with model size (weights dominate traffic at 7B, launch overhead dominates at 0.5B) - pick quant by regime: Q4 for decode, fp16/Q8 for prefill-heavy work

### E12-H35 the sm_89-real build serves Ada natively

Checks that the same binary generalizes across the fleet: the two-arch fatbin should serve the older Ada card with native code rather than falling back to slow PTX JIT. It settles the portability question a single build must answer before the round's numbers can be trusted on every card.

The identical two-arch binary is run on the RTX 5000 Ada and compared against the old sm_120-only build that forced Ada through PTX JIT, over the same Qwen GGUF suite. Holding the model set and card fixed and changing only which build loads means any init or throughput difference reflects native SASS versus JIT, not a workload change.

- **Hypothesis** - one build with `CMAKE_CUDA_ARCHITECTURES=89-real;120` covers all three cards (the preinstalled sm_120-only build left Ada to PTX JIT)
- **Lever** - multi-arch fatbin (89-real;120a) on the Ada card versus the sm_120-only build, same models and suite fixed
- **Mechanism** - compiling for 89-real bakes native Ada SASS into the fatbin alongside the sm_120a code, so the RTX 5000 Ada loads a native kernel instead of PTX-JIT-compiling the sm_120 image at runtime
- **Prediction** - Ada initializes with native code and shows the same quant ordering
- **Acceptance bar** - Ada initializes with native code (not PTX JIT) and reproduces the bandwidth-ordered decode Q4_K_M > Q8_0 > F16
- **Experiment** - setup: the single 89-real;120a fatbin (vendor/llama.cpp/build/bin/llama-bench, master 4fc4ec5, CMAKE_CUDA_ARCHITECTURES=89-real;120a, GGML_CUDA_FA_ALL_QUANTS=ON, recipe docs/llamacpp-build-recipe.md) run on the RTX 5000 Ada Generation 32GB (PCI idx 2, log 32759 MiB, cc 8.9, CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=2) versus the preinstalled sm_120-only build that left Ada on PTX JIT<br>models: same Qwen2.5-0.5B/7B-Instruct-GGUF suite (official Qwen-team quants, Apache-2.0, downloaded) in Q4_K_M/Q8_0/F16, synthetic pp512/tg128, -fa 1 -ngl -1, results/llamacpp/A5-qwen05b-bench.json + A5-qwen05b-fp16-bench.json + A5-qwen7b-bench.json<br>baseline: the in-stack F16 decode on this card; a foreign workload shared the Ada card during the run
- **Result** - Ada initializes (`compute capability 8.9, VMM: yes`) and runs the full quant set; decode ordering realized: Q4_K_M 242 > Q8_0 228 > F16 146 tok/s (Q4 = 1.66x fp16); prefill inverts: F16 31.0k > Q8_0 29.7k > Q4_K_M 22.4k tok/s. Caveat: a foreign workload occupied ~12 GB and bursts of Ada utilization during the run, so Ada numbers are lower bounds
- **Verdict** - Confirmed; one two-arch build serves all three cards, and Ada shows the same bandwidth-ordered decode win

### E12-H36 batched llama-server multiplies decode throughput

Closes the round by stacking the throughput lever from E07 on top of the int4 bandwidth win, asking whether parallel decode slots still multiply once the weights are already quantized. This is where the single-stream decode gain turns into a serving-throughput number.

The batched llama-server harness sweeps parallel decode slots on the PRO 6000 while the 7B Qwen weights stay at each fixed quant level. Turning only the slot count on top of an already-quantized model shows whether the batching multiplier from E07 stacks on the int4 bandwidth win rather than replacing it.

- **Hypothesis** - `llama-batched-bench` / parallel llama-server slots recover the batching lever (E07: batching 15.8x) on top of the int4 bandwidth win
- **Lever** - batch/parallel decode slots (-npl 1..32) at fixed quant, model, and card
- **Mechanism** - filling parallel decode slots batches the per-token matmul so one weight read serves many sequences, amortizing the memory traffic that bounds bs=1 decode - stacked on the smaller int4 footprint rather than replacing it
- **Prediction** - near-linear scaling to at least b8 on the PRO 6000
- **Acceptance bar** - near-linear decode scaling to at least batch 8 on the PRO 6000
- **Experiment** - setup: vendor/llama.cpp/build/bin/llama-batched-bench (master 4fc4ec5) sweeping -npl 1,2,4,8,16,32 at fixed -npp 512 -ntg 128, -ngl 99 -fa 1, n_kv_max 32768, on the RTX PRO 6000 Blackwell Max-Q Workstation Edition 96GB (PCI idx 1, log 97886 MiB, cc 12.0, CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1)<br>models: model Qwen2.5-7B-Instruct-GGUF Q4_K_M/Q8_0/F16 (official Qwen-team quant, Apache-2.0, downloaded, q4_k_m 4,683,073,632 B on disk), outputs results/llamacpp/P6-qwen7b-{q4,q8,fp16}-batched.txt<br>baseline: the baseline is the batching lever from E07 (recorded 15.8x) stacked on the H34 bs=1 int4 bandwidth win
- **Result** - 7B aggregate decode (pp512/tg128, PRO 6000): Q4_K_M B1 224 → B4 555 → B16 2,075 → B32 3,317 tok/s (14.8x); Q8_0 reaches 2,923 at B32; F16 1,192 at B16. Scaling is stepped, not linear - a kernel regime switch at B16 triples throughput (B8 627 → B16 2,075 for Q4), and Q4 dips below Q8 exactly at B8 (627 vs 790, the batched-GEMM boundary)
- **Verdict** - Confirmed; batching multiplies the int4 win (Q4@B32 = 35x fp16@B1) and quant keeps its edge under batching (Q4 1.13x Q8, 1.74x fp16 at B16-32) - but avoid the B8 pocket for Q4

## E13 - vLLM production serving on sm_120 (Qwen2.5-0.5B, PRO 4000/6000)

Alternative-stack round 2: vLLM 0.24 (torch 2.11+cu130, own venv) ships Marlin/Machete quant GEMMs and continuous batching - a second escape route around the torchao kernel gaps, and the natural "give to the team" serving layer.

### E13-H37 vLLM runs on consumer Blackwell

The round opens with a gating check - the vLLM engine must initialize and serve on the consumer Blackwell PRO 4000 before any quant lever it offers can be measured. Nothing downstream matters if the stack cannot reach engine init on sm_120.

This is a bare engine-init probe: vLLM is stood up in its own venv on the PRO 4000 with a small Qwen decoder, and the only question is whether the engine reaches serving on sm_120 at all. No quant lever is turned yet, so the outcome reads purely on whether the shipped wheels and a self-provided toolchain can build kernels for compute 12.0.

- **Hypothesis** - vLLM 0.24 initializes and serves on sm_120 (wheels ship sm_120 SASS)
- **Lever** - inference stack (vLLM 0.24 vs torch) on the PRO 4000 sm_120 card, model and env fixed
- **Mechanism** - the vLLM 0.24 wheels ship sm_120 SASS, so the engine can build native kernels for compute 12.0 at start rather than falling back to unsupported paths
- **Prediction** - engine builds, generates correctly on the PRO cards
- **Acceptance bar** - engine builds and generates correctly on the PRO cards
- **Experiment** - setup: vLLM 0.24.0 in the dedicated `~/venvs/vllm` [Python 3.12.3, torch 2.11.0+cu130, triton], invoked as `~/venvs/vllm/bin/python qbench_vllm.py`; card RTX PRO 4000 Blackwell 24 GB, PCI idx 0 "P4", sm_120 / compute_cap 12.0, pinned `CUDA_DEVICE_ORDER=PCI_BUS_ID` + `CUDA_VISIBLE_DEVICES` set to the P4 device; WSL2 host<br>models: artifact `Qwen/Qwen2.5-0.5B-Instruct` downloaded pre-trained from HF, `model.safetensors` 0.92 GB bf16<br>procedure: the H37 probe only builds the engine - the three env fixes required to reach init are named in Result; log `logs/e13-vllm-p4.log`
- **Result** - works after wiring a CUDA toolchain for FlashInfer's JIT: vLLM compiles sm_120f kernels at engine start and needs nvcc (`CUDA_HOME` → the pip cu13 toolkit venv), a host g++ (`NVCC_PREPEND_FLAGS='-ccbin <conda g++13>'`), and curand headers (`nvidia-curand` wheel). With those three env fixes the engine serves on the PRO 4000; first engine init pays ~60 s JIT (cached in `~/.cache/flashinfer` thereafter, later inits 22-24 s)
- **Verdict** - Confirmed; sm_120 is served, but only with a self-provided CUDA 13 toolchain - stock environments without nvcc fail at engine init

### E13-H38 on-the-fly fp8 beats bf16 in vLLM decode

With the engine serving, the first quant lever tests whether vLLM's fused fp8 kernels turn quantization into a decode win - the outcome eager torch could not produce, where fp8 regressed.

With the engine already serving, the fp8 flag is flipped on and its bs=1 and batched decode compared against the same worker's bf16 numbers on the PRO 4000. The model, prompt, and stack are held identical to the bf16 baseline, so the only variable is whether vLLM's fused fp8 kernels turn quantization into a decode gain rather than the regression eager torch showed.

- **Hypothesis** - `quantization="fp8"` (W8A8-fp8, dynamic scales) raises decode throughput vs bf16 in vLLM, unlike eager torch where fp8 regressed
- **Lever** - vLLM `quantization="fp8"` (W8A8-fp8, dynamic scales) vs bf16 on the PRO 4000, model, prompt, and stack fixed
- **Mechanism** - the `fp8` flag casts weights and activations to W8A8-fp8 with dynamic per-tensor scales computed at load, dispatching to vLLM's fused fp8 GEMMs, so no pre-quantized checkpoint is needed
- **Prediction** - fp8 ≥ bf16 on bs=1 and batched decode
- **Acceptance bar** - fp8 ≥ bf16 on bs=1 and batched decode
- **Experiment** - models: `quantization="fp8"` on `Qwen/Qwen2.5-0.5B-Instruct` - W8A8-fp8 with dynamic per-tensor scales computed at load, no checkpoint needed; base weights `model.safetensors` 0.92 GB bf16 from HF<br>setup: card RTX PRO 4000 Blackwell 24 GB, PCI idx 0 "P4", sm_120; run via `qbench_vllm.py` in `~/venvs/vllm` [vLLM 0.24.0, torch 2.11.0+cu130], env `CUDA_DEVICE_ORDER=PCI_BUS_ID`, `HF_HUB_OFFLINE=1`, `TOKENIZERS_PARALLELISM=false`, `VLLM_LOGGING_LEVEL=WARNING` plus the H37 FlashInfer JIT toolchain [`CUDA_HOME` = pip cu13 toolkit, `NVCC_PREPEND_FLAGS='-ccbin <conda g++13>'`, `nvidia-curand`]<br>procedure: engine `LLM(dtype="bfloat16", gpu_memory_utilization=0.80, enforce_eager=False)` so CUDA graphs capture; prompt = fixed filler truncated to 256 tokens, gen 128 tokens greedy [`SamplingParams(temperature=0, ignore_eos=True)`]; bs=1 decode = min over 3 timed single-prompt generations after 1 warmup, batched = 64 identical prompts in one continuous-batching `generate()` call<br>baseline: P4 bf16 same worker/shapes `results/qvllm/P4-qwen05b-bf16.json` bs=1 373.3, batch-64 11,789.5 tok/s; result `results/qvllm/P4-qwen05b-fp8.json`, log `logs/e13-vllm-p4.log`
- **Result** - Qwen2.5-0.5B on PRO 4000: bs=1 decode 453 vs 373 tok/s (+21%); batch-64 20,125 vs 11,790 tok/s (+71%). No checkpoint needed - quantizes at load
- **Verdict** - Confirmed; the fused-kernel serving stack realizes the quant decode win that eager torch could not - fp8 is the batched-throughput winner

### E13-H39 GPTQ-int4 via Marlin/Machete works on sm_120

The int4 question the torch rounds could not answer - vLLM's GPTQ Marlin/Machete kernels are tested for whether they run a 4-bit checkpoint on sm_120 and win bs=1 decode, where torchao and MSLK could not.

A pre-quantized 4-bit GPTQ checkpoint is loaded into the same vLLM worker and card as the fp8 run, letting the auto-detected Marlin/Machete kernels carry the int4 GEMMs. Everything but the checkpoint and its kernel path matches H38, so a working generate at or above bf16 decode is a direct answer to the int4 question torchao and MSLK left open.

- **Hypothesis** - vLLM's GPTQ path (Marlin kernel family) runs int4 on consumer Blackwell where torchao/MSLK could not, and wins bs=1 decode
- **Lever** - int4 GPTQ checkpoint + vLLM kernel dispatch (Marlin/Machete) vs bf16 on the P4, same card, stack, and prompt as H38
- **Mechanism** - the pre-quantized W4A16 int4 checkpoint's quant format is auto-detected, so dispatch lands on the Marlin/Machete kernel family without an explicit flag, the bypass route the torchao path lacked
- **Prediction** - loads, generates, decode ≥ bf16
- **Acceptance bar** - loads, generates, decode ≥ bf16
- **Experiment** - models: `Qwen/Qwen2.5-0.5B-Instruct-GPTQ-Int4` pre-quantized checkpoint downloaded from HF, produced by Qwen / Alibaba; W4A16 int4, quant format auto-detected so the vLLM flag stays null and dispatch lands on the Marlin/Machete kernel family; on-disk size not recorded - checkpoint no longer in the HF cache; float16 weights cast to bfloat16 at load per worker `dtype="bfloat16"`<br>setup: same P4 card / stack / env / prompt shape as H38, `qbench_vllm.py` in `~/venvs/vllm`<br>baseline: P4 bf16 `results/qvllm/P4-qwen05b-bf16.json` bs=1 373.3, batch-64 11,789.5 tok/s; result `results/qvllm/P4-qwen05b-gptq.json`, log `logs/e13-vllm-p4.log`
- **Result** - Qwen2.5-0.5B-GPTQ-Int4: bs=1 decode 470 tok/s (+26% vs bf16), batch-64 18,452 (+57%)
- **Verdict** - Confirmed; int4 runs on sm_120 through vLLM's Marlin-family kernels - the first working int4 decode on this machine

### E13-H40 AWQ-int4 works on sm_120

The complementary int4 path - AWQ through the awq_marlin kernel is tested for whether it clears the same sm_120 wall as GPTQ and reaches Q4-class decode speed.

The AWQ 4-bit checkpoint is dropped into the same worker, card, and prompt as the GPTQ run, dispatching through the auto-detected awq_marlin kernel. Because only the checkpoint and its kernel change from H38 and H39, its decode speed can be read directly against both bf16 and the GPTQ int4 result as the complementary int4 route.

- **Hypothesis** - the AWQ path (awq_marlin) equally bypasses the wall
- **Lever** - int4 AWQ checkpoint via the `awq_marlin` kernel vs bf16 on the P4, same card, stack, and prompt as H38
- **Mechanism** - the pre-quantized W4A16 int4 AWQ checkpoint dispatches through the auto-detected `awq_marlin` kernel with the flag null, the same bypass route as the GPTQ Marlin family
- **Prediction** - loads and generates at Q4-class speed
- **Acceptance bar** - loads and generates at Q4-class speed
- **Experiment** - models: `Qwen/Qwen2.5-0.5B-Instruct-AWQ` pre-quantized checkpoint downloaded from HF, produced by Qwen / Alibaba; W4A16 int4 via the `awq_marlin` kernel, quant format auto-detected [flag null]; on-disk size not recorded - checkpoint no longer in the HF cache; float16 weights cast to bfloat16 at load<br>setup: same P4 card / stack / env / prompt shape as H38, `qbench_vllm.py` in `~/venvs/vllm`<br>baseline: in-round baseline P4 bf16 `results/qvllm/P4-qwen05b-bf16.json` bs=1 373.3 tok/s; the verdict's 95 tok/s "best HF transformers path" is the cross-round compiled-bf16 decode anchor from the earlier torch decode rounds [`qbench_decoder.py`]; result `results/qvllm/P4-qwen05b-awq.json`, log `logs/e13-vllm-p4.log`
- **Result** - Qwen2.5-0.5B-AWQ: bs=1 decode 495 tok/s (+33% vs bf16, best of all methods), batch-64 18,848 (+60%)
- **Verdict** - Confirmed; AWQ-int4 is the bs=1 decode winner at 0.5B - 5.2x the best HF transformers path (95 tok/s compiled bf16)

### E13-H41 continuous batching is the dominant serving lever

The round closes by re-checking the campaign's ordering result on the vLLM stack - whether continuous batching, not quantization, remains the first-order decode lever, as the earlier torch E07 round found.

The knob is the batch width itself: sixty-four identical prompts submitted in one generate() call are set against a single-prompt decode, run back-to-back on the same PRO 4000 card, vLLM stack, and environment carried over from the H38 quant sweep. Holding model, card, and serving stack fixed leaves the number of requests the scheduler packs into each decode step as the only moving part, so any aggregate gain is attributable to continuous batching rather than the quant kernels layered on top.

- **Hypothesis** - vLLM's continuous batching multiplies decode throughput far beyond any quant effect (E07 showed batching 15.8x vs quant ≤1x)
- **Lever** - number of concurrent requests (batch-64 continuous batching vs bs=1 decode) at fixed P4 card, vLLM stack, and model
- **Mechanism** - continuous batching submits 64 concurrent requests in one `generate()` call so the scheduler packs decode steps across sequences, multiplying aggregate throughput independent of the per-request quant kernel
- **Prediction** - batch-64 aggregate ≥ 10x bs=1, larger than any quant delta
- **Acceptance bar** - batch-64 aggregate ≥ 10x bs=1, larger than any quant delta
- **Experiment** - setup: same P4 card / stack / env as H38 [vLLM 0.24.0, `~/venvs/vllm`, RTX PRO 4000 Blackwell idx 0 sm_120]<br>procedure: continuous batching: batch-64 = 64 identical prompts submitted in one `qbench_vllm.py generate()` call vs bs=1 single-prompt decode; the quant deltas layered on top are the H38-H40 fp8 / GPTQ / AWQ runs<br>baseline: bf16 numbers from `results/qvllm/P4-qwen05b-bf16.json` [bs=1 373.3, batch-64 11,789.5 tok/s]; the E07 anchor cited in the hypothesis - batching 15.8x vs quant ≤1x - is the earlier torch encoder/decoder batching round<br>artifacts: log `logs/e13-vllm-p4.log`
- **Result** - bf16 batch-64 = 31.6x bs=1 (11,790 vs 373 tok/s);<br>quant deltas are +21-33% on top
- **Verdict** - Confirmed; batching is the first-order lever (30x), quantization the second-order multiplier (1.2-1.7x) - and they stack

`[... rounds E14-E36 (64 hypotheses: Triton/gemlite/bnb, TensorRT, 72B ceiling, llama-server batch engine, GitHub kernel candidates, NVFP4/MXFP8 block-scaled, SageAttention, cross-stack closure, speculation, dual-Blackwell pooling, MoE regime, heresies, serving/compiler knobs, encoder-record push, kernel rebuild, speculation rehabilitation) omitted from this skill example. The closing sections below are preserved - trimmed to representative bullets - to show the full document skeleton ...]`

## Lessons learned

- **Compile is the precondition, not an optimization** - eager quant regresses on every card (int8-dynamic 0.07x); the same method reaches 2.57x once compiled, a ~35x swing from fusion alone
- **The winning recipe is compile + dynamic-activation quant** - weight-only never accelerates throughput (parity at best, 0.03x at worst when compiled)
- **Decode is its own regime** - bs=1 decode is ~200x slower per token than prefill (memory/launch-bound); batching (15.8x at bs16) is the decode throughput lever here, not quantization
- **The wall was the torch ecosystem, not sm_120** - llama.cpp (custom CUDA), vLLM (Marlin/Machete/fp8) and TensorRT all run quantized - including int4 - on consumer Blackwell; only torchao's CUTLASS paths and MSLK lack sm_120 kernels
- **The decode win needs persistent-engine kernels** - the same int4 that loses 3x in torch (gemlite Triton, per-call launch overhead) wins 2.3-2.8x in llama.cpp/vLLM; fused low-bit decode pays off only inside a serving engine with graph-captured, persistent kernels
- **At bs=1 the stack does not matter, the bytes do** - vLLM and llama.cpp converge (224 vs 213-226 tok/s 7B-int4; at 72B the 4-bit GGUF beats the 8-bit fp8 checkpoint 28.5 vs 19.2) - single-stream decode is pure weight bandwidth
- **Speculative decoding never won here, in any regime** - fast 7B target (0.25-0.49x), ngram on prose (1.01x), under batching (0.24x), even the 24x-ratio 72B target (0.98x); off-the-shelf drafts fail on speed ratio *or* acceptance rate - the wins in the papers need trained-per-target heads (MTP/EAGLE/DSpark)
- `[... ~22 further lessons omitted from this skill example ...]`

## Conclusions

- **Ships (encoder throughput)** - on the PRO 6000: MXFP8-dynamic + sdpa + compile, 771k tok/s at cosine 0.970 - the new champion (+19% over int8-dyn in the same harness); int8-dynamic + sdpa + compile remains the fidelity-conservative pick (748k, cosine 0.998)
- **Ships (decoder serving)** - vLLM with an NVFP4 checkpoint where one exists (12,528 tok/s b128 on the PRO 6000), else fp8 (throughput: batch +71-81%) or AWQ/GPTQ-int4 (latency: bs=1 +26-33% at 0.5B, 2.8x at 7B); needs the CUDA toolchain env wiring on this host
- **Ships (decoder single-stream / local)** - llama.cpp Q4_K_M: 7B decode 213 tok/s on the PRO 6000 (2.27x fp16), batched to 3,317 tok/s at B32
- **Ships (always)** - torch.compile on the bf16 model even without quant: ~2x, the single highest-value change; the quant edge is a b8-b64 window peaking at b32
- **Do not use** - eager quantization anywhere, HF transformers for decoder inference, int8-weight-only+compile (0.03x trap), max-autotune (InductorError on sm_120), off-the-shelf speculative decoding in any regime
- `[... further Ships / Task-safe bullets omitted ...]`
- **Design distilled in** [`../quantized-inference-sota.md`](../quantized-inference-sota.md)

## Next steps

- **Trained draft heads** - the only speculation path left open: EAGLE-3/MTP heads trained for the target (what DSpark actually ships); llama.cpp already exposes `--spec-type draft-eagle3|draft-mtp` - needs a compatible head checkpoint for Qwen
- **NVFP4 task-accuracy gate** - fp4 encoders broke the cosine floor (0.89-0.91); run the E10-style retrieval eval under NVFP4 before it ships anywhere
- `[... further open threads omitted ...]`
- **Refuted, do not revisit** - eager quantization for speed, int8-weight-only+compile, max-autotune on sm_120, larger batch as a quant lever on a saturated GPU, static-cache decode on sm_120, int4 via torchao/MSLK/gemlite for speed on sm_120, off-the-shelf draft/ngram speculation (five refutations), BitBLAS, MLC-LLM wheels, SageAttention below multi-k contexts
