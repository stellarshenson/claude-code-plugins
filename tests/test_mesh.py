"""Tests for the bundled CC0 mesh catalogue, its search and its cache.

No network: the catalogue is package data, and every download is served by a
monkeypatched ``urllib.request.urlopen`` returning an in-memory zip.
"""

import http.client
import io
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

import pytest

from stellars_claude_code_plugins.svg_tools import mesh, mesh_cache, mesh_crawl, wireframe
from stellars_claude_code_plugins.svg_tools.mesh_cache import MeshFetchError, cached_path, fetch
from stellars_claude_code_plugins.svg_tools.mesh_catalog import (
    category_counts,
    filter_by_category,
    load_catalog,
)
from stellars_claude_code_plugins.svg_tools.mesh_crawl import (
    asset_sitemap_url,
    asset_slugs,
    crawl,
    download_url,
    parse_asset_page,
)
from stellars_claude_code_plugins.svg_tools.mesh_search import rank

CLI = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "stellars_claude_code_plugins"
    / "svg_tools"
    / "cli.py"
)

OBJ = "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n"

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex><sitemap><loc>https://www.thebasemesh.com/pages-sitemap.xml</loc></sitemap>
<sitemap><loc>https://www.thebasemesh.com/dynamic-asset_p_x_0_5000-sitemap.xml</loc></sitemap>
</sitemapindex>"""

ASSET_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset><url><loc>https://www.thebasemesh.com/asset/anvil</loc></url>
<url><loc>https://www.thebasemesh.com/asset/sports-car-01</loc></url></urlset>"""


class _Response:
    """The slice of an HTTP response that ``http_get`` uses."""

    def __init__(self, body):
        self.body = body
        self.headers = {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def test_catalog_ships_the_whole_library(catalog):
    assert len(catalog) > 1000
    assert len({e["slug"] for e in catalog}) == len(catalog)


def test_every_entry_is_a_cc0_asset_with_a_download(catalog):
    for entry in catalog:
        assert entry["slug"] and entry["name"] and entry["category"]
        assert entry["license"] == "CC0"
        assert entry["source"] == "thebasemesh.com"
        assert entry["download_url"].startswith("https://www.thebasemesh.com/_files/archives/")
        assert entry["page_url"] == f"https://www.thebasemesh.com/asset/{entry['slug']}"


def test_categories_cover_the_object_kinds_the_wireframe_needs(catalog):
    counts = category_counts(catalog)
    for category in ("Transportation", "Animals", "Buildings", "Tools", "Furniture", "Nature"):
        assert counts.get(category, 0) > 0, f"{category} is empty"


def test_category_filter_keeps_only_that_category(catalog):
    animals = filter_by_category(catalog, "animals")
    assert 0 < len(animals) < len(catalog)
    assert all("Animals" in entry["categories"] for entry in animals)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_search_ranks_the_exact_name_first(catalog):
    # A query with competition for first place: "chair" also fuzzy-matches "chain".
    hits = rank("wooden chair", catalog)
    assert len(hits) > 10
    assert hits[0][1]["slug"] == "wooden-chair-01"
    assert hits[0][0] > hits[1][0]


def test_a_category_word_finds_members_whose_names_never_mention_it(catalog):
    hits = rank("animals", catalog)[:3]
    assert hits and all("Animals" in entry["categories"] for _, entry in hits)
    assert all("animal" not in entry["name"].lower() for _, entry in hits)


def test_search_survives_a_one_letter_typo(catalog):
    assert "anvil" in [entry["slug"] for _, entry in rank("anvel", catalog)[:5]]


def test_search_matches_a_run_together_compound_on_its_leading_word(catalog):
    hits = [entry["slug"] for _, entry in rank("cardboardbox", catalog)[:5]]
    assert any(slug.startswith("cardboard-box") for slug in hits)


def test_search_within_a_category_only_returns_that_category(catalog):
    hits = rank("chair", filter_by_category(catalog, "Furniture"))
    assert hits and all("Furniture" in entry["categories"] for _, entry in hits)


def test_a_query_without_a_searchable_word_is_rejected(catalog):
    with pytest.raises(ValueError):
        rank("!!!", catalog)


# ---------------------------------------------------------------------------
# Crawler helpers
# ---------------------------------------------------------------------------


def test_the_asset_sitemap_is_picked_out_of_the_index():
    assert asset_sitemap_url(SITEMAP_INDEX).endswith("dynamic-asset_p_x_0_5000-sitemap.xml")
    assert asset_slugs(ASSET_SITEMAP) == ["anvil", "sports-car-01"]


def test_a_wix_document_reference_becomes_a_direct_download():
    assert (
        download_url("wix:document://v1/archives/b36d2d_abc.zip/anvil.zip")
        == "https://www.thebasemesh.com/_files/archives/b36d2d_abc.zip?dn=anvil.zip"
    )


def _record(slug: str, title: str, categories: list) -> dict:
    """A database record shaped like the ones the site embeds in an asset page."""
    return {
        "title": title,
        "link-test-1-title": f"/asset/{slug}",
        "food": categories,
        "triCount": "782",
        "download": f"wix:document://v1/archives/b36d2d_{slug}.zip/{slug}.zip",
    }


def _asset_html(*records: dict) -> str:
    """An asset page carrying the given records in its warmup block."""
    warmup = {
        "appsWarmupData": {
            "dataBinding": {
                "dataStore": {
                    "recordsByCollectionId": {"Test": {str(i): r for i, r in enumerate(records)}}
                }
            }
        }
    }
    return (
        '<html><script type="application/json" id="wix-warmup-data">'
        + json.dumps(warmup)
        + "</script></html>"
    )


def test_an_asset_page_yields_the_entry_of_its_own_slug_not_a_neighbour():
    # The page's own record is not first: the "latest assets" strip is embedded too.
    html = _asset_html(
        _record("goblet-06", "Goblet 06", ["Fantasy"]),
        _record("anvil", "Anvil", ["Tools", "Industrial"]),
    )
    entry = parse_asset_page(html, "anvil")
    assert entry["name"] == "Anvil"
    assert entry["category"] == "Tools"
    assert entry["categories"] == ["Tools", "Industrial"]
    assert entry["tri_count"] == 782
    assert entry["license"] == "CC0"
    assert entry["download_url"].endswith("b36d2d_anvil.zip?dn=anvil.zip")


def test_an_asset_page_without_its_record_is_an_error():
    with pytest.raises(ValueError):
        parse_asset_page("<html>no warmup block</html>", "anvil")


def test_crawl_walks_the_sitemap_and_reports_the_pages_it_could_not_parse(monkeypatch):
    pages = {
        "https://www.thebasemesh.com/sitemap.xml": SITEMAP_INDEX,
        "https://www.thebasemesh.com/dynamic-asset_p_x_0_5000-sitemap.xml": ASSET_SITEMAP,
        "https://www.thebasemesh.com/asset/anvil": _asset_html(
            _record("anvil", "Anvil", ["Tools"])
        ),
        "https://www.thebasemesh.com/asset/sports-car-01": "<html>rendered client-side</html>",
    }
    monkeypatch.setattr(mesh_crawl, "REQUEST_DELAY_S", 0)
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout=None: _Response(pages[request.full_url].encode("utf-8")),
    )
    messages = []
    entries = crawl(report=messages.append)
    assert [entry["slug"] for entry in entries] == ["anvil"]
    assert any("skip sports-car-01" in message for message in messages)
    assert "done: 1 entries, 1 failed" in messages


# ---------------------------------------------------------------------------
# Cache and fetch
# ---------------------------------------------------------------------------


def _archive(members: dict) -> bytes:
    """Build a zip in memory from a name -> text mapping."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in members.items():
            archive.writestr(name, text)
    return buffer.getvalue()


@pytest.fixture
def offline_cache(tmp_path, monkeypatch):
    """Redirect the cache to tmp_path and serve every download from memory.

    Yields a ``calls`` list that records each requested URL.
    """
    monkeypatch.setattr(mesh_cache, "cache_dir", lambda: tmp_path)
    calls = []
    bodies = {
        "https://x/anvil.zip": _archive({"anvil.fbx": "x", "anvil.obj": OBJ}),
        "https://x/noobj.zip": _archive({"noobj.fbx": "x", "noobj.glb": "y"}),
    }

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        return _Response(bodies[request.full_url])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


def test_fetch_writes_the_obj_and_never_downloads_it_twice(offline_cache):
    entry = {"slug": "anvil", "download_url": "https://x/anvil.zip"}
    path = fetch(entry)
    assert path == cached_path("anvil")
    assert path.read_text(encoding="utf-8") == OBJ
    assert offline_cache == ["https://x/anvil.zip"]

    assert fetch(entry) == path
    assert offline_cache == ["https://x/anvil.zip"]


def test_a_truncated_download_exits_with_the_fetch_hint_not_a_traceback(
    offline_cache, monkeypatch, capsys
):
    monkeypatch.setattr(mesh_crawl, "RETRY_DELAY_S", 0)

    def truncated(request, timeout=None):
        offline_cache.append(request.full_url)
        raise http.client.IncompleteRead(b"partial")

    monkeypatch.setattr(urllib.request, "urlopen", truncated)
    monkeypatch.setattr(sys, "argv", ["wireframe", "--model", "anvil"])
    assert wireframe.main() == 1
    assert "mesh fetch anvil" in capsys.readouterr().err
    assert len(offline_cache) == 2  # the first attempt and its one retry


def test_an_archive_without_an_obj_is_reported_with_the_formats_it_has(offline_cache):
    with pytest.raises(MeshFetchError) as excinfo:
        fetch({"slug": "noobj", "download_url": "https://x/noobj.zip"})
    assert "no OBJ" in str(excinfo.value)
    assert "FBX, GLB" in str(excinfo.value)
    assert not cached_path("noobj").exists()


def _run_mesh(monkeypatch, *args):
    """Call the mesh CLI in-process so the redirected cache applies."""
    monkeypatch.setattr(sys, "argv", ["svg-infographics mesh", *args])
    return mesh.main()


def test_path_prints_a_cached_mesh_and_fails_loudly_on_a_cold_one(
    offline_cache, monkeypatch, capsys
):
    assert _run_mesh(monkeypatch, "path", "anvil") == 1
    assert "mesh fetch anvil" in capsys.readouterr().err

    cached_path("anvil").write_text(OBJ, encoding="utf-8")
    assert _run_mesh(monkeypatch, "path", "anvil") == 0
    assert capsys.readouterr().out.strip() == str(cached_path("anvil"))


def test_fetch_skips_the_archive_without_an_obj_and_exits_non_zero(
    offline_cache, monkeypatch, capsys
):
    monkeypatch.setattr(
        mesh, "entry_for", lambda slug: {"slug": slug, "download_url": f"https://x/{slug}.zip"}
    )
    assert _run_mesh(monkeypatch, "fetch", "anvil", "noobj") == 1
    captured = capsys.readouterr()
    assert "fetched" in captured.out
    assert "noobj: archive has no OBJ" in captured.err
    assert cached_path("anvil").is_file()


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def _run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True)


def test_search_through_the_unified_cli_prints_ranked_slugs():
    result = _run_cli("mesh", "search", "anvil", "--top", "3")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0].split()[1] == "anvil"


def test_list_through_the_unified_cli_filters_by_category():
    result = _run_cli("mesh", "list", "--category", "Animals")
    assert result.returncode == 0, result.stderr
    assert "assets" in result.stderr
    assert all("Animals" in line for line in result.stdout.splitlines() if line.strip())


def test_categories_through_the_unified_cli_counts_the_library():
    result = _run_cli("mesh", "categories")
    assert result.returncode == 0, result.stderr
    assert "CC0 from thebasemesh.com" in result.stdout
    assert "Animals" in result.stdout
