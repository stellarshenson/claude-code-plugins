---
description: Port an existing project to copier-data-science standards or update an existing copier project
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
argument-hint: "path to project root (default: current directory)"
---

# Fix Project Structure

Port an existing data science project to the copier-data-science template standards, or update an already-templated project to the latest version.

## Step 1: Detect project state

Check the project root for:
- `.copier-answers.yml` -> project was created with copier (can update)
- `Makefile` with known targets -> partial copier structure
- Neither -> legacy/manual project (needs full port)

Report the detected state and ASK user to confirm.

## Mode A: Update existing copier project

If `.copier-answers.yml` exists:

```bash
copier update --trust
```

This pulls the latest template changes while preserving user modifications. Review the diff and resolve any conflicts.

If `copier` is not installed: `pip install copier` or `uv tool install copier`.

## Mode B: Port legacy project to copier

If no `.copier-answers.yml`:

1. **Audit current structure**:
   - List all directories and their contents
   - Identify: data directories, notebooks, source modules, model artifacts, configs
   - Map existing structure to copier-data-science conventions

2. **ASK user**:
   - Project name (for copier)
   - Author name and email
   - What to preserve vs what to reorganize
   - Any directories that should NOT be moved

3. **Create copier scaffold alongside**:
   ```bash
   copier copy https://github.com/stellarshenson/copier-data-science .copier-temp
   ```

4. **Port existing files**:
   - Move `*.py` notebooks to `notebooks/` (if not already there)
   - Move data files to `data/{raw,processed,interim}/` based on content
   - Move model artifacts to `models/`
   - Move source modules to `src/<project_name>/`
   - Merge Makefiles (keep existing targets, add missing copier targets)
   - Merge `.gitignore` (union of both)
   - Merge `pyproject.toml` / `setup.py` (keep deps, adopt structure)

5. **Install copier answers**:
   - Move `.copier-answers.yml` from temp scaffold to project root
   - Remove temp scaffold
   - Now `copier update` works for future template updates

6. **Verify**:
   - `make install` or equivalent works
   - `make test` passes (if tests exist)
   - All notebooks still run
   - git status shows the reorganization

## Mode C: Fix specific structure issues

If user doesn't want a full port, fix individual issues:
- Missing `data/raw/` -> create it, move raw data there
- Notebooks at root -> move to `notebooks/`
- No `src/` modules -> extract reusable code from notebooks
- No Makefile -> create from template
- Missing `.gitignore` entries -> add standard DS ignores (`*.ipynb`, `data/`, `models/`)

## Critical questions (ASK before proceeding)

- **Port mode**: "This is a legacy project without copier. Full port to copier-data-science, or fix specific issues only?"
- **Directory moves**: "Moving notebooks/ to match copier structure. These files will move: [list]. Any that should stay?"
- **Makefile merge**: "Your Makefile has custom targets. Merge with copier Makefile? I'll keep all your targets and add missing ones."
- **Dependencies**: "Your requirements.txt will merge into pyproject.toml. Review the merged deps?"
- **CI/CD paths**: "This project has CI/CD. Moving directories will break workflow paths. Update them?"

## Rules

- Restructure aggressively - move files, merge configs, create directories
- Use `git mv` to preserve history where possible
- User confirms each significant change through normal tool approval flow
- If project has CI/CD, warn and fix paths after restructuring
- Archive replaced config files to `@archive/` (old Makefile, old setup.py)
