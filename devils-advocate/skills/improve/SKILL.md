---
name: improve
description: Bridge between evaluate and iterate. Asks user how to address devil's concerns - user suggestions, auto-apply recommended options, or planning mode. Produces corrections for the iterate skill to evaluate.
---

# Devil's Advocate - Improve

Decide HOW to address the devil's concerns before iterating. This skill sits between evaluate (which found the problems) and iterate (which re-scores after changes).

**Prerequisites**: `devils_advocate.md` must contain a scorecard with top gaps identified. Run `/devils-advocate:evaluate` first if not.

## Read the current state

1. Read `devils_advocate.md` - find the latest scorecard and top gaps
2. List the top 5 concerns by residual risk with their recommended options

## Ask the user

Present the top gaps and ask:

"Here are the highest-residual concerns. How would you like to address them?

1. **Your suggestions** - tell me what changes you'd make and I'll apply them
2. **Auto-apply** - I'll apply the recommended options from the scorecard autonomously
3. **Planning mode** - let's discuss each concern and design the best approach together before making changes

Which approach? (or mix: 'auto for #1-3, discuss #4-5')"

## Mode 1: User suggestions

The user describes changes. Apply them to a new versioned copy:
- Copy current as `<name>_v<NN+1>.md`
- Apply the user's specific changes
- Note which concerns each change targets

## Mode 2: Auto-apply

Apply the recommended options from the scorecard's "Explore options" section:
- Copy current as `<name>_v<NN+1>.md`
- For each top gap, apply the recommended option
- Track cross-concern tensions (fixing one may worsen another)

## Mode 3: Planning mode

For each top concern, discuss with the user:
- What's the root cause of this concern?
- What are 2-3 ways to address it?
- What are the trade-offs?
- Which approach does the user prefer?

Then apply the agreed changes.

## After changes are applied

1. The versioned copy exists with changes applied
2. Hand off to `iterate` skill for re-scoring
3. Iterate will: re-read the document, re-score all concerns, update the scorecard, rename the file with the new score

## When user made changes outside Claude

If the user says they already made changes (edited the document themselves, outside Claude):
- Do NOT create a versioned copy (user's changes are in the original)
- Go directly to `iterate` in re-score mode
- Iterate will evaluate the current document state and update `devils_advocate.md` with the new scorecard
