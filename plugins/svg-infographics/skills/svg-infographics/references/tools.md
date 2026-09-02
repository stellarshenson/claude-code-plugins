# SVG Infographics Toolbox

Tool palette for svg-infographics. Every coordinate, colour, connector, placement = tool call.

Live roster: `svg-infographics --help` (grouped, one line each) and `svg-infographics <subcommand> --help` (flags). The tree below is the map; when they disagree, `--help` is the truth.

```
svg-infographics
 |
 |-- primitives <shape>          Shape geometry + named anchors (run bare or --list / --caveman for the full catalogue)
 |   |-- rect                    Rectangle. --x --y --width --height [--radius] [--accent]
 |   |-- square                  Square. --x --y --size [--radius]
 |   |-- circle                  Circle. --cx --cy --r
 |   |-- ellipse                 Ellipse. --cx --cy --rx --ry
 |   |-- diamond                 Diamond/rhombus. --cx --cy --width --height
 |   |-- hexagon                 Hexagon. --cx --cy --r [--pointy-top]
 |   |-- star                    Star polygon. --cx --cy --r [--inner-r --points]
 |   |-- arc                     Arc segment. --cx --cy --r --start --end (degrees)
 |   |-- gear                    Toothed gear. --x --y --outer-r [--inner-r --teeth --mode filled|outline]
 |   |-- cloud                   Cloud shape. --x --y --w --h [--lobes 5 --mode filled|outline]
 |   |-- document                Dog-ear page. --x --y --w --h [--fold --mode filled|outline]
 |   |-- pyramid                 Isometric 3D pyramid. --x --y --base-w --height [--mode filled|wire]
 |   |-- cube                    Isometric cube. --x --y --width --height [--depth --mode fill|wire]
 |   |-- cuboid                  Isometric cuboid. --x --y --width --height --depth [--mode fill|wire]
 |   |-- cylinder                Isometric cylinder. --cx --cy --rx --ry --height [--mode fill|wire]
 |   |-- sphere                  Wireframe sphere. --cx --cy --r [--mode fill|wire]
 |   |-- plane                   Ground plane. --x --y --width --depth [--tilt]
 |   |-- speech                  Speech bubble + callout spike. --x --y --w --h [--tip-x --tip-y] [--shape rect|soft-rect|ellipse] [--rx --ry] [--id NAME]
 |   |-- thought                 Thought cloud + decreasing-bubble trail. --x --y --w --h [--tip-x --tip-y] [--trail-bubbles N] [--id NAME]
 |   |-- axis                    3-axis coordinate system. --origin "x,y" --length [--axes x|y|xy|xyz --ticks --tick-spacing --no-labels]
 |   '-- spline                  PCHIP curve through waypoints. --points "x1,y1 x2,y2 ..." [--samples --closed]
 |
 |-- connector --mode <m>        Connector routing (5 modes)
 |   |-- straight                Direct line. Auto edge-snap via --src-rect / --tgt-rect
 |   |-- l                       Right-angle bend, sharp corners
 |   |-- l-chamfer               Beveled corners. Auto-route, straight-line collapse, stem-min
 |   |   |-- --auto-route        A* grid routing around obstacles. Requires --svg
 |   |   |-- --container-id      Clip routing inside a specific shape
 |   |   |-- --straight-tolerance  Collapse near-aligned to straight (default 20px)
 |   |   '-- --stem-min          Min cardinal stem behind arrowhead (default 20px)
 |   |-- spline                  Smooth PCHIP or cubic Bezier with tangent dirs
 |   '-- manifold                Sankey bundle: N->merge->spine->fork->M
 |       |-- --tension           Strand stiffness 0-1 (default 0.5). Increase if crossing
 |       |-- --shape             Sub-strand shape: straight|l|l-chamfer|spline
 |       |-- --align-elbows      Aligned L-elbows for clean rail-style routing
 |       '-- --organic auto|on|off Force-based strand relaxation
 |
 |-- geom <op>                   Alignment, constraints, measurements
 |   |-- POINT/LINE
 |   |   |-- midpoint            Midpoint between two points
 |   |   |-- distance            Distance between two points
 |   |   |-- extend              Extend a line by N px
 |   |   |-- perpendicular       Perpendicular foot from point to line
 |   |   |-- parallel            Parallel line through a point
 |   |   |-- bisector            Angle bisector direction
 |   |   '-- curve-midpoint      Arc-length midpoint + tangent on polyline
 |   |
 |   |-- INTERSECTIONS
 |   |   |-- intersect           Line-line intersection
 |   |   |-- intersect-line-circle  Line-circle intersection points
 |   |   |-- intersect-circles   Circle-circle intersection points
 |   |   '-- tangent             Tangent lines from external point to circle
 |   |
 |   |-- LAYOUT (polar, radial)
 |   |   |-- polar               Point at angle + distance from centre
 |   |   |-- evenly-spaced       N points on a circle
 |   |   '-- concentric          Concentric rings at given radii
 |   |
 |   |-- ATTACHMENT
 |   |   |-- attach              Snap to rect edge (side+pos) or circle perimeter (angle)
 |   |   |-- rect-edge           Ray from centre to rect edge intersection
 |   |   '-- contains            Point/bbox/line/polygon inside outer polygon?
 |   |
 |   |-- ALIGNMENT (multi-rect)
 |   |   |-- align               Align rects: --edge left|right|top|bottom|h-center|v-center
 |   |   |-- distribute          Space evenly: --axis h|v --mode center|gap
 |   |   '-- stack               H-stack or v-stack: --axis h|v --gap N
 |   |
 |   |-- OFFSET
 |   |   |-- offset-rect         Parallel offset (halo, padding)
 |   |   |-- offset-line         Parallel offset of a line
 |   |   |-- offset-polyline     Parallel offset of a polyline
 |   |   |-- offset-circle       Concentric circle offset
 |   |   |-- offset-polygon      Polygon offset
 |   |   '-- offset-point        Point offset from line at parameter t
 |   |
 |   '-- SHAPE ANALYSIS
 |       '-- shape-midpoint      Area-weighted centroid of closed polygon
 |
 |-- boolean --op <op>           Boolean / margin operations on path shapes
 |   |-- union                   A ∪ B - merge filled regions
 |   |-- intersection            A ∩ B - overlap (optional pre-inset both via --margin)
 |   |-- difference              A \ B - subtract (optional inflate B via --margin)
 |   |-- xor                     A △ B - symmetric difference (Inkscape Exclusion)
 |   |-- buffer                  Inflate / deflate one shape. REQUIRED --margin (sign: + grow, - shrink)
 |   |-- cutout                  One-step "cut B from A with N px breathing room". REQUIRED --margin
 |   |-- outline                 One-step closed annulus of width N around boundary. REQUIRED --margin
 |   |-- --join {round,mitre,bevel}    Corner style for buffer-based ops (default round)
 |   |-- --quad-segs N           Round-corner sample count (default 16)
 |   |-- --tolerance N           Polyline simplification (drops curve-flatten noise)
 |   |-- --replace-id ID         In-place rewrite of a named element's d= attribute
 |   '-- --out FILE              Write to file instead of stdout
 |
 |-- callouts                    Joint label placement via greedy solver
 |   |-- --plan callouts.json    JSON list of callout requests
 |   |-- --svg scene.svg         Target SVG for obstacle detection
 |   |-- --container-id          Clip placement inside a shape
 |   |-- leader mode             Line + text, 20px standoff, scored on length/angle
 |   '-- leaderless mode         Text-only, 5px standoff, centre-distance scoring
 |
 |-- empty-space                 Free-region detection
 |   |-- --svg scene.svg         Input SVG
 |   |-- --tolerance N           Min erosion (default 20px)
 |   |-- --min-area N            Drop slivers (default 500)
 |   |-- --container-id          Clip to shape interior
 |   |-- --edges-only            Ignore fills, only edges/text as obstacles (for decoration placement)
 |   |-- --layers a,b            Obstacles ONLY from these canonical layers
 |   |-- --ignore-layers a,b     Obstacles from everything EXCEPT these layers
 |   '-- --verbose               Full boundary polygons (default truncates - bbox is usually enough)
 |
 |-- map                         One-glance occupancy scan (per-layer + global in ONE call)
 |   |-- --svg scene.svg         Input SVG
 |   |-- --cell N                Cell size px (default ~48 columns)
 |   '-- ASCII grid              letter = topmost layer per cell (b/n/c/t/o), '.' = free,
 |                               + per-layer stats + largest free placement rects
 |
 |-- scaffold                    Ready-to-author skeleton for a standard format
 |   |-- --list                  Show presets (doc-stats/timeline/flow/header/grid, slide-16x9/4x3, square)
 |   |-- --format NAME           Canvas preset (viewBox, margins, rhythm)
 |   |-- --cols C --rows R       Grid shape (5px-snapped by design)
 |   |-- --cards N               Placeholder card groups (data-placeholder="true")
 |   |-- --title "..."           Title text placeholder with a reserved band
 |   '-- --out FILE [--force]    Write (refuses overwrite without --force)
 |
 |-- workflow                    Phase inference + next actions from the file itself
 |   |-- --svg file.svg          scaffold / author / content / finalize / ship
 |   |-- --no-finalize           Skip the validator sweep (faster)
 |   '-- --json                  Structured gate report
 |
 |-- preflight                   GATE 1: declare the build via flags -> matching rule bundle + warnings. Before any <rect>
 |-- check                       GATE 2: does the SVG match its declaration? Exit 1 on component drift / missing dark mode
 |-- finalize                    GATE 3: ship-ready. XML + overlap + connector validators in one call; exit 1 on any HARD finding
 |   '-- --checklist             The pre-delivery roster - every row PASS / NA / FAIL / SKIP
 |
 |-- place                       Position an element (icon, text bbox, badge) inside a named container -> top-left (x, y)
 |
 |-- charts <type>               Pygal SVG charts
 |   |-- line | bar | hbar       Standard chart types
 |   |-- area | radar | dot      Distribution charts
 |   |-- histogram | pie         Frequency charts
 |   '-- --colors / --colors-dark  BOTH required. WCAG contrast audit on every series
 |
 |-- shapes                      draw.io stencil library (downloaded on demand)
 |   |-- index --source URL      Download + cache a library
 |   |-- search "query"          Fuzzy search by name/category
 |   |-- render <name>           Render at target size, returns primitives-compatible result
 |   '-- catalogue --category X  Visual SVG grid of all shapes in category
 |
 |-- icons                       Bundled plugin-own icons + catalogue of every route
 |   |-- list [--category X]     Bundled custom icons + pointers to Lucide / draw.io
 |   |-- search "query"          Search bundled icons by name/keyword
 |   '-- render NAME [--size N]  Paste-ready <g>, 24-grid stroke convention
 |
 |-- background --type <texture> Procedural textures: circuit, neural, topo, grid, organic, celtic, scifi, constellation, flourish, geometric, crystalline
 |
 |-- text-to-path                ON REQUEST: text + TTF/OTF -> <path> outlines, no font dependency
 |
 |-- VALIDATORS (finalize runs the gate set in one call; run one singly only to drill into a finding)
 |   |-- overlaps                Text/shape overlap, spacing rhythm, font floors, callout collisions
 |   |-- contrast                WCAG 2.1 AA/AAA in both light and dark mode
 |   |-- alignment               Grid snapping, vertical rhythm, layout topology
 |   |-- connectors              Zero-length, edge-snap, missing chamfers, dangling endpoints
 |   |-- css                     Inline fills, forbidden colours, missing dark-mode overrides
 |   |-- collide                 Pairwise connector intersection with near-miss detection
 |   |-- validate                XML well-formedness + structural sanity: '-- in comment', missing viewBox, empty <path d>
 |   |-- geometry                Element bboxes as JSON, transforms applied - feeds finalize's visual checks
 |   '-- consistency             Cross-file deck check: card anatomy across sibling SVGs
 |
 '-- COMMANDS (user-invoked)
     |-- /svg-infographics:create        Full 6-phase workflow
     |-- /svg-infographics:theme         Generate/update theme swatch
     |-- /svg-infographics:validate      Run all validators
     |-- /svg-infographics:fix           Fix layout/style/contrast/connectors (argument describes intent)
     |-- /svg-infographics:beautify      Additive decoration pass (8 dimensions x 4 levels, geometry-guarded)
     '-- /svg-infographics:export-png    Render SVG to PNG (light/dark/both, transparent bg)

render-png (its own console script, not an svg-infographics subcommand)
 |-- --mode light|dark|both       Colour scheme. "both" creates .light.png + .dark.png
 |-- --width N                    Output width px (default 3000)
 '-- --bg "#hex"                  Background colour (default: transparent)
```

## Quick lookup

| Need | Tool |
|------|------|
| Place a shape | `primitives <shape>` |
| Discover all primitives | `primitives` (bare) or `primitives --list` for the grouped catalogue; `primitives --caveman` for ultra-terse one-liners |
| Speech / quote bubble | `primitives speech --x --y --w --h [--tip-x --tip-y] [--shape rect/soft-rect/ellipse]` |
| Thought bubble | `primitives thought --x --y --w --h [--tip-x --tip-y --trail-bubbles N]` |
| Terse top-level catalogue | `svg-infographics --caveman` / `document-processing --caveman` |
| Connect two shapes | `connector --mode l-chamfer --src-rect ... --tgt-rect ... --standoff 2` |
| Route around obstacles | `connector --auto-route --svg scene.svg --standoff 2` |
| Fan N sources to M sinks | `connector --mode manifold --standoff 2` |
| Align cards in a row | `geom align --edge top --rects "[...]"` |
| Equal spacing | `geom distribute --axis h --rects "[...]"` |
| Stack vertically | `geom stack --axis v --gap 12 --rects "[...]"` |
| Snap to card edge | `geom attach --shape rect --geometry x,y,w,h --side right` |
| Place labels | `callouts --svg scene.svg --plan callouts.json` |
| Find empty space | `empty-space --svg scene.svg` (`--layers` / `--ignore-layers` to scope obstacles) |
| Whole canvas at a glance | `map --svg scene.svg` (per-layer ASCII occupancy + free placement rects) |
| Start a new SVG | `scaffold --format slide-16x9 --cols 3 --rows 2 --cards 5 --out file.svg` |
| Where am I / what next | `workflow --svg file.svg` |
| Merge two shapes into one path | `boolean --op union --svg scene.svg --ids a b` |
| Cut a hole with breathing room | `boolean --op cutout --svg scene.svg --ids container hole --margin 4` |
| Stroked-look filled ring | `boolean --op outline --svg scene.svg --ids shape --margin 6` |
| Inflate / deflate a shape | `boolean --op buffer --svg scene.svg --ids shape --margin 8` |
| Check before delivery | `finalize --checklist` - one call; the single validators are for drilling into a finding |
| Declare before building | `preflight` with the flags that describe the build |
| Place an icon or text block | `place --svg scene.svg --container ID --size N ...` |
| Add visual richness | `/svg-infographics:beautify file.svg medium` |
| Browse bundled custom icons | `icons list` |
| Search for icons | `icons search "brain"` (custom) or `shapes search "database"` (draw.io) |
| Export SVG to PNG | `render-png input.svg output.png --mode both --width 3000` |
