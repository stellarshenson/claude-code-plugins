---
description: Run the full devil's advocate critical analysis workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "describe the document to critique and who the toughest reader is"
---

# Devil's Advocate - Run

Full end-to-end critical analysis workflow with improvement loop.

## Flow

1. **Setup** (`devils-advocate:setup`) - build devil persona + harvest fact repository
2. **Evaluate** (`devils-advocate:evaluate`) - generate concern catalogue + baseline scorecard
3. **Improve loop** (repeat until done):
   a. **Improve** (`devils-advocate:improve`) - ask user how to address top concerns (suggestions / auto-apply / planning mode)
   b. **Iterate** (`devils-advocate:iterate`) - re-score after changes, update scorecard
   c. **Check**: stop if residual risk < 10% of total, or top gaps < 3.0 each, or user accepts

## Versioned files

Every time Claude applies changes (auto or from user suggestions), a versioned copy is created:
- `<name>_v01_<score>.md` - original with embedded scorecard
- `<name>_v02_<score>.md` - after first correction pass
- `<name>_v03_<score>.md` - after second correction pass

The score suffix is the total residual risk (lower = better).

## When user edits outside Claude

If the user made changes to the document outside Claude (in their editor, another tool):
- No versioned copy needed - the user's changes are in the original
- Run `iterate` in re-score mode: evaluate the current document state
- Update `devils_advocate.md` with the new scorecard reflecting actual state

## Stopping

The improve -> iterate loop stops when:
- Residual risk below 10% of total absolute risk
- Top remaining gaps have residual < 3.0 each
- User explicitly accepts the current score
- Score stopped improving (stagnation)

## Execute

Run these skills IN ORDER:

```
/devils-advocate:setup
/devils-advocate:evaluate
# Loop:
/devils-advocate:improve
/devils-advocate:iterate
# Check stopping criteria, loop if not met
```
