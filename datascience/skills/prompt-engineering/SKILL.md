---
name: prompt-engineering
description: Apply research-backed prompt engineering techniques to improve LLM output quality. Offers multiple techniques with templates and references. Auto-triggered when crafting system prompts, agent instructions, or LLM prompts.
---

# Prompt Engineering Techniques

Research-backed techniques. Each has a reference - paper, template, usage. Read reference before applying.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

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

1. Pick from table
2. Read reference for template + examples
3. Apply template
4. Techniques **stack** - psychological + chain-of-thought + self-refine for max effect

## When auto-triggered

System prompts, agent definitions, orchestrator templates, `claude -p` prompts, evaluation criteria.
