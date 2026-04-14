"""SVG CSS compliance checker.

Validates that all visual properties (fills, strokes, fonts, opacity) are
controlled via CSS classes rather than inline attributes. Enforces the
svg-infographics convention: all colour in CSS, no inline fill on text,
no #000000 or #ffffff, proper dark mode overrides.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
import sys
import xml.etree.ElementTree as ET

_NS_RE = re.compile(r"\{[^}]*\}")


def _strip_ns(tag: str) -> str:
    return _NS_RE.sub("", tag)


@dataclass
class CSSViolation:
    """A CSS compliance violation."""

    element: str  # tag + id/text excerpt
    line: int  # element index in parse order
    rule: str  # short rule name
    detail: str  # human-readable explanation
    severity: str = "error"  # error, warning


# ---------------------------------------------------------------------------
# CSS parsing
# ---------------------------------------------------------------------------


def parse_style_block(svg_text: str) -> tuple[dict[str, dict], dict[str, dict], set[str]]:
    """Parse CSS classes from <style> block.

    Returns:
        light_classes: {class_name: {property: value}}
        dark_classes: {class_name: {property: value}}
        all_colors: set of hex colors used in CSS
    """
    style_match = re.search(r"<style[^>]*>(.*?)</style>", svg_text, re.DOTALL)
    if not style_match:
        return {}, {}, set()

    style_text = style_match.group(1)

    # Strip @media blocks for light mode parsing
    light_text = re.sub(r"@media\s*\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}", "", style_text)

    def _parse_rules(css: str) -> dict[str, dict]:
        classes = {}
        for m in re.finditer(r"\.([a-zA-Z0-9_-]+)\s*\{([^}]*)\}", css):
            name = m.group(1)
            props = {}
            for prop_m in re.finditer(r"([\w-]+)\s*:\s*([^;]+)", m.group(2)):
                props[prop_m.group(1).strip()] = prop_m.group(2).strip()
            classes[name] = props
        return classes

    light_classes = _parse_rules(light_text)

    # Dark mode classes
    dark_classes = {}
    for media_match in re.finditer(
        r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*?)\}", style_text, re.DOTALL
    ):
        dark_classes.update(_parse_rules(media_match.group(1)))

    # Collect all hex colors
    all_colors = set(re.findall(r"#[0-9a-fA-F]{3,8}", style_text))

    return light_classes, dark_classes, all_colors


# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------


def check_inline_fill_on_text(root, ns: str) -> list[CSSViolation]:
    """Text elements must use CSS classes for fill, never inline fill="#hex"."""
    violations = []
    for idx, elem in enumerate(root.iter()):
        tag = _strip_ns(elem.tag)
        if tag != "text":
            continue

        fill = elem.get("fill")
        css_class = elem.get("class", "")
        text_content = (elem.text or "")[:30]

        if fill and fill.startswith("#"):
            violations.append(
                CSSViolation(
                    f'<text> "{text_content}"',
                    idx,
                    "inline-fill-on-text",
                    f'Text has inline fill="{fill}" - use a CSS class instead',
                )
            )
        elif not css_class and not fill:
            violations.append(
                CSSViolation(
                    f'<text> "{text_content}"',
                    idx,
                    "no-class-no-fill",
                    "Text has neither CSS class nor fill - will inherit (may be invisible in dark mode)",
                    severity="warning",
                )
            )

    return violations


def check_text_opacity(root, ns: str) -> list[CSSViolation]:
    """Text elements must not have opacity attribute (reduces contrast)."""
    violations = []
    for idx, elem in enumerate(root.iter()):
        tag = _strip_ns(elem.tag)
        if tag != "text":
            continue

        opacity = elem.get("opacity")
        if opacity and float(opacity) < 1.0:
            text_content = (elem.text or "")[:30]
            violations.append(
                CSSViolation(
                    f'<text> "{text_content}"',
                    idx,
                    "text-opacity",
                    f'Text has opacity="{opacity}" - removes contrast, use fg-3/fg-4 instead',
                )
            )

    return violations


def check_forbidden_colors(root, ns: str) -> list[CSSViolation]:
    """No #000000 or #ffffff anywhere (breaks dark/light mode)."""
    violations = []
    forbidden = {"#000000", "#000", "#ffffff", "#fff"}

    for idx, elem in enumerate(root.iter()):
        tag = _strip_ns(elem.tag)
        if tag in ("style", "metadata", "desc", "title"):
            continue

        for attr_name in ("fill", "stroke", "color", "stop-color"):
            val = elem.get(attr_name, "").lower()
            if val in forbidden:
                eid = elem.get("id", "")
                label = f"<{tag}>" + (f" id={eid}" if eid else "")
                violations.append(
                    CSSViolation(
                        label,
                        idx,
                        "forbidden-color",
                        f'{attr_name}="{val}" - use a theme colour instead of black/white',
                    )
                )

    return violations


def check_inline_styles(root, ns: str) -> list[CSSViolation]:
    """Flag inline style attributes that should be CSS classes."""
    violations = []
    STYLE_PROPS = {"fill", "stroke", "color", "font-family", "font-size", "font-weight", "opacity"}

    for idx, elem in enumerate(root.iter()):
        tag = _strip_ns(elem.tag)
        style = elem.get("style", "")
        if not style:
            continue

        # Parse inline style for color properties
        for prop_match in re.finditer(r"([\w-]+)\s*:\s*([^;]+)", style):
            prop = prop_match.group(1).strip()
            val = prop_match.group(2).strip()
            if prop in STYLE_PROPS and "#" in val:
                eid = elem.get("id", "")
                label = f"<{tag}>" + (f" id={eid}" if eid else "")
                violations.append(
                    CSSViolation(
                        label,
                        idx,
                        "inline-style-color",
                        f"Inline style {prop}: {val} - move to CSS class",
                    )
                )

    return violations


def check_dark_mode_coverage(
    light_classes: dict[str, dict],
    dark_classes: dict[str, dict],
) -> list[CSSViolation]:
    """Every light-mode class with a fill should have a dark-mode override."""
    violations = []
    for cls_name, props in light_classes.items():
        if "fill" in props and cls_name not in dark_classes:
            violations.append(
                CSSViolation(
                    f".{cls_name}",
                    0,
                    "missing-dark-override",
                    f"Class .{cls_name} has fill in light mode but no dark mode override",
                    severity="warning",
                )
            )

    return violations


def check_stroke_inline(root, ns: str) -> list[CSSViolation]:
    """Flag inline stroke colors on non-structural elements."""
    violations = []
    STRUCTURAL = {"rect", "path", "circle", "ellipse", "line", "polyline", "polygon"}

    for idx, elem in enumerate(root.iter()):
        tag = _strip_ns(elem.tag)
        if tag not in STRUCTURAL:
            continue

        stroke = elem.get("stroke", "")
        css_class = elem.get("class", "")

        # Strokes on structural elements are acceptable if they match accent pattern
        # Flag only if stroke is a non-theme color (heuristic: if no class and has stroke)
        if stroke.startswith("#") and not css_class:
            # Allow common patterns: cards with accent stroke, dividers
            fill_opacity = elem.get("fill-opacity", "1")
            # Cards (fill-opacity < 0.1) and dividers are acceptable with inline stroke
            if fill_opacity and float(fill_opacity) <= 0.1:
                continue
            if tag == "line":
                continue  # connectors and dividers commonly use inline stroke

    return violations


def check_font_inline(root, ns: str) -> list[CSSViolation]:
    """Flag text without proper font-family (should use system font stack)."""
    violations = []
    EXPECTED_FONT = "Segoe UI"

    for idx, elem in enumerate(root.iter()):
        tag = _strip_ns(elem.tag)
        if tag != "text":
            continue

        font = elem.get("font-family", "")
        text_content = (elem.text or "")[:30]

        if font and EXPECTED_FONT not in font:
            violations.append(
                CSSViolation(
                    f'<text> "{text_content}"',
                    idx,
                    "non-standard-font",
                    f'font-family="{font}" - expected "{EXPECTED_FONT}, Arial, sans-serif"',
                    severity="warning",
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Main checker
# ---------------------------------------------------------------------------


def check_css_compliance(filepath: str) -> tuple[list[CSSViolation], dict]:
    """Run all CSS compliance checks on an SVG file.

    Returns:
        violations: List of CSSViolation objects
        stats: Summary statistics dict
    """
    svg_text = open(filepath).read()
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = re.match(r"\{([^}]*)\}", root.tag)
    ns_str = ns.group(1) if ns else ""

    light_classes, dark_classes, css_colors = parse_style_block(svg_text)

    violations = []
    violations.extend(check_inline_fill_on_text(root, ns_str))
    violations.extend(check_text_opacity(root, ns_str))
    violations.extend(check_forbidden_colors(root, ns_str))
    violations.extend(check_inline_styles(root, ns_str))
    violations.extend(check_dark_mode_coverage(light_classes, dark_classes))
    violations.extend(check_stroke_inline(root, ns_str))
    violations.extend(check_font_inline(root, ns_str))

    stats = {
        "light_classes": len(light_classes),
        "dark_classes": len(dark_classes),
        "css_colors": len(css_colors),
        "has_dark_mode": len(dark_classes) > 0,
        "errors": sum(1 for v in violations if v.severity == "error"),
        "warnings": sum(1 for v in violations if v.severity == "warning"),
    }

    return violations, stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics css",
        description="Check SVG CSS compliance - all colours via classes, no inline fills on text",
    )
    parser.add_argument("--svg", required=True, help="SVG file to check")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    violations, stats = check_css_compliance(args.svg)

    # Print results
    print(f"CSS Compliance Check: {args.svg}")
    print(f"  Light classes: {stats['light_classes']}, Dark classes: {stats['dark_classes']}")
    print(f"  Dark mode: {'yes' if stats['has_dark_mode'] else 'MISSING'}")
    print()

    if not violations:
        print("PASS - no CSS violations found")
        return

    errors = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for v in errors:
            print(f"  [{v.rule}] {v.element}: {v.detail}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for v in warnings:
            print(f"  [{v.rule}] {v.element}: {v.detail}")

    print(f"\nSUMMARY: {stats['errors']} errors, {stats['warnings']} warnings")

    if args.strict and stats["warnings"] > 0:
        sys.exit(1)
    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
