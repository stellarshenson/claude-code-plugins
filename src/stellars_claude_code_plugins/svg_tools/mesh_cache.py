"""On-disk cache of downloaded meshes.

One OBJ per asset at ``~/.cache/svg-infographics/meshes/<slug>.obj``. The archive
is unpacked from memory, so no zip is ever left on disk, and a slug already in
the cache is never downloaded again.

Tests point the cache elsewhere by monkeypatching :func:`cache_dir`.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
import zipfile

from stellars_claude_code_plugins.svg_tools.mesh_crawl import TRANSIENT, http_get

_CACHE_DIR = "~/.cache/svg-infographics/meshes"


class MeshFetchError(RuntimeError):
    """A mesh could not be downloaded, or its archive carries no OBJ."""


def cache_dir() -> Path:
    """Directory holding cached meshes. Monkeypatch this to relocate the cache."""
    return Path(os.path.expanduser(_CACHE_DIR))


def cached_path(slug: str) -> Path:
    """Path a mesh occupies once cached, whether or not it is there yet."""
    return cache_dir() / f"{slug}.obj"


def extract_obj(archive: bytes, slug: str) -> bytes:
    """Return the first OBJ member of a zip archive.

    Args:
        archive: Raw zip bytes.
        slug: Asset slug, for the error message.

    Returns:
        bytes: Contents of the OBJ member.

    Raises:
        MeshFetchError: The archive is unreadable or holds no ``.obj`` member.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            names = zf.namelist()
            for name in names:
                if name.lower().endswith(".obj"):
                    return zf.read(name)
    except zipfile.BadZipFile as exc:
        raise MeshFetchError(f"{slug}: archive is not a readable zip ({exc})") from exc
    formats = sorted({Path(n).suffix.lstrip(".").upper() for n in names if Path(n).suffix})
    raise MeshFetchError(f"{slug}: archive has no OBJ, only {', '.join(formats) or 'no files'}")


def fetch(entry: dict) -> Path:
    """Download an asset's archive and cache its OBJ. Idempotent.

    Args:
        entry: Catalogue entry, needing at least ``slug`` and ``download_url``.

    Returns:
        Path: The cached OBJ. Already-cached meshes are returned untouched.

    Raises:
        MeshFetchError: The download failed, or the archive holds no OBJ.
    """
    slug = entry["slug"]
    destination = cached_path(slug)
    if destination.is_file():
        return destination
    try:
        archive = http_get(entry["download_url"])
    except TRANSIENT as exc:
        raise MeshFetchError(f"{slug}: download failed ({exc})") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(extract_obj(archive, slug))
    return destination
