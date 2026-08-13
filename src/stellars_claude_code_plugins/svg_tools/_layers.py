"""Canonical layer model for SVG infographics.

The five named layers are the z-order backbone of every infographic
(bottom-up render order). This module is the single source of truth -
scaffold generation, empty-space obstacle filtering, auto-route obstacle
filtering and the manifest layer-discipline check all import from here.
"""

CANONICAL_LAYERS: tuple[str, ...] = (
    "background",
    "nodes",
    "connectors",
    "content",
    "callouts",
)

LAYER_ROLES: dict[str, str] = {
    "background": "fills, textures, banners - lowest z",
    "nodes": "cards, circles, hexes - the shapes connectors attach to",
    "connectors": "every arrow / strand / spine, tool-generated only",
    "content": "icons, labels, text - never behind nodes",
    "callouts": "callout groups - topmost",
}

# Non-layer top-level groups that are legitimate outside the five layers:
# authoring aids and decoration passes documented by their own commands.
AUXILIARY_GROUPS: tuple[str, ...] = (
    "guide-grid",
    "beautify-decorations",
    "beautify-icons",
    "add-life-decorations",
    "add-life-icons",
)


# How far from the canvas origin a plate may start and still be the plate.
# Exported because a caller that normalises coordinates itself needs the same
# number for its own bounds, and two copies drift silently.
BACKPLATE_ORIGIN_TOL = 0.04

# How much of the canvas a rect must cover to be the plate. Named for the same
# reason as the origin tolerance: the pair is one dial, and one half sitting as
# a bare literal is how the copies drift apart.
BACKPLATE_COVER_MIN = 0.92


def is_backplate_geometry(
    x: float, y: float, w: float, h: float, canvas_w: float, canvas_h: float
) -> bool:
    """True when a rect covers ~the whole canvas from ~the origin.

    The full-canvas background plate is layout chrome, not a card:
    treating it as a card/container reads every connector endpoint as
    "inside" it and every box as "overlapping" it. Geometry-first so the
    rule holds for transparent, solid AND gradient plates regardless of
    naming - the fill/id conventions are honoured separately by the
    checkers that also accept them.
    """
    if canvas_w <= 0 or canvas_h <= 0:
        return False
    return (
        w >= BACKPLATE_COVER_MIN * canvas_w
        and h >= BACKPLATE_COVER_MIN * canvas_h
        and x <= BACKPLATE_ORIGIN_TOL * canvas_w
        and y <= BACKPLATE_ORIGIN_TOL * canvas_h
    )


def parse_layer_list(raw: str | None) -> tuple[str, ...]:
    """Parse a comma-separated layer list; validates against the canon.

    Raises ValueError on unknown layer names so typos fail loudly instead
    of silently filtering nothing.
    """
    if not raw:
        return ()
    names = tuple(part.strip() for part in raw.split(",") if part.strip())
    unknown = [n for n in names if n not in CANONICAL_LAYERS]
    if unknown:
        raise ValueError(
            f"unknown layer(s) {unknown}; canonical layers are {', '.join(CANONICAL_LAYERS)}"
        )
    return names


def make_layer_filter(layers=None, ignore_layers=None):
    """Return ``allowed(layer_name) -> bool`` for obstacle collection.

    ``layers`` (include mode): only elements inside these top-level layer
    groups count. ``ignore_layers`` (exclude mode): everything counts
    except these. Passing both raises - the combination is ambiguous.
    Elements outside any known layer group (root-level loose shapes,
    auxiliary groups) count as layer ``None``: included in exclude mode,
    dropped in include mode.
    """
    include = tuple(layers or ())
    exclude = tuple(ignore_layers or ())
    if include and exclude:
        raise ValueError("pass either layers= (include) or ignore_layers= (exclude), not both")
    unknown = [n for n in (*include, *exclude) if n not in CANONICAL_LAYERS]
    if unknown:
        raise ValueError(
            f"unknown layer(s) {unknown}; canonical layers are {', '.join(CANONICAL_LAYERS)}"
        )
    if include:
        return lambda layer: layer in include
    if exclude:
        return lambda layer: layer not in exclude
    return lambda layer: True
