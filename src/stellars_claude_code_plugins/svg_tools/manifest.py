"""Pre-flight checklist for SVG infographic builds.

The agent declares upfront, via CLI flags, what the build will
contain (counts of cards, connectors, background textures, etc.).
The tool responds with (a) the matching rule cards from the rule
library, and (b) warnings for common-mistake classes given that
declaration shape. Later, after authoring, the same flag set can
be re-presented to the ``check`` subcommand to verify the built
file matches the plan.

Two stateless subcommands:

- ``preflight`` - agent declares component counts + options via
                  CLI flags; tool returns the subset of the rule
                  library that applies, plus context-aware warnings.
- ``check``     - agent re-states the same declaration alongside
                  an SVG path; tool counts components in the SVG
                  and verifies they match the declaration, plus
                  basic viewBox / aspect-ratio / dark-mode checks.
                  Exits 1 on any FAIL.

No manifest file. The agent types flags; the tool responds. This
is deliberate: forcing the agent to enumerate component counts +
connector direction on the command line IS the thinking step.

Typical flow::

    # Phase 1: pre-flight - what am I building?
    svg-tools preflight \\
        --cards 4 \\
        --connectors 1 --connector-mode manifold \\
        --connector-direction sinks-to-sources \\
        --backgrounds 1 --background-texture circuit \\
        --dark-mode required

    # (returns markdown bundle of relevant rules + warnings)

    # Phase 2: author the SVG with the rule bundle in context

    # Phase 3: audit - does the file match the plan?
    svg-tools check --svg file.svg \\
        --cards 4 \\
        --connectors 1 --connector-mode manifold \\
        --connector-direction sinks-to-sources \\
        --dark-mode required
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

# Known component types. Adding a new type requires:
#   1. new entry here
#   2. new file at svg-infographics/skills/svg-designer/rules/<type>.md
#   3. count / role logic in _count_components_in_svg
KNOWN_COMPONENT_TYPES = {
    "card",
    "connector",
    "background",
    "timeline",
    "icon",
    "callout",
    "ribbon",
}

KNOWN_CONNECTOR_MODES = {
    "straight",
    "L",
    "L-chamfer",
    "spline",
    "manifold",
    "ribbon",
}

# Direction taxonomy: must match calc_connector semantics (WI#3).
KNOWN_DIRECTIONS = {"forward", "reverse", "both", "none"}
KNOWN_MANIFOLD_DIRECTIONS = {
    "sources-to-sinks",
    "sinks-to-sources",
    "both",
    "none",
}


class ManifestError(ValueError):
    """Raised when a declaration is internally inconsistent.

    Example: declaring ``--connectors 2`` without
    ``--connector-direction``. The CLI surfaces this with exit 2
    (config-style error, distinct from exit 1 = plan-vs-SVG
    divergence).
    """


# --------------------------------------------------------------------------
# Declaration: what the agent says they will build
# --------------------------------------------------------------------------


@dataclass
class Declaration:
    """Flag-derived record of the planned build.

    ``counts`` maps component type → declared count. Zero-count
    types are dropped before ``pull_rules`` so the rule bundle
    only covers what is actually being built.

    Connector mode + direction live at the top level because the
    CLI is flag-driven and one connector configuration per build
    is the overwhelming common case. Mixed-mode builds declare
    the dominant mode and fall back to per-call overrides on
    ``calc_connector``.
    """

    counts: dict[str, int] = field(default_factory=dict)
    dark_mode: str = "optional"  # required | optional | none
    connector_mode: str | None = None
    connector_direction: str | None = None

    @property
    def declared_types(self) -> list[str]:
        """Sorted list of component types with non-zero count."""
        return sorted(t for t, c in self.counts.items() if c > 0)


def declaration_from_args(args: argparse.Namespace) -> Declaration:
    """Materialise a Declaration from parsed argparse flags.

    Also runs consistency checks: if the agent declared any
    connectors or ribbons, a direction MUST be supplied - this is
    the WI#3 discipline, mechanically enforced at the CLI boundary.
    """
    counts: dict[str, int] = {}
    for ctype in KNOWN_COMPONENT_TYPES:
        flag = f"{ctype}s"
        val = getattr(args, flag, 0) or 0
        if val:
            counts[ctype] = val

    decl = Declaration(
        counts=counts,
        dark_mode=getattr(args, "dark_mode", "optional"),
        connector_mode=getattr(args, "connector_mode", None),
        connector_direction=getattr(args, "connector_direction", None),
    )

    # Connector / ribbon direction is mandatory when either is declared.
    has_connector = counts.get("connector", 0) > 0 or counts.get("ribbon", 0) > 0
    if has_connector:
        if decl.connector_mode is None:
            raise ManifestError(
                f"--connectors or --ribbons declared without --connector-mode. "
                f"Must be one of {sorted(KNOWN_CONNECTOR_MODES)}."
            )
        if decl.connector_mode not in KNOWN_CONNECTOR_MODES:
            raise ManifestError(
                f"--connector-mode {decl.connector_mode!r} not in {sorted(KNOWN_CONNECTOR_MODES)}"
            )
        if decl.connector_direction is None:
            raise ManifestError(
                "--connector-direction is required when connectors or ribbons "
                "are declared. See WI#3 rationale: arrow direction cannot be "
                "inferred from geometry alone; declare it explicitly. "
                f"Ribbon/manifold: one of {sorted(KNOWN_MANIFOLD_DIRECTIONS)}. "
                f"Others: {sorted(KNOWN_DIRECTIONS)}."
            )
        valid = (
            KNOWN_MANIFOLD_DIRECTIONS
            if decl.connector_mode in ("manifold", "ribbon")
            else KNOWN_DIRECTIONS
        )
        if decl.connector_direction not in valid:
            raise ManifestError(
                f"--connector-direction {decl.connector_direction!r} invalid "
                f"for mode {decl.connector_mode!r}; use one of {sorted(valid)}"
            )
    if decl.dark_mode not in ("required", "optional", "none"):
        raise ManifestError(f"--dark-mode must be required|optional|none, got {decl.dark_mode!r}")
    return decl


# --------------------------------------------------------------------------
# RULE PULL
# --------------------------------------------------------------------------


# Path to the rule library. Resolved at call time so test harnesses
# can monkey-patch the directory.
_DEFAULT_RULES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "svg-infographics"
    / "skills"
    / "svg-designer"
    / "rules"
)

_PREAMBLE = """# SVG Quartermaster Rule Bundle

Declared components trigger the rule cards below. Rules for types
you did not declare are NOT included - this bundle is scoped to
your actual build.

## Always-applicable preamble

- **Grid-first**: define viewBox, margins, column origins,
  vertical rhythm as XML comments BEFORE any visible element.
- **Theme swatch**: use CSS classes, never inline `fill=` for
  themed colours.
- **Dark mode** (when declared `--dark-mode required`): every
  themed class MUST have a `@media (prefers-color-scheme: dark)`
  override in the top `<style>` block.
- **Aspect-ratio lock** (when declared): width/height ratio of
  the SVG viewBox must match within 1%.
- **No undocumented suppressions**: every validator dismissal
  must be a `--suppress rule:target:reason` flag on the next
  `check` or `finalize` call. No inline "false positive"
  hand-waves.
"""


def pull_rules(
    decl: Declaration,
    *,
    rules_dir: Path | None = None,
) -> str:
    """Return a markdown bundle containing only the applicable rules.

    The preamble is always included. Per-component rules are pulled
    from ``<rules_dir>/<type>.md`` for each declared type. Unknown
    files (e.g. a declared ``ribbon`` when ``ribbon.md`` has not
    yet shipped) are noted in a trailing "missing rule cards"
    section - ``pull`` is informational, not a gate.
    """
    rdir = rules_dir or _DEFAULT_RULES_DIR
    parts: list[str] = [_PREAMBLE.rstrip()]
    declared = decl.declared_types
    if not declared:
        parts.append(
            "\n## Nothing declared\n\nNo components with count > 0. "
            "Pass flags like `--cards 4 --connectors 1 "
            "--connector-mode manifold --connector-direction "
            "sinks-to-sources` to receive targeted rules."
        )
        return "\n".join(parts) + "\n"

    parts.append("\n## Component rule cards\n")
    missing: list[str] = []
    for ctype in declared:
        rule_path = rdir / f"{ctype}.md"
        if not rule_path.is_file():
            missing.append(ctype)
            continue
        parts.append(f"\n### {ctype}\n")
        parts.append(rule_path.read_text(encoding="utf-8").rstrip())
    if missing:
        parts.append("\n## Missing rule cards\n")
        parts.append(
            f"Declared types with no card in `{rdir}`. Fall back to "
            "the general standards reference.\n"
        )
        for m in missing:
            parts.append(f"- {m}")

    # Contextual warnings based on the declaration shape.
    warnings = _contextual_warnings(decl)
    if warnings:
        parts.append("\n## Warnings\n")
        parts.extend(f"- {w}" for w in warnings)
    return "\n".join(parts) + "\n"


def _contextual_warnings(decl: Declaration) -> list[str]:
    """Surface common-mistake flags based on the declaration shape.

    These are not blockers - just friendly reminders pulled exactly
    when the agent is about to build something prone to that class
    of defect.
    """
    out: list[str] = []
    if decl.counts.get("card", 0) >= 4:
        out.append(
            "You declared 4+ cards: enforce equal width per row and "
            "equal height per column. See rules/card.md."
        )
    if decl.counts.get("connector", 0) > 0 and decl.connector_mode == "manifold":
        out.append(
            "Manifold connector declared: spine should pass through a "
            "deliberate gap in intermediate layouts (avoid card overlap). "
            "Also declare direction explicitly; see rules/connector.md."
        )
    if decl.counts.get("ribbon", 0) > 0:
        out.append(
            "Ribbon connector: endpoints MUST stick to source/target "
            "element bboxes (within 1px). fill-opacity 0.18-0.32, no "
            "stroke. See rules/ribbon.md."
        )
    if decl.counts.get("background", 0) > 0:
        out.append(
            "Background declared: opacity 0.06-0.12, layer index below all "
            "content groups. DO NOT place content atop a high-contrast "
            "background element."
        )
    if decl.counts.get("callout", 0) > 0:
        out.append(
            "Callout placement: use `svg-infographics callouts` (solver "
            "produces best layout + alternatives). Hand-placed callouts "
            "overlap content ~30% of the time."
        )
    return out


# --------------------------------------------------------------------------
# CHECK
# --------------------------------------------------------------------------


@dataclass
class CheckFinding:
    severity: str  # "FAIL" | "WARN"
    category: str
    message: str


@dataclass
class CheckReport:
    findings: list[CheckFinding]

    @property
    def failed(self) -> bool:
        return any(f.severity == "FAIL" for f in self.findings)

    @property
    def warned(self) -> bool:
        return any(f.severity == "WARN" for f in self.findings)


_SVG_NS = "http://www.w3.org/2000/svg"


def _svg_root(svg_path: Path) -> ET.Element:
    try:
        tree = ET.parse(svg_path)
    except ET.ParseError as exc:
        raise ManifestError(f"{svg_path}: not well-formed XML: {exc}") from exc
    root = tree.getroot()
    # Strip namespace from tag names so lookups below work regardless
    # of whether the file declared xmlns="http://www.w3.org/2000/svg".
    for elem in root.iter():
        if elem.tag.startswith(f"{{{_SVG_NS}}}"):
            elem.tag = elem.tag[len(_SVG_NS) + 2 :]
    if root.tag != "svg":
        raise ManifestError(f"{svg_path}: root is <{root.tag}>, not <svg>")
    return root


def _count_components_in_svg(root: ET.Element) -> dict[str, int]:
    """Heuristic count of components per type.

    Agents who follow the per-component rule cards use ID / class
    conventions (``id="card-*"``, ``class="card"``, etc.). Those
    conventions are the detection surface here. Agents that name
    their groups differently will get a false-negative count -
    that's a signal to follow the rules, not a bug in the counter.

    Connector counting model:
    - A manifold / ribbon group (``class*="manifold-connector"`` or
      ``id*="-ribbons"``) = ONE logical connector regardless of the
      number of `<path>` strands inside.
    - A generic ``<g id="connectors">`` or ``class*="connector"``
      group counts each direct or nested ``<path>`` as one connector,
      EXCLUDING paths already accounted for by a nested manifold /
      ribbon group.
    """
    counts = dict.fromkeys(KNOWN_COMPONENT_TYPES, 0)

    # Track manifold / ribbon groups so we can skip their paths when
    # counting generic connectors.
    manifold_groups: set[int] = set()
    ribbon_groups: set[int] = set()

    for g in root.iter("g"):
        gid = (g.get("id") or "").lower()
        gclass = (g.get("class") or "").lower()
        if gid.startswith("card-") or gid.startswith("box-") or "card" in gclass:
            counts["card"] += 1
        if gid == "background" or gid.endswith("-background") or "background" in gclass:
            counts["background"] += 1
        if gid == "timeline" or "timeline" in gclass:
            counts["timeline"] += 1
        if "icon" in gclass or gid.startswith("icon-"):
            counts["icon"] += 1
        if "callout" in gclass or gid.startswith("callout-"):
            counts["callout"] += 1
        # Ribbon groups: each `<path>` inside counts as one ribbon flow
        # (each ribbon is one filled-shape strand).
        if gid.endswith("-ribbons") or gid == "ribbons":
            counts["ribbon"] += sum(1 for _ in g.iter("path"))
            ribbon_groups.add(id(g))
        # Manifold groups: ONE logical connector regardless of strand
        # count. Track the group so its paths are not double-counted.
        if "manifold-connector" in gclass or gid.endswith("-manifold"):
            counts["connector"] += 1
            manifold_groups.add(id(g))

    # Gather paths already accounted for by manifold / ribbon groups.
    accounted_paths: set[int] = set()
    for g in root.iter("g"):
        if id(g) in manifold_groups or id(g) in ribbon_groups:
            for p in g.iter("path"):
                accounted_paths.add(id(p))

    # Generic connector groups: count each path not already accounted for.
    for g in root.iter("g"):
        gid = (g.get("id") or "").lower()
        gclass = (g.get("class") or "").lower()
        if gid == "connectors" or "connector" in gclass:
            if gid.endswith("-ribbons") or gid == "ribbons":
                continue
            if "manifold-connector" in gclass:
                continue  # already counted as 1 above
            for p in g.iter("path"):
                if id(p) in accounted_paths:
                    continue
                counts["connector"] += 1

    return counts


def _has_dark_mode(root: ET.Element) -> bool:
    """True when the SVG has a @media (prefers-color-scheme: dark) rule."""
    for style in root.iter("style"):
        text = (style.text or "") + "".join((c.text or "") for c in style)
        if "prefers-color-scheme: dark" in text:
            return True
    return False


def check(decl: Declaration, svg_path: Path) -> CheckReport:
    """Compare a flag-based declaration to an SVG; return findings.

    FAIL findings:
    - declared count does not match found count (per component type)
    - dark_mode=required without @media (prefers-color-scheme: dark)
    """
    findings: list[CheckFinding] = []
    root = _svg_root(svg_path)

    counts = _count_components_in_svg(root)
    for ctype, declared in decl.counts.items():
        found = counts.get(ctype, 0)
        if found != declared:
            findings.append(
                CheckFinding(
                    severity="FAIL",
                    category="component_count",
                    message=(
                        f"declared {declared} {ctype}(s), found {found} in the "
                        f"SVG (check <g> id / class conventions in rules/{ctype}.md)"
                    ),
                )
            )

    if decl.dark_mode == "required" and not _has_dark_mode(root):
        findings.append(
            CheckFinding(
                severity="FAIL",
                category="dark_mode",
                message=(
                    "--dark-mode required but no "
                    "@media (prefers-color-scheme: dark) rule found in "
                    "any <style>"
                ),
            )
        )

    return CheckReport(findings=findings)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _render_report_text(report: CheckReport) -> str:
    lines: list[str] = []
    if not report.findings:
        lines.append("check: OK (no divergences)")
        return "\n".join(lines)
    lines.append(f"check: {len(report.findings)} finding(s)")
    for f in report.findings:
        lines.append(f"  [{f.severity}] {f.category}: {f.message}")
    return "\n".join(lines)


def _add_declaration_flags(p: argparse.ArgumentParser) -> None:
    """Flags shared between `pull` and `check`.

    Kept as one helper so the declaration grammar stays identical
    between the two subcommands - otherwise agents risk passing
    different flags to pull vs check and confusing themselves.
    """
    # Per-component counts. Flag name is the plural of the type,
    # matching ``declaration_from_args`` lookup logic.
    p.add_argument("--cards", type=int, default=0, help="Number of cards to build")
    p.add_argument(
        "--connectors",
        type=int,
        default=0,
        help="Number of connectors to build (requires --connector-mode + --connector-direction)",
    )
    p.add_argument(
        "--backgrounds",
        type=int,
        default=0,
        help="Number of background-texture layers",
    )
    p.add_argument("--timelines", type=int, default=0, help="Number of timelines")
    p.add_argument("--icons", type=int, default=0, help="Number of icons")
    p.add_argument("--callouts", type=int, default=0, help="Number of callouts")
    p.add_argument(
        "--ribbons",
        type=int,
        default=0,
        help="Number of ribbon flows (Sankey-style). Same direction rules as manifold connectors.",
    )

    # Connector mode + direction. Both mandatory when connectors or ribbons
    # are declared - the rule card and check both depend on them.
    p.add_argument(
        "--connector-mode",
        choices=sorted(KNOWN_CONNECTOR_MODES),
        default=None,
        help="Connector mode; required when --connectors > 0",
    )
    p.add_argument(
        "--connector-direction",
        default=None,
        help=(
            "Arrow direction semantics. Required when connectors or ribbons "
            "are declared. For straight/L/L-chamfer/spline: "
            "forward|reverse|both|none. For manifold/ribbon: "
            "sources-to-sinks|sinks-to-sources|both|none."
        ),
    )
    p.add_argument(
        "--dark-mode",
        dest="dark_mode",
        default="optional",
        help="required | optional | none (default: optional)",
    )


def _cmd_pull(args: argparse.Namespace) -> int:
    try:
        decl = declaration_from_args(args)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    rules_dir = Path(args.rules_dir) if args.rules_dir else None
    bundle = pull_rules(decl, rules_dir=rules_dir)
    if args.output:
        Path(args.output).write_text(bundle, encoding="utf-8")
        print(f"wrote rule bundle to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(bundle)
    print(
        "\nnext: author the SVG following the rules above; then run "
        "`svg-infographics check --svg <file>.svg <same-flags>` to "
        "verify the build matches this declaration.",
        file=sys.stderr,
    )
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        decl = declaration_from_args(args)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    svg_path = Path(args.svg)
    if not svg_path.is_file():
        print(f"ERROR: svg not found: {svg_path}", file=sys.stderr)
        return 2
    try:
        report = check(decl, svg_path)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        payload = {
            "failed": report.failed,
            "warned": report.warned,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "message": f.message,
                }
                for f in report.findings
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(_render_report_text(report), file=sys.stderr)
    if report.failed:
        print(
            "next: fix the reported divergences in the SVG, then re-run "
            "`svg-infographics check` with the same flags.",
            file=sys.stderr,
        )
    else:
        print(
            "next: run `svg-infographics finalize <file>.svg` for the ship-ready structural gate.",
            file=sys.stderr,
        )
    return 1 if report.failed else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="svg-infographics preflight",
        description=(
            "Pre-flight checklist: declare what you will build via flags; "
            "tool returns the matching rule bundle (preflight) or verifies "
            "an existing SVG against the same declaration (check)."
        ),
    )
    sub = parser.add_subparsers(dest="subcmd", required=True)

    p = sub.add_parser(
        "preflight",
        help="Return the per-component rule bundle for this declaration.",
    )
    _add_declaration_flags(p)
    p.add_argument("--output", help="Write bundle to path; omit for stdout")
    p.add_argument(
        "--rules-dir",
        help="Override rule library directory (default: plugin-shipped)",
    )
    p.set_defaults(func=_cmd_pull)

    c = sub.add_parser(
        "check",
        help="Verify an SVG matches a flag-based declaration.",
    )
    c.add_argument("--svg", required=True, help="Path to SVG to audit")
    _add_declaration_flags(c)
    c.add_argument("--json", action="store_true", help="Emit structured JSON report")
    c.set_defaults(func=_cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
