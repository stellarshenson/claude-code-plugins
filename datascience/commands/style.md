---
description: Apply rich output styling standards to a notebook or script - fix colors, formatting, print patterns
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
argument-hint: "path to file to fix, e.g. 'notebooks/01-kj-analysis.py'"
---

# Fix Rich Output Styling

Read a notebook or script and fix all rich output to comply with standards.

## What to fix

1. **Multiple individual prints -> single multiline print**
   - Find sequences of `rich.print()` or `rprint()` calls for related output
   - Merge into single multiline call

2. **Wrong colors -> semantic colors**
   - `cyan` for values -> `dark_sea_green` (no units) or `light_sea_green` (with units)
   - `green` for success -> `dark_sea_green`
   - `red` for error -> `indian_red`
   - `yellow` for warning -> `dark_goldenrod`
   - Hex colors in rich -> standard named colors
   - `white` for headers -> `medium_purple`

3. **Missing rich formatting**
   - Plain `print()` for structured output -> `rich.print()` with semantic colors
   - f-strings without color for metrics/status -> add appropriate colors
   - Tables without styled columns -> add column styles (grey70, light_coral, steel_blue)

4. **Import fixes**
   - Missing `import rich.jupyter as rich` or `from rich import print as rprint`
   - Rich import not in the imports cell (notebook)

5. **Progress bar patterns**
   - Setup text in same cell as Progress bar -> split into separate cells
   - tqdm where rich.progress would work -> suggest replacement

## Process

1. Read the file
2. List all violations found (with line numbers)
3. ASK user: "Found N styling issues. Fix all, or let me show them first?"
4. Apply fixes
5. Show summary of what changed
