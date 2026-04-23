# stellars-claude-code-plugins

[![GitHub Actions](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/stellars-claude-code-plugins.svg)](https://pypi.org/project/stellars-claude-code-plugins/)
[![Total PyPI downloads](https://static.pepy.tech/badge/stellars-claude-code-plugins)](https://pepy.tech/project/stellars-claude-code-plugins)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)

<img alt="stellars-claude-code-plugins marketplace overview - 6 plugins grouped by category" src="assets/svg/01_marketplace_overview.svg" width="100%">

A plugin marketplace for Claude Code providing structured workflows for software development, document analysis, data science, and project management. Each plugin is pure configuration (skills, commands, YAML) - install one or all depending on your needs.

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
```

The marketplace includes a shared YAML-driven orchestration engine (`autobuild`) that pulls agents through structured phases with quality gates, a semi-data-science document critic (`devils-advocate`) with Fibonacci risk scoring, production SVG infographics (`svg-infographics`) with grid-first design and automated validation, data science project standards (`datascience`) with notebook scaffolding and compliance fixes, structured document processing (`document-processing`) with source grounding, and project journaling (`journal`).

> [!NOTE]
> Read the full article on the orchestration approach: [Your AI Agent Will Cut Corners. Here's How to Stop It.](https://medium.com/@konradwitowskijele/your-ai-agent-will-cut-corners-heres-how-to-stop-it-40f3bc7a4762)
>
> Read about the SVG infographics plugin: [Stop Fixing Your AI's SVGs](https://medium.com/towards-artificial-intelligence/stop-fixing-your-ai-svgs-715df70ccca0)

## Plugins

| Plugin | What it solves |
|--------|---------------|
| [autobuild](autobuild/) | Executes code and artefact builds toward an objective with iterations driven by a calculated outcome benchmark - enforces structured phases with multi-agent review |
| [devils-advocate](devils-advocate/) | Produces high-quality documents for a specific audience using a scientific, measured, iterative approach - quantified critique with Fibonacci risk scoring and per-iteration residual measurement |
| [svg-infographics](svg-infographics/) | Produces high-quality standardised SVG infographics - grid-first design, theme-driven styling, dark/light mode, 5 routing modes (straight/L/L-chamfer/spline/manifold) with A* auto-routing, callout placement solver, chart generation, and 6 automated checkers |
| [datascience](datascience/) | Produces high-quality data science projects and notebooks following consistent standards - scaffolds projects from copier templates, enforces notebook structure, applies rich output styling, and supports prompt engineering techniques |
| [document-processing](document-processing/) | Processes documents according to user requests with grounding in source materials - source tracing, compliance checking, PDF automation |
| [journal](journal/) | Produces a work journal marking key changes, implementations, and decisions - append-only audit trail with continuous numbering, archiving, and deterministic `journal-tools` CLI for validation, sorting, and word-count enforcement |

## autobuild

<img alt="autobuild 8-phase lifecycle: research, hypothesis, plan, implement, test, review, record, next" src="assets/svg/02_autobuild_phases.svg" width="100%">

Runs structured multi-iteration development cycles where each iteration passes through a full phase lifecycle with quality gates. A program defines what to build, a benchmark measures progress, and the engine enforces the workflow until the objective is met or iterations are exhausted.

- **Shallow fixes** - forces research and hypothesis before implementation
- **Scope creep** - plan locks scope, review catches deviations
- **Lost context** - hypothesis catalogue and failure context persist across iterations
- **Unchecked quality** - two independent gates (readback + gatekeeper) per phase
- **No accountability** - every phase records agents, outputs, and verdicts in YAML audit logs
- **Benchmark gaming** - guardian agent checks for benchmark-specific tuning vs genuine improvement

**Skills**: `autobuild` (orchestrator), `program-writer`, `benchmark-writer`

### Workflow types

| Type | Phases | Use when |
|------|--------|----------|
| `full` | RESEARCH → HYPOTHESIS → PLAN → IMPLEMENT → TEST → REVIEW → RECORD → NEXT | Feature work, improvements |
| `fast` | PLAN → IMPLEMENT → TEST → REVIEW → RECORD → NEXT | Clear objective, no exploration needed |
| `gc` | PLAN → IMPLEMENT → TEST → RECORD → NEXT | Cleanup, refactoring |
| `hotfix` | IMPLEMENT → TEST → RECORD | Targeted bug fix |
| `planning` | RESEARCH → PLAN → RECORD → NEXT | Work breakdown (auto-chains before full) |

### Usage

```bash
# Describe what you want - the plugin handles the rest
/autobuild improve error handling in the API layer
```

The plugin writes PROGRAM.md and BENCHMARK.md from your prompt, asks you to approve, then runs the orchestrator autonomously.

See [autobuild/README.md](autobuild/) for the full phase lifecycle, agent architecture, and configuration details.

## devils-advocate

<img alt="devils-advocate Fibonacci risk matrix and sample concerns iterating to resolved" src="assets/svg/03_devils_advocate_scoring.svg" width="100%">

Systematically critiques documents from the perspective of their toughest audience. Builds a devil persona, harvests verifiable facts, generates a risk-scored concern catalogue, and iterates corrections until residual risk is acceptable.

**Skills**: `setup` (build persona + fact repository), `evaluate` (concern catalogue + baseline scorecard), `iterate` (apply corrections or re-score), `run` (full workflow end-to-end)

Risk scoring uses a Fibonacci scale (1-8) for likelihood and impact, producing risk scores from 1-64. Each concern is scored 0-100% on how well the document addresses it, and the residual risk (what remains unaddressed) drives iteration priority.

### Usage

```bash
# Full end-to-end workflow
/devils-advocate:run

# Step by step
/devils-advocate:setup       # Build persona, harvest facts
/devils-advocate:evaluate    # Generate concerns + baseline scorecard
/devils-advocate:iterate     # Apply corrections, re-score (repeat)
```

See [devils-advocate/README.md](devils-advocate/) for scoring formula details, artefact format, and the full concern catalogue methodology.

## svg-infographics

<img alt="svg-infographics 6-phase workflow and 8 shipped CLI tools (validators + calculators)" src="assets/svg/04_svg_infographics_workflow.svg" width="100%">

Creates production-quality SVG infographics with a mandatory 6-phase workflow (research, grid, scaffold, content, finishing, validation). Every coordinate is Python-calculated, every colour traces to an approved theme swatch, and six validation tools check overlaps, WCAG contrast, alignment, connector quality, CSS compliance, and pairwise connector collisions before delivery.

Five connector routing modes (`straight`, `l`, `l-chamfer`, `spline`, `manifold`) with grid A* auto-routing around obstacles, container-scoped routing within specific shapes, straight-line collapse for near-aligned endpoints, and stem preservation guaranteeing clean cardinal segments behind arrowheads. Callout placement via greedy solver with leader and leaderless modes. Charts via pygal with dual light/dark palette and WCAG contrast audit.

**Skills**: `svg-designer` (fork-context design agent with tool palette, 6-phase workflow, design rules, validation gates), `theme` (palette approval + swatch generation)

### Usage

```bash
# Create infographic(s) with full workflow
/svg-infographics:create card grid showing 4 platform modules

# Generate theme swatch for approval
/svg-infographics:theme corporate blue palette

# Run validation on existing SVGs
/svg-infographics:validate docs/images/*.svg

# Fix issues in existing SVGs (layout / style / contrast / connectors / all)
/svg-infographics:fix docs/images/overview.svg style
/svg-infographics:fix docs/images/overview.svg layout

# Additive decoration pass on existing SVGs
/svg-infographics:beautify docs/images/overview.svg medium
```

Includes 60+ production SVG examples, 12 CLI tools (6 validators + 6 calculators), and theme swatches. See [svg-infographics/README.md](svg-infographics/) for the five capability groups and workflow details.

## datascience

<img alt="datascience project scaffold and notebook section pipeline (header, GPU, imports, config, data, model, eval)" src="assets/svg/05_datascience_pipeline.svg" width="100%">

Enforces data science project standards derived from production notebook workflows. Five skills auto-trigger when working with notebooks, datasets, rich output, prompts, or progress bars. Nine commands fix existing code, scaffold new projects, and apply prompt engineering techniques.

**Skills**: `datascience` (project conventions), `notebook-standards` (section order, GPU-first), `rich-output` (semantic colors), `prompt-engineering` (7 research-backed techniques), `progressbars` (tqdm/rich)

### Usage

```bash
# Create a new project from copier template
/datascience:new-project

# Fix an existing notebook to comply with standards
/datascience:fix-notebook notebooks/01-kj-analysis.py

# Apply rich styling fixes (wrong colors, multiple prints)
/datascience:apply-style notebooks/02-kj-train.py

# Add or fix progress bars (choose tqdm or rich)
/datascience:apply-progressbar notebooks/02-kj-train.py

# Apply prompt engineering technique (CoT, CoD, ToT, few-shot, etc.)
/datascience:apply-prompt-technique

# Full psychological prompting stack for hard problems
/datascience:challenge

# Port legacy project to copier-data-science template
/datascience:fix-project
```

See [datascience/README.md](datascience/) for the full list of standards enforced.

## journal

<img alt="journal append-only timeline with archive and continuous numbering" src="assets/svg/07_journal_audit.svg" width="100%">

Project journal management with append-only entry format, continuous numbering, and automatic archiving. Auto-triggers on journal-related phrases (see below) or after substantive work, maintaining a consistent audit trail in `.claude/JOURNAL.md`. Includes a deterministic `journal-tools` CLI for validation, sorting, and word-count enforcement - no generative AI in the loop.

**Skill**: `journal` (auto-triggered by the phrases below or after finishing substantive work)

### Auto-trigger phrases

| Command | Triggers on |
|---------|-------------|
| `/journal:update` | "update journal", "add journal entry", "add entry", "log this", "journal this", "record this in the journal" |
| `/journal:create` | "create journal", "init journal", "start journal", "new journal" (refuses if file already exists) |
| `/journal:archive` | "archive journal", "prune journal", "compact journal" (auto-suggests when >40 entries) |

Clear split: `create` = scaffold-from-empty one-time, `update` = every write after that (append new entry or extend the last one), `archive` = runs the CLI archiver.

### Usage

```bash
# Add a new entry — use this for 99% of journal writes
/journal:update added retry logic to API client

# Initialise a fresh journal (only when JOURNAL.md does not yet exist)
/journal:create backfill from this session

# Archive older entries (keeps last 20 in main, appends rest to JOURNAL_ARCHIVE.md)
/journal:archive

# Validate format, numbering, and word counts (deterministic CLI)
journal-tools check .claude/JOURNAL.md

# Re-number entries sequentially (fixes gaps or reorders)
journal-tools sort .claude/JOURNAL.md --dry-run
```

Two word-count tiers: **Standard** (~70-120 words, the default) and **Extended** (~250-350 words, ONLY when the user explicitly asks or the work is an architectural decision / platform migration / multi-iteration debug). The checker emits warnings (not errors) when entries exceed the standard target or the extended max — length is a nudge, never a block.

See [journal/README.md](journal/) for entry format, CLI tools, and archiving rules.

## document-processing

<img alt="document-processing 3-stage flow: sources, grounding, compliant cited output" src="assets/svg/06_document_processing_grounding.svg" width="100%">

Structured document processing with source grounding and quality control. Takes input documents through a verified workflow (analyze, draft, ground, uniformize) and produces outputs where every factual claim is traceable to source material.

**Skills**: `process-documents` (4-phase workflow), `validate-document` (grounding + compliance), `pdf` (basic operations), `pdf-pro` (production workflows)

**CLI**: ships the `document-processing` command with three-layer lexical grounding (regex + Levenshtein + BM25) plus an optional fourth semantic layer (multilingual-e5 + FAISS). Every hit returns line / column / paragraph / page / context snippet — the agent cites without rereading. **Saves tokens: measured 64-86% reduction vs batched generative grounding** on real sources. Semantic layer is opt-in via `pip install 'stellars-claude-code-plugins[semantic]'` + `document-processing setup`.

### Usage

```bash
# Full workflow from objective
/document-processing:run synthesize expert opinions into position paper

# Update existing output with new source material
/document-processing:update add new hearing transcript to timeline

# Validate a document against its sources
/document-processing:validate

# First-run: interactive opt-in prompt for optional semantic grounding
document-processing setup

# Direct CLI: ground a single claim (all four layers when semantic enabled)
document-processing ground \
  --claim "Kubernetes runs on 12 nodes" \
  --source docs/source.md \
  --threshold 0.85 --bm25-threshold 0.5 --semantic-threshold 0.85 --json

# Batch ground N claims from JSON, force semantic on for this call
document-processing ground-many \
  --claims validation/claims.json \
  --source docs/source.md \
  --output validation/grounding-report.md \
  --semantic on
```

See [document-processing/README.md](document-processing/) for the grounding methodology, folder structure, and PDF processing details.

## Install

The library ships the deterministic CLIs that every plugin depends on — install it alongside the plugin marketplace. Without the library the skills fall back to manual work and lose all automation.

```bash
pip install stellars-claude-code-plugins
```

Provides these binaries:

| Binary | Used by |
|--------|---------|
| `orchestrate` | `autobuild` |
| `svg-infographics` | `svg-infographics`, `devils-advocate` (visuals) |
| `render-png` | `svg-infographics` (Playwright-based SVG → PNG) |
| `journal-tools` | `journal` (check / sort / archive) |
| `document-processing` | `document-processing` (ground / ground-many, three-layer grounding) |

As a Claude Code plugin marketplace:

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
```

## Building a new plugin

Plugins are pure configuration - no Python code required. Create a directory with skills and register it in the marketplace:

```
my-plugin/
  .claude-plugin/plugin.json           # Plugin registration and skill triggers
  skills/
    my-skill/SKILL.md                  # Skill definition with description and instructions
```

The `plugin.json` registers your skills with Claude Code, defining when they trigger and what tools they have access to. Each `SKILL.md` contains the instructions Claude follows when the skill is invoked. The shared orchestration engine (`pip install stellars-claude-code-plugins`) provides the `orchestrate` CLI command that handles state management, FSM transitions, gate execution, and audit logging.

Register your plugin in the marketplace by adding an entry to `.claude-plugin/marketplace.json`.

## Development

```bash
make install          # create venv, install deps, editable install
make test             # run tests
make lint             # ruff format + check
make format           # auto-fix formatting
make build            # clean, test, bump version, build wheel
make publish          # build + twine upload to PyPI
```

## License

MIT License
