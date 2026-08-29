# Code graph as a review instrument - graphify

The how of using a code-graph index during a review: which query answers which review question, what each costs, and where the tool lies to you - deliberately out of the agent prompts, for the reason in the last line.

**This is a SNAPSHOT of graphify 0.8.18, read on 2026-08-29 from the installed binary and this repository's graph.** Upstream (Graphify-Labs/graphify) is already on 0.9.x and has fixed at least one gotcha below. When anything here looks stale, re-read it rather than trusting it: `graphify --version`, then `graphify --help`, which is the only usable index this CLI has.

## Which review question each query answers

- **Does this defect escape its file** - blast radius before rating severity → `affected`. The only command that answers it. CHEAP: 0.46 s and 9.1 KB of text for 141 hits on a 7,202-node graph, no LLM. Read the relation tag on every hit - a `calls` dependent is a live caller, a `uses` dependent is often just a test importing the type
- **How wide may the fix be** - radius before bounding a change → the same `affected` at rising `--depth`. Measured here on seed `Connector`: 97 dependents at depth 1, 141 at 2, 148 at 3, 149 at 4. The curve saturates, so depth 1 is the direct-caller set, depth 2 is the practical change budget, and past 3 you only inflate the reported radius. Narrow with `--relation calls --relation inherits` to drop incidental `uses` edges
- **Do two lenses report one cause** → `path "<A symbol>" "<B symbol>"`. Returns the hop chain with each edge's relation and an EXTRACTED or INFERRED tag. CHEAP: 0.23 s. A short EXTRACTED-only chain is real coupling; one routed through a test class or through `str`/`Path` is a god-node artefact, not a shared cause
- **How much does this symbol matter** → `explain "<symbol>"`. Source file and line, community, degree, and the neighbour list with direction and provenance. CHEAP: 0.21 s. Degree is the cheapest severity prior available - the same defect in a degree-108 node is not the same finding as in a degree-2 node
- **How does X work** → `query "<question>"`, NOISY as issued. Seeds come from keyword scoring over node labels and source paths, and the corpus mixes code symbols with markdown headings, so a plain question returns documentation. `--context call` restricts traversal to true call edges and is the single most effective noise control: one question here returned 18 nodes bare and the 6 call-connected ones with the filter
- **What to read first in an unfamiliar tree** → the God Nodes and Community Hubs sections of `<out>/GRAPH_REPORT.md`, not a command; 0.8.18 has no `god-nodes` subcommand. AVOID reading that file whole - 143 KB over 2,148 lines here, roughly 36k tokens. Read the head (Corpus Check, Summary, Graph Freshness, God Nodes, Surprising Connections) and stop before the per-community dump, which carries most of the bytes
- **Can the graph be trusted at all** → `diagnose multigraph`, once, before a review leans on it. Reports `effective_directed`, dangling and self-loop edges, and same-endpoint collapse counts

Weight anything the graph suggests by its edge provenance. This repository's graph is 11,215 EXTRACTED against 1,491 INFERRED, 88 percent to 12. An INFERRED edge is a heuristic guess - never raise a finding's severity on one without opening the file.

## Commands

```bash
graphify affected  "<node-or-label>" --graph <graph.json> [--depth N] [--relation R]...
graphify path      "<A>" "<B>"       [--graph <graph.json>]
graphify explain   "<symbol>"        [--graph <graph.json>]
graphify query     "<question>"      [--graph <graph.json>] [--context C] [--budget N] [--dfs]
graphify diagnose multigraph         [--graph <graph.json>] [--json] [--max-examples N]
graphify update    <path>            [--force] [--no-cluster]
```

Defaults read off the binary: `affected --depth 2`, traversing calls, references, imports, imports_from, re_exports, inherits, extends, implements, uses, mixes_in, embeds; `query` depth 2 and `--budget 2000`, with `--context` values call, import, field, parameter_type, return_type, generic_arg, attribute. Every command above is free - AST only, no API key, no tokens - including `graphify update`, which is the post-edit refresh and takes seconds. `graphify extract` and the `/graphify` skill pipeline are the LLM-billed paths.

## Artefacts and the refresh point

One index directory per repository - `tmp/graphify-out/` here, `graphify-out/` by default. What a prompt names as data:

- `graph.json` - the index itself; the only artefact a reviewer needs pointed at
- `GRAPH_REPORT.md` - communities, god nodes, surprising connections, Graph Freshness; read the head only
- `manifest.json` - a file inventory `update` only writes, never reads; the readers are `graphify extract`'s incremental mode and the LLM-billed `/graphify --update` semantic pass. `update`'s own skip decision is a post-rebuild topology comparison, so it re-extracts the whole code corpus either way
- dated subdirectories (`2026-08-29/`) - prior builds, kept for comparison, never the one to hand over

Refresh at one point in the loop: after a fix round lands and before the confirming round spawns. `graphify update <path>` re-extracts the whole code corpus from AST in seconds at no token cost, so it never needs deliberating over. A confirming round handed the pre-fix index re-reports the findings the fixes closed.

## Gotchas

- **The default artefact path is `graphify-out/` under the working directory** - this repository keeps its graph at `tmp/graphify-out/`, so every bare invocation fails with `error: graph file not found: <repo>/graphify-out/graph.json`
- **`GRAPHIFY_OUT` is honoured by some commands and silently ignored by others** - query, path, explain and tree honour it; `affected` and `benchmark` hardcode the literal `graphify-out` (`__main__.py:1779` and `:2724`), verified both ways on this box. Pass `--graph` explicitly and the split stops mattering. The variable is read once at interpreter start, so exporting it mid-process changes nothing
- **A bare existing path is rewritten to `extract`** - `graphify .` and `graphify ./src` become the LLM-billed full pipeline at `__main__.py:3454`, with no confirmation. There is no read-only "inspect this directory" invocation
- **A stale graph looks exactly like a fresh one** - query, affected, path and explain answer confidently from whatever `graph.json` is on disk and never warn. Compare `built_at_commit` in `graph.json` (also in GRAPH_REPORT.md's Graph Freshness section) against `git rev-parse HEAD` before trusting a radius; on this checkout the two differ, so the graph is behind the tree
- **`affected` degrades on an undirected graph, and the default build is undirected** - it walks `in_edges`, which exists only on a DiGraph; on an `nx.Graph` it falls back to scanning all edges for `target == current` (`affected.py:90-96`), sees only the stored orientation and misses roughly half the reverse edges. This repository's graph is `directed: false`, so treat its radius as a lower bound
- **`affected` needs a unique seed** - exact node id, then unique exact label, then unique source file, then unique substring; anything ambiguous returns the single line `No unique node match for <query>`. A common name such as `check` will not resolve, so take the id from `explain` or `query`
- **`path` warns `target match was ambiguous`** when it picked an endpoint by score tie-break - the chain returned may not be the one you meant
- **`--context` is precise and lossy** - only 5,428 of 12,706 edges here carry a `context` attribute (call 4062, parameter_type 735, return_type 309, generic_arg 300, import 22). The other 7,278 - contains 4,320, rationale_for 1,490, uses 736, method 726, inherits 5, defines 1 - are dropped entirely by any context filter. `references` is not among them: all 1,344 of them carry a type context (parameter_type 735, return_type 309, generic_arg 300) and survive the filter. Right for call flow, wrong for asking what a module contains
- **`--budget` is a ceiling, not a target** - one query returned 5,737 characters at both `--budget 2000` and `--budget 20000`, and 1,648 at `--budget 500` with a truncation line naming how many nodes were cut. Raising it will not enlarge a subgraph that already fits
- **`update` never removes a deleted file's nodes, and `--force` cannot make it** - the CLI calls `_rebuild_code` with no change list (`__main__.py:2260`), so `deleted_paths` stays empty (`watch.py:366-382`), `evict_sources` stays empty (`watch.py:411`), and every existing node the new AST output lacks is preserved (`watch.py:418-427`). The candidate count therefore never falls below the existing one, the shrink guard (`watch.py:243`, called at `:461` and `:565`) can never fire on a deletion, and `--force` / `GRAPHIFY_FORCE=1` has nothing to override - though `--help` still advertises the flag as "use after refactors that delete code". Verified on an 11-node scratch tree: after deleting one source file, plain `update`, `update --force` and `GRAPHIFY_FORCE=1 update` each printed `No code-graph topology changes detected; outputs left untouched` and left 11 nodes, and `explain` still placed the deleted class at its old file and line. Two things do evict - the post-commit hook from `graphify hook install`, which passes the changed-file list including deletions (8 nodes → 4 on a committed removal here), and removing `graph.json` before `update`, which rebuilds AST-only and drops whatever semantic layer that graph carried (11 → 7 here)
- **`update` writes `manifest.json` relative to the working directory** (`detect.py:26` holds the literal, outside the `GRAPHIFY_OUT` override), so a relocated output tree collects a stray `graphify-out/manifest.json` beside the real one
- **Per-subcommand `--help` mostly does not exist** - six subcommands escape the generic line - `save-result` and `install` have real handlers, `path` prints one usage line, `uninstall --help` errors as an unknown option, and `query --help` / `explain --help` treat `--help` as the thing being asked about. Everything else prints `Run 'graphify --help' for full usage.` The top-level `--help` is the only index, and it is wrong in places: it documents `tree --top-k-edges` as default 12 against a code default of 0, omits `--version`, and omits `install --project`

An agent prompt passes the index as data - what it is, where - and never a command, because a written invocation pins an API that moves; this file is for the session that runs the instrument, not for the prompt that spawns an agent.
