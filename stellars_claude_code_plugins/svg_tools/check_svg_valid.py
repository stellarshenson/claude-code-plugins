"""Final SVG well-formedness + structural sanity validator.

Runs four quick checks on a finished SVG so Claude can gate its output:

1. **XML well-formedness** via ElementTree.parse - catches unbalanced tags,
   `--` inside comments (the #1 cause of "17 is broken"), stray ampersands,
   bad entity references. Reports line/column of the first parse failure.
2. **SVG root** - top-level element must be an <svg>.
3. **viewBox** - warns if the root SVG has no viewBox (breaks responsive scaling).
4. **Empty path d attributes** - paths with no `d` or `d=""` are silent bugs.

This is the "final gate" validator: run it LAST on every SVG before delivery.
Non-zero exit code on any hard failure (XML parse error or missing <svg> root).
Warnings alone return zero; they print to stderr so CI captures them.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"


def _iter_elements(root):
    """Walk the tree including the root itself."""
    yield root
    for el in root.iter():
        if el is not root:
            yield el


def validate_svg(path: Path) -> tuple[int, int, list[str]]:
    """Validate one SVG file.

    Returns (error_count, warning_count, messages). `messages` is a list of
    human-readable strings tagged "ERROR: ..." or "WARNING: ..." so callers
    can just print them.
    """
    messages: list[str] = []
    errors = 0
    warnings = 0

    if not path.exists():
        messages.append(f"ERROR: {path}: file does not exist")
        return 1, 0, messages

    try:
        raw = path.read_bytes()
    except OSError as exc:
        messages.append(f"ERROR: {path}: cannot read ({exc})")
        return 1, 0, messages

    # 1. XML well-formedness
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        # Rewrite the error slightly to surface the "-- inside comment" case
        # that bites repeatedly when copying CLI command lines into comments.
        text = str(exc)
        if "Comment" in text or "double-dash" in text.lower():
            messages.append(
                f"ERROR: {path}: XML parse failed - {text}. "
                f"A '--' inside an <!-- ... --> comment is ILLEGAL. "
                f"Replace 'cmd --flag' with 'cmd flag=...' or reword the comment."
            )
        else:
            messages.append(f"ERROR: {path}: XML parse failed - {text}")
        return 1, 0, messages

    # 2. Root must be <svg>
    if not root.tag.endswith("svg"):
        messages.append(f"ERROR: {path}: root element is <{root.tag}>, expected <svg>")
        errors += 1

    # 3. viewBox present on root
    if "viewBox" not in root.attrib:
        messages.append(
            f"WARNING: {path}: root <svg> has no viewBox attribute; "
            f"responsive scaling will be broken."
        )
        warnings += 1

    # 4. Empty path d attributes
    empty_paths = 0
    for el in _iter_elements(root):
        tag = el.tag.rsplit("}", 1)[-1]  # strip namespace
        if tag == "path":
            d = el.attrib.get("d", "").strip()
            if not d:
                empty_paths += 1
    if empty_paths:
        messages.append(
            f"WARNING: {path}: {empty_paths} <path> element(s) have empty "
            f"or missing 'd' attribute."
        )
        warnings += 1

    return errors, warnings, messages


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="svg-infographics validate",
        description=(
            "VALIDATE: XML well-formedness + SVG structural sanity. "
            "Run this LAST on every finished SVG. Catches 'double-dash in "
            "comment' bugs that silently break the file."
        ),
    )
    parser.add_argument(
        "svg",
        nargs="+",
        help="One or more SVG files to validate.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress WARNING lines; only print ERROR messages and exit code.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    total_errors = 0
    total_warnings = 0
    for p in args.svg:
        errors, warnings, messages = validate_svg(Path(p))
        total_errors += errors
        total_warnings += warnings
        for msg in messages:
            if args.quiet and msg.startswith("WARNING:"):
                continue
            # ERRORs go to stderr, WARNINGs to stderr, summary to stdout
            print(msg, file=sys.stderr)
    if total_errors == 0 and total_warnings == 0:
        print(f"OK: {len(args.svg)} file(s) validated, no issues.")
    else:
        print(
            f"{'FAIL' if total_errors else 'OK'}: "
            f"{total_errors} error(s), {total_warnings} warning(s) "
            f"across {len(args.svg)} file(s)."
        )
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
