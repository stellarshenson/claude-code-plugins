"""Deterministic helpers around an adversarial code review.

A whole-repo reviewer re-reads its entire transcript on every API turn, so
its bill grows with the square of the turn count while the files it reads
stay a few hundred KB. Measured over 69 reviews of this repository: 67-115
turns, 9-16M cached input tokens and 15-25 minutes each, of which roughly
1-2% was file content. Forty to sixty of those turns rediscover the same
inventory every time - which files exist, where the symbols are, what the
CLI surface is, where the risky primitives live, which literal is duplicated
across modules. Three commands remove that cost or make it measurable:

    dossier   one markdown document with the inventory, produced by AST in
              seconds, pasted into every reviewer's prompt
    cost      turns, tokens, tool mix and re-reads per subagent transcript,
              so a prompt change can be shown to have saved something
    findings  the VERDICT line and severity-tagged bullets of N reviewer
              reports merged by file:line, so the adjudicator starts from
              one table rather than four prose reports

Everything here is read-only over the repository; the only file it writes is
the one `--out` names.
"""

from __future__ import annotations

import argparse
import ast
import collections
import datetime as dt
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tomllib

# ---------------------------------------------------------------------------
# Dossier
# ---------------------------------------------------------------------------

# Executable primitives a reviewer greps for first. Each is a class name and
# the line regex that finds it; the dossier lists every hit as file:line.
RISKY = (
    ("write", re.compile(r"""\bopen\([^)]*["'][wax]b?\+?["']|\.write_text\(|\.write_bytes\(""")),
    (
        "delete",
        re.compile(r"\bos\.(?:remove|unlink|rmdir)\(|\.unlink\(|\.rmdir\(|shutil\.rmtree\("),
    ),
    ("subprocess", re.compile(r"\bsubprocess\.|\bos\.system\(|\bos\.exec\w*\(")),
    ("environ", re.compile(r"\bos\.environ\b|\bos\.getenv\(")),
    (
        "broad-except",
        re.compile(
            r"^\s*except\s*(?:\(?\s*(?:Exception|BaseException)\s*\)?\s*(?:as\s+\w+)?)?\s*:"
        ),
    ),
    ("clock", re.compile(r"\b(?:datetime|date)\.(?:now|today|utcnow)\(|\btime\.time\(")),
    (
        "fs-order",
        re.compile(
            r"\.(?:glob|rglob|iterdir)\(|\bos\.(?:listdir|walk|scandir)\(|\bglob\.i?glob\("
        ),
    ),
    ("tempfile", re.compile(r"\btempfile\.")),
    ("exit", re.compile(r"\bsys\.exit\(")),
    ("eval", re.compile(r"(?<![\w.])(?:eval|exec)\(")),
)

# Literals too common to mean anything when they recur.
_TRIVIAL_STRINGS = {"__main__", "store_true", "store_false", "utf-8", "ascii", "replace", "strict"}
_STRING_MIN, _STRING_MAX = 4, 40
_INT_MIN = 10  # smaller integers recur everywhere and mean nothing
_MAX_FILES = 8  # a literal in more files than this is a convention, not drift
_CAP_HITS = 60  # per risky class
_CAP_LITERALS = 40
_CAP_CALLERS = 5  # per most-called symbol
_SNIPPET = 70


def py_files(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(q for q in p.rglob("*.py") if "__pycache__" not in q.parts))
        elif p.suffix == ".py":
            out.append(p)
    return out


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def symbol_index(tree: ast.AST) -> list[str]:
    """Compact locators: `name:L12` per top-level def, `Class:L5{m:L6,m:L9}` per class."""
    rows: list[str] = []
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            rows.append(f"{node.name}:L{node.lineno}")
        elif isinstance(node, ast.ClassDef):
            methods = ",".join(
                f"{s.name}:L{s.lineno}"
                for s in node.body
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            rows.append(f"{node.name}:L{node.lineno}" + (f"{{{methods}}}" if methods else ""))
    return rows


def cli_surface(tree: ast.AST) -> dict[str, list[tuple[str, dict, int]]]:
    """argparse surface from the AST: parser label -> [(flag names, kwargs, line)].

    A parser variable bound by `x = sub.add_parser("name")` is labelled by that
    name and the `ArgumentParser(...)` itself is `(top)`. An `add_argument` on a
    variable this walk never saw bound (a helper's parameter, a loop variable)
    keeps the variable name with a `?` prefix, so shared-filter helpers stay
    visible instead of vanishing. Subcommands themselves come from `--help`
    (see `help_subcommands`), because a loop-built parser has no literal here.
    """
    labels: dict[str, str] = {}
    out: dict[str, list[tuple[str, dict, int]]] = collections.OrderedDict()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        fn = node.value.func
        name = (
            fn.attr
            if isinstance(fn, ast.Attribute)
            else fn.id
            if isinstance(fn, ast.Name)
            else None
        )
        args = node.value.args
        if name == "add_parser" and args and isinstance(args[0], ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    labels[t.id] = str(args[0].value)
            out.setdefault(str(args[0].value), [])
        elif name == "ArgumentParser":
            for t in node.targets:
                if isinstance(t, ast.Name):
                    labels[t.id] = "(top)"
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            continue
        owner = node.func.value
        label = labels.get(owner.id, f"?{owner.id}") if isinstance(owner, ast.Name) else "?"
        names = "/".join(str(a.value) for a in node.args if isinstance(a, ast.Constant))
        kws = {
            k.arg: ast.unparse(k.value)
            for k in node.keywords
            if k.arg in ("default", "action", "choices", "required", "nargs")
        }
        out.setdefault(label, []).append((names, kws, node.lineno))
    return out


def help_subcommands(module: str) -> set[str] | None:
    """Subcommand names of a console script, or None when the module cannot run.

    Three shapes are read, in order: argparse's `invalid choice: ... (choose from
    'a', 'b')` error for a probe subcommand, which is right even for a parser built
    in a loop or hidden behind a `metavar`; the `{a,b,c}` group in `--help`; and a
    hand-written help whose `Subcommands:` section lists one name per indented line.
    """

    def run(*args: str) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(
                [sys.executable, "-m", module, *args],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    probe = run("__probe__")
    if probe is None:
        return None
    m = re.search(r"choose from (.+?)\)", probe.stderr + probe.stdout, re.S)
    if m:
        # argparse quotes each choice on some interpreter versions and lists them
        # bare on others; read both shapes, or the probe returns an empty set and
        # the --help fallback never runs
        names = {c.strip().strip("'\"") for c in m.group(1).split(",")}
        return {n for n in names if re.fullmatch(r"[\w-]+", n)}
    help_ = run("--help")
    if help_ is None or help_.returncode != 0:
        return None
    usage = help_.stdout.split("\n\n")[0]
    for m in re.finditer(r"(\S+)\s+\{([\w,-]+)\}", usage):
        if not m.group(1).startswith(
            "-"
        ):  # `--mode {a,b}` is a flag's choices, not the subcommands
            return set(m.group(2).split(","))
    names: set[str] = set()
    listing = False
    for line in help_.stdout.split("\n"):
        if re.match(r"^\S.*commands:\s*$", line, re.I):
            listing = True
            continue
        if listing:
            lm = re.match(r"^\s{2,}([a-z][a-z0-9-]*)\s{2,}\S", line)
            if lm:
                names.add(lm.group(1))
            elif line.strip() and not line.startswith(" "):
                listing = False
    return names


def literals(tree: ast.AST) -> list[tuple[object, int]]:
    """Constant values worth cross-checking - no docstrings, no f-string parts, no help texts."""
    skip: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            skip.update(id(v) for v in node.values)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            skip.add(id(node.value))
        elif isinstance(node, ast.Call):
            for k in node.keywords:
                if k.arg in ("help", "description", "epilog"):
                    skip.add(id(k.value))
    out: list[tuple[object, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or id(node) in skip:
            continue
        v = node.value
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, str):
            if not (_STRING_MIN <= len(v) <= _STRING_MAX) or "\n" in v or v in _TRIVIAL_STRINGS:
                continue
        elif isinstance(v, int):
            if abs(v) < _INT_MIN:
                continue
        elif isinstance(v, float):
            if v in (0.0, 1.0):
                continue
        else:
            continue
        out.append((v, node.lineno))
    return out


def risky_hits(lines: list[str]) -> dict[str, list[tuple[int, str]]]:
    hits: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("#"):
            continue
        for cls, rx in RISKY:
            if rx.search(line):
                hits[cls].append((i, s[:_SNIPPET]))
    return hits


def load_scripts(pyproject: Path | None) -> dict[str, str]:
    """console script name -> 'pkg.module' from [project.scripts]."""
    if not pyproject or not pyproject.exists():
        return {}
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    scripts = data.get("project", {}).get("scripts", {})
    return {name: target.split(":")[0] for name, target in scripts.items()}


_CODE_RX = re.compile(r"```.*?```|`[^`\n]+`", re.S)


def doc_references(
    plugins: Path | None, scripts: dict[str, str]
) -> tuple[collections.Counter, collections.Counter]:
    """(module refs, (script, subcommand) refs) counted over code spans and fenced blocks only.

    Prose after a script name is not a command (`pm-tools console output`), so
    only what the docs present as runnable text counts as advertised.
    """
    mods: collections.Counter = collections.Counter()
    subs: collections.Counter = collections.Counter()
    if not plugins or not plugins.exists():
        return mods, subs
    mod_rx = re.compile(r"python3?\s+-m\s+([\w.]+)")
    sub_rx = (
        re.compile(
            r"(?<![\w/-])(" + "|".join(re.escape(s) for s in scripts) + r")\s+([a-z][a-z0-9-]*)"
        )
        if scripts
        else None
    )
    for md in sorted(plugins.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        for span in _CODE_RX.findall(text):
            for m in mod_rx.finditer(span):
                if m.group(1) != "pip":
                    mods[m.group(1)] += 1
            if sub_rx:
                for m in sub_rx.finditer(span):
                    subs[(m.group(1), m.group(2))] += 1
    return mods, subs


def graph_callers(graph: Path, files: set[str], top: int) -> list[tuple[str, str, list[str]]]:
    """Most-called function nodes inside `files`: (label, file:line, callers)."""
    data = json.loads(graph.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    callers: dict[str, set[str]] = collections.defaultdict(set)
    for e in data.get("links", data.get("edges", [])):
        if e.get("relation") != "calls":
            continue
        tgt = nodes.get(e.get("target"))
        src = nodes.get(e.get("source"))
        if (
            not tgt
            or not src
            or tgt.get("source_file") not in files
            or not str(tgt.get("label", "")).endswith("()")
        ):
            continue
        site = f"{e.get('source_file', src.get('source_file'))}:{e.get('source_location', src.get('source_location'))}"
        callers[tgt["id"]].add(f"{src.get('label')} ({site})")
    ranked = sorted(callers.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:top]
    return [
        (
            nodes[k]["label"],
            f"{nodes[k].get('source_file')}:{nodes[k].get('source_location')}",
            sorted(v),
        )
        for k, v in ranked
    ]


def build_dossier(
    paths: list[Path],
    root: Path,
    pyproject: Path | None,
    plugins: Path | None,
    graph: Path | None,
    top: int = 20,
    run_help: bool = True,
) -> dict:
    files = py_files(paths)
    inventory: list[dict] = []
    symbols: dict[str, list[str]] = {}
    surface: dict[str, dict] = {}
    risky: dict[str, dict[str, list[tuple[int, str]]]] = {}
    lit_index: dict[object, dict[str, list[int]]] = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )
    for f in files:
        rel = _rel(f, root)
        text = f.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            inventory.append(
                {"file": rel, "lines": len(lines), "error": f"syntax error line {exc.lineno}"}
            )
            continue
        syms = symbol_index(tree)
        inventory.append({"file": rel, "lines": len(lines), "symbols": len(syms)})
        symbols[rel] = syms
        cli = cli_surface(tree)
        if cli:
            surface[rel] = cli
        hits = risky_hits(lines)
        if hits:
            risky[rel] = hits
        for v, ln in literals(tree):
            lit_index[v][rel].append(ln)
    shared = sorted(
        ((v, dict(fs)) for v, fs in lit_index.items() if 2 <= len(fs) <= _MAX_FILES),
        key=lambda kv: (len(kv[1]), -sum(len(x) for x in kv[1].values()), repr(kv[0])),
    )
    scripts = load_scripts(pyproject)
    mod_refs, sub_refs = doc_references(plugins, scripts)
    module_of = {rel.removesuffix(".py").replace("/", "."): rel for rel in symbols}
    surface_check = []
    for script, module in scripts.items():
        rel = next((r for m, r in module_of.items() if m.endswith(module)), None)
        if rel is None:
            surface_check.append({"script": script, "module": module, "file": None})
            continue
        live = help_subcommands(module) if run_help else None
        defined = (
            live
            if live is not None
            else {d for d in surface.get(rel, {}) if d != "(top)" and not d.startswith("?")}
        )
        referenced = {sub for (s, sub) in sub_refs if s == script} - {"subcommand", "command"}
        if not defined:
            referenced = set()
        surface_check.append(
            {
                "script": script,
                "module": module,
                "file": rel,
                "source": "--help" if live is not None else "ast",
                "defined": sorted(defined),
                "advertised_undefined": sorted(referenced - defined),
                "defined_unadvertised": sorted(defined - referenced),
            }
        )
    callers: list = []
    graph_note = None
    if graph:
        if graph.exists():
            try:
                callers = graph_callers(graph, set(symbols), top)
            except (OSError, ValueError, KeyError) as exc:
                graph_note = f"graph unreadable: {exc}"
        else:
            graph_note = f"graph not found: {graph}"
    return {
        "root": str(root),
        "inventory": inventory,
        "symbols": symbols,
        "surface": surface,
        "risky": risky,
        "shared_literals": shared,
        "scripts": scripts,
        "module_refs": dict(mod_refs),
        "surface_check": surface_check,
        "callers": callers,
        "graph_note": graph_note,
    }


def render_dossier(d: dict) -> str:
    out: list[str] = ["# Review dossier", "", f"Root: `{d['root']}`", ""]
    out += ["## Inventory", "", "| file | lines | symbols |", "|---|---:|---:|"]
    total = 0
    for row in d["inventory"]:
        total += row["lines"]
        out.append(
            f"| `{row['file']}` | {row['lines']} | {row.get('symbols', row.get('error', '-'))} |"
        )
    out += [f"| **total** | **{total}** | |", ""]
    out += [
        "## Symbols",
        "",
        "`name:Lnn` per top-level def, `Class:Lnn{method:Lnn,...}` per class.",
        "",
    ]
    for rel, syms in d["symbols"].items():
        if syms:
            out.append(f"- `{rel}`: " + " ".join(syms))
    out.append("")
    out += ["## CLI surface", ""]
    for rel, cli in d["surface"].items():
        out.append(f"### `{rel}`")
        for label, args in cli.items():
            head = f"- **{label}**" + (
                " (shared helper, parser variable unresolved)" if label.startswith("?") else ""
            )
            parts = []
            for names, kws, ln in args:
                extra = ",".join(f"{k}={v}" for k, v in kws.items())
                parts.append(f"`{names}`" + (f"({extra})" if extra else "") + f" L{ln}")
            out.append(head + ": " + "; ".join(parts) if parts else head)
        out.append("")
    if d["surface_check"]:
        out += ["## Advertised surface vs parser", ""]
        for row in d["surface_check"]:
            if not row["file"]:
                out.append(f"- `{row['script']}` → `{row['module']}` (module not in scope)")
                continue
            out.append(
                f"- `{row['script']}` → `{row['file']}` ({row['source']}): "
                + ", ".join(f"`{s}`" for s in row["defined"])
            )
            if row["advertised_undefined"]:
                out.append(
                    f"  - advertised in docs, no parser: {', '.join('`' + s + '`' for s in row['advertised_undefined'])}"
                )
            if row["defined_unadvertised"]:
                out.append(
                    f"  - parser defines, docs never mention: {', '.join('`' + s + '`' for s in row['defined_unadvertised'])}"
                )
        if d["module_refs"]:
            out.append(
                "- `python -m` references in docs: "
                + ", ".join(f"`{m}` ×{n}" for m, n in sorted(d["module_refs"].items()))
            )
        out.append("")
    out += ["## Risky primitives", ""]
    by_class: dict[str, list[str]] = collections.defaultdict(list)
    for rel, hits in d["risky"].items():
        for cls, rows in hits.items():
            by_class[cls].extend(f"`{rel}:{ln}` `{s}`" for ln, s in rows)
    for cls, _ in RISKY:
        rows = by_class.get(cls)
        if not rows:
            continue
        out.append(f"### {cls} ({len(rows)})")
        out.extend(f"- {r}" for r in rows[:_CAP_HITS])
        if len(rows) > _CAP_HITS:
            out.append(f"- ... {len(rows) - _CAP_HITS} more")
        out.append("")
    out += ["## Literals shared across modules", ""]
    if not d["shared_literals"]:
        out.append("- none")
    for v, fs in d["shared_literals"][:_CAP_LITERALS]:
        items = sorted(fs.items())
        where = "; ".join(f"`{rel}`:{','.join(map(str, lns[:4]))}" for rel, lns in items[:4])
        out.append(f"- `{v!r}` in {len(fs)} files - {where}" + (" ..." if len(items) > 4 else ""))
    if len(d["shared_literals"]) > _CAP_LITERALS:
        out.append(f"- ... {len(d['shared_literals']) - _CAP_LITERALS} more")
    out.append("")
    if d["callers"] or d["graph_note"]:
        out += ["## Most-called symbols (code graph)", ""]
        if d["graph_note"]:
            out.append(f"- {d['graph_note']}")
        for label, site, callers in d["callers"]:
            shown = ", ".join(f"`{c}`" for c in callers[:_CAP_CALLERS])
            out.append(
                f"- `{label}` `{site}` ← {len(callers)} callers: {shown}"
                + (" ..." if len(callers) > _CAP_CALLERS else "")
            )
        out.append("")
    return "\n".join(out)


def cmd_dossier(args: argparse.Namespace) -> int:
    root = args.root or Path.cwd()
    pyproject = (
        args.pyproject
        if args.pyproject
        else (root / "pyproject.toml" if (root / "pyproject.toml").exists() else None)
    )
    d = build_dossier(
        args.paths, root, pyproject, args.plugins, args.graph, args.top, run_help=not args.no_help
    )
    text = json.dumps(d, indent=2, default=str) if args.json else render_dossier(d)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"{args.out} ({len(text) // 1024} KB, {len(d['inventory'])} files)")
    else:
        print(text)
    return 0


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------


def _ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _bash_verb(cmd: str) -> str:
    """First command word, looking past `cd X &&`, `cd X;` and a `cd` on its own line."""
    for line in cmd.strip().split("\n"):
        toks = [t.lstrip("(") for t in line.split() if not re.match(r"^[A-Z_]+=", t)]
        toks = [t for t in toks if t]
        if not toks:
            continue
        if toks[0] == "cd":
            rest = toks[3:] if len(toks) > 3 and toks[2] in ("&&", ";") else []
            if not rest:
                continue
            toks = rest
        return toks[0]
    return "?"


def cost_of(path: Path) -> dict:
    """Per-transcript cost profile, deduplicated by API message id.

    The harness writes one transcript line per content block, so a turn that
    thought and then called a tool appears twice with the same `message.id`
    and the same `usage`; summing per line double-counts the bill.
    """
    turns: dict[str, dict] = collections.OrderedDict()
    tool_name: dict[str, str] = {}
    result_bytes: collections.Counter = collections.Counter()
    tiny = 0
    targets: collections.Counter = collections.Counter()
    verbs: collections.Counter = collections.Counter()
    first = last = None
    events = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            ts = ev.get("timestamp")
            if ts:
                t = _ts(ts)
                first = first or t
                last = t
            msg = ev.get("message") or {}
            content = msg.get("content")
            if msg.get("role") == "assistant":
                events += 1
                turn = turns.setdefault(
                    msg.get("id") or f"anon{events}", {"usage": {}, "tools": []}
                )
                u = msg.get("usage") or {}
                for k in (
                    "input_tokens",
                    "output_tokens",
                    "cache_read_input_tokens",
                    "cache_creation_input_tokens",
                ):
                    turn["usage"][k] = max(turn["usage"].get(k, 0), u.get(k) or 0)
                for c in content if isinstance(content, list) else []:
                    if not isinstance(c, dict) or c.get("type") != "tool_use":
                        continue
                    name = c.get("name", "?")
                    turn["tools"].append(name)
                    tool_name[c.get("id")] = name
                    inp = c.get("input") or {}
                    if name == "Bash":
                        verbs[_bash_verb(inp.get("command", ""))] += 1
                    tgt = inp.get("file_path") or inp.get("path") or inp.get("pattern")
                    if name in ("Read", "Grep", "Glob") and tgt:
                        targets[(name, tgt)] += 1
            elif msg.get("role") == "user" and isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        name = tool_name.get(c.get("tool_use_id"), "?")
                        body = c.get("content")
                        if isinstance(body, str):
                            n = len(body)
                        elif isinstance(body, list):
                            n = sum(len(x.get("text", "")) for x in body if isinstance(x, dict))
                        else:
                            n = 0
                        result_bytes[name] += n
                        tiny += n < 80
    usage: collections.Counter = collections.Counter()
    contexts: list[int] = []
    tool_calls: collections.Counter = collections.Counter()
    tool_turns = multi = 0
    for turn in turns.values():
        u = turn["usage"]
        usage.update(u)
        contexts.append(
            u.get("input_tokens", 0)
            + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0)
        )
        tool_calls.update(turn["tools"])
        tool_turns += bool(turn["tools"])
        multi += len(turn["tools"]) > 1
    return {
        "file": str(path),
        "turns": len(turns),
        "events": events,
        "wall_min": round((last - first).total_seconds() / 60, 1) if first and last else None,
        "input_tokens": usage["input_tokens"],
        "cache_read": usage["cache_read_input_tokens"],
        "cache_create": usage["cache_creation_input_tokens"],
        "output_tokens": usage["output_tokens"],
        "context_median": int(statistics.median(contexts)) if contexts else 0,
        "context_max": max(contexts) if contexts else 0,
        "tool_turns": tool_turns,
        "multi_tool_turns": multi,
        "tool_calls": dict(tool_calls.most_common()),
        "result_kb": {k: round(v / 1024, 1) for k, v in result_bytes.most_common()},
        "tiny_results": tiny,
        "distinct_targets": len(targets),
        "rereads": sum(v - 1 for v in targets.values() if v > 1),
        "bash_verbs": dict(verbs.most_common(8)),
    }


def render_cost(rows: list[dict]) -> str:
    out = [
        "| transcript | turns | min | cache read | cache create | output | ctx median | tool calls | result KB | re-reads |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def line(name: str, r: dict, ctx: str) -> str:
        wall = r["wall_min"] if r["wall_min"] is not None else "-"
        return (
            f"| {name} | {r['turns']} | {wall} | {r['cache_read']:,} | {r['cache_create']:,} | {r['output_tokens']:,} "
            f"| {ctx} | {sum(r['tool_calls'].values())} | {sum(r['result_kb'].values()):.0f} | {r['rereads']} |"
        )

    for r in rows:
        out.append(line(f"`{Path(r['file']).name}`", r, f"{r['context_median']:,}"))
    if len(rows) > 1:
        total = {
            "turns": sum(r["turns"] for r in rows),
            "wall_min": round(sum(r["wall_min"] or 0 for r in rows), 1),
            "cache_read": sum(r["cache_read"] for r in rows),
            "cache_create": sum(r["cache_create"] for r in rows),
            "output_tokens": sum(r["output_tokens"] for r in rows),
            "tool_calls": collections.Counter(),
            "result_kb": collections.Counter(),
            "rereads": sum(r["rereads"] for r in rows),
        }
        for r in rows:
            total["tool_calls"].update(r["tool_calls"])
            total["result_kb"].update(r["result_kb"])
        out.append(line("**total**", total, ""))
    out.append("")
    out.append(
        "Cache read is the bill: every turn re-reads the whole transcript, so it grows with turns squared, "
        "while result KB is what the reviewer actually read."
    )
    out.append("")
    for r in rows:
        out.append(
            f"- `{Path(r['file']).name}`: {r['tool_turns']} tool turns of {r['turns']} ({r['multi_tool_turns']} batched), "
            f"{r['tiny_results']} near-empty results, tools {r['tool_calls']}, bash {r['bash_verbs']}"
        )
    return "\n".join(out)


def cmd_cost(args: argparse.Namespace) -> int:
    rows = [cost_of(p) for p in args.transcripts]
    print(json.dumps(rows, indent=2) if args.json else render_cost(rows))
    return 0


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

VERDICT_RE = re.compile(r"VERDICT:\s*(SHIP|DO-NOT-SHIP)(?:\s*\((\d+)\s*findings?\))?", re.I)
SEV_RE = re.compile(r"\[(CRITICAL|MAJOR|MINOR)(?:\s*\((taste)\))?\]")
BULLET_RE = re.compile(r"^(\s*)(?:[-*+]\s+|\*{0,2}\d+\.\s+)")
LOC_RE = re.compile(
    r"(?<![\w/])((?:[\w.-]+/)*[\w.-]+\.(?:py|md|txt|json|ya?ml|toml|sh|ts|tsx|js|css|svg|html|cfg|ini))(?::L?(\d+))?"
)
SEV_RANK = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}
NEAR_LINES = 25  # two lenses citing the same file this close apart are one defect


def _location(body: str) -> tuple[str | None, int | None]:
    """First cited location, preferring one with a line number over a bare filename in prose."""
    best = None
    for m in LOC_RE.finditer(body):
        if m.group(2):
            return m.group(1), int(m.group(2))
        best = best or m.group(1)
    return best, None


def parse_report(text: str, lens: str) -> dict:
    """VERDICT + one record per severity-tagged finding line, dash bullet or
    numbered-bold heading (`**1. [MAJOR] ...**`), with its continuation lines."""
    verdict = None
    m = VERDICT_RE.search(text)
    if m:
        verdict = {"verdict": m.group(1).upper(), "count": int(m.group(2)) if m.group(2) else None}
    findings: list[dict] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        bm = BULLET_RE.match(line)
        sm = SEV_RE.search(line) if bm else None
        if not sm:
            i += 1
            continue
        indent = len(bm.group(1))
        block = [line]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            nb = BULLET_RE.match(nxt)
            if not nxt.strip() or nxt.startswith("#") or (nb and len(nb.group(1)) <= indent):
                break
            block.append(nxt)
            j += 1
        body = " ".join(s.strip() for s in block)
        after = line[sm.end() :].strip().lstrip("*").strip()
        title = re.split(r"\*\*|\s+-\s+", after, maxsplit=1)[0].strip().rstrip(":") or after[:80]
        file, ln = _location(body)
        findings.append(
            {
                "lens": lens,
                "severity": sm.group(1).upper(),
                "taste": bool(sm.group(2)),
                "title": title[:120],
                "file": file,
                "line": ln,
                "text": "\n".join(block),
            }
        )
        i = j
    return {"lens": lens, "verdict": verdict, "findings": findings}


def verdict_inconsistencies(reports: list[dict]) -> list[str]:
    """Coupling rule: SHIP iff the report carries no CRITICAL and no MAJOR finding.

    Reviewer prose drifts - observed 2026-08-28: four of eight rounds returned
    DO-NOT-SHIP on a severity mix the contract maps to SHIP, and the loop ran on.
    """
    out = []
    for rep in reports:
        v = (rep.get("verdict") or {}).get("verdict")
        if not v:
            continue
        blocking = sum(1 for f in rep["findings"] if f["severity"] in ("CRITICAL", "MAJOR"))
        if v == "SHIP" and blocking:
            out.append(
                f"{rep['lens']}: VERDICT INCONSISTENT - SHIP with {blocking} CRITICAL/MAJOR "
                "finding(s); the coupling rule maps this mix to DO-NOT-SHIP"
            )
        elif v == "DO-NOT-SHIP" and not blocking:
            out.append(
                f"{rep['lens']}: VERDICT INCONSISTENT - DO-NOT-SHIP with no CRITICAL or MAJOR "
                "finding parsed; the coupling rule maps this mix to SHIP"
            )
    return out


def merge_findings(reports: list[dict]) -> list[dict]:
    """One row per defect: same file (by basename) within NEAR_LINES, or the same normalised title."""
    rows: list[dict] = []
    for rep in reports:
        for f in rep["findings"]:
            base = Path(f["file"]).name if f["file"] else None
            tkey = re.sub(r"\W+", " ", f["title"].lower()).strip()
            hit = None
            for row in rows:
                if (
                    base
                    and row["base"] == base
                    and f["line"]
                    and row["line"]
                    and abs(f["line"] - row["line"]) <= NEAR_LINES
                ):
                    hit = row
                    break
                if row["tkey"] == tkey:
                    hit = row
                    break
            if hit is None:
                rows.append(
                    {**f, "base": base, "tkey": tkey, "lenses": [f["lens"]], "texts": [f["text"]]}
                )
                continue
            hit["lenses"].append(f["lens"])
            hit["texts"].append(f["text"])
            if SEV_RANK[f["severity"]] < SEV_RANK[hit["severity"]]:
                hit["severity"], hit["title"] = f["severity"], f["title"]
    rows.sort(
        key=lambda r: (SEV_RANK[r["severity"]], r["taste"], r["file"] or "~", r["line"] or 0)
    )
    return rows


def render_findings(reports: list[dict], rows: list[dict], full: bool) -> str:
    out = [
        "## Verdicts",
        "",
        "| lens | verdict | claimed | parsed | critical | major | minor |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for rep in reports:
        v = rep["verdict"] or {}
        sev = collections.Counter(f["severity"] for f in rep["findings"])
        claimed = v.get("count") if v.get("count") is not None else "-"
        out.append(
            f"| {rep['lens']} | {v.get('verdict', '-')} | {claimed} | {len(rep['findings'])} | {sev['CRITICAL']} | {sev['MAJOR']} | {sev['MINOR']} |"
        )
    out += [
        "",
        f"## Findings ({len(rows)} after merge)",
        "",
        "| # | severity | location | title | lenses |",
        "|---:|---|---|---|---|",
    ]
    for n, r in enumerate(rows, 1):
        loc = (
            f"`{r['file']}:{r['line']}`"
            if r["file"] and r["line"]
            else (f"`{r['file']}`" if r["file"] else "-")
        )
        sev = r["severity"] + (" (taste)" if r["taste"] else "")
        out.append(
            f"| {n} | {sev} | {loc} | {r['title']} | {', '.join(dict.fromkeys(r['lenses']))} |"
        )
    if full:
        out += ["", "## Full text", ""]
        for n, r in enumerate(rows, 1):
            out.append(f"### {n}. [{r['severity']}] {r['title']}")
            for lens, text in zip(r["lenses"], r["texts"]):
                out += [f"_{lens}_", text, ""]
    return "\n".join(out)


def cmd_findings(args: argparse.Namespace) -> int:
    reports = [parse_report(p.read_text(encoding="utf-8"), p.stem) for p in args.reports]
    rows = merge_findings(reports)
    bad = verdict_inconsistencies(reports)
    if args.json:
        summary = [
            {"lens": r["lens"], "verdict": r["verdict"], "findings": len(r["findings"])}
            for r in reports
        ]
        print(json.dumps({"reports": summary, "findings": rows, "inconsistencies": bad}, indent=2))
    else:
        print(render_findings(reports, rows, args.full))
        if bad:
            print("\n## Verdict check\n\n" + "\n".join(f"- {b}" for b in bad))
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="review-tools", description="Deterministic helpers around an adversarial code review."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_d = sub.add_parser(
        "dossier",
        help="Inventory a tree for reviewers: symbols, CLI surface, risky primitives, shared literals, callers.",
    )
    p_d.add_argument("paths", nargs="+", type=Path, help="Python files or directories in scope.")
    p_d.add_argument(
        "--root", type=Path, help="Path prefix to strip from file names (default: cwd)."
    )
    p_d.add_argument(
        "--pyproject",
        type=Path,
        help="pyproject.toml for console scripts (default: ./pyproject.toml when present).",
    )
    p_d.add_argument(
        "--plugins",
        type=Path,
        help="Markdown tree whose code spans are the advertised CLI surface.",
    )
    p_d.add_argument("--graph", type=Path, help="graphify graph.json for the most-called symbols.")
    p_d.add_argument(
        "--top", type=int, default=20, help="Most-called symbols to list from the graph."
    )
    p_d.add_argument(
        "--no-help",
        action="store_true",
        help="Do not run each console script's --help; read subcommands from the AST only.",
    )
    p_d.add_argument("--out", type=Path, help="Write here instead of stdout.")
    p_d.add_argument("--json", action="store_true")

    p_c = sub.add_parser(
        "cost", help="Turns, tokens, tool mix and re-reads per subagent transcript (JSONL)."
    )
    p_c.add_argument("transcripts", nargs="+", type=Path)
    p_c.add_argument("--json", action="store_true")

    p_f = sub.add_parser(
        "findings", help="Merge reviewer reports into one severity table keyed by file:line."
    )
    p_f.add_argument(
        "reports", nargs="+", type=Path, help="Reviewer reports; the file stem is the lens name."
    )
    p_f.add_argument(
        "--full", action="store_true", help="Append every finding's original text under the table."
    )
    p_f.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "dossier":
        return cmd_dossier(args)
    if args.command == "cost":
        return cmd_cost(args)
    if args.command == "findings":
        return cmd_findings(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
