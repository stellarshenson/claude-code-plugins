"""Access to the bundled The Base Mesh catalogue.

The catalogue is package data - ``svg_tools/data/basemesh_catalog.json`` - built
by :mod:`mesh_crawl` and read by everything else. Every asset is CC0, so a mesh
may be redrawn and shipped without attribution.
"""

from __future__ import annotations

import json
from pathlib import Path

from stellars_claude_code_plugins.svg_tools.mesh_cache import cached_path, fetch
from stellars_claude_code_plugins.svg_tools.mesh_crawl import LICENSE, SITE, SOURCE

CATALOG_PATH = Path(__file__).parent / "data" / "basemesh_catalog.json"


def load_catalog() -> list[dict]:
    """Read every catalogue entry.

    Returns:
        list[dict]: Entries, each with slug, name, category, categories,
        tri_count, page_url, download_url, license and source.

    Raises:
        FileNotFoundError: The catalogue is missing from the package.
    """
    if not CATALOG_PATH.is_file():
        raise FileNotFoundError(
            f"mesh catalogue missing at {CATALOG_PATH} - run 'svg-infographics mesh index "
            "--rebuild' to crawl thebasemesh.com."
        )
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["entries"]


def write_catalog(entries: list[dict]) -> Path:
    """Write the catalogue to package data, replacing any previous build.

    Args:
        entries: Catalogue entries, as returned by ``mesh_crawl.crawl``.

    Returns:
        Path: The file written.
    """
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"site": SITE, "source": SOURCE, "license": LICENSE, "entries": entries}
    CATALOG_PATH.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return CATALOG_PATH


def filter_by_category(entries: list[dict], category: str) -> list[dict]:
    """Entries carrying a category, matched case-insensitively across all of them."""
    wanted = category.strip().lower()
    return [e for e in entries if wanted in {c.lower() for c in e.get("categories") or []}]


def category_counts(entries: list[dict]) -> dict[str, int]:
    """Number of entries per category, most populous first.

    An asset with several categories counts once under each.
    """
    counts: dict[str, int] = {}
    for entry in entries:
        for category in entry.get("categories") or [entry["category"]]:
            counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def entry_for(slug: str) -> dict:
    """The catalogue entry of one slug.

    Args:
        slug: Asset slug, as printed by ``mesh search``.

    Returns:
        dict: The entry.

    Raises:
        KeyError: No such slug.
    """
    for entry in load_catalog():
        if entry["slug"] == slug:
            return entry
    raise KeyError(f"unknown mesh slug {slug!r} - try 'svg-infographics mesh search {slug}'")


def resolve(slug: str) -> Path:
    """Cached OBJ path for a slug, downloading it once if the cache is cold.

    Args:
        slug: Asset slug.

    Returns:
        Path: Path to the cached OBJ.

    Raises:
        KeyError: No such slug.
        MeshFetchError: The download failed or the archive holds no OBJ.
    """
    path = cached_path(slug)
    return path if path.is_file() else fetch(entry_for(slug))
