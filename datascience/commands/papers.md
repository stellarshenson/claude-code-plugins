---
description: Download every cited paper and write a structured digest into references/papers/ - the paper reference library for a project's design / experiment / hypothesis docs
allowed-tools: [Read, Write, Edit, Glob, Grep, WebFetch, Bash]
argument-hint: "the paper(s) to reference, e.g. 'arxiv 2401.12345' or 'the EAGLE-3 speculative decoding paper cited in R7'"
---

# Papers

Read the `datascience:papers` skill first - it is the single source of truth for the artifact naming, the digest format, and the download / verify rules. Do NOT duplicate it here.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## What to do

1. Read the `datascience:papers` skill
2. Resolve each paper to a verified open-access PDF URL (prefer arXiv `https://arxiv.org/pdf/<id>`)
3. Download into `references/papers/[paper] <short name>, <year>.pdf`; verify the `%PDF` magic header - never trust the extension
4. Write `references/papers/[paper digest] <short name>.md` using the skill's digest prompt (bold-header title, overview, main findings, key takeaways, tags, source). `**Source**` MUST be the resolvable online provenance link - never a local filename or path
5. Cite the digest from the calling document by its local filename; a citation without both artifacts is a defect
6. Several papers in one round - batch: download all, verify all, digest all, then finalize the citing doc
