# Release

Full release pipeline: lint + format, publish to PyPI, bump plugin versions, journal, commit, push. Use when shipping a finished session's work as a marketplace release.

## Pre-flight

1. Run `git status` and confirm the working tree has the changes you intend to release. If there are unstaged or uncommitted changes whose purpose is unclear, STOP and ask the user what to do with them before touching anything else.
2. Run `git log --oneline -5` so you can reference the latest prior commit in the journal entry if useful.

## Pipeline

Execute strictly in this order. If any step fails, STOP, report the failure, and wait for the user to decide whether to continue or abort.

### 1. Lint and format

```bash
uv run ruff format
uv run ruff check --fix
```

If `ruff check --fix` leaves unfixable violations, STOP and surface them - do not publish code with lint errors.

### 2. Run tests

```bash
uv run pytest -q
```

A green suite is a hard gate. Never publish on red.

### 3. Publish to PyPI

```bash
make publish
```

This auto-bumps the patch in `pyproject.toml` and uploads the wheel to PyPI. Capture the new PyPI version from the output (e.g. `1.0.12` → `1.0.13`). Record it - you will cite it in the journal entry.

### 4. Bump plugin versions

Run the `/increment-plugin-version` workflow:

- Read current version from `.claude-plugin/marketplace.json` `metadata.version`
- Increment PATCH by 1
- Update all 6 `plugin.json` files AND every `"version"` entry in `.claude-plugin/marketplace.json` (metadata + 6 plugin entries)
- ALL plugin versions MUST stay in sync
- Only bump PATCH unless the user explicitly asks for MINOR or MAJOR

Record the new plugin version - you will cite it in the journal entry.

### 5. Update the journal

Append a new entry to `.claude/JOURNAL.md` using the modus secundis rich-paragraph style. The entry title MUST cite both versions: `(vX.Y.Z PyPI, plugins vA.B.C)`.

Follow the shape documented in `journal/skills/journal/references/examples.md` — specifically the "Multi-topic Normal Entry" example:

- Single dense paragraph, no sub-headers or bullet lists
- Problem or motivation FIRST, then solution, then tools/files touched, then performance/tests, then release stamp at the end
- Concrete numbers (ms, %, test counts, file paths, function names in backticks)
- Commit SHA and published version at the end as the release stamp

Never invent entry content - write only about work that actually happened in the current session.

### 6. Stage and commit

```bash
git status --short
git add <specific files from status>
```

**NEVER** use `git add -A` blindly. If `git status` shows files outside the release scope (stray edits, temp files, log output), STOP and ask the user which files to include. When unsure, list the files and ask. Do not commit files you cannot justify.

Commit message format:

```
chore: release plugins vA.B.C to marketplace

<one-line description of what the release contains>

PyPI: stellars-claude-code-plugins vX.Y.Z
```

Body is optional; for multi-topic sessions, prefer pointing at the journal entry (`See JOURNAL.md entry N`) instead of duplicating content.

**NEVER** include `Generated with Claude Code`, `Co-Authored-By: Claude`, or any other AI-attribution footer. The repo's commit policy forbids it.

### 7. Push

```bash
git push origin main
```

Report the commit SHA and the push destination in the final summary.

## Final report

At the end, print a compact summary:

```
Release vA.B.C complete
  PyPI:    stellars-claude-code-plugins vX.Y.Z  (pypi.org/project/stellars-claude-code-plugins/X.Y.Z/)
  Commit:  <sha>
  Pushed:  origin/main
  Journal: entry N appended
```

## Rules

- Order matters. Lint → tests → publish → bump → journal → commit → push. A lint failure should never make it to PyPI.
- Never skip tests even if the changes are "just docs". A red suite means the repo is broken - fix it before shipping.
- Never bypass git hooks with `--no-verify`.
- Never force-push to main.
- Never commit files you cannot justify. Ask when uncertain.
- The journal entry is MANDATORY - a release without a journal entry is half-finished.
- If PyPI publish fails after plugin version bump, revert the bump files (`git checkout -- <plugin.json files>`) before retrying - partial version state across files is worse than no bump at all.
