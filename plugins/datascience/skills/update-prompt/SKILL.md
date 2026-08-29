---
name: update-prompt
description: Update a prompt, system instruction, or agent definition by applying a research-backed prompt engineering technique
allowed-tools: [Read, Write, Edit, Glob, Grep, Skill, AskUserQuestion]
---

# Update Prompt

Take an existing prompt (or task description) and update it by applying a research-backed prompt engineering technique.

## Step 1: ASK the user

Present the available techniques:

"Which prompt engineering technique should I apply?

1. **Psychological Prompting** - stakes + persona + challenge + self-check (best for complex tasks needing maximum effort)
2. **Chain of Thought** - step-by-step reasoning (best for math, logic, debugging)
3. **Chain of Draft** - minimal per-step drafts, 7.6% of the token cost (best for token-limited reasoning)
4. **Tree of Thought** - explore 2-3 approaches, evaluate, select (best for design decisions)
5. **Few-Shot** - provide examples of desired output (best for structured format)
6. **Self-Refine** - generate -> critique -> improve loop (best for iterative quality)
7. **Rephrase and Respond** - restate problem before solving (best for ambiguous requirements)
8. **Stack multiple** - combine techniques for maximum effect

Which technique(s)? (number or name, can pick multiple)"

## Step 2: Read the reference

Read the relevant reference document(s) from `references/` in the prompt-engineering skill directory.

## Step 3: Apply

Take the user's prompt/task and restructure it using the selected technique's template. Show the before and after.

If stacking: apply techniques in order (persona first, then methodology, then self-check last).

## Step 4: Iterate

Ask: "Does this capture your intent? Adjust anything?"
