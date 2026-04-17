# svg-infographics-beautify directive (project-local)

Local beautify rules for THIS project. Questionnaire lives in the `/svg-infographics:beautify` command. This file stores answers and history.

## Standing directive overrides

None. Using shipped defaults from the command (13 standing directives including 0.10 bg opacity cap, in-family colour only, icon-per-item, hard validation gates, push-hue-harder per directive #13).

### Local enforcement: DO NOT CHANGE GEOMETRY (absolute)

UNDER NO CIRCUMSTANCES change geometry unless I explicitly ask. No original `<path>`, `<line>`, `<rect>`, `<circle>`, `<polygon>` may be moved, resized, rewritten, or deleted. Decorations in a SEPARATE `<g id="beautify-decorations">` group. Post-pass: count each element tag in the original vs output; every original count preserved (output ≥ original per tag). If any count dropped: FIX IN PLACE - copy the missing elements from the original into the output file, keep the decorations. Do not revert the whole pass.

## Creative brief (rewritten each run, free-text from user)

Medium-intensity beautification pass on article 02 SVGs. Goal: lift the plain card grids to a distinctive futuristic-tech look without redesigning them. Moderate hue changes on cards stay within the Stellars-Tech family (teal can drift to cyan / blue-teal / sky-teal, amber to ochre / copper); no greens, no violets, no reds. Every repeating card / pillar / phase / tool-tile gets its own hue variant on body + stroke + accent bar - visible rhythm across the row, not timid tinting. Icons on every visible item (one per card / bullet / tool). Futuristic flourishes here and there: corner brackets, tech-line marks, scan-line accents, subtle bracket decorations. Decorative particles in the whitespace. Background textures are barely-visible (≤ 10% opacity, HARD CAP) - dendrite / circuit-trace / topo / grid themes chosen per-file to match domain. Selective glow where it matters: focal borders, titles, accent bars, gate diamonds. All placement validated via tools (`empty-space`, `geom align`). Zero container overflow, zero text-text overlaps, WCAG AA preserved.

## Resolved pattern (rewritten by the command each run)

```yaml
# last update: 2026-04-16
target_files:
  - docs/medium/images_article_02/01-five-defects.svg
  - docs/medium/images_article_02/02-three-pillars.svg
  - docs/medium/images_article_02/03-six-phase-workflow.svg
  - docs/medium/images_article_02/04-tools-inventory.svg
  - docs/medium/images_article_02/05-failfirst-flow.svg
  - docs/medium/images_article_02/06-manifold-showcase.svg
  - docs/medium/images_article_02/07-theme-approval.svg
  - docs/medium/images_article_02/08-charts-showcase.svg
output_suffix: "+"
level: medium
colour: moderate   # push-hue-harder per directive #13, wide in-family drift
shapes: moderate
icons:
  mode: per-item
  library: lucide
  per_card_count: 1
embroidery: moderate
abstract: moderate
bg_texture:
  # per-file theme, chosen to match domain:
  # 01 five-defects    -> neural/dendritic (failure-mode fan-out)
  # 02 three-pillars   -> circuit/PCB traces (geometry-painting-validation)
  # 03 six-phase       -> topographic contours (process-as-journey)
  # 04 tools-inventory -> grid/technical (engineering drawing)
  # 05 failfirst-flow  -> circuit/PCB traces
  # 06 manifold        -> circuit/PCB traces (wire merging)
  # 07 theme-approval  -> organic/geometric swatch grid
  # 08 charts-showcase -> grid/technical (chart plotting)
  theme: per-file
  max_opacity: 0.10
glow:
  mode: connectors+titles
  palette: dual
  std_dev_cool: 2
  std_dev_warm: 1.5-1.8
validation_strictness: strict-errors-only
```

## History (append-only)

```
# 2026-04-16 - 01-five-defects+.svg / 02-three-pillars+.svg - medium - OK (27.7KB / 23.9KB, 0 container-overflow, WCAG AA)
# 2026-04-16 - 03-six-phase-workflow+.svg / 04-tools-inventory+.svg - medium - OK (24.7KB / 26.9KB)
# 2026-04-16 - 01-03 per-card hue variants added (card-body-N / card-stroke-N classes, 5/3/6 variants, dark-mode overrides) - OK
# 2026-04-16 - 05-failfirst-flow+.svg / 07-theme-approval+.svg - medium - OK
# 2026-04-16 - 06-manifold-showcase+.svg / 08-charts-showcase+.svg - medium - OK
# 2026-04-16 - 11-connector-modes+.svg / 12-honeycomb+.svg - medium - OK (22.1KB / 17.2KB, 0 container-overflow, WCAG AA preserved)
# 2026-04-16 - 16-algorithm-stack+.svg / 17-self-documenting+.svg - medium - OK (20.5KB / 23.1KB, 0 container-overflow, WCAG AA preserved, all tag counts >= original)
# 2026-04-16 - 18-failure-driven-development+.svg / 19-scientific-method+.svg - medium - OK (25.7KB / 32.3KB, geometry preserved vs baseline, 4 defect+4 tool hue variants 18 circuit theme, 3 zone+4 hist hue variants 19 neural theme, WCAG AA preserved, 19 retains baseline container-overflow warnings only, no new ones)
# 2026-04-16 - 13-constellation+.svg - medium - OK (71.9KB, 6 per-hub hue variants (4 teal + 2 ochre drift), organic/dendritic bg, orbit rings + starbursts + sparkle icons on focal hubs, dual-palette glow on cores, geometry preserved vs baseline, WCAG AA preserved)
# 2026-04-16 - 14-container-routing+.svg - medium - OK (17.0KB, 2 card + 4 obstacle hue variants, circuit/PCB bg, corner brackets on cards + obstacles, 5 lucide icons (card-A box, card-B package, src play, tgt target, dst flag), cyan+warm glow on title + route, geometry preserved, baseline WCAG carry-over only)
# 2026-04-16 - 15-design-app-analogy+.svg - medium - OK (27.3KB, 10 per-row hue variants (5 teal + 5 ochre drifts), grid/technical bg texture, corner brackets on every card, 10 lucide row icons, scan lines under each card title, dual-palette glow on title + column headers, geometry preserved, baseline container-overflow carry-over only (checker limitation - g#row-N bbox excludes row content))
```
