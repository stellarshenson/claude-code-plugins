---
description: Apply a prompt engineering technique to improve a prompt, system instruction, or agent definition
allowed-tools: [Read, Write, Edit, Glob, Grep, Skill, AskUserQuestion]
argument-hint: "describe the prompt or task to improve"
---

# Apply Prompt Engineering Technique

Take an existing prompt (or task description) and apply a research-backed technique to improve it.

## Step 1: ASK the user

Present the available techniques:

"Which prompt engineering technique should I apply?

1. **Psychological Prompting** - stakes + persona + challenge + self-check (best for complex tasks needing maximum effort)
2. **Chain of Thought** - step-by-step reasoning (best for math, logic, debugging)
3. **Tree of Thought** - explore 2-3 approaches, evaluate, select (best for design decisions)
4. **Few-Shot** - provide examples of desired output (best for structured format)
5. **Self-Refine** - generate -> critique -> improve loop (best for iterative quality)
6. **Rephrase and Respond** - restate problem before solving (best for ambiguous requirements)
7. **Stack multiple** - combine techniques for maximum effect

Which technique(s)? (number or name, can pick multiple)"

## Step 2: Read the reference

Read the relevant reference document(s) from `references/` in the prompt-engineering skill directory.

## Step 3: Apply

Take the user's prompt/task and restructure it using the selected technique's template. Show the before and after.

If stacking: apply techniques in order (persona first, then methodology, then self-check last).

## Step 4: Iterate

Ask: "Does this capture your intent? Adjust anything?"
