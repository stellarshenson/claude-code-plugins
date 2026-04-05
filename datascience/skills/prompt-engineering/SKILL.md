---
name: prompt-engineering
description: Apply research-backed prompt engineering techniques to improve LLM output quality. Offers multiple techniques with templates and references. Auto-triggered when crafting system prompts, agent instructions, or LLM prompts.
---

# Prompt Engineering Techniques

Research-backed prompting techniques. Each has a reference document with the paper, template, and usage guidance. Read the reference before applying.

## Techniques

| # | Technique | Best for | Reference |
|---|-----------|----------|-----------|
| 1 | **Psychological Prompting** | Complex tasks, max effort (+45-115%) | `references/psychological-prompting.md` |
| 2 | **Chain of Thought** | Math, logic, debugging (+46%) | `references/chain-of-thought.md` |
| 3 | **Chain of Draft** | Token-limited reasoning (7.6% token cost) | `references/chain-of-draft.md` |
| 4 | **Tree of Thought** | Design decisions, architecture | `references/tree-of-thought.md` |
| 5 | **Few-Shot** | Structured output, classification | `references/few-shot.md` |
| 6 | **Self-Refine** | Code, documents, iterative quality | `references/self-refine.md` |
| 7 | **Rephrase and Respond** | Ambiguous requirements | `references/rephrase-and-respond.md` |

## How to use

1. Pick a technique from the table
2. Read the reference file for the template and examples
3. Apply the template to your prompt
4. Techniques **stack** - psychological + chain-of-thought + self-refine for maximum effect

## When auto-triggered

Building system prompts, agent definitions, orchestrator templates, `claude -p` prompts, or evaluation criteria.
