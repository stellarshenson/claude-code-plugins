---
name: prompt-engineering
description: Apply research-backed prompt engineering techniques to improve LLM output quality. Offers multiple techniques (psychological prompting, chain-of-thought, tree-of-thought, few-shot, self-refine, rephrase-and-respond) with templates. Auto-triggered when crafting system prompts, agent instructions, or LLM prompts.
---

# Prompt Engineering Techniques

Apply research-backed prompting techniques to improve output quality. Each technique has a reference document in `references/` with the research paper, template, and usage guidance.

## Available Techniques

| # | Technique | Best for | Effect |
|---|-----------|----------|--------|
| 1 | **Psychological Prompting** | Complex tasks needing maximum effort | +45-115% on reasoning. Stakes + persona + challenge + self-check |
| 2 | **Chain of Thought** | Math, logic, debugging | +46% accuracy. "Think step by step" |
| 3 | **Tree of Thought** | Design decisions, architecture | Explore 2-3 paths, evaluate, select best |
| 4 | **Few-Shot** | Structured output, classification | Show examples of desired format |
| 5 | **Self-Refine** | Code, documents, iterative quality | Generate -> critique -> improve loop |
| 6 | **Rephrase and Respond** | Ambiguous requirements | Restate problem before solving |

## When auto-triggered

- Building system prompts or agent definitions
- Writing orchestrator phase templates
- Crafting prompts for `claude -p` subprocess calls
- Designing LLM evaluation criteria
- Any prompt that needs higher quality output

## How to apply

Read the relevant reference document for the template. Techniques can be **stacked** - psychological prompting combines naturally with chain-of-thought and self-refine for maximum effect on complex tasks.
