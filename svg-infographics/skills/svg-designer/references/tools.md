# SVG Infographics Toolbox

Tool palette for svg-infographics. Every coordinate, colour, connector, placement = tool call.

```
svg-infographics
 |
 |-- primitives <shape>          Shape geometry + named anchors
 |   |-- rect                    Rectangle. --x --y --w --h [--mode filled|outline|wire]
 |   |-- square                  Square. --x --y --size
 |   |-- circle                  Circle. --x --y --r
 |   |-- ellipse                 Ellipse. --x --y --rx --ry
 |   |-- diamond                 Diamond/rhombus. --x --y --w --h
 |   |-- hexagon                 Hexagon. --x --y --r [--flat-top]
 |   |-- star                    Star polygon. --x --y --r --points
 |   |-- arc                     Arc segment. --x --y --r --start-deg --end-deg
 |   |-- gear                    Toothed gear. --x --y --outer-r [--teeth 12 --inner-r]
 |   |-- cloud                   Cloud shape. --x --y --w --h [--lobes 5]
 |   |-- document                Dog-ear page. --x --y --w --h [--fold]
 |   |-- pyramid                 Isometric 3D pyramid. --x --y --base-w --height
 |   |-- cube                    Isometric cube. --x --y --size [--mode wire]
 |   |-- cuboid                  Isometric cuboid. --x --y --w --h --d
 |   |-- cylinder                Isometric cylinder. --x --y --r --h
 |   |-- sphere                  Wireframe sphere. --x --y --r
 |   |-- plane                   Ground plane. --x --y --w --h
 |   |-- axis                    3-axis coordinate system. --x --y --length
 |   '-- spline                  PCHIP curve through waypoints. --points "x1,y1 x2,y2 ..."
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
 |       |-- --tension           Strand stiffness 0-1 (default 0.75). Increase if crossing
 |       |-- --shape             Sub-strand shape: straight|l|l-chamfer|spline
 |       |-- --align-elbows      Aligned L-elbows for clean rail-style routing
 |       '-- --organic           Force-based strand relaxation
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
 |   '-- --edges-only            Ignore fills, only edges/text as obstacles (for decoration placement)
 |
 |-- charts <type>               Pygal SVG charts
 |   |-- line | bar | hbar       Standard chart types
 |   |-- area | radar | dot      Distribution charts
 |   |-- histogram | pie         Frequency charts
 |   |-- --colors / --colors-dark  BOTH required. WCAG contrast audit on every series
 |   '-- --theme                 Theme preset name
 |
 |-- shapes                      draw.io stencil library (downloaded on demand)
 |   |-- index --source URL      Download + cache a library
 |   |-- search "query"          Fuzzy search by name/category
 |   |-- render --name X         Render at target size, returns primitives-compatible result
 |   '-- catalogue --category X  Visual SVG grid of all shapes in category
 |
 |-- VALIDATORS (quality panel - all six MUST pass before delivery)
 |   |-- overlaps                Text/shape overlap, spacing rhythm, font floors, callout collisions
 |   |-- contrast                WCAG 2.1 AA/AAA in both light and dark mode
 |   |-- alignment               Grid snapping, vertical rhythm, layout topology
 |   |-- connectors              Zero-length, edge-snap, missing chamfers, dangling endpoints
 |   |-- css                     Inline fills, forbidden colours, missing dark-mode overrides
 |   '-- collide                 Pairwise connector intersection with near-miss detection
 |
 |-- render-png                    SVG to PNG via Playwright (evaluates CSS media queries)
 |   |-- --mode light|dark|both   Colour scheme. "both" creates .light.png + .dark.png
 |   |-- --width N                Output width px (default 3000)
 |   '-- --bg "#hex"              Background colour (default: transparent)
 |
 '-- COMMANDS (user-invoked)
     |-- /svg-infographics:create        Full 6-phase workflow
     |-- /svg-infographics:theme         Generate/update theme swatch
     |-- /svg-infographics:validate      Run all validators
     |-- /svg-infographics:fix           Fix layout/style/contrast/connectors (argument describes intent)
     |-- /svg-infographics:beautify      Additive decoration pass (7 dimensions x 4 levels, geometry-guarded)
     '-- /svg-infographics:export-png    Render SVG to PNG (light/dark/both, transparent bg)
```

## Quick lookup

| Need | Tool |
|------|------|
| Place a shape | `primitives <shape>` |
| Connect two shapes | `connector --mode l-chamfer --src-rect ... --tgt-rect ... --standoff 2` |
| Route around obstacles | `connector --auto-route --svg scene.svg --standoff 2` |
| Fan N sources to M sinks | `connector --mode manifold --standoff 2` |
| Align cards in a row | `geom align --edge top --rects "[...]"` |
| Equal spacing | `geom distribute --axis h --rects "[...]"` |
| Stack vertically | `geom stack --axis v --gap 12 --rects "[...]"` |
| Snap to card edge | `geom attach --shape rect --geometry x,y,w,h --side right` |
| Place labels | `callouts --svg scene.svg --plan callouts.json` |
| Find empty space | `empty-space --svg scene.svg` |
| Check before delivery | `overlaps` + `contrast` + `alignment` + `connectors` + `css` + `collide` |
| Add visual richness | `/svg-infographics:beautify file.svg medium` |
| Search for icons | `shapes search "database"` |
| Export SVG to PNG | `render-png input.svg output.png --mode both --width 3000` |
