"""Crawler that builds the bundled The Base Mesh catalogue.

The site (https://www.thebasemesh.com) is a Wix build. Two facts make it
crawlable without a browser:

* the sitemap index has one child sitemap whose name starts with
  ``dynamic-asset`` and it lists every asset page;
* each asset page embeds its database record in a
  ``<script type="application/json" id="wix-warmup-data">`` block, under
  ``dataStore.recordsByCollectionId``. The record carries the title, the
  category list (field ``food``) and the archive link (field ``download``).

Only the index run touches the network - ``mesh search`` and friends read the
JSON this module writes.
"""

from __future__ import annotations

from collections.abc import Callable
import gzip
import http.client
import json
import re
import time
import urllib.parse
import urllib.request

SITE = "https://www.thebasemesh.com"
SITEMAP_URL = f"{SITE}/sitemap.xml"
LICENSE = "CC0"
SOURCE = "thebasemesh.com"

USER_AGENT = "svg-infographics-mesh/1.0 (+https://github.com/stellarshenson/claude-code-plugins)"
REQUEST_DELAY_S = 0.3
REQUEST_TIMEOUT_S = 30
RETRY_DELAY_S = 1.0

_WARMUP_RE = re.compile(
    r'<script type="application/json" id="wix-warmup-data">(.*?)</script>', re.S
)
_LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
_ASSET_PATH_RE = re.compile(r"/asset/([^/?#]+)$")
_WIX_DOC_PREFIX = "wix:document://v1/"

# A long crawl meets truncated chunked responses and reset connections. None of
# http.client's exceptions derive from OSError, so they need naming explicitly;
# EOFError is gzip.decompress on a body cut short. mesh_cache shares the tuple.
TRANSIENT = (OSError, http.client.HTTPException, EOFError)


def http_get(url: str, retries: int = 1) -> bytes:
    """Fetch a URL politely, transparently decompressing a gzip response.

    Args:
        url: Absolute URL to fetch.
        retries: Extra attempts after the first failure.

    Returns:
        bytes: The response body.

    Raises:
        OSError, http.client.HTTPException or EOFError: The last attempt failed,
            or its gzip body was cut short.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return body
        except TRANSIENT:
            if attempt == retries:
                raise
            time.sleep(RETRY_DELAY_S)
    raise AssertionError("unreachable")


def asset_sitemap_url(sitemap_index_xml: str) -> str:
    """Return the child sitemap that lists asset pages.

    Args:
        sitemap_index_xml: Body of ``/sitemap.xml``.

    Returns:
        str: URL of the ``dynamic-asset...`` child sitemap.

    Raises:
        ValueError: No child sitemap matches; the site layout changed.
    """
    for loc in _LOC_RE.findall(sitemap_index_xml):
        if "dynamic-asset" in loc:
            return loc
    raise ValueError("no dynamic-asset sitemap in the sitemap index - site layout changed")


def asset_slugs(asset_sitemap_xml: str) -> list[str]:
    """Return every asset slug listed in the asset sitemap, in site order."""
    slugs = []
    for loc in _LOC_RE.findall(asset_sitemap_xml):
        match = _ASSET_PATH_RE.search(loc)
        if match:
            slugs.append(match.group(1))
    return slugs


def _records(warmup: object) -> list[dict]:
    """Collect every database record from the warmup JSON, at any nesting depth."""
    found: list[dict] = []
    stack = [warmup]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            by_collection = node.get("recordsByCollectionId")
            if isinstance(by_collection, dict):
                for collection in by_collection.values():
                    found.extend(r for r in collection.values() if isinstance(r, dict))
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def download_url(wix_document: str) -> str:
    """Convert a ``wix:document://`` archive reference into a direct download URL.

    Args:
        wix_document: Value of the record's ``download`` field, of the form
            ``wix:document://v1/archives/<id>.zip/<name>.zip``.

    Returns:
        str: ``https://www.thebasemesh.com/_files/archives/<id>.zip?dn=<name>.zip``.

    Raises:
        ValueError: The reference is not a Wix document URI.
    """
    if not wix_document.startswith(_WIX_DOC_PREFIX):
        raise ValueError(f"not a wix document reference: {wix_document!r}")
    doc_path, _, filename = wix_document[len(_WIX_DOC_PREFIX) :].rpartition("/")
    return f"{SITE}/_files/{doc_path}?dn={urllib.parse.quote(filename)}"


def parse_asset_page(html: str, slug: str) -> dict:
    """Build one catalogue entry from an asset page.

    Args:
        html: Full HTML of ``/asset/<slug>``.
        slug: Asset slug, used to pick this page's record out of the block of
            records the page also embeds for its "latest assets" strip.

    Returns:
        dict: Catalogue entry with slug, name, category, categories, tri_count,
        page_url, download_url, license and source.

    Raises:
        ValueError: The warmup block, the record or its download link is missing.
    """
    match = _WARMUP_RE.search(html)
    if not match:
        raise ValueError(f"{slug}: no wix-warmup-data block")
    page_path = f"/asset/{slug}"
    for record in _records(json.loads(match.group(1))):
        if record.get("link-test-1-title") != page_path:
            continue
        categories = [c for c in record.get("food") or [] if c]
        return {
            "slug": slug,
            "name": record.get("title") or slug,
            "category": categories[0] if categories else "Misc",
            "categories": categories,
            "tri_count": int(record.get("triCount") or 0),
            "page_url": f"{SITE}{page_path}",
            "download_url": download_url(record["download"]),
            "license": LICENSE,
            "source": SOURCE,
        }
    raise ValueError(f"{slug}: no database record on the page")


def fetch_entry(slug: str, retries: int = 1) -> dict:
    """Fetch one asset page and turn it into a catalogue entry.

    The site occasionally answers with a variant page that carries no warmup
    block; a second request a moment later returns the normal page, so a parse
    failure is retried as well as a transport failure.

    Args:
        slug: Asset slug.
        retries: Extra attempts after the first failure.

    Returns:
        dict: The catalogue entry.

    Raises:
        ValueError: The last attempt produced a page without the asset's record.
        OSError, http.client.HTTPException or EOFError: The last attempt failed to load.
    """
    for attempt in range(retries + 1):
        try:
            html = http_get(f"{SITE}/asset/{slug}").decode("utf-8", "replace")
            return parse_asset_page(html, slug)
        except (*TRANSIENT, ValueError):
            if attempt == retries:
                raise
            time.sleep(RETRY_DELAY_S)
    raise AssertionError("unreachable")


def crawl(report: Callable[[str], None] = print) -> list[dict]:
    """Crawl every asset page and return the catalogue entries.

    Args:
        report: Callable taking one progress string. Defaults to ``print``.

    Returns:
        list[dict]: One entry per asset that parsed, sorted by slug. Assets that
        fail to parse are reported and skipped.
    """
    index_xml = http_get(SITEMAP_URL).decode("utf-8", "replace")
    sitemap_url = asset_sitemap_url(index_xml)
    slugs = asset_slugs(http_get(sitemap_url).decode("utf-8", "replace"))
    report(f"{len(slugs)} asset pages listed in {sitemap_url}")

    entries, failures = [], 0
    for position, slug in enumerate(slugs, 1):
        time.sleep(REQUEST_DELAY_S)
        try:
            entries.append(fetch_entry(slug))
        except (*TRANSIENT, ValueError) as exc:
            failures += 1
            report(f"skip {slug}: {exc}")
        if position % 50 == 0:
            report(f"{position}/{len(slugs)} pages, {len(entries)} entries, {failures} failed")
    report(f"done: {len(entries)} entries, {failures} failed")
    return sorted(entries, key=lambda e: e["slug"])
