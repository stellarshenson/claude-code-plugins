# Summary: Stop Fixing Your AI's SVGs

This article introduces a plugin for Claude Code that lets AI agents design SVG infographics the way a human uses a vector editor - with snap-to-grid placement, smart connectors, alignment guides, and a quality gate.

## The problem

When you ask an LLM to "draw an SVG infographic", you are asking it to be an SVG coder: typing `<rect>` and guessing coordinates. Every number is a token prediction, nothing snaps, and no ruler or alignment guide exists. The model is drawing blind.

A human designer, in contrast, gets snapping, smart connectors, alignment guides, a colour swatch, and a layer panel. Shapes are placed; the application computes the geometry.

## Five recurring defects

Five things that a designer has and an LLM does not. Each adds manual fix-up time:

- Snap-to-grid missing - 5-15 min per image
- Smart connectors missing - 5-10 min per arrow
- Colour swatches missing - 10-20 min for CSS overrides
- Alignment guides missing - 5-10 min per pass
- Quality gate missing - 30-90 min per image

For a six-image article, this totals 3-6 hours of hand-editing with zero creative value.

## Twelve tools in a CLI

The plugin exposes twelve tools via the `svg-infographics` CLI, split into six design tools and six validators.

Design tools: `primitives` (18 shape types with anchors), `connector` (five routing modes with auto-routing), `geom` (alignment and constraints), `callouts` (auto-placement via solver), `empty-space` (free-region detection), and `charts` (pygal chart rendering).

Validators: `overlaps`, `contrast` (WCAG 2.1), `alignment`, `connectors`, `css`, and `collide`. Each targets a specific defect class so nothing ships with a known flaw.

## Paraphrased claims (for grounding test)

The tool turns placement, routing, and charting into computed operations - the agent says where and what, the tools handle exact coordinates.

A vector editor provides snap guides and a colour palette that an LLM does not have when it writes SVG by hand.

The validation panel refuses broken output before the file is delivered.

## A claim not in the article (should NOT ground)

The plugin requires a GPU with at least 16GB of VRAM to run inference locally.
