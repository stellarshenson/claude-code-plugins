---
description: Fix issues in SVG infographics. Argument describes what to fix (layout / style / contrast / connectors / all). Dispatches the svg-infographics umbrella skill - an in-session fork by default. Triggers - "fix svg", "fix layout", "fix style", "fix contrast", "fix connectors", "fix infographic".
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "SVG file path + optional intent (e.g. 'docs/fig.svg overlaps' or 'docs/*.svg style')"
---

# Fix SVG

Invoke the `svg-infographics:fix` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
