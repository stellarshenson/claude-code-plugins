# HN post draft - svg-infographics

Status: ready to paste. The Medium article ["Stop Fixing Your AI's SVGs"](https://medium.com/towards-artificial-intelligence/stop-fixing-your-ai-svgs-715df70ccca0) is the long-form anchor for this post; the title and framing mirror it.

> Don't post if: the marketplace HN post (`hn-post.md`) was posted in the last 3 weeks - HN penalises repeat self-promotion from the same account; or the boolean tool has any open bugs; or you can't be online for 4 hours after posting.

---

## Title (80 char limit)

Pick one. Title is the entire conversion lever.

**Strongest** (mirrors the published article, names the wound):
```
Show HN: Stop Fixing Your AI's SVGs (Python-calculated, 6 validators)
```

**Variant A** (broader audience, agent-agnostic):
```
Show HN: Headless SVG toolkit for AI agents - Python-calculated geometry + validators
```

**Variant B** (lean into the boolean-ops hook, more technical):
```
Show HN: One-step cutout-with-margin for SVG paths (no Inkscape required)
```

**Variant C** (specific receipt as title):
```
Show HN: 9 declarative cutouts replaced ~25 hand-computed rect splits
```

Avoid: "AI-powered SVG", "next-gen", "ecosystem", "framework". HN scans those as bloat.

Recommended: the **strongest** title. It mirrors the article (so search-engine credit accrues to both), states the wound directly, and the parenthetical gives the cure-shape in 3 words.

---

## Body (3 paragraphs + concrete receipts + bullets)

```
You ask Claude (or any agent) for "an architecture diagram." It ships an
SVG with text overlapping connectors, no dark mode, contrast failures, and
a <path d="M ..."> glued together by hand. You spend twice as long fixing
the output as you would have spent drawing it.

I built svg-infographics, a Claude Code plugin that makes that impossible.
Every coordinate is computed via a Python CLI calculator (rect / circle /
hex / star / cube / cylinder / spline / connector / boolean). Every colour
traces to an approved theme swatch with a @media (prefers-color-scheme:
dark) block. Six independent validators block delivery on overlap /
contrast (WCAG 2.1) / alignment / connector quality / CSS compliance /
pairwise connector collisions. A stop-and-think warning gate forces a
conscious ack with terse reasoning per finding before any producer tool
emits its primary output, so warnings cannot scroll past unread.

13 CLI tools total (6 validators + 7 calculators). 60+ production examples
in the repo (mix of card grids, pipelines, scorecards, headers, timelines,
manifold connectors). All run headless - no browser, no Inkscape, no
Figma. The recent addition is headless boolean operations on path shapes:
union / intersection / difference / xor (the Inkscape Path menu) PLUS
one-step buffer (Inset / Outset), cutout-with-margin (subtract B inflated
by N units from A), and outline-as-band (closed annulus of width N around
a shape's boundary). The cutout-with-margin and outline-as-band primitives
are NOT exposed as one-button operations by Inkscape, Illustrator,
Affinity, Figma, Sketch, or CorelDRAW - each requires a 2-step workflow
there. Bundling them as primitives is the agentic value-add.

Real session feedback after using the boolean cutout to punch 9
lightning-glyph holes (with 10 px breathing-room margins) into a 9-bar
chart - replacing ~25 manually-computed rect splits per row with 9
declarative cutout calls:

  "Output was multipolygon paths (2 disconnected islands per bar) with
  curved edges that follow the lightning's actual silhouette - not
  approximated rectangular gaps. One-step cutout-with-margin (Inkscape /
  Illustrator need 2 steps). Deterministic warning tokens that block
  until acknowledged caught two intentional conditions and forced a
  conscious ack rather than silently producing weird output. In-place
  rewrite via --replace-id kept the SVG structure intact, just swapped
  each bar's d= attribute. Output validates clean (svg-infographics
  validate 0 issues, contrast AAA 6/6 text pass)."

A few patterns worth pulling out:

- Stop-and-think warning gate. Every producer tool (calc_connector,
  charts, drawio_shapes, empty-space, finalize, boolean) blocks output on
  any warning until acknowledged with --ack-warning TOKEN=reason. Tokens
  are deterministic SHA-256(canonical_argv, warning_text)[:8] so reruns
  reproduce them. Forces a conscious per-finding decision instead of
  letting warnings scroll past.

- Comment preservation. The boolean tool's --replace-id mode previously
  stripped <!-- agent annotations --> on rewrite. Now it preserves them
  via ET.TreeBuilder(insert_comments=True) AND fires a COMMENTS-NEED-REVIEW
  gate warning listing every comment with line number and nearest id - the
  agent must verify each still describes the (possibly changed) structure
  given the rewrite. No copy-paste burden in the 95% case where the
  comment still applies.

- Five connector routing modes. Straight, L (right-angle), L-chamfer
  (softened corner), spline (PCHIP / cubic Bezier), manifold (Sankey
  bundle: N starts converge through a shared spine, fork to M ends). All
  with grid A* auto-routing around obstacles, container-scoped routing
  inside a named shape, straight-line collapse for near-aligned endpoints,
  stem preservation guaranteeing clean cardinal segments behind
  arrowheads.

Open source, MIT. Runs as a Claude Code plugin (skills + commands + YAML)
plus a Python package (pip install stellars-claude-code-plugins) that ships
the deterministic CLIs.

Long-form on the design philosophy: <medium link>
Showcase folder with 10 picked production examples + 4 devils-advocate
analyses + 3 autobuild iteration trajectories: <link to showcase/>
Repo: https://github.com/stellarshenson/claude-code-plugins

Honest disclaimers:

- It's Claude-Code-first. The CLIs are agent-agnostic Python (you can
  shell out from any agent or build script), but the plugin install is
  /plugin marketplace add ... which is Claude-specific.
- Boolean ops are polygon-only via shapely. Bezier / Arc inputs are
  flattened to polylines (lossy round-trip), surfaced via a CURVE-FLATTENED
  warning. For curve-preserving ops use Inkscape interactively. For
  cards / hexagons / banners / connectors / rounded rects we actually
  generate, the polygon round-trip is fine.
- Dark mode requires a CSS class. Inline fills break the gate. Some users
  find the discipline annoying; that's the point.

Happy to take "your validator is overzealous" / "why not D3" / "why
not graphviz" critiques.
```

Word count: ~620. Longer than the marketplace HN post (340) because the boolean-ops + comment-preservation patterns are technical and worth pulling out for the HN audience. Trim if it scrolls past your reader's first screen.

---

## Anticipated comments + pre-drafted replies

**"Why not D3 / Vega-Lite / Observable Plot?"**

> Different problem. D3 et al render data into SVG; svg-infographics builds the SVG that surrounds the chart - the architecture diagram, the card grid, the manifold connector ribbon, the scorecard. The two compose: charts via pygal (themed for light/dark with WCAG audit), surrounded by validated infographic structure. If you only need the chart and not the diagram, D3 is fine.

**"Why not graphviz / Mermaid?"**

> Both produce diagrams; neither lets the agent author the geometry. graphviz commits you to the dot algorithm's layout decisions - acceptable for graph topology, terrible for "I want this card top-left at exactly x=200, y=120 with a 4px corner radius matching the theme swatch." Mermaid is text-driven and fast for code documentation, but layout and styling control are limited and dark-mode rendering is fragile across renderers. svg-infographics is for production deliverables where the agent has to commit to specific coordinates and a specific theme - typically client decks, research papers, technical proposals. It's the slower, harder path. For internal architecture sketches, Mermaid is the right tool.

**"Why not Inkscape / Illustrator + an MCP?"**

> Tried that direction. The Inkscape command-line surface is real but the agent can't see what it produced - no visual-feedback loop without Playwright + render-png + validators. svg-infographics inverts the loop: the agent works in headless code, the validators are the "eyes" that catch overlap / contrast / alignment / connector / CSS / collision findings before delivery, render-png is for the human at the end. The validator-first design is what makes the agent loop converge instead of doom-spiral.

**"Is this just SVG validation? validator.w3.org has existed forever."**

> No - those validate XML well-formedness and DTD compliance. svg-infographics' six validators check overlap detection (text/shape pixel-level via svgelements rasterisation + Pillow font metrics), WCAG 2.1 AA/AAA contrast in BOTH light and dark mode (most validators only do one), grid/rhythm alignment, connector geometry quality (zero-length, edge-snap, missing chamfers, dangling endpoints), CSS class compliance (catches inline fills that should be classes), and pairwise connector collision detection (crossing, near-miss with tolerance). Each validator is a separate CLI subcommand, individually invocable, individually gated.

**"Polygon-only boolean ops are limiting."**

> Yes, that's the trade-off. shapely is polygon-only and lives in 90% of CAD / GIS / 3D-printing toolchains for good reason - it's robust, well-tested, no new deps for us. Curve-rich input (cubic Beziers, arcs) flattens to polylines, surfaced via a CURVE-FLATTENED warning the agent has to ack. For organic curve-preserving ops (icon offsets in Illustrator output) use Inkscape interactively. For cards / hexagons / banners / rounded rects / annotated chart bars - what infographic SVGs actually contain - polygon ops are fine. Swap to skia-python or pyclipper2 is local to two functions if curve preservation ever becomes hard-required.

**"Why not just use Tailwind / DaisyUI / pre-baked SVG kits?"**

> Pre-baked kits are great when your needs match the kit's library. They're useless when you need a 9-bar chart with lightning glyphs cut into each bar and 10px breathing-room margins around the cutouts (real session). The CLIs are for the cases the kits don't have - which is what AI agents end up generating most of the time anyway, because clients ask for specific diagrams not stock icons.

**"How do you handle accessibility beyond WCAG contrast?"**

> Honest answer: contrast and dark-mode are the two checks shipped today. Other ARIA / role attribute / readable-text-as-text validators are open work. The framework supports adding new validators (one Python module per check, slot into the finalize gate). Issues / PRs welcome.

**"Star bait."**

> Same charge as last time. Counter: every claim in the README links to a real artefact in the repo. Click `showcase/` - 10 production SVGs, 4 devils-advocate analyses, 3 autobuild trajectories, the grounding CV result. If receipts don't hold up, downvote.

---

## After-action

Whether it goes well or poorly:

- Watch the boolean tool's GitHub issues for the first 24 hours - any
  curve-flattening edge cases people hit will surface fastest under HN
  traffic
- Pin the comments thread URL in `svg-infographics/README.md` for 48h
- Reply to substantive comments within an hour for the first 6h
- If <50 points by hour 4, didn't catch; pull the pin, move on
- If it does catch, the showcase folder will get the most clicks - check
  every link resolves before posting
- The screenshot to attach to the comment thread (NOT the post body) is
  the lightning-glyph chart from the production-feedback session: it's
  visually concrete and the only one in the repo with both before
  (manually-split rects) and after (boolean cutout) shapes available
