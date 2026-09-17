---
name: project-basemesh-wireframe
description: thebasemesh.com crawl quirks, the mesh cache layout, and what the CC0 library actually contains (props, not vehicles or creatures)
metadata:
  type: project
---

`svg-infographics mesh` + `svg-infographics wireframe` (modules `mesh*.py`,
`obj_mesh.py`, `wireframe*.py` in `svg_tools/`). Catalogue is package data at
`svg_tools/data/basemesh_catalog.json`, declared in `pyproject.toml` under
`[tool.setuptools.package-data]` as `"...svg_tools" = ["data/*.json"]`.

## Site facts the code depends on (Wix)

- Asset list: `/sitemap.xml` → the child whose name contains `dynamic-asset`
  (the rest of that name is a UUID, so match on the prefix, never the full URL).
- Each `/asset/<slug>` page embeds its database record in
  `<script type="application/json" id="wix-warmup-data">`, under a
  `recordsByCollectionId` dict nested at `appsWarmupData.dataBinding.dataStore`.
  A page carries ~13 records: its own plus the site's "latest" strip, so pick
  the one whose `link-test-1-title` equals `/asset/<slug>`.
- Record fields: `title`, `food` (the **category list** - misleading name),
  `triCount`, `download`. No tags and no description exist anywhere on the page.
- `download` is `wix:document://v1/archives/<id>.zip/<name>.zip` and converts to
  `https://www.thebasemesh.com/_files/archives/<id>.zip?dn=<name>.zip`.
- Zips hold FBX + GLB + OBJ (quad topology, Y up, Blender export). Never triangulate.

## Traps

- **`.gitignore` has a bare `data/` rule** (line ~129, for OpenVINO datasets), so
  any new `*/data/` package-data directory is silently untracked and ships in no
  clone. Follow the existing `document_processing/models/` exception pattern:
  negate the directory *and* the glob, in that order - a negated file alone does
  not work once the parent directory is excluded.

- **`http.client.IncompleteRead` is neither `OSError` nor `ValueError`.** A first
  crawl died at page ~570 because `except OSError` missed it. `_TRANSIENT` in
  `mesh_crawl.py` names `http.client.HTTPException` explicitly. Any long crawl
  over this site will hit truncated chunked responses.
- **A burst of pages can arrive without their warmup record.** Nine consecutive
  assets (pool-ladder-01 .. paintbrush-02) parsed as "no database record"; the
  same URLs parsed fine minutes later. `fetch_entry` retries a *parse* failure,
  not only a transport failure, for exactly this.
- A full crawl is 1254 pages at ~1.5 s each plus a 0.3 s delay: **about 45
  minutes**, ~270 MB with `Accept-Encoding: gzip` (930 KB per page uncompressed).
  Run it detached with `run_in_background`; a plain `nohup ... &` inside a Bash
  tool call is killed when the call returns.

## What the library holds

1,254 assets, 30 categories, biggest first: Urban 212, Home 189, Decorative 118,
Industrial 112, Architectural 97. Props and set dressing, not subjects.

- `Buildings` (38) is genuine: `building-residential-*`, `building-industrial-*`,
  `building-tower-*`, `church-01`, `cooling-tower`.
- `Transportation` (24) holds vehicle *parts* - tyres, hubcaps, rail profiles,
  traffic cones. The only whole vehicles are `wooden-boat-01` and `glider`.
- `Animals` (12) is animal-adjacent props plus two real forms: `deer-head` and
  `duck-sculpture`. The rest are horse shoes, antlers, a kennel.
- `Nature` (33) is rocks, logs, mushrooms, shells and leaves. **No trees, no plants.**
- **Human figures: none.** A name search over the whole catalogue turns up only
  `peg-person` (a toy peg) and `skull-(no-teeth)`.

Do not promise a car, a dog or a tree to a caller without checking first.

Model orientation is per-asset: `deer-head` faces along its own -X, so the
default three-quarter view (yaw 35) shows it nose-on and unreadable; `--yaw 110`
gives the profile. Always eyeball a new slug before shipping it.

## Cache

`~/.cache/svg-infographics/meshes/<slug>.obj`, one OBJ per asset, extracted from
the zip in memory (no zip ever lands on disk). Tests relocate it by
monkeypatching `mesh_cache.cache_dir` - there is no environment variable, which
matches `drawio_shapes.py`'s module-level `CACHE_DIR` convention.
