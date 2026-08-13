# datascience

Data science project standards for Claude Code. Enforces notebook structure, naming conventions, rich output styling, and project layout. Scaffolds new projects from a copier template, reviews existing code for compliance, applies research-backed prompt engineering techniques, and structures hypothesis-driven experiment documentation - a canonical experiments log plus a SOTA design doc.

Unlike ad-hoc notebook cleanups, this plugin treats the notebook as a standardised artefact - fixed section order, GPU selection before torch/tf/jax imports, a single configuration cell with rich display, and completion-safe progress bars. Project scaffolding is driven by the [copier-data-science](https://github.com/stellarshenson/copier-data-science) template so new projects match existing ones on day one.

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install datascience@stellarshenson-marketplace
```

## Commands

| Command | What it does |
|---------|--------------|
| `/datascience:new-project` | Scaffold a new project from the `copier-data-science` template |
| `/datascience:notebook` | Create a properly structured Jupyter notebook with all standard sections |
| `/datascience:review` | Review a notebook or script against all standards and produce a violation checklist |
| `/datascience:fix-notebook` | Restructure a notebook to comply with every standard - layout, styling, progress bars, header |
| `/datascience:fix-project` | Port an existing project to `copier-data-science` standards or update an existing copier project |
| `/datascience:apply-style` | Apply rich output styling - colours, print patterns, missing formatting |
| `/datascience:apply-progressbar` | Add or fix progress bars, choosing classic (tqdm) or modern (rich) |
| `/datascience:apply-footnotes` | Add JupyterLab-compatible footnotes using the anchor-link pattern |
| `/datascience:update-prompt` | Update a prompt, system instruction, or agent definition by applying a prompt engineering technique |
| `/datascience:challenge` | Full psychological prompting stack for difficult problems - stakes, incentive, competitive framing |
| `/datascience:hypothesis` | Write or extend a hypothesis-driven experiments log and its SOTA design doc - record a round, fan out the next one, or conclude the design |
| `/datascience:popular-science` | Create or update an accessible, well-sourced popular-science article or explainer from technical work - spine, sourced-and-numbered claims, best-in-class figures, arc-back kicker |
| `/datascience:adversarial-review` | Hostile independent review of an experiments log, pipeline, article or spec - the data-science entry point into the `devils-advocate:adversarial-review` skill (requires the `devils-advocate` plugin) |

## Skills

Auto-triggered based on context.

| Skill | Triggers when |
|-------|--------------|
| `datascience` | Working with data science projects, datasets, ML models, PyTorch, Polars, sklearn |
| `notebook-standards` | Creating or modifying Jupyter notebooks (`.ipynb` or Jupytext `.py`) - includes the rich colour palette and equation conventions as `references/` |
| `progressbars` | Adding progress bars with tqdm (classic) or rich (modern) |
| `footnotes` | Adding references, citations, or notes in notebooks and markdown |
| `prompt-engineering` | Crafting system prompts, agent instructions, or LLM prompts |
| `hypothesis` | Writing up an experiment, recording a hypothesis and result, fanning out the next round from persona generators, deciding which approach won, or drafting an experiments log / SOTA design doc |
| `dataset` | Downloading, vendoring or documenting a public or private corpus into a `data/external/<task>-datasets/` folder, or auditing what data a project holds and under what licence |

## Prompt engineering techniques

The `prompt-engineering` skill ships seven research-backed techniques. Each reference contains the paper, a template, and usage guidance. See [`skills/prompt-engineering/references/`](skills/prompt-engineering/references/) for full content.

| # | Technique | Best for |
|---|-----------|----------|
| 1 | Psychological Prompting | Complex tasks, maximum effort (+45-115%) |
| 2 | Chain of Thought | Math, logic, debugging (+46% on GSM8K) |
| 3 | Chain of Draft | Token-limited reasoning (~7.6% of CoT tokens) |
| 4 | Tree of Thought | Design decisions, architecture trade-offs |
| 5 | Few-Shot | Structured output, classification, format-sensitive extraction |
| 6 | Self-Refine | Code, documents, iterative quality improvement |
| 7 | Rephrase and Respond | Ambiguous requirements, multi-part questions |

Use `/datascience:update-prompt` to pick and apply a technique to an existing prompt, or `/datascience:challenge` to apply the full psychological stack.

## Hypothesis-driven documentation

The `hypothesis` skill structures and maintains two complementary research documents - a canonical, append-only **experiments log** (each hypothesis with its setup, prediction, result, and verdict) and a **SOTA document** that distils the winning hypotheses into a final design. The log is the system of record across runs: each run reads it, appends the next round, and never rewrites a recorded verdict.

| Aspect | What it enforces |
|--------|------------------|
| Per-hypothesis template | Hypothesis (one falsifiable causal claim) → Lever → Mechanism → Prediction → Acceptance bar → Result → Verdict |
| Canonical doc across runs | one log per track at `docs/experiments/<project>-experiments.md`, monotonic rounds, immutable verdicts (superseded by back-reference) |
| SOTA shape | Abstract → Problem → Solution → Pipeline → Mechanism → Performance → Limitations → FAQ → Implementation → Conclusions → Bibliography |
| Style | terse overview-then-bullets, numbers inline, sweeps as tables, maths as separated `$$…$$` display blocks, "private dataset" sanitisation |
| Fanout | next-round generation from the campaign kernel via persona generators; pre-registration (prediction + acceptance bar, user sign-off) is the prerequisite - nothing lands or runs before it |

The skill also **generates** hypotheses, not just records them. Seven pluggable hypothesisers under [`skills/hypothesis/generators/`](skills/hypothesis/generators/) - follower, contrarian, heretical, hybridizer, mechanist, deflationist, scout - each an exploration policy over the campaign's kernel (channel vocabulary, lever record, metric panel + naive baseline, verdict protocol) with an expected verdict signature that self-tests the round. A fanout asks for scale (probe 3-5 / round 8-12 / batch 15-25) and persona, dedupes against the global H-ordinal registry, kill-gates cheaply, then pre-registers the batch for sign-off; mechanics in [`skills/hypothesis/references/fanout.md`](skills/hypothesis/references/fanout.md).

Four worked examples ship under [`skills/hypothesis/examples/`](skills/hypothesis/examples/) - the `wmd-docdistance-*` pair is the canonical shape, with a long 12-round arc shown by the `lexical-grounding-*` pair. Use `/datascience:hypothesis` to record a round, fan out the next, or conclude the design.

## Example usage

Create a new project, scaffold the first notebook, then review it:

```bash
/datascience:new-project yolo-homeobjects "train YOLOv8 on 10 home object classes"
/datascience:notebook "01 baseline training on the assembled dataset"
/datascience:review notebooks/01-kj-baseline.py
```

## Reference

- [`skills/notebook-standards/SKILL.md`](skills/notebook-standards/SKILL.md) - section order, GPU selection, imports, configuration, naming convention. Configuration cells use a sectioned Rich render; the active GPU's name (and compute capability + memory) appears in a `[bold]Device[/bold]` sub-section when CUDA is used. Each section carries a 1-2 sentence overview below its header so a scrolling reader can navigate without expanding code. LaTeX renders as equations inside notebook markdown (`$f(x)$`, `$$P(A|B) = \frac{P(B|A) P(A)}{P(B)}$$`); dollar amounts in prose escape as `\$`
- [`skills/notebook-standards/references/rich-output.md`](skills/notebook-standards/references/rich-output.md) - semantic colour palette and print patterns
- [`skills/notebook-standards/references/equations.md`](skills/notebook-standards/references/equations.md) - unicode inline math + standalone `$$` display blocks for image rasterisation
- [`skills/progressbars/SKILL.md`](skills/progressbars/SKILL.md) - tqdm and rich progress bar recipes
- [`skills/footnotes/SKILL.md`](skills/footnotes/SKILL.md) - JupyterLab-compatible anchor pattern (standard `[^1]` does not render in JupyterLab)
- [`skills/prompt-engineering/references/`](skills/prompt-engineering/references/) - per-technique papers, templates, and usage guidance
- [`skills/datascience/SKILL.md`](skills/datascience/SKILL.md) - project conventions, naming, file format standards
- [`skills/hypothesis/SKILL.md`](skills/hypothesis/SKILL.md) - hypothesis-driven experiments log + SOTA doc structure, the per-hypothesis template, and canonical-doc-across-runs management; four worked examples under [`skills/hypothesis/examples/`](skills/hypothesis/examples/) (the `wmd-docdistance-*` pair is the canonical shape); fanout mechanics in [`skills/hypothesis/references/fanout.md`](skills/hypothesis/references/fanout.md) with persona generators under [`skills/hypothesis/generators/`](skills/hypothesis/generators/)
- [`skills/dataset/SKILL.md`](skills/dataset/SKILL.md) - two artifacts per corpus (gitignored `dataset-<name>.zip`, tracked `dataset-<name>.md` sidecar) in `data/external/<task>-datasets/` (location confirmed with the user first), the licence-first admission gate applied before downloading, and the restriction fields a private corpus carries; the sidecar is rendered from the fetcher's spec so it cannot drift from what was downloaded. Prototype sidecars and the fetcher skeleton under [`skills/dataset/examples/`](skills/dataset/examples/)
- [copier-data-science](https://github.com/stellarshenson/copier-data-science) - project scaffolding template used by `/datascience:new-project` and `/datascience:fix-project`
