---
description: Create a new data science project from copier template
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
argument-hint: "project name and brief description"
---

# Create New Data Science Project

Scaffold a new data science project using the copier-data-science template.

## Prerequisites

- `copier` must be installed: `pip install copier` or `uv tool install copier`
- Template: `https://github.com/stellarshenson/copier-data-science`

## Steps

1. ASK the user:
   - **Project name** (e.g. `my-analysis`)
   - **Description** (one line)
   - **Author** (name and email)
   - **Python version** (default: 3.12)
   - **Location** (default: current directory)

2. Run copier:
   ```bash
   copier copy https://github.com/stellarshenson/copier-data-science <project-name>
   ```

3. After scaffolding:
   - Initialize git: `git init && git add -A && git commit -m "initial scaffold from copier-data-science"`
   - Create venv: `make create_environment` (if Makefile exists)
   - Install deps: `make requirements`

4. Report what was created:
   - List the directory structure
   - Show the Makefile targets
   - Confirm the project is ready

## Do NOT

- Skip asking the user for project name
- Run copier without user confirmation
- Modify the template output (it follows all datascience standards already)
