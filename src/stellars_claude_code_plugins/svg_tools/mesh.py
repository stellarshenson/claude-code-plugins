"""CLI for the CC0 mesh catalogue sourced from thebasemesh.com.

Usage:
    svg-infographics mesh index [--rebuild]
    svg-infographics mesh search QUERY [--category C] [--top N] [--json]
    svg-infographics mesh list [--category C]
    svg-infographics mesh categories
    svg-infographics mesh fetch SLUG [SLUG ...]
    svg-infographics mesh path SLUG

Only ``index --rebuild`` and a cold ``fetch`` touch the network. Meshes land in
``~/.cache/svg-infographics/meshes/<slug>.obj`` and feed
``svg-infographics wireframe --model <slug>``.
"""

from __future__ import annotations

import argparse
import json
import sys

from stellars_claude_code_plugins.svg_tools.mesh_cache import MeshFetchError, cached_path, fetch
from stellars_claude_code_plugins.svg_tools.mesh_catalog import (
    category_counts,
    entry_for,
    filter_by_category,
    load_catalog,
    write_catalog,
)
from stellars_claude_code_plugins.svg_tools.mesh_crawl import LICENSE, SOURCE, crawl
from stellars_claude_code_plugins.svg_tools.mesh_search import rank


def _print_counts(entries: list[dict]) -> None:
    """Print the per-category tally under a total."""
    print(f"{len(entries)} assets, {LICENSE} from {SOURCE}")
    for category, count in category_counts(entries).items():
        print(f"  {category:<16} {count}")


def _cmd_index(args: argparse.Namespace) -> int:
    """Report the bundled catalogue, or crawl the site and rebuild it."""
    if not args.rebuild:
        _print_counts(load_catalog())
        print("\nRe-crawl with: svg-infographics mesh index --rebuild")
        return 0
    entries = crawl(report=lambda message: print(message, file=sys.stderr, flush=True))
    path = write_catalog(entries)
    print(f"wrote {path}")
    _print_counts(entries)
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    """Rank the catalogue against a query and print the best matches."""
    entries = load_catalog()
    if args.category:
        entries = filter_by_category(entries, args.category)
    hits = rank(args.query, entries)[: args.top]
    if args.json:
        json.dump(
            [{"score": round(score, 3), **entry} for score, entry in hits], sys.stdout, indent=2
        )
        print()
        return 0
    if not hits:
        print(f"no match for {args.query!r}", file=sys.stderr)
        return 1
    for score, entry in hits:
        print(f"{score:6.2f}  {entry['slug']:<34} {entry['name']:<28} {entry['category']}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    """Print every catalogue entry, optionally within one category."""
    entries = load_catalog()
    if args.category:
        entries = filter_by_category(entries, args.category)
    for entry in entries:
        print(f"{entry['slug']:<34} {entry['name']:<28} {', '.join(entry['categories'])}")
    print(f"\n{len(entries)} assets", file=sys.stderr)
    return 0


def _cmd_categories(_args: argparse.Namespace) -> int:
    """Print the categories and how many assets each holds."""
    _print_counts(load_catalog())
    return 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    """Download and cache the OBJ of each slug, skipping what is already cached."""
    failures = 0
    for slug in args.slugs:
        already = cached_path(slug).is_file()
        try:
            path = fetch(entry_for(slug))
        except (KeyError, MeshFetchError) as exc:
            print(f"skip {exc}", file=sys.stderr)
            failures += 1
            continue
        print(f"{'cached' if already else 'fetched'} {path}")
    return 1 if failures else 0


def _cmd_path(args: argparse.Namespace) -> int:
    """Print the cached OBJ path of a slug, or explain how to get it."""
    path = cached_path(args.slug)
    if not path.is_file():
        print(
            f"{args.slug} is not cached - run: svg-infographics mesh fetch {args.slug}",
            file=sys.stderr,
        )
        return 1
    print(path)
    return 0


def main() -> int:
    """Entry point for the ``mesh`` subcommand of ``svg-infographics``."""
    parser = argparse.ArgumentParser(
        prog="svg-infographics mesh",
        description=(
            f"CC0 mesh catalogue from {SOURCE}: index, search, list, fetch. "
            "Cached at ~/.cache/svg-infographics/meshes/."
        ),
    )
    sub = parser.add_subparsers(dest="subcmd")

    p_index = sub.add_parser("index", help="Report the bundled catalogue, or re-crawl the site.")
    p_index.add_argument(
        "--rebuild", action="store_true", help="Crawl every asset page and rewrite the catalogue."
    )

    p_search = sub.add_parser("search", help="Rank the catalogue against a query (BM25, fuzzy).")
    p_search.add_argument("query", help="Words to search for, e.g. 'sports car'.")
    p_search.add_argument("--category", help="Restrict to one category.")
    p_search.add_argument("--top", type=int, default=10, help="Max results (default 10).")
    p_search.add_argument("--json", action="store_true", help="Print full entries as JSON.")

    p_list = sub.add_parser("list", help="List catalogue entries.")
    p_list.add_argument("--category", help="Restrict to one category.")

    sub.add_parser("categories", help="List categories with asset counts.")

    p_fetch = sub.add_parser("fetch", help="Download and cache the OBJ of one or more slugs.")
    p_fetch.add_argument("slugs", nargs="+", help="Asset slugs, as printed by 'mesh search'.")

    p_path = sub.add_parser("path", help="Print the cached OBJ path of a slug.")
    p_path.add_argument("slug", help="Asset slug.")

    args = parser.parse_args()
    dispatch = {
        "index": _cmd_index,
        "search": _cmd_search,
        "list": _cmd_list,
        "categories": _cmd_categories,
        "fetch": _cmd_fetch,
        "path": _cmd_path,
    }
    if args.subcmd not in dispatch:
        parser.print_help()
        return 1
    return dispatch[args.subcmd](args)


if __name__ == "__main__":
    sys.exit(main())
