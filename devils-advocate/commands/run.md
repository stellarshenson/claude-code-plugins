---
description: Run the full devil's advocate critical analysis workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "describe the document to critique and who the toughest reader is"
---

# Devil's Advocate - Run

Full end-to-end critical analysis with improvement loop.

## Flow

1. **Setup** (`devils-advocate:setup`) - build devil persona + harvest fact repository
2. **Evaluate** (`devils-advocate:evaluate`) - generate concern catalogue + baseline scorecard. ASK: in-session or standalone scoring
3. **Iterate loop** (repeat until done):
   - `devils-advocate:iterate` runs the full cycle:
     a. ASK how to improve (user suggestions / auto-apply / planning / user already edited)
     b. Apply changes, create `<name>_v<NN>.md`
     c. Score (in-session or standalone)
     d. Rename to `<name>_v<NN>_<score>.md`
     e. Update `devils_advocate.md` with new scorecard
     f. Check: stop if residual < 10%, stagnation, or user accepts

## Versioned files

Every AI correction creates a versioned file with MANDATORY score suffix:
- `report_v01_89.md` - baseline with scorecard (residual 89)
- `report_v02_34.md` - first correction (residual 34)
- `report_v03_12.md` - second correction (residual 12)

User edits outside Claude: no versioned copy, just re-score and update `devils_advocate.md`.

## Execute

```
/devils-advocate:setup
/devils-advocate:evaluate
/devils-advocate:iterate   # repeat until done
```
