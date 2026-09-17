---
name: project-dotsea-generator
description: dotsea background style - its constants are fitted to a reference plate, not derived; how to re-measure if they need retuning
metadata:
  type: project
---

`dotsea` in `svg_tools/gen_backgrounds.py` is a perspective marker lattice rolling to a hazy
horizon, added to match `tmp/dotsea/reference-plate-16x9.png`.

The `_DOTSEA_*` constants (`DEPTH_RATIO`, `TILT`, `RADIUS_RATIO`, `FADE_EXP`, `SWELL_AMP`,
`BASE_SPACING`) are **fitted numbers, not derived ones**. Two facts about the plate that the
code cannot show:

- The plate is not a physical camera. Its geometric vanishing line sits far above the height
  where the dots disappear, so the visible convergence is much gentler than a true pinhole
  ground plane would give. `_DOTSEA_DEPTH_RATIO = 1.55` encodes exactly that gap - the field
  only spans a 1.55x depth range.
- The plate's rows are tighter than its columns (about 12px vs 18px at the near edge), which
  is why `_DOTSEA_TILT = 0.72` exists at all.
- The plate also carries a bottom-edge vignette that the generator deliberately does **not**
  reproduce, so a straight ink comparison at the near edge will always read heavy.

**Why:** anyone retuning these will otherwise try to make the perspective physically correct
and end up far from the plate.
**How to apply:** if the look needs to change, re-measure rather than guess - compare a
render against the plate on four numbers (top-of-field per x band, column period vs y, row
period vs y, mean ink per band) using local-contrast high-pass plus autocorrelation. The
full round-by-round record is in `tmp/dotsea/ITERATIONS.md`.
