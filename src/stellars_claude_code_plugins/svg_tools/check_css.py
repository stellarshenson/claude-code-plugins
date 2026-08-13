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
from typing import NamedTuple
import xml.etree.ElementTree as ET

from stellars_claude_code_plugins.svg_tools._layers import (
    BACKPLATE_ORIGIN_TOL,
    is_backplate_geometry,
)

# One CSS declaration. Shared by the rule-body parser, the cascade's inline
# `style=` reader and the two checkers that scan `style=` - four copies of the
# same pattern was four places to widen when a spelling was missed.
_DECL_RE = re.compile(r"([\w-]+)\s*:\s*([^;]+)")

# The paints this module has rules about, in one place: the tuple was spelled
# three times inside `check_forbidden_colors` alone.
_PAINT_PROPS = ("fill", "stroke", "color", "stop-color")


def _strip_ns(tag: str) -> str:
    # `{ns}tag` -> `tag`. Called ~70k times over the corpus, so the split beats
    # a regex substitution; both leave a namespace-free tag untouched.
    return tag.rsplit("}", 1)[-1]


def _element_id(elem) -> str:
    """What distinguishes this element from its siblings, or ``""``.

    The ack gate dedupes byte-identical finding text, so a finding that names
    only the tag collapses N defects into one line with one token: four white
    `<text>` fills became one `[W-…]` that a single pasted ack cleared. Text
    content first (that is what an author searches for), then id, class, and
    finally the coordinates every shape has.
    """
    parts = []
    text = (elem.text or "").strip()[:30]
    if text:
        parts.append(f'"{text}"')
    elif elem.get("id"):
        parts.append(f"id={elem.get('id')}")
    elif elem.get("class"):
        parts.append(f"class={elem.get('class')}")
    # Coordinates as well as the name, not instead of it: a deck repeats its
    # labels, and two `<text>` elements both reading "89%" collapse back into
    # one ack token on a name alone.
    x, y = elem.get("x") or elem.get("cx"), elem.get("y") or elem.get("cy")
    if x is not None and y is not None:
        parts.append(f"at {x},{y}")
    elif not parts:
        # A <path>/<polygon> carries neither name nor x/y; its geometry is the
        # only thing that tells two of them apart.
        geom = (elem.get("d") or elem.get("points") or "").strip()[:24]
        if geom:
            parts.append(f"at {geom}")
    return (" " + " ".join(parts)) if parts else ""


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


_DARK_QUERY_RE = re.compile(r"prefers-color-scheme\s*:\s*dark", re.I)


def strip_important(value: str | None) -> str:
    """A declaration value without its `!important` flag.

    The value regex captures the flag, and every consumer that compares the
    value - exact membership, `re.fullmatch`, `float()` - fails on it. Adding
    the strip per site left four paths behind, including the guide-grid
    exclusion; `charts.py` marks every colour it emits `!important`.
    """
    return re.sub(r"\s*!\s*important\s*$", "", str(value or ""), flags=re.I).strip()


def is_display_none(el) -> bool:
    """This element's own attribute or inline style hides it - one predicate.

    Three layers gate on the answer (colour scan, connector walk, overlaps
    model); when each kept its own copy the spellings diverged - a substring
    read hid `border-display:none` groups from one layer while another read
    them live, and `display:none !important` went the other way, so one
    element got two answers and the disagreement reached the HARD tier. The
    style side is declaration-precise and flag-stripped; the CLASS spelling
    (`.hidden{display:none}`) stays unresolved - the predicate holds no rules
    map.
    """
    return (el.get("display") or "").strip().lower() == "none" or any(
        m.group(1).strip().lower() == "display" and strip_important(m.group(2)).lower() == "none"
        for m in _DECL_RE.finditer(el.get("style") or "")
    )


def strip_xml_comments(svg_text: str) -> str:
    """Blank `<!-- … -->` spans, preserving length.

    The dark-block probe moved into the parser, but the parser's own input was
    still the whole file - so a `<style>` element commented out of the document
    was read as live CSS and the file reported a theme it does not have.
    """
    return re.sub(r"<!--.*?(?:-->|$)", lambda m: " " * len(m.group(0)), svg_text, flags=re.DOTALL)


def strip_css_comments(css: str) -> str:
    """Blank out `/* … */` while preserving offsets.

    Offsets matter: the @media spans are computed against this text and applied
    to it. Replacing each comment with spaces of equal length keeps every later
    index valid. A comment merely mentioning `@media` used to start a balanced
    scan inside it and swallow the following rule whole.
    """
    return re.sub(r"/\*.*?(?:\*/|$)", lambda m: " " * len(m.group(0)), css, flags=re.DOTALL)


def _media_blocks(
    style_text: str, top_level_only: bool = False
) -> list[tuple[str, str, int, int]]:
    """Extract @media blocks with balanced-brace scanning.

    Returns a list of (header, body, start, end) where header is the @media
    prelude (without the opening brace), body is everything between the
    balanced outer braces, and [start, end) spans the whole block in
    ``style_text``.

    ``top_level_only`` drops blocks nested inside another block. Removing
    overlapping spans from the light-mode text shifted the outer span's indices
    and truncated everything after it, so one nested query emptied the whole
    light stylesheet.
    """
    blocks: list[tuple[str, str, int, int]] = []
    for m in re.finditer(r"@media\s*[^{]*\{", style_text):
        depth = 1
        i = m.end()
        while i < len(style_text) and depth:
            if style_text[i] == "{":
                depth += 1
            elif style_text[i] == "}":
                depth -= 1
            i += 1
        if depth == 0:
            header = style_text[m.start() : m.end() - 1]
            body = style_text[m.end() : i - 1]
            blocks.append((header, body, m.start(), i))
    if top_level_only:
        blocks = [
            b
            for b in blocks
            if not any(o is not b and o[2] <= b[2] and b[3] <= o[3] for o in blocks)
        ]
    return blocks


def _split_selectors(selectors: str) -> list[str]:
    """Split a selector list on TOP-LEVEL commas only.

    `.ghost:is(.a, .b)` is one selector; splitting naively minted two phantom
    classes (one named `b)`) and lost the real one.
    """
    out, depth, cur = [], 0, ""
    for ch in selectors:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [s.strip() for s in out if s.strip()]


# Where each declaration sat in the stylesheet, stored inside the selector's own
# property dict as `{property: source offset}`. Equal-specificity rules are
# decided by source order, and nothing else in the parsed shape records it.
# The key cannot collide with a real property: the declaration regex below
# accepts `[\w-]+`, which can never contain `@`.
_SEQ = "@seq"


def parse_css_rules(css: str) -> dict[str, dict]:
    """Every rule in ``css`` as ``{selector: {property: value}}``.

    Selectors are normalised to their last simple component, so `.a, .b { }`
    registers BOTH `.a` and `.b`, `circle.dot` registers `.dot`, and element
    and id rules (`text { }`, `#plate { }`) register as `text` and `#plate`.
    Matching only `.name{` immediately before the brace dropped `.a` from a
    grouped selector entirely - and a dropped class is never checked for a dark
    override, never measured for inertness, and never scanned for #000/#fff.

    Each selector also carries a ``@seq`` entry - see ``_SEQ`` above.
    """
    rules: dict[str, dict] = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = m.group(1)
        # An @media prelude is not a selector; its body is scanned separately.
        if "@" in selectors:
            continue
        props: dict[str, str] = {}
        for prop_m in re.finditer(r"([\w-]+)\s*:\s*([^;]+)", m.group(2)):
            props[prop_m.group(1).strip()] = prop_m.group(2).strip()
        if not props:
            continue
        for sel in _split_selectors(selectors):
            # Drop functional-pseudo arguments first: the whitespace inside
            # `:is(.a, .b)` is not a descendant combinator, and splitting on it
            # keyed a rule as `.b)` - a class with a bracket in its name.
            sel = re.sub(r"\([^()]*\)", "", sel)
            # Last simple component: `g.card > rect.body` keys on `.body`.
            parts = re.split(r"[\s>+~]+", sel)
            last = parts[-1]
            # Drop a trailing attribute filter and any pseudo: `rect[x="y"]:hover`
            # is still a `rect` rule, and `.t:hover` is still `.t`.
            last = re.sub(r"\[[^\]]*\]", "", last)
            last = re.split(r"::?", last)[0]
            key = None
            if "." in last:
                key = "." + last.rsplit(".", 1)[-1]
            elif last.startswith("#"):
                key = last
            elif len(parts) == 1 and re.fullmatch(r"[a-zA-Z][\w-]*", last or ""):
                # Only a BARE element selector becomes an element rule. `.a b`
                # would otherwise register `b`, and the cascade would then paint
                # every <b> in the document from a descendant rule.
                key = last
            if not key:
                continue
            # Merge, do not replace. CSS cascades: a second rule for the same
            # selector adds to it. Replacing silently deleted properties that
            # were already seen - a regression the moment several <style> bodies
            # got concatenated, which is precisely the composed-deck case.
            entry = rules.setdefault(key, {})
            entry.update(props)
            # The match offset IS the source order; no counter to keep in sync.
            # The SELECTOR's start, not the match's: over a length-preserved
            # blanked sheet the `([^{}]+)` above swallows the leading blank run
            # into group(1), and `m.start()` then demotes the first rule after
            # a blanked span to the span's start - offset 0 for the first rule
            # of the document's first dark block, which lost every tie to light.
            sel_start = m.start() + (len(m.group(1)) - len(m.group(1).lstrip()))
            entry.setdefault(_SEQ, {}).update(dict.fromkeys(props, sel_start))
    return rules


def _opacity_value(raw: str | None) -> float | None:
    """An opacity declaration as a float, or None when it is not a number.

    One home for the `%`-or-unit-fraction parse that three call sites were
    each writing out again.
    """
    s = strip_important(raw)
    if not s:
        return None
    try:
        return float(s[:-1]) / 100.0 if s.endswith("%") else float(s)
    except ValueError:
        return None


def parse_style_block(
    svg_text: str,
) -> tuple[dict[str, dict], dict[str, dict], set[str], dict]:
    """Parse the CSS out of every ``<style>`` element.

    Returns:
        light_classes: {class_name: {property: value}}  (no leading dot)
        dark_classes:  {class_name: {property: value}}  (no leading dot)
        all_colors:    set of hex colours used in CSS
        meta:          {"has_dark_block", "light_rules", "dark_rules"} -
                       the rule maps keep their selector prefix (`.a`, `#b`,
                       `text`), so element and id rules are visible to callers
                       that need them. The two class dicts are the historical
                       contract and carry only class rules.

    ``has_dark_block`` is computed HERE, from the parsed media headers, so
    callers stop re-deriving it. A raw-text grep over the whole file counted a
    mention inside an XML comment - `theme_swatch_3_meridian.svg` has no
    ``<style>`` element at all and was reporting a dark block present.
    """
    empty_meta = {"has_dark_block": False, "light_rules": {}, "dark_rules": {}}
    # Every <style> element, not just the first - a composed deck carries one
    # per merged panel, and reading only the first sees a fraction of the CSS
    # while every downstream check reports its verdict as if it saw all of it.
    bodies = re.findall(r"<style[^>]*>(.*?)</style>", strip_xml_comments(svg_text), re.DOTALL)
    if not bodies:
        return {}, {}, set(), empty_meta

    style_text = strip_css_comments("\n".join(bodies))

    # Blank top-level @media blocks out of the light-mode text (balanced-brace
    # scan; regex cannot match nested rule braces reliably). BLANKED, not
    # spliced: splicing compressed every offset after a block, and the merged
    # sheet compares light `@seq` values against dark ones - two coordinate
    # spaces in one tie-break resolved cross-selector ties to the wrong class.
    light_chars = list(style_text)
    for _header, _body, start, end in _media_blocks(style_text, top_level_only=True):
        light_chars[start:end] = " " * (end - start)
    # The `rstrip` drops the trailing brace-free run, which is quadratic for the
    # rule regex to scan (measured 3s on a 20KB sheet ending in a media block);
    # every offset before it is preserved.
    light_rules = parse_css_rules("".join(light_chars).rstrip())

    # The dark sheet is parsed in ONE pass over the whole stylesheet, with every
    # non-dark span blanked out (length preserved). Parsing each @media body
    # separately restarted `@seq` at 0 per block, so offsets from two dark blocks
    # were compared as if they shared a coordinate space - and `.update()` on a
    # re-declared selector replaced its whole `@seq` map, defaulting the lost
    # properties to 0. On a composed deck (one <style> per merged panel, which is
    # exactly what this parser exists for) that picks the wrong declaration and
    # the file reports a dark ground it does not have.
    dark_chars = [" "] * len(style_text)
    has_dark_block = False
    for header, body, start, _end in _media_blocks(style_text):
        if not _DARK_QUERY_RE.search(header):
            continue
        has_dark_block = True
        body_start = start + len(header) + 1  # past the opening brace
        dark_chars[body_start : body_start + len(body)] = style_text[
            body_start : body_start + len(body)
        ]
    # Guarded: an all-blank string is the regex's worst case, and a single-theme
    # file has no dark rules to find in it.
    dark_rules = parse_css_rules("".join(dark_chars).rstrip()) if has_dark_block else {}

    def _classes(rules: dict[str, dict]) -> dict[str, dict]:
        return {k[1:]: v for k, v in rules.items() if k.startswith(".")}

    all_colors = set(re.findall(r"#[0-9a-fA-F]{3,8}", style_text))
    meta = {
        "has_dark_block": has_dark_block,
        "light_rules": light_rules,
        "dark_rules": dark_rules,
    }
    return _classes(light_rules), _classes(dark_rules), all_colors, meta


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
        if fill and fill.startswith("#"):
            violations.append(
                CSSViolation(
                    f"<text>{_element_id(elem)}",
                    idx,
                    "inline-fill-on-text",
                    f'Text has inline fill="{fill}" - use a CSS class instead',
                )
            )
        elif not css_class and not fill:
            violations.append(
                CSSViolation(
                    f"<text>{_element_id(elem)}",
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

        # `opacity`, `fill-opacity` and a `style="opacity:…"` all fade the glyph
        # identically; reading only the first left two spellings of one defect
        # passing a row named for forbidding it.
        style_attr = elem.get("style") or ""
        candidates = [
            (f'opacity="{elem.get("opacity")}"', elem.get("opacity")),
            (f'fill-opacity="{elem.get("fill-opacity")}"', elem.get("fill-opacity")),
        ]
        for m in re.finditer(r"(fill-opacity|opacity)\s*:\s*([^;]+)", style_attr):
            candidates.append((f'style="{m.group(1)}:{m.group(2).strip()}"', m.group(2)))
        for where, raw in candidates:
            value = _opacity_value(raw)
            if value is not None and value < 1.0:
                violations.append(
                    CSSViolation(
                        f"<text>{_element_id(elem)}",
                        idx,
                        "text-opacity",
                        f"Text has {where} - removes contrast, use fg-3/fg-4 instead",
                    )
                )
                break

    return violations


# Containers whose contents never paint a COLOUR. A full-canvas rect inside
# <mask>/<clipPath> is idiomatic ("show everything"), and white there is an
# alpha value, not a colour - judging it as paint is a false positive.
#
# <defs> is deliberately absent. Its contents do not render in place, but they
# render wherever they are referenced: a <marker> is drawn on the stroke that
# cites it, a <symbol> through <use>, a <pattern> as a tiled fill, a gradient
# <stop> as part of every fill that names it. Exempting the container hid a
# black arrowhead behind `[PASS] no #000/#fff` - and since markers are
# conventionally written inside <defs>, exempting <marker> and <defs> both is
# the same hole twice. Measured over the 71 shipped examples: zero new
# findings either way.
NONRENDER_TAGS = {"mask", "clippath"}

# Specificity of the declaration that wins, coarse but in the right order:
# an id selector beats a class, a class beats an element, and every author rule
# beats a presentation attribute.
_SPEC_STYLE, _SPEC_ID, _SPEC_CLASS, _SPEC_ELEMENT, _SPEC_ATTR = 1000, 100, 10, 1, 0

# `!important` outranks EVERYTHING, including an inline `style=`. The value is
# stripped before comparison (every consumer fails on the flag), so the rank has
# to carry the importance instead - otherwise a `.lbl{fill:#fff !important}`
# loses to `style="fill:#1e3a5f"`, and the checker reports 1.00:1 "invisible
# text" on a document that renders legibly.
_SPEC_IMPORTANT = 10_000
_IMPORTANT_RE = re.compile(r"!\s*important\s*$", re.I)


def _is_important(value: str | None) -> bool:
    return bool(_IMPORTANT_RE.search(str(value or "")))


# Properties SVG inherits from the parent chain. `stop-color` is deliberately
# absent - it is NOT inherited, and treating it as such would let a gradient's
# stops pick up the document's fill.
# Exactly the properties this package RESOLVES that SVG also inherits. `color`
# and the `font-*` family were dead weight - nothing queries them - while the
# three that decide whether a stroke is visible at all were absent, so an
# outline-only card under `<g stroke-width="2">` scored as having no stroke.
# `opacity` is deliberately NOT here: it composites through the tree rather than
# inheriting, and `_ancestor_opacity` is its answer. `fill-opacity` DOES inherit.
# `font-size` inherits but is absent too: its one consumer resolves it through
# `_font_size` (em/% compound against the parent), and leaving it here would hand
# any future caller the ancestor's RAW `1.2em` string.
_INHERITED_PROPS = {
    "fill",
    "stroke",
    "fill-opacity",
    "stroke-opacity",
    "stroke-width",
    "font-weight",
}


def build_render_model(root):
    """`(is_nonrendering, is_displaced, resolve_paint, winning_paint, parent_of, own_paint)`.

    ``is_nonrendering(node)`` - inside a non-rendering container or display:none.
    ``is_displaced(node)`` - that, or moved by a transform we do not resolve.
    ``resolve_paint(node, prop, rules)`` - the value that actually wins for
    ``prop``, by CSS specificity: an id rule beats a class rule beats an element
    rule beats the presentation attribute. Reading the attribute alone
    let a `fill="transparent"` left over from the scaffold hide a class that
    paints the plate near-white in both themes.

    ``parent_of`` is handed back rather than kept private because the ancestor
    walks outside this function need the same map, and rebuilding it there was
    a second full-tree pass over a document already walked.
    """
    parent_of = {id(child): parent for parent in root.iter() for child in parent}

    def is_nonrendering(node) -> bool:
        """Nothing this node paints reaches the canvas.

        `display:none` is read in its attribute and inline-`style=` spellings -
        the style spelling is what most authoring tools emit, and reading only
        the attribute scanned a hidden group as live paint (two false HARD per
        hidden text). The hidden test itself is the shared `is_display_none`
        predicate - per-layer copies diverged on the spellings, and the CLASS
        spelling (`.hidden{display:none}`) stays unresolved there: the
        predicate holds no rules map.
        """
        cur = node
        while cur is not None:
            # NOT _TEMPLATE_TAGS. This gates the COLOUR SCAN, and a black
            # marker inside <defs> is a real defect that must stay flagged; the
            # template exclusion belongs to the background election alone, where
            # `_in_template` already expresses it.
            hidden = is_display_none(cur)
            if _strip_ns(cur.tag).lower() in NONRENDER_TAGS or hidden:
                return True
            cur = parent_of.get(id(cur))
        return False

    def is_displaced(node) -> bool:
        """Its raw x/y are not where it renders. A geometry question only -
        folding it into the paint test exempted a quarter of the corpus's
        elements from the colour scan.

        A nested `<svg>` establishes a new viewport and a `<use>` instance
        renders wherever the reference sits; neither carries a `transform`, so a
        transform-only walk admitted their contents at raw coordinates. One
        shipped banner draws its logo in `<svg x="656" y="34" viewBox="0 0 560
        512">`, whose 280x512 rect was then elected as the ground for all four
        banner texts - eight HARD findings against a colour nothing sits on.
        """
        cur = node
        while cur is not None:
            if cur.get("transform"):
                return True
            # A NESTED <svg>, never the root - the root is every element's
            # ancestor, so matching on the tag alone declares the whole document
            # displaced.
            parent = parent_of.get(id(cur))
            if (
                parent is not None
                and parent is not root
                and _strip_ns(parent.tag).lower() in ("svg", "use")
            ):
                return True
            cur = parent
        return is_nonrendering(node)

    def own_paint(node, prop: str, rules: dict[str, dict]) -> tuple[int, str | None, str]:
        """What this node ITSELF declares for ``prop``, ignoring inheritance."""
        # An inline `style="fill:…"` outranks every author rule, and it was the
        # one spelling of "paint" the cascade could not see - so a plate written
        # that way read as no plate at all, and the roster said so about a
        # document that plainly had one.
        inline = None
        for m in _DECL_RE.finditer(node.get("style") or ""):
            if m.group(1).strip() == prop:
                inline = m.group(2)
        if inline is not None and _is_important(inline):
            return _SPEC_IMPORTANT, strip_important(inline), "style="
        # NOT an early return: a rule marked `!important` outranks an inline
        # style, so the rules below still have to be consulted. Returning here
        # made `_SPEC_IMPORTANT` unreachable for any node that also carried a
        # `style=` for the same property - the exact case its comment cites.
        nid = node.get("id")
        if nid and _is_important(rules.get(f"#{nid}", {}).get(prop)):
            return _SPEC_IMPORTANT, strip_important(rules[f"#{nid}"][prop]), f"#{nid}"
        # Every rule shape gets its importance test before an inline style can
        # win - `!important` outranks `style=` whatever declared it.
        # Two important class declarations of one property tie on importance AND
        # specificity; the tiebreak is SOURCE order, not the order the names
        # appear in the class attribute - the same rule the normal branch below
        # implements with `_SEQ`.
        best_i = None
        for cls_i in (node.get("class") or "").split():
            rule_i = rules.get(f".{cls_i}")
            if rule_i and _is_important(rule_i.get(prop)):
                seq_i = rule_i.get(_SEQ, {}).get(prop, 0)
                if best_i is None or seq_i >= best_i[0]:
                    best_i = (seq_i, rule_i[prop], f".{cls_i}")
        if best_i is not None:
            return _SPEC_IMPORTANT, strip_important(best_i[1]), best_i[2]
        _tag_i = _strip_ns(node.tag).lower()
        if _is_important(rules.get(_tag_i, {}).get(prop)):
            return _SPEC_IMPORTANT, strip_important(rules[_tag_i][prop]), _tag_i
        if inline is not None:
            return _SPEC_STYLE, strip_important(inline), "style="
        if nid and rules.get(f"#{nid}", {}).get(prop):
            # Importance already returned above; what remains is the plain id rule.
            return _SPEC_ID, strip_important(rules[f"#{nid}"][prop]), f"#{nid}"
        # Equal specificity is decided by SOURCE order, not by the order the
        # names happen to appear in the class attribute - `class="a b"` with
        # `.b` declared before `.a` paints from `.a`, and reading the attribute
        # right-to-left read the losing declaration.
        best = None
        for cls in (node.get("class") or "").split():
            rule = rules.get(f".{cls}")
            if rule and prop in rule:
                seq = rule.get(_SEQ, {}).get(prop, 0)
                if best is None or seq >= best[0]:
                    best = (seq, rule[prop], f".{cls}")
        if best is not None:
            return _SPEC_CLASS, strip_important(best[1]), best[2]
        tag = _strip_ns(node.tag).lower()
        tag_rule = rules.get(tag)
        if tag_rule and prop in tag_rule:
            return _SPEC_ELEMENT, strip_important(tag_rule[prop]), tag
        attr = node.get(prop)
        return _SPEC_ATTR, (strip_important(attr) if attr else None), f"<{tag}>"

    def winning_paint(node, prop: str, rules: dict[str, dict]) -> tuple[int, str | None, str]:
        """`(specificity, value, selector)` of the declaration that wins.

        The specificity is returned because a dark ``@media`` block only ADDS
        declarations - the light ones keep competing under the query - so a
        caller comparing the two themes has to know which side outranks the
        other rather than assuming the dark map wins by being the dark map.
        ``selector`` is the winner's own key, so a message can name the
        declaration it measured instead of guessing at the element's class list.

        INHERITED properties continue up the tree when the node itself declares
        nothing. `fill` is inherited in SVG, and `<g fill="…">` around a group of
        labels is the ordinary way to paint them: stopping at the node read 15 of
        one corpus file's 48 texts as unpainted, and read a plate wrapped in a
        painted `<g>` as no plate at all - a roster note claiming the document
        has no canvas-covering rect when it plainly has one.
        """
        spec, val, sel = own_paint(node, prop, rules)
        if val is not None or prop not in _INHERITED_PROPS:
            return spec, val, sel
        cur = parent_of.get(id(node))
        while cur is not None:
            spec, val, sel = own_paint(cur, prop, rules)
            if val is not None:
                return spec, val, sel
            cur = parent_of.get(id(cur))
        return _SPEC_ATTR, None, f"<{_strip_ns(node.tag).lower()}>"

    def resolve_paint(node, prop: str, rules: dict[str, dict]) -> str | None:
        return winning_paint(node, prop, rules)[1]

    return is_nonrendering, is_displaced, resolve_paint, winning_paint, parent_of, own_paint


class ThemePaint(NamedTuple):
    """What one property resolves to on one node in each theme.

    ``light`` / ``dark`` are raw declaration values, ``subject`` names the
    winning light selector, ``light_spec`` is its specificity (``_SPEC_ATTR``
    means nothing but a presentation attribute paints it, which no media query
    can reach), and ``overridden`` says whether the dark block displaced it.
    """

    light: str | None
    dark: str | None
    subject: str
    light_spec: int
    overridden: bool


def merged_rules(light_rules: dict[str, dict], dark_rules: dict[str, dict]) -> dict[str, dict]:
    """The sheet as it stands UNDER the dark query: light rules plus the dark
    block's additions, per selector.

    Resolving anything against `dark_rules` alone repeats, one level down, the
    error `theme_paint` exists to prevent. A gradient overridden in the dark
    block whose stops carry classes declared in the BASE sheet - the ordinary
    way to write it - resolved to nothing, and the plate was reported as having
    no dark value at all.
    """
    out = {}
    for sel in (*light_rules, *dark_rules):
        light, dark = light_rules.get(sel, {}), dark_rules.get(sel, {})
        merged = dict(light)
        landed = []
        l_seq, d_seq = light.get(_SEQ, {}), dark.get(_SEQ, {})
        for p, dv in dark.items():
            if p == _SEQ:
                continue
            lv = light.get(p)
            # A normal dark declaration displaces a normal light one (later
            # source order) but never a light `!important` - the dark block ADDS
            # declarations, and a plain merge would silently drop the ranking.
            # "Later" has to be true, not assumed: a light redeclaration AFTER
            # the media block wins the equal-specificity tie, and both offset
            # maps sit in the one original-text space, so the tie is decidable.
            # Source order only breaks a tie of EQUAL importance - a dark
            # `!important` outranks a later light normal declaration, and the
            # outer test already keeps a light `!important` over a dark normal.
            if lv is None or not (_is_important(lv) and not _is_important(dv)):
                if (
                    p in l_seq
                    and p in d_seq
                    and d_seq[p] < l_seq[p]
                    and _is_important(lv) == _is_important(dv)
                ):
                    continue
                merged[p] = dv
                landed.append(p)
        # `_SEQ` is itself a key in the property dict, so a plain merge replaced
        # the LIGHT source-order map wholesale - every property the dark block
        # left alone then tied at offset 0 and lost its equal-specificity
        # tiebreak. Merge the two offset maps per property instead, taking the
        # dark offset only for the declarations that actually landed.
        if _SEQ in light or _SEQ in dark:
            merged[_SEQ] = {
                **light.get(_SEQ, {}),
                **{p: d_seq[p] for p in landed if p in d_seq},
            }
        out[sel] = merged
    return out


def theme_paint(
    node, prop: str, light_rules, dark_rules, winning_paint, merged=None
) -> ThemePaint:
    """Resolve ``prop`` on ``node`` in both themes, through ONE cascade.

    A dark ``@media`` block ADDS declarations; it does not replace the
    stylesheet. The dark side is therefore resolved over the MERGED sheet
    (``merged_rules``), where the light rules keep competing under the query.
    Resolving against the dark map alone walks the ancestors with a different
    rule set and can stop at a DIFFERENT element than the light walk; comparing
    the two specificities then ranks declarations that never competed, and an
    ancestor's dark repaint read as overriding the node's own light paint.
    ``overridden`` is simply "the dark value differs from the light winner".
    Callers in a parse loop pass the hoisted ``merged`` map; building it per
    element is the R26 shape.

    Shared deliberately: the contrast layer had its own weaker copy of this
    (class-name lookup, attribute beating class, unresolved paint defaulting to
    black), and it gates the HARD tier - so the strictest verdicts in the gate
    were computed on the loosest model.
    """
    if merged is None:
        merged = merged_rules(light_rules, dark_rules)
    l_spec, l_raw, subject = winning_paint(node, prop, light_rules)
    _d_spec, d_raw, _d_sel = winning_paint(node, prop, merged)
    return ThemePaint(l_raw, d_raw, subject, l_spec, d_raw != l_raw)


# `url(#id)`, the only indirection either paint reader has to follow.
_URL_REF_RE = re.compile(r"url\(\s*#([^)\s]+)\s*\)", flags=re.I)

_LENGTH_RE = re.compile(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([a-z%]*)", flags=re.I)

# A dropped rect leaves no candidate and the row prints PASS, so every unit the
# spec allows is converted rather than discarded.
_UNIT_FACTORS = {
    "": 1.0,
    "px": 1.0,
    "em": 16.0,
    "rem": 16.0,
    "pt": 96 / 72,
    "pc": 16.0,
    "in": 96.0,
    "cm": 96 / 2.54,
    "mm": 96 / 25.4,
    # Half the `em` figure this table already assumes; `ex` is an SVG 1.1
    # length and a rect dropped for an unconvertible unit leaves no plate
    # candidate at all, which the roster then reports as "no canvas-covering
    # <rect>" about a document that has one.
    "ex": 8.0,
}


def _length(raw: str | None, span: float) -> float | None:
    """A dimension in user units - `400`, `400px`, `25em`, `100%`."""
    s = (raw or "").strip()
    if not s:
        return None
    if s.endswith("%"):
        try:
            return float(s[:-1]) / 100.0 * span
        except ValueError:
            return None
    m = _LENGTH_RE.fullmatch(s)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    unit = m.group(2).lower()
    return v * _UNIT_FACTORS[unit] if unit in _UNIT_FACTORS else None


def _gradient_stops(root, ref: str) -> list:
    """Every `<stop>` under the element `ref` names, `[]` when there is none.

    An empty list and a missing target mean the same thing to both callers -
    nothing measurable - so they are not distinguished.
    """
    target = next((el for el in root.iter() if el.get("id") == ref), None)
    if target is None:
        return []
    return [s for s in target.iter() if _strip_ns(s.tag).lower() == "stop"]


def _stop_prop(stop, prop: str, rules: dict[str, dict] | None) -> str | None:
    """A stop's declared `prop`, falling back to whatever its class declares."""
    v = stop.get(prop)
    if not v and rules:
        for cls in (stop.get("class") or "").split():
            if rules.get(f".{cls}", {}).get(prop):
                return rules[f".{cls}"][prop]
    return v


def paint_luma(value: str | None, root, rules: dict[str, dict]) -> float | None:
    """Luma of a paint value, resolving `url(#id)` to its gradient stops.

    A plate painted from a gradient of hardcoded stops cannot answer the media
    query, and treating it as merely unmeasurable printed PASS over it - while
    the tool's own remedy text told authors to move inline fills into exactly
    that construct.
    """
    v = (value or "").strip()
    m = _URL_REF_RE.fullmatch(v)
    if not m:
        return _luma255(v)
    lumas = []
    for s in _gradient_stops(root, m.group(1)):
        # A stop at `stop-opacity="0"` paints nothing, so averaging its colour
        # in invents a ground nobody sees: a dark plate fading out through a
        # pale stop measured 130/255 and was reported as "not dark enough"
        # against a visible #12181e. Alpha carried INSIDE the colour value is
        # already handled by `_luma255`; this is the sibling-attribute spelling.
        if _opacity_value(_stop_prop(s, "stop-opacity", rules)) == 0.0:
            continue
        lum = _luma255(_stop_prop(s, "stop-color", rules))
        if lum is not None:
            lumas.append(lum)
    return sum(lumas) / len(lumas) if lumas else None


def check_forbidden_colors(
    root,
    ns: str,
    light_rules: dict[str, dict] | None = None,
    dark_rules: dict[str, dict] | None = None,
) -> list[CSSViolation]:
    """No #000000 or #ffffff anywhere (breaks dark/light mode).

    "Anywhere" includes the ``<style>`` block. Reading only presentation
    attributes let ``.card { fill: #ffffff }`` through untouched - the exact
    declaration this rule exists to forbid, in the place the project tells
    authors to put their colours.
    """
    violations = []

    # Every rule shape, not just `.class` - `text { fill: #000 }` and
    # `#plate { fill: #fff }` are the same defect written differently.
    for scope, rules in (("light", light_rules or {}), ("dark", dark_rules or {})):
        where = "the base rules" if scope == "light" else "the dark block"
        for sel, props in rules.items():
            for prop in _PAINT_PROPS:
                val = strip_important(props.get(prop, ""))
                if _is_forbidden(val):
                    violations.append(
                        CSSViolation(
                            f"{sel} ({scope})",
                            0,
                            "forbidden-color",
                            f'{prop}="{val.strip()}" in {where} - use a theme '
                            f"colour instead of black/white",
                        )
                    )

    is_nonrendering, _displaced, _resolve, _winning, _parents, _own = build_render_model(root)
    for idx, elem in enumerate(root.iter()):
        # White inside a <mask> is an alpha value, not a colour.
        if is_nonrendering(elem):
            continue
        tag = _strip_ns(elem.tag)
        if tag in ("style", "metadata", "desc", "title"):
            continue

        for attr_name in _PAINT_PROPS:
            val = elem.get(attr_name, "").lower()
            # 88% of these attributes are absent; the colour parser is the most
            # expensive check in the module, so it is not asked about nothing.
            if not val:
                continue
            # A stop that fades to nothing is not a live white.
            if _is_forbidden(val) and _opacity_value(elem.get("stop-opacity")) != 0.0:
                violations.append(
                    CSSViolation(
                        f"<{tag}>{_element_id(elem)}",
                        idx,
                        "forbidden-color",
                        f'{attr_name}="{val}" - use a theme colour instead of black/white',
                    )
                )
        # An inline `style="fill:#ffffff"` paints exactly what the attribute
        # spelling does, and reading only the attribute left the row that
        # forbids the colour printing PASS over a live white fill.
        for m in _DECL_RE.finditer(elem.get("style", "")):
            prop, val = m.group(1).strip(), strip_important(m.group(2)).lower()
            if prop in _PAINT_PROPS and _is_forbidden(val):
                violations.append(
                    CSSViolation(
                        f"<{tag}>{_element_id(elem)}",
                        idx,
                        "forbidden-color",
                        f'style="{prop}:{val}" - use a theme colour instead of black/white',
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
        for prop_match in _DECL_RE.finditer(style):
            prop = prop_match.group(1).strip()
            val = prop_match.group(2).strip()
            if prop in STYLE_PROPS and "#" in val:
                violations.append(
                    CSSViolation(
                        f"<{tag}>{_element_id(elem)}",
                        idx,
                        "inline-style-color",
                        f"Inline style {prop}: {val} - move to CSS class",
                    )
                )

    return violations


# A dark-mode override that does not change the rendering is not an override.
# Measured on a real 17-file deck: 431 colour overrides, none above 6/255, every
# file scoring 100% "coverage" while rendering identically in both themes.
_MIN_THEME_LUM_DELTA = 32.0

# Fewer overrides than this and the proportion is noise, so the verdict falls
# back to "every one of them is inert".
_MIN_THEME_SAMPLE = 4

# The ground answers a stricter question than a foreground swatch: not "did this
# move" but "did it land on a dark ground". 96/255 of separation, AND a dark
# value below mid-grey - distance alone is not inversion, since #f5f9fc ->
# #989898 clears 96 with both ends still light. #f5f9fc -> #d0d0d0 (delta 40)
# fails on separation; #12181e -> #f7fbff fails on direction.
_MIN_BACKPLATE_LUM_DELTA = 96.0

# The dividing line the backplate must cross, not merely move away from.
_MID_GREY = 128.0


# The only two CSS colour keywords this module has a RULE about. The full
# 148-name table is deliberately absent: an unresolvable paint is reported as
# unmeasurable (see `check_theme_background`), which covers every other keyword
# without this module growing a colour dictionary it would then have to maintain.
_KEYWORD_RGBA = {
    "black": (0.0, 0.0, 0.0, 1.0),
    "white": (255.0, 255.0, 255.0, 1.0),
    "transparent": (0.0, 0.0, 0.0, 0.0),
}


def _rgba(color: str | None) -> tuple[float, float, float, float] | None:
    """`(r, g, b, a)` on 0-255 / 0-1, or None when the value is not a colour.

    ONE colour reader for the module. Alpha is carried out rather than dropped:
    the plate election has to know that `rgba(…, 0.15)` and `#0b122040` are
    washes, and the forbidden-colour rule has to know that a fully transparent
    stop is not a live white.
    """
    raw = strip_important(color).lower()
    if raw in _KEYWORD_RGBA:
        return _KEYWORD_RGBA[raw]

    m = re.fullmatch(r"#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", raw)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        r, g, b = (float(int(h[i : i + 2], 16)) for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
        return r, g, b, a

    m = re.fullmatch(r"rgba?\(([^)]*)\)", raw)
    if m:
        parts = [p.strip() for p in re.split(r"[ ,/]+", m.group(1)) if p.strip()]
        if len(parts) >= 3:
            try:
                r, g, b = (
                    float(p[:-1]) * 2.55 if p.endswith("%") else float(p) for p in parts[:3]
                )
                a = 1.0
                if len(parts) >= 4:
                    a = float(parts[3][:-1]) / 100.0 if parts[3].endswith("%") else float(parts[3])
            except ValueError:
                return None
            return r, g, b, a

    return None


def _luma255(color: str | None) -> float | None:
    """Rec.709 luma of a colour on a 0-255 scale, or None if unreadable.

    Deliberately NOT WCAG relative luminance - this measures "did the colour
    move", for which gamma-encoded luma is the right scale. ``relative_luminance``
    in ``check_contrast`` / ``charts`` is the linearized 0-1 WCAG quantity and
    answers a different question; keep the two names apart.
    """
    rgba = _rgba(color)
    if rgba is None:
        return None
    r, g, b, a = rgba
    # A fully transparent paint has no colour to measure. Reporting it as black
    # would make `fill: transparent` look like the darkest thing on the canvas.
    if a == 0:
        return None
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _is_forbidden(value: str | None) -> bool:
    """True when this paint renders as pure black or pure white.

    Compared on the RESOLVED colour, not on string membership: `fill="black"`
    is the same defect as `fill="#000000"`, and `shaders.md` ships the keyword
    spelling in its own overlay recipe. A fully transparent paint is not a live
    colour, so a `stop-opacity="0"` white fade is not reported.
    """
    rgba = _rgba(value)
    if rgba is None:
        return False
    r, g, b, a = rgba
    return a > 0 and ((r, g, b) == (0.0, 0.0, 0.0) or (r, g, b) == (255.0, 255.0, 255.0))


def _paint_alpha(value: str | None, root=None, rules: dict[str, dict] | None = None):
    """Alpha the paint itself carries, resolving `url(#id)` to its stops.

    Returns None when the value is not a readable paint - the caller decides
    what to do with "unknown", which is never "assume opaque" at the plate.
    """
    v = strip_important(value)
    m = _URL_REF_RE.fullmatch(v)
    if not m:
        rgba = _rgba(v)
        return rgba[3] if rgba else None
    if root is None:
        return None
    alphas = []
    for stop in _gradient_stops(root, m.group(1)):
        a = _opacity_value(_stop_prop(stop, "stop-opacity", rules))
        paint_a = _paint_alpha(stop.get("stop-color"))
        alphas.append(min(a if a is not None else 1.0, paint_a if paint_a is not None else 1.0))
    # The MOST opaque stop: a gradient fading to nothing still covers the ground
    # where it is solid, so its peak alpha is what decides whether it is a wash.
    return max(alphas) if alphas else None


# The documented card-fill band is 0.04-0.08. A paint this faint composites
# over whatever ground is behind it and so carries the theme without being
# repainted - the scaffold's own `.card { fill: accent; fill-opacity: 0.04 }`
# is exactly that, and its dark block correctly repaints only the stroke.
_COMPOSITED_OPACITY = 0.1


def _composited_away(props: dict, prop: str) -> bool:
    """True when this paint is too faint to carry a colour of its own."""
    for key in (f"{prop}-opacity", "opacity"):
        v = _opacity_value(props.get(key))
        if v is not None and v <= _COMPOSITED_OPACITY:
            return True
    a = _paint_alpha(props.get(prop))
    return a is not None and a <= _COMPOSITED_OPACITY


def _ancestor_opacity(node, parent_of: dict, resolve_paint=None, rules=None) -> float:
    """The lowest `opacity` on the node's ancestors, 1.0 when none.

    Group opacity multiplies through to its children, so a wash inside
    `<g opacity="0.06">` is a wash however opaque its own declarations look.
    With a resolver the value goes through the cascade, so a CLASS-declared
    group opacity (`.grain{opacity:0.06}`) counts as well as the attribute
    spelling; without one the attribute alone is read.
    """
    out = 1.0
    cur = parent_of.get(id(node))
    while cur is not None:
        raw = resolve_paint(cur, "opacity", rules) if resolve_paint else cur.get("opacity")
        v = _opacity_value(raw)
        if v is not None:
            out = min(out, v)
        cur = parent_of.get(id(cur))
    return out


# Containers whose contents paint only where they are referenced, never in
# place. Distinct from NONRENDER_TAGS, which is about paint that is not colour.
_TEMPLATE_TAGS = {"defs", "symbol", "marker", "pattern", "mask", "clippath"}


def _in_template(node, parent_of: dict) -> bool:
    cur = node
    while cur is not None:
        if _strip_ns(cur.tag).lower() in _TEMPLATE_TAGS:
            return True
        cur = parent_of.get(id(cur))
    return False


def _resolved_opacity(
    node, prop: str, rules: dict[str, dict], resolve_paint, root=None, parent_of=None
) -> float:
    """Effective opacity of ``prop`` on one element, 1.0 when unspecified.

    The rule-level ``_composited_away`` answers the same question about a rule
    in isolation; this one answers it about an element, through the cascade, for
    callers that hold a node rather than a declaration block.
    """
    out = 1.0
    for key in (f"{prop}-opacity", "opacity"):
        v = _opacity_value(resolve_paint(node, key, rules))
        if v is not None:
            out = min(out, v)
    # Alpha carried by the PAINT itself, not by an opacity property: `rgba(…)`,
    # an 8-digit hex, or a gradient whose stops fade out. A wash spelled that way
    # measured as fully opaque and was elected the ground - and the house's own
    # `paper-grain` overlay is a full-canvas rect placed last on purpose, so
    # "topmost covering rect" hands the election to it unless alpha is read.
    a = _paint_alpha(resolve_paint(node, prop, rules), root, rules)
    if a is not None:
        out = min(out, a)
    # Group opacity composites through the tree. `find_backplate` folded this in
    # separately while every other consumer did not, so a class-painted rect
    # inside `<g opacity="0.06">` was measured as fully opaque - an 11.53:1 PASS
    # in the un-ackable tier where the rendered ratio is 1.05:1.
    if parent_of is None and root is not None:
        parent_of = {id(child): parent for parent in root.iter() for child in parent}
    if parent_of is not None:
        out = min(out, _ancestor_opacity(node, parent_of, resolve_paint, rules))
    return out


def painting_properties(props: dict) -> list[str]:
    """The `fill`/`stroke` this rule actually paints with.

    `none` / `transparent` paints nothing, so it has nothing to invert - a
    `.hairline { fill: none }` geometry helper is not a theme defect - and a
    paint under the composite threshold carries the ground's theme already.
    """
    return [
        p
        for p in ("fill", "stroke")
        if strip_important(props.get(p)).lower() not in ("", "none", "transparent")
        and not _composited_away(props, p)
    ]


def has_dark_block(svg_text: str) -> bool:
    """True when the document declares a `prefers-color-scheme: dark` block.

    ONE home for the question and for its failure value. Two callers each wrote
    the `parse_style_block(text)[3]["has_dark_block"]` probe with the same bare
    `except: return False`, so the tuple position was load-bearing in three
    modules and the decision to answer "no dark block" about a file nobody could
    parse lived in two places that could drift apart.
    """
    try:
        return bool(parse_style_block(svg_text)[3]["has_dark_block"])
    except Exception:
        return False


def painting_selectors(rules: dict[str, dict]) -> list[str]:
    """Selectors the dark block has to answer for.

    ONE definition, shared with the checklist's inventory. A gate computed over
    a WIDER set than the checker reads does not make the row stricter - it turns
    "nothing was judged" into PASS, which is strictly worse than the NA it
    replaced.
    """
    return [sel for sel, props in rules.items() if painting_properties(props)]


def check_dark_mode_coverage(
    light_rules: dict[str, dict],
    dark_rules: dict[str, dict],
) -> list[CSSViolation]:
    """Every light-mode rule that paints should have a dark-mode override.

    Painting means fill OR stroke - a stroke-only rule (rules, connectors,
    axes) is as invisible against the wrong ground as a filled one. Every
    selector shape is judged: `text { fill: … }` and `#plate { fill: … }` go
    unthemed exactly as a class does, and iterating classes alone left them
    unexamined under a row that reported PASS.
    """
    violations = []
    for sel, props in light_rules.items():
        painted = painting_properties(props)
        if not painted:
            continue
        dark = dark_rules.get(sel)
        if dark is None:
            violations.append(
                CSSViolation(
                    sel,
                    0,
                    "missing-dark-override",
                    f"Rule {sel} sets {'/'.join(painted)} in light mode "
                    f"but has no dark mode override",
                    severity="warning",
                )
            )
            continue
        # Per PROPERTY, not per selector. A dark rule that touches the selector
        # without repainting it - overriding only `opacity`, or only `fill` on a
        # rule that also strokes - leaves that paint at its light value under
        # the media query, and a name-only test called the rule covered.
        # Presence is not coverage either when the light declaration is
        # `!important` and the dark one is not: the addition LOSES, so the paint
        # keeps its light value however the dark rule reads.
        absent = [
            p
            for p in painted
            if not _is_important(dark.get(p)) and (p not in dark or _is_important(props.get(p)))
        ]
        if absent:
            violations.append(
                CSSViolation(
                    sel,
                    0,
                    "missing-dark-override",
                    f"Rule {sel} sets {'/'.join(absent)} in light mode and its dark "
                    f"rule does not override {'it' if len(absent) == 1 else 'them'}, so that "
                    f"paint keeps its light value in dark mode",
                    severity="warning",
                )
            )

    return violations


def theme_deltas(
    light_rules: dict[str, dict], dark_rules: dict[str, dict]
) -> list[tuple[float, str, str, str, str]]:
    """Every light/dark colour pair this module can actually measure.

    Exported because the checklist row that reports on these has to be gated on
    the SAME set: a dark block that redeclares only selectors the light sheet
    never paints, or only values that are not colours, leaves nothing to
    measure - and an empty result read as agreement is the free PASS the roster
    exists to abolish.
    """
    deltas = []
    for sel, props in light_rules.items():
        dark = dark_rules.get(sel)
        if not dark:
            continue
        for prop in ("fill", "stroke"):
            # A normal dark declaration under a light `!important` never wins -
            # counting it here reports a theme delta on a colour that does not move.
            if _is_important(props.get(prop)) and not _is_important(dark.get(prop)):
                continue
            lv = _luma255(props.get(prop))
            dv = _luma255(dark.get(prop))
            if lv is None or dv is None:
                continue
            deltas.append(
                (
                    abs(lv - dv),
                    sel,
                    prop,
                    str(props.get(prop)).strip(),
                    str(dark.get(prop)).strip(),
                )
            )
    return deltas


def check_dark_mode_effective(
    light_rules: dict[str, dict],
    dark_rules: dict[str, dict],
) -> list[CSSViolation]:
    """Overridden classes must actually change colour between themes.

    Coverage counts overrides; this measures them. A dark block whose colours
    sit a few luminance points from the light ones renders identically, so the
    file is single-theme with a media query draped over it - and every
    presence-based check calls that complete.

    Judged on the SHARE of overrides that move, not on the largest one. Gating
    on the maximum let a single repainted class buy silence for 400 inert ones
    beside it; gating on each override individually is wrong in the other
    direction, because some colours are legitimately theme-invariant (text on a
    saturated accent that does not itself invert). A dark block is inert when
    most of it does nothing.
    """
    deltas = theme_deltas(light_rules, dark_rules)
    if not deltas:
        return []
    inert = sorted(d for d in deltas if d[0] < _MIN_THEME_LUM_DELTA)
    if not inert:
        return []
    # Below the floor there is no meaningful proportion to take, so the claim
    # reverts to the strict one: every override in the block is inert.
    if len(deltas) >= _MIN_THEME_SAMPLE and len(inert) * 2 <= len(deltas):
        return []
    if len(deltas) < _MIN_THEME_SAMPLE and len(inert) < len(deltas):
        return []

    shown = ", ".join(
        f"{sel} {prop} {light}→{dark} ({d:.0f})" for d, sel, prop, light, dark in inert[:6]
    )
    more = f" (+{len(inert) - 6} more)" if len(inert) > 6 else ""
    return [
        CSSViolation(
            "<style>",
            0,
            "inert-dark-mode",
            f"{len(inert)} of {len(deltas)} colour overrides move less than "
            f"{_MIN_THEME_LUM_DELTA:.0f} of 255 in 8-bit brightness (Rec.709 luma, not WCAG "
            f"relative luminance), so {'all' if len(inert) == len(deltas) else 'most'} of the "
            f"dark block renders the same in both themes: "
            f"{shown}{more}. Repaint the dark block against a dark ground rather than tinting "
            f"the light one.",
            severity="warning",
        )
    ]


def find_backplate(root, light_rules: dict[str, dict] | None = None):
    """The `<rect>` that paints the canvas ground, or None.

    Shared so the checklist can tell "no plate to judge" from "a plate that
    inverts" - returning no findings for both made the row print PASS on 55 of
    71 example files where nothing had been examined.

    The plate is found by GEOMETRY, not by name. Searching for an id/class
    containing "background" and stopping at the first hit found the decorative
    texture group instead of the plate under it, and named nothing at all in
    the example files whose plate is an unnamed root rect.

    `<rect>` only, opaque only, and the LAST qualifying one in document order.
    Document order IS paint order, so the ground the viewer sees is the topmost
    shape that covers the canvas opaquely - a 94%-coverage decoration painted
    UNDER a full-bleed plate is hidden by it, and area is not evidence of
    z-order either way. Near-transparent full-bleed washes composite over the
    ground rather than being it, so they are skipped at the module's own
    threshold; electing one judged the decoration's theme and left the real
    ground unexamined.

    Paths are not candidates. Reading a path's `d` as absolute alternating x/y
    demoted a relative-spelled full-bleed plate (`M0 0 h1920 v1080 h-1920 z`
    boxes as 3840 wide) and promoted a swoosh whose control points reach the
    corners. A plate drawn as a path therefore reads as no plate, which the
    roster says in exactly those words rather than guessing.
    """
    lrules = light_rules or {}
    vb = (root.get("viewBox") or "").strip()
    parts = [x for x in re.split(r"[ ,]+", vb) if x]
    if len(parts) != 4:
        return None
    try:
        min_x, min_y, canvas_w, canvas_h = (float(x) for x in parts)
    except ValueError:
        return None
    if canvas_w <= 0 or canvas_h <= 0:
        return None

    _nonrendering, is_displaced, resolve_paint, _winning, parent_of, _own = build_render_model(
        root
    )
    plate = None
    for node in root.iter():
        if _strip_ns(node.tag) != "rect":
            continue
        # Scaffold placeholders are unfinished by design - the author paints the
        # real plate over them. Judging them is judging the skeleton.
        if "slot" in (node.get("class") or "").split() or node.get("data-placeholder") == "true":
            continue
        # Non-rendering containers, display:none, and rects displaced by a
        # transform whose coordinates we do not resolve.
        if is_displaced(node):
            continue
        # Resolved through the cascade: a leftover `fill="transparent"` attribute
        # loses to a class that paints the rect, and skipping on the attribute
        # alone hid exactly that plate. `none`/`transparent` paints no ground -
        # a transparent backplate is the documented idiom, inheriting the
        # document ground, which inverts.
        resolved = (resolve_paint(node, "fill", lrules) or "").strip()
        if resolved.lower() in ("", "none", "transparent"):
            continue
        # A pattern fill is chrome (the scaffold's guide grid), not the ground.
        pm = _URL_REF_RE.fullmatch(resolved)
        if pm and any(
            el.get("id") == pm.group(1) and _strip_ns(el.tag).lower() == "pattern"
            for el in root.iter()
        ):
            continue
        # A near-transparent full-bleed wash composites over the ground rather
        # than being it - and the module already has a threshold for exactly
        # that. Electing one as the plate judged the decoration's theme and left
        # the real ground unexamined. Alpha counts wherever it is written:
        # `fill-opacity`, `opacity` on the rect or any ancestor, `rgba(…)`, an
        # 8-digit hex, or a gradient's stops - all folded into `_resolved_opacity`,
        # which also gets the parent map this loop already holds.
        if (
            _resolved_opacity(node, "fill", lrules, resolve_paint, root, parent_of)
            <= _COMPOSITED_OPACITY
        ):
            continue
        # A filtered rect is whatever the filter makes of it. The house's own
        # `paper-grain` overlay is `fill="black"` + `filter=…`, painted last on
        # purpose - opaque by every declaration, a texture on the page.
        if node.get("filter"):
            continue
        # `<defs>`/`<symbol>` contents paint where they are REFERENCED, not in
        # place, so nothing inside one is the ground. The colour scan reads them
        # for exactly the same reason; only the plate hunt needs them excluded.
        if _in_template(node, parent_of):
            continue
        w = _length(node.get("width"), canvas_w)
        h = _length(node.get("height"), canvas_h)
        if w is None or h is None:
            continue
        # An offset present but unreadable is not an offset of zero.
        x = _length(node.get("x"), canvas_w) if node.get("x") else 0.0
        y = _length(node.get("y"), canvas_h) if node.get("y") else 0.0
        if x is None or y is None:
            continue
        # is_backplate_geometry bounds x/y from above only; a rect starting far
        # off-canvas is a bleed decoration, not the ground.
        if x - min_x < -BACKPLATE_ORIGIN_TOL * canvas_w:
            continue
        if y - min_y < -BACKPLATE_ORIGIN_TOL * canvas_h:
            continue
        if not is_backplate_geometry(x - min_x, y - min_y, w, h, canvas_w, canvas_h):
            continue
        plate = node

    return plate


def check_theme_background(
    root,
    ns: str,
    light_rules: dict[str, dict],
    dark_rules: dict[str, dict],
) -> list[CSSViolation]:
    """The ground must change with the theme, or nothing on it can.

    A backplate painted with an inline fill cannot answer the media query at
    all; one painted by a rule the dark block leaves alone keeps every
    foreground colour sitting on the same ground in both themes.
    """
    lrules, drules = light_rules, dark_rules
    # A file with no dark block is single-theme by construction; the missing
    # block is the finding, and `dark block present` already carries it.
    if not drules:
        return []
    _nonrendering, _displaced, _resolve, winning_paint, _parents, _own = build_render_model(root)
    plate = find_backplate(root, lrules)
    if plate is None:
        return []

    # Measure the declaration that actually wins, not every class on the plate.
    # Looping the class list judged an `#id`-themed plate not at all - the loop
    # body never ran, so the row printed PASS over a near-white dark ground -
    # and reported one rect twice when it carried two painting classes.
    paint = theme_paint(plate, "fill", lrules, drules, winning_paint)
    l_raw, subject, l_spec = paint.light, paint.subject, paint.light_spec
    lv = paint_luma(l_raw, root, lrules)
    # Unconditional: a gradient plate whose STOPS are dark-overridden never sets
    # `overridden` (the plate's own `fill: url(#g)` is unchanged), so gating on
    # it resolved those stops against the light sheet and reported a plate that
    # inverts 246 -> 20 as unthemed. `paint_luma` ignores `rules` for a flat
    # colour, so merging is strictly correct and strictly shorter.
    dv = paint_luma(paint.dark, root, merged_rules(lrules, drules))
    if lv is None:
        # UNMEASURABLE IS NOT CLEAN. Returning nothing here made the row print
        # PASS over a ground the tool never read - `fill:white`, `ghostwhite`,
        # `var(--bg)`, `currentColor` and `url(#missing)` all took a free pass.
        # This module resolves hex, `rgb()/rgba()` and the two keywords it has a
        # rule about; anything else is reported as unjudged rather than assumed
        # fine, which closes the whole class without a 148-name colour table.
        return [
            CSSViolation(
                subject,
                0,
                "unthemed-background",
                f'Backplate {subject} is painted "{l_raw}", which this checker cannot read as '
                f"a colour, so the inversion was NOT judged. Use a hex or rgb() value - or "
                f"treat this row as unverified.",
                severity="warning",
            )
        ]
    # Nothing but a presentation attribute paints it, so no media query can
    # reach it whatever its value - including `url(#gradient)`, whose stops are
    # hardcoded. Measured like any other plate; only the remedy differs.
    inline_only = (
        l_spec == _SPEC_ATTR
    )  # Distance alone is not inversion: a light ground repainted WHITER in the
    # dark block moves 227/255 and still flashes near-white under
    # prefers-color-scheme: dark. The dark value must actually be dark.
    far_enough = dv is not None and abs(lv - dv) >= _MIN_BACKPLATE_LUM_DELTA
    right_way = dv is not None and dv < _MID_GREY
    if far_enough and right_way:
        return []
    if dv is None:
        why = "dark absent"
    elif not right_way:
        why = (
            f"light {lv:.0f}, dark {dv:.0f} - the dark-mode ground is not dark "
            f"(needs to sit below {_MID_GREY:.0f}/255)"
        )
    else:
        why = (
            f"light {lv:.0f}, dark {dv:.0f}; need {_MIN_BACKPLATE_LUM_DELTA:.0f}/255 of separation"
        )
    # The winner can be an ANCESTOR's attribute (the inheritance walk) - the
    # remedy then has to name the ancestor, not claim a fill the plate itself
    # does not carry.
    _own_spec, own_val, _own_sel = _own(plate, "fill", lrules)
    if inline_only and own_val is None:
        remedy = (
            f'An ancestor\'s fill="{l_raw}" presentation attribute paints it, which no '
            f"media query can reach - move it to a CSS rule and override that rule in "
            f"the dark block."
        )
    elif inline_only:
        remedy = (
            f'Its fill="{l_raw}" is a presentation attribute, which no media query can '
            f"reach - move it to a CSS rule and override that rule in the dark block."
        )
    else:
        remedy = "Every foreground colour sits on the same ground in both themes."
    return [
        CSSViolation(
            subject,
            0,
            "unthemed-background",
            f"Backplate {subject} does not invert between themes ({why}). {remedy}",
            severity="warning",
        )
    ]


def check_font_inline(root, ns: str) -> list[CSSViolation]:
    """Flag text without proper font-family (should use system font stack)."""
    violations = []
    EXPECTED_FONT = "Segoe UI"

    for idx, elem in enumerate(root.iter()):
        tag = _strip_ns(elem.tag)
        if tag != "text":
            continue

        font = elem.get("font-family", "")
        if font and EXPECTED_FONT not in font:
            violations.append(
                CSSViolation(
                    f"<text>{_element_id(elem)}",
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
    svg_text = open(filepath, encoding="utf-8").read()
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = re.match(r"\{([^}]*)\}", root.tag)
    ns_str = ns.group(1) if ns else ""

    light_classes, dark_classes, css_colors, style_meta = parse_style_block(svg_text)

    violations = []
    # A real finding, not a roster-only verdict. The checklist row used to be
    # decided inside build_checklist and carry a fabricated tier, so the row,
    # the findings list, the ack gate and --json all disagreed about whether
    # the file had dark mode at all.
    if not style_meta["has_dark_block"]:
        has_style = bool(style_meta["light_rules"] or style_meta["dark_rules"])
        violations.append(
            CSSViolation(
                "<style>" if has_style else "<svg> (no <style> element)",
                0,
                "missing-dark-block",
                "No @media (prefers-color-scheme: dark) block"
                + ("" if has_style else " and no <style> element at all")
                + " - the file renders in light colours on a dark ground. Add the "
                "block and override every painting class in it.",
                severity="warning",
            )
        )
    violations.extend(check_inline_fill_on_text(root, ns_str))
    violations.extend(check_text_opacity(root, ns_str))
    violations.extend(
        check_forbidden_colors(root, ns_str, style_meta["light_rules"], style_meta["dark_rules"])
    )
    violations.extend(check_inline_styles(root, ns_str))
    # The RULE maps, not the class maps. The checklist's gate reads every
    # selector shape, so a class-only checker under it turned "nothing judged"
    # into PASS over an unthemed `text { fill: … }` or `#plate { fill: … }`.
    violations.extend(
        check_dark_mode_coverage(style_meta["light_rules"], style_meta["dark_rules"])
    )
    violations.extend(
        check_dark_mode_effective(style_meta["light_rules"], style_meta["dark_rules"])
    )
    violations.extend(
        check_theme_background(root, ns_str, style_meta["light_rules"], style_meta["dark_rules"])
    )
    violations.extend(check_font_inline(root, ns_str))

    stats = {
        "light_classes": len(light_classes),
        "dark_classes": len(dark_classes),
        "css_colors": len(css_colors),
        "has_dark_mode": style_meta["has_dark_block"],
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
