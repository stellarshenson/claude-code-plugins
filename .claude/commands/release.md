# Release

Full release pipeline: lint + format, publish the library, sync plugins to its version, journal, commit, push. Use when shipping a finished session's work as a marketplace release.

## Execution discipline (READ FIRST - prevents the known failure modes)

These rules are not optional. Two real incidents motivated them: a parallel-tool batch that raced on the git index, and corrupted terminal output that led to a wrong "no Makefile" conclusion.

- **One step at a time. NEVER batch dependent operations in parallel.** Every git mutation (`add`, `rm`, `reset`, `commit`, `push`) and every version-bump write MUST run as its own tool call, and you MUST read its result before the next. Parallel tool calls are allowed ONLY for independent read-only inspection (e.g. several `grep`/`cat` with no ordering between them) - never for anything that writes, and never across a step boundary.
- **`.git/index.lock` means a git process is mid-flight or crashed.** If you see it: STOP, confirm no git command is still running, then `rm -f .git/index.lock` and re-verify with a single `git status` before continuing. Do not blindly retry the locked command.
- **Distrust corrupted/garbled tool output.** If a result looks truncated, shows the wrong file, or contains content that cannot belong to the command (interleaving, control-sequence noise), do NOT draw conclusions from it. Re-run that ONE command alone with a sentinel (`echo MARKER; <cmd>`) and confirm the marker before trusting the output. A misread here once caused a wrong "make publish does not exist" conclusion - the target existed and had already run.
- **One synced version, the library leads.** `make publish` bumps `pyproject.toml` (PATCH) and uploads to PyPI - that resulting number is `vN`, the single source of truth for the release. Step 4 then writes `vN` into the 13 plugin strings (6 `plugin.json` + `marketplace.json` metadata + 6 entries) so library and plugins always match. NEVER publish the library by hand (`uv build` / `twine`) - always `make publish`. NEVER set the plugin version independently of `vN` (do not run `/increment-plugin-version` during release).
- **EVERY release ships BOTH the CLI and the plugins. There is no plugin-only release.** The plugins are documentation for a CLI they cannot function without: skills and commands are written against the *current* flags, so shipping plugin text without the matching library strands every user on a CLI that rejects the flags the new docs tell them to use. This is not hypothetical - it is the `unrecognized arguments: --svg` incident, where plugins at 1.6.31 drove a library at 1.5.5. A "docs-only" change is still a CLI release: run `make publish` anyway so `vN` advances on both sides together. The only case where the library does not upload is `make publish` failing, and that ABORTS the release - it never downgrades to a plugin-only push.
- **Verify after every mutating step before proceeding.** Publish → confirm the new `pyproject.toml` version + the PyPI upload. Sync → confirm all 13 plugin strings equal `vN` and zero stale ones remain. Stage → confirm the staged set matches intent and nothing leaked in. Commit → confirm file count + clean worktree. Push → confirm `LOCAL == REMOTE`.

## Pre-flight

1. Run `git status` and confirm the working tree has the changes you intend to release. Sort EVERY entry into one of: this-session's-work (release scope), or not-this-session's. Pre-existing deletions, stray edits, or untracked files you did not create are NOT automatically in scope.
2. If anything is outside this session's work, or its purpose is unclear, STOP and ask the user what to do with each such item (keep / restore / delete / exclude) before touching anything else. Do not guess. Do not sweep them in.
3. Run `git log --oneline -5` so you can reference the latest prior commit in the journal entry if useful.

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

### 3. Publish the library to PyPI (this IS the version bump)

```bash
make publish
```

- `make publish` auto-bumps the `pyproject.toml` PATCH, builds, and uploads the wheel + sdist to PyPI. The new `pyproject.toml` version is `vN`, the single source of truth for this release. Read it back and record it - you will cite it in the journal entry and use it in step 4.
- ALWAYS publish the library through `make publish`. NEVER `uv build` + `twine` by hand.
- **Then install what you just published and verify parity.** The release box must end the release running the CLI it just shipped, otherwise it keeps developing and testing against a stale binary - that is exactly how this repo came to publish 1.6.31 while its own user-level interpreter still ran 1.5.5:

  ```bash
  python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
  python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))"
  ```

  The printed version MUST equal `vN`. PyPI can take a few seconds to serve a fresh upload - if the install still reports the previous version, wait briefly and retry once before treating it as a failure.
- **MINOR / MAJOR**: `make publish` only ever increments PATCH. For a patch-level jump, set `pyproject.toml` `version` to one patch below the target before `make publish` so the `+1` lands on it. A true minor/major (`MAJOR.MINOR.0`) cannot be produced by the auto-increment - set `pyproject.toml` to `MAJOR.MINOR.0` and `make publish` lands at `MAJOR.MINOR.1`; landing exactly on `.0` would require changing the Makefile increment (out of scope for the normal flow). Whatever number `make publish` actually produces is `vN` - read it back and sync the plugins to it.

### 4. Sync the plugin versions to the library

Read `vN` from `pyproject.toml`, then write that exact number into all 13 plugin strings:

- all 6 `plugin.json` `"version"` fields
- `.claude-plugin/marketplace.json` `metadata.version` plus every one of the 6 plugin-entry `"version"` fields

Do NOT run `/increment-plugin-version` - it bumps the plugins independently and would desync them from the library. Verify: grep for `vN` shows all 13 strings updated, and grep for the previous plugin version returns zero hits.

### 5. Update the journal

Invoke `/journal:update`. Nothing else. The command handles format, numbering, Standard-length default, append-vs-extend decision, and `journal-tools check` validation. Do NOT edit `.claude/JOURNAL.md` directly.

### 6. Stage and commit

Run as discrete, ordered steps - never one parallel batch:

```bash
git status --short                       # 1. inspect
git add <specific files from status>     # 2. stage tracked modifications by name
git rm <specific deletions>              # 3. stage intended deletions by name
git add <new files / new dirs>           # 4. stage untracked additions by name
git diff --cached --name-status          # 5. VERIFY the staged set before committing
```

After step 5, confirm the staged set is exactly the intended release scope (added / modified / deleted counts all match expectation) AND `git status --porcelain` shows nothing unintended left unstaged. Only then commit.

**NEVER** use `git add -A` or `git add .` to sweep the tree - stage by explicit path. If `git status` shows files outside the release scope (stray edits, temp files, log output, deletions you did not make), STOP and ask the user which to include. When unsure, list the files and ask. Do not commit files you cannot justify.

**`uv.lock` note**: the lockfile change produced by this release's own `make publish` install step (recording `vN`) is in scope; unrelated lockfile drift is not. Check the diff if unsure.

Commit message format:

```
chore: release plugins vN to marketplace

<one-line description of what the release contains>

PyPI: stellars-claude-code-plugins vN
```

The PyPI / library version and the plugin version are the same number (`vN`). Body is optional; for multi-topic sessions, prefer pointing at the journal entry (`See JOURNAL.md entry N`) instead of duplicating content.

**NEVER** include `Generated with Claude Code`, `Co-Authored-By: Claude`, or any other AI-attribution footer. The repo's commit policy forbids it.

### 7. Push

```bash
git push origin main
```

Report the commit SHA and the push destination in the final summary.

## Final report

At the end, print a compact summary:

```
Release vN complete
  PyPI:    stellars-claude-code-plugins vN  (pypi.org/project/stellars-claude-code-plugins/N/)
  Commit:  <sha>
  Pushed:  origin/main
  Journal: entry M appended
```

## Rules

- **Sequential execution.** One mutating step per tool call; read its result before the next. Never parallelise dependent git or version-write operations. See "Execution discipline" at the top.
- Order matters. Lint → tests → publish (library, via `make publish`) → sync plugins → journal → commit → push. A lint failure should never make it to PyPI.
- **Always publish the library with `make publish`** - never `uv build` + `twine` by hand. The library version is the single source of truth; the plugins follow it.
- Never skip tests even if the changes are "just docs". A red suite means the repo is broken - fix it before shipping.
- Never bypass git hooks with `--no-verify`.
- Never force-push to main.
- Never commit files you cannot justify. Ask when uncertain.
- The journal entry is MANDATORY and MUST be created via `/journal:update` - never inline-edit `JOURNAL.md`. A release without a journal entry is half-finished.
- If the plugin-sync (step 4) or a later step fails after `make publish` already uploaded, the library is live at `vN` on PyPI (irreversible). Bring the plugins up to `vN` and finish the release - do not roll the library back. If `make publish` itself fails before upload, revert any partial `pyproject.toml` / `uv.lock` change before retrying.
