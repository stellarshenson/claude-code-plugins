# Examples Index

69 production SVG references. Study before creating. Closest match to target = best starting point.

Recipes below carry the geometry - read the INDEX plus ONE closest example, not 3-5.

## Concept drafts (before any SVG)

The plain-text spec written and approved *before* generation - canvas, theme, every band, the
concrete facts each band carries, data sources, open questions. Draft this first for a deck; build
the SVGs only once the spec is approved.

| File | Description |
|------|-------------|
| `concept_draft_deck.md` | Three-slide deck spec (issues / reranker / grounder) in `svg-infographics` blocks |

## By type

### Card grids

**Recipe** (from `card_grid`): viewBox 800x320 - 10px edge margins - row 1: 4 cards w=185, row 2: 3 cards w=253, h=130, 10px gutters, 20px between rows
- card: square-top/rounded-bottom path (Q r=10), fill accent 0.04 + drop-shadow filter, stroke accent w=1, accent bar rect h=5 op 0.6 flush top
- text at x+20: label 11px/600 accent at y+32, title 14px/700 at y+54 (second line +18), body 10px from y+98 on 14px rhythm
- Lucide icon top-right corner: translate + scale 0.667, stroke-width 2, opacity 0.5
- caption 10px at viewBox bottom (y=312)

| File | Description |
|------|-------------|
| `card_grid` | Basic card grid template |
| `modules_overview_meridian` | 8-module scope card grid |
| `modules_overview_optima_manufacturing` | 6-module scope card grid |
| `opportunity_map_apex_financial` | Four opportunity areas as cards |
| `stability_metrics` | 10 metrics by domain |
| `llm_call_sites_nexus` | LLM engagement matrix as cards |

### Flow diagrams

**Recipe** (from `flow_diagram`): viewBox 800x140 - boxes rect rx=8, w=130-160, h=50-80, fill accent 0.06, stroke w=1.5 - 45-50px gaps between boxes
- arrow: stem line stroke-width 2 op 0.3 + tip polygon `0,0 -10,-5 -10,5` op 0.8, stem ends at back of head
- fork/merge: build arrow horizontal with tip at origin, then `translate(tip) rotate(angle)` - fork up -54.5deg, merge down 29.7deg
- box text centered: title 9-11px/600 fg, sub 8px muted; icon scale 0.583-0.667 stroke-width 2
- vertically centre boxes on a shared midline (y=70); fork targets stack at y=10 and y=80

| File | Description |
|------|-------------|
| `flow_diagram` | Basic flow template |
| `pipeline_flow_nexus` | Ingestion pipeline flow |
| `methodology_flow_meridian` | Analysis pipeline with fork/merge |
| `curing_decision_flow` | 6-level priority chain |
| `10_benchmark_program_flow` | Input/output benchmark flow |
| `ingestion_pipeline_titan_industries` | Data ingestion pipeline |
| `query_flow_titan_industries` | Query flow through system |

### Timelines

**Recipe** (from `timeline`): viewBox 800x120 - track on y=55, stroke-width 3 round-cap op 0.3, drawn as segments with cutouts around milestones (circle r=18 + 20px clearance each side)
- milestone: circle r=18, fill accent 0.06, stroke w=2; Lucide icon inside at translate(cx-7, cy-7) scale 0.583
- date 12px/700 accent above at y=26 (text-anchor middle); label 10px below at y=88, second line y=101 (13px rhythm)
- progress chevrons mid-segment: polygon `x,55 x-10,50 x-10,60` op 0.4
- milestone spacing ~160-180px; first cx=140, track starts x=80

| File | Description |
|------|-------------|
| `timeline` | Basic timeline template |
| `timeline_hexagon` | Hexagon milestone timeline |
| `delivery_timeline_meridian` | 19-week delivery timeline |
| `project_timeline_optima_manufacturing` | 10-month project timeline |

### Architecture / hub-and-spoke

**Recipe** (from `cognitive_architecture_apex_financial`): viewBox 800x130 - layered stack: full-width bands rect rx=4, h=28-32, x=20 w=760, 12-14px vertical gaps
- band: fill accent 0.08-0.12, top accent strip rect h=3 op 0.4-0.5; bottom layer may use square-top/rounded-bottom path
- band text on one baseline: layer name 9-10px/600 at x+10, item labels 7px muted spread along the band
- inter-layer connectors: vertical line stroke-width 0.75 op 0.4 + small polygon tip (6px base), label 6px letter-spacing 1 centered in gap
- CSS classes fg-1..fg-3 with `@media (prefers-color-scheme: dark)` overrides

| File | Description |
|------|-------------|
| `architecture_overview_titan_industries` | System architecture overview |
| `cognitive_architecture_apex_financial` | Cognitive services layer |
| `hybrid_architecture_nexus` | Hybrid architecture overview |
| `tracking_solution_optima_manufacturing` | Production tracking architecture |
| `type_hierarchy` | Type hierarchy and self-evolution |
| `delivery_model_optima_manufacturing` | Hybrid delivery model |

### Banners and headers

**Recipe** (stats, from `stats_banner`): viewBox 800x100 - N stats on even centres (text-anchor middle) - number 28px/700 at y=34, label 11px at y=52, sub 8px at y=64 - vertical dividers between stats, y=16..70, stroke w=1 op 0.15

**Recipe** (header, from `header_banner_nexus`): viewBox 800x120 - left text block at x=40: title 20px/700 y=36, subtitle 14px/600 y=58, description 11px y=80, meta 10px y=98
- bottom accent bar: rect 0,110 800x10, linearGradient primary→accent, op 0.6
- decorative motif right side (~x=650-760), group opacity 0.35
- fg text via CSS classes with dark-mode overrides

| File | Description |
|------|-------------|
| `stats_banner` | Basic stats banner template |
| `stats_banner_meridian` | Key metrics horizontal banner |
| `header_banner_apex_financial` | Partnership opportunity header |
| `header_banner_meridian` | Project proposal header |
| `header_banner_nexus` | Design document header |
| `header_banner_optima_manufacturing` | Project proposal header |
| `header_banner_titan_industries` | Presentation header |
| `header_banner_verdant_grounds` | Engagement / architecture doc header - kicker, route-pin motif, gradient monogram |
| `header_cover_banner_halcyon_labs` | Whitepaper cover banner (Pattern B, 800×170) - brand logo-mark variant |
| `landscape_apex_financial` | Estate overview with key stats |

### Data visualisation

**Recipe** (h-bar chart, from `07_retrieval_rank_distribution`): viewBox 800x260 - title 10px/600 letter-spacing 1 centered y=18, subtitle 8px y=32
- row labels text-anchor=end at x=100; bar area x=120, full track w=480, bar h=18, stride 30, rx=3
- track fill accent 0.06; filled bar same accent 0.3, width = pct x 480; value label 8px placed 8px past fill end
- highlight row: alternate accent (teal) with stroke w=0.8 + bold label
- takeaway notes bottom-left: 9px/600 heading + 8px lines on 16px rhythm

| File | Description |
|------|-------------|
| `15_logistic_regression_2d` | 2D decision boundary |
| `06_hybrid_scorecard` | Per-question scoring breakdown |
| `07_retrieval_rank_distribution` | Hit rate at different K values |
| `09_benchmark_variance` | Repeated runs with confidence bands |
| `12_reranking_lift` | Before/after re-ranking positions |
| `value_effort_matrix_optima_manufacturing` | Value-effort automation matrix |
| `confidence_propagation` | Confidence score transformation |

### Retrieval / AI pipeline

**Recipe** (from `03_mature_retrieval_pipeline`): viewBox 800x300 - 20px side margins (usable 760) - 3 stage cards w=240 h=134 (y=36..170), 20px gaps holding the arrows
- card: square-top/rounded-bottom path r=3, fill accent 0.04, stroke w=1, accent bar h=5 op 0.6; text at x+16: kicker 8px/600 letter-spacing 1, title 11px/700, body 8px on 14px rhythm, footnote 7px
- inner sub-rows: rect h=20 rx=3, 8px inset (w=224), 26px stride; status colours teal=current, amber=proposed
- inter-card arrow: line stroke-width 1.5 op 0.4 + polygon tip 4px deep, on card mid-height
- container band below: same path shape, fill 0.02, stroke 0.8 op 0.25, bar h=4 op 0.15; legend swatches 8x8 rx=1 with 7px labels
- keep an embedded `=== GRID REFERENCE ===` comment listing all x/y bands

| File | Description |
|------|-------------|
| `01_current_evaluation_pipeline` | Current evaluation lifecycle |
| `02_retrieval_blind_spots` | Similarity-based retrieval limits |
| `03_mature_retrieval_pipeline` | 3-stage retrieval pipeline |
| `04_hybrid_retrieval_strategies` | Semantic vs BM25 vs PageIndex |
| `05_pageindex_tree_navigation` | Document structure navigation |
| `08_gold_standard_evaluation` | Multi-dimensional scoring |
| `11_end_to_end_retrieval_flow` | Complete proposed pipeline |
| `13_query_comprehension_flow` | Query transformation |
| `14_component_search_bm25` | Fuzzy + BM25 hybrid search |

### Scoring and methodology

**Recipe** (matrix rows, from `engagement_model_apex_financial`): viewBox 800x110 - column headers 7px letter-spacing 1 at y=16 - rows on 18px stride from y=26
- row label 9px at x=20; per-column pills rect h=14 rx=3
- pill weight encodes role: Lead w=180 op 0.25 + 7px/600 accent text, Support w=60-100 op 0.12-0.15 + muted text
- column x positions fixed (e.g. 340 and 560); empty cell = omit pill

| File | Description |
|------|-------------|
| `16_llm_scoring_practices` | LLM scoring best practices |
| `17_fibonacci_scoring` | Fibonacci-based max score |
| `18_benchmark_discipline` | Fixed conditions, one variable |
| `bayesian_resolution` | Bayesian cross-type resolution |
| `deferred_dedup` | Deferred dedup evidence accumulation |
| `engagement_model_apex_financial` | Partnership responsibility split |
| `quality_control_optima_manufacturing` | Quality control challenge |

### Theme swatches

**Recipe** (from `theme_swatch_0_stellars-tech`): viewBox 800x528 - three v-stacked sections: palette reference y=0..150 (transparent bg), light strip y=166..330 (#f5f7fa), dark strip y=346..510 (#1e1e1e), strips mirror the same internal layout
- declares CSS classes fg-1..fg-4 (most→least contrastive), accent-1/2, on-fill, each with `@media (prefers-color-scheme: dark)` override
- swatch chips 12x12 rx=2, hex labels 8px alongside; 14px vertical rhythm, 20px margins
- header comment carries the canonical DESIGN NOTES: card path r=3, accent bar h=5 op 0.6, fill 0.04, container fill 0.02 / stroke 0.8 op 0.25 / bar h=4, L-connectors with 4px chamfers, arrow tips 6px base x 4px deep

| File | Description |
|------|-------------|
| `theme_swatch_0_stellars-tech` | Stellars-Tech palette (primary reference) |
| `theme_swatch_1_kolomolo` | Kolomolo brand palette |
| `theme_swatch_3_meridian` | Meridian brand palette |
| `theme_swatch_5_optima_manufacturing` | Optima Manufacturing palette |
| `theme_swatch_6_stackrails` | StackRails palette (emerald on near-black; light mode derived, dark mode brand-verbatim) |

### Embroidery / decorative

**Recipe** (from `65_embroidery_basic_tier`): viewBox 1000x520 - 8x4 glyph grid, cell 110x106, 12px gutters, symmetric 18px side margins (8x110 + 7x12 = 964)
- glyph: stroke-based motif in ~50x50 box centred at (col+55, row+46); label 8px at row+96
- cell plate: card r=6, accent bar h=3, alternating teal/ochre tint; colour cycles through 10 palette shades by cell index
- glow filter (feGaussianBlur stdDeviation 1.5 + merge) on even-indexed glyphs
- grid math worked out in an embedded `=== GRID ===` comment - verify last column edge + margin symmetry the same way

| File | Description |
|------|-------------|
| `65_embroidery_basic_tier` | 32 basic stroke glyphs (electronics, AI, science, abstract) |
| `66_embroidery_midtier_scifi` | 32 intricate sci-fi/cyberpunk glyphs with glow + gradients |

### Reference / patterns

**Recipe** (from `arrow_patterns`): horizontal-first rule - define every arrow pointing right with tip at origin: stem `line x1=-L y1=0 x2=-10 y2=0` + head `polygon 0,0 -10,-5 -10,5`, then place with `translate(tipX, tipY) rotate(angle)`
- fork up = rotate(-54.5), merge down = rotate(29.7), straight = rotate(0)
- arrow heads fully opaque; stem ends at back of head (x2=-10), never protrudes through the tip

| File | Description |
|------|-------------|
| `arrow_patterns` | Arrow construction reference |
