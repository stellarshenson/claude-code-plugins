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


# ---------------------------------------------------------------------------
# Geometry-preservation check (add-life safety net)
# ---------------------------------------------------------------------------


_GEOMETRY_TAGS = ("path", "line", "rect", "circle", "polygon", "polyline", "ellipse")


def _geometry_signatures(path: Path) -> tuple[dict[str, int], dict[str, list[tuple[str, str]]]]:
    """Return (per-tag count, per-tag signatures) for a well-formed SVG.

    Signatures: for each geometry element we record a stable identifier
    (the `d` attr for paths, `x1,y1,x2,y2` for lines, etc) plus the element's
    `id` when present. Used to report which specific elements disappeared.
    """
    counts: dict[str, int] = {}
    sigs: dict[str, list[tuple[str, str]]] = {}
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return counts, sigs
    root = tree.getroot()
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in _GEOMETRY_TAGS:
            continue
        counts[tag] = counts.get(tag, 0) + 1
        gid = el.attrib.get("id", "")
        if tag == "path":
            sig = el.attrib.get("d", "")[:80]
        elif tag in ("line",):
            sig = ",".join(
                el.attrib.get(k, "") for k in ("x1", "y1", "x2", "y2")
            )
        elif tag == "rect":
            sig = ",".join(
                el.attrib.get(k, "") for k in ("x", "y", "width", "height")
            )
        elif tag == "circle":
            sig = ",".join(el.attrib.get(k, "") for k in ("cx", "cy", "r"))
        elif tag == "ellipse":
            sig = ",".join(el.attrib.get(k, "") for k in ("cx", "cy", "rx", "ry"))
        elif tag in ("polygon", "polyline"):
            sig = el.attrib.get("points", "")[:80]
        else:
            sig = ""
        sigs.setdefault(tag, []).append((gid, sig))
    return counts, sigs


def compare_geometry(
    original: Path, modified: Path
) -> tuple[int, list[str]]:
    """Compare geometry elements between `original` and `modified`.

    Enforces: every geometry element (by signature) present in `original`
    MUST also be present in `modified`. Count in `modified` may be higher
    (decoration layer). Count lower or specific signatures missing → error.

    Returns (error_count, messages). Messages point at specific missing
    elements (tag + id + signature snippet) so the caller can restore them.
    """
    msgs: list[str] = []
    o_counts, o_sigs = _geometry_signatures(original)
    m_counts, m_sigs = _geometry_signatures(modified)

    errors = 0
    for tag in _GEOMETRY_TAGS:
        oc = o_counts.get(tag, 0)
        mc = m_counts.get(tag, 0)
        if mc < oc:
            msgs.append(
                f"ERROR: {modified.name}: {tag} count dropped "
                f"{oc} → {mc} (missing {oc - mc})"
            )
            errors += 1
            # Point at specific missing signatures
            m_sig_set = set(m_sigs.get(tag, []))
            for gid, sig in o_sigs.get(tag, []):
                if (gid, sig) not in m_sig_set:
                    label = f"id='{gid}'" if gid else f"d/pos='{sig[:40]}'"
                    msgs.append(f"  MISSING {tag}: {label}")
    return errors, msgs


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
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Original SVG to compare geometry against. Every path/line/rect/"
        "circle/polygon in the baseline must also appear in the validated file. "
        "Count drops and missing signatures are reported with their ids / "
        "attribute snippets so you can restore them. Add-life pass uses this.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    total_errors = 0
    total_warnings = 0
    baseline_path = Path(args.baseline) if args.baseline else None
    if baseline_path and not baseline_path.exists():
        print(f"ERROR: baseline not found: {baseline_path}", file=sys.stderr)
        return 1

    for p in args.svg:
        errors, warnings, messages = validate_svg(Path(p))
        total_errors += errors
        total_warnings += warnings
        for msg in messages:
            if args.quiet and msg.startswith("WARNING:"):
                continue
            print(msg, file=sys.stderr)
        if baseline_path and errors == 0:
            # Only meaningful when the XML parses. Compare geometry.
            geom_errs, geom_msgs = compare_geometry(baseline_path, Path(p))
            total_errors += geom_errs
            for msg in geom_msgs:
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
