---
description: Run the consolidated SVG validation gate (finalize - all checkers in one call) on one or more files. Triggers - "validate svg", "check svg", "audit svg", "validate infographic".
allowed-tools: [Read, Bash, Glob, Grep, Skill, TaskCreate, TaskUpdate]
argument-hint: "SVG file path or directory, e.g. 'docs/images/*.svg'"
---

# Validate SVG Infographics

Invoke the `svg-infographics:validate` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
