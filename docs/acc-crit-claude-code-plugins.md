# Acceptance Criteria - Claude Code Plugins

One consolidated acceptance-criteria doc for the marketplace. One `##` section per feature or scope; new scopes append a section and a Contents pointer.

## Contents

- [SVG validation split](#svg-validation-split)

## SVG validation split

Validation of a generated SVG is two things, not one: a deterministic CLI floor (`svg-infographics finalize` and its checkers) that proves construction sanity, and a validator process with a generative model in the loop that judges everything requiring judgment. The CLI must never attempt the second kind - the evals below the line are possible only via a generative model.

| Functionality | CLI validator (deterministic floor) | Validator process (generative model) |
| ------------- | ----------------------------------- | ------------------------------------ |
| Document construction (parses, canvas/viewBox sane) | owns | - |
| Connector construction (stem attaches, head aligned and sized to stem, no zero-length stems) | owns, where cheaply computable | borderline cases |
| Overlap geometry of rendered boxes | owns | adjudicates intentional layering |
| Colour arithmetic (WCAG ratios, both themes, dark declarations present) | owns | - |
| CSS discipline (class-based paint, no forbidden colours) | owns | - |
| Roster honesty (every aspect judged or its SKIP surfaced) | owns | - |
| Legibility in context (reads at ship size, hierarchy scans) | - | owns |
| Semantic fit (the graphic says what the hypothesis claims) | - | owns |
| Aesthetic quality vs the examples/ bar | - | owns |
| Label/number truth against source content | - | owns |

- [x] **CLI: document construction** - parseable XML, canvas/viewBox read, per-tag geometry sane
  - log: 2026-08-13 in place (v1.6.45)
- [x] **CLI: connector construction** - stem attaches to card edge, arrowhead aligned to stem and sized from it, zero-length stems flagged
  - log: 2026-08-13 in place (v1.6.45)
- [x] **CLI: overlap geometry** - rendered boxes of visible elements do not overlap; hidden subtrees excluded via one shared `is_display_none` predicate across colour scan, connector walk and overlaps model
  - log: 2026-08-13 predicate unified across the three layers (round-8 fix)
- [x] **CLI: colour arithmetic** - WCAG contrast ratios in both themes against the elected background; unreadable paint is reported UNMEASURABLE, never silently passed
  - log: 2026-08-13 in place (v1.6.45)
- [x] **CLI: CSS discipline** - class-based paint, no forbidden colours, dark-mode declarations where light ones exist
  - log: 2026-08-13 in place (v1.6.45)
- [x] **CLI: roster honesty** - every aspect reports PASS/FAIL/NA/SKIP; an unasked SKIP flips the verdict to NOT VERIFIED plus exit 1 on every branch, HARD path included; `--json` carries the per-file `skipped` map and `totals`
  - log: 2026-08-13 HARD-path stderr gap closed (round-8 fix)
- [x] **CLI: no generative evals** - the CLI never attempts readability, semantic or aesthetic judgment; checks stay deterministic (construction, geometry, colour arithmetic)
  - log: 2026-08-13 doctrine set by the Star Colonel
- [ ] **CLI: verdict names the floor** - verdict lines assert what was checked, never overall quality
  - log: 2026-08-13 criterion added - the current "OK - shippable" wording predates the split; reword decision pending the Star Colonel
- [x] **Process: hypothesis first** - every graphic states its rationale before any wireframing; the CLI cannot check this
  - log: 2026-08-13 in place (standing directive)
- [ ] **Process: legibility at ship size** - generative review of the rendered PNG; no deterministic proxy exists
  - log: 2026-08-13 criterion added
- [ ] **Process: semantic fit** - the graphic says what the hypothesis claims; metaphor and flow fit the content
  - log: 2026-08-13 criterion added
- [ ] **Process: examples bar** - side-by-side against `plugins/svg-infographics/examples/` production references; "readable infographic" is a generative judgment
  - log: 2026-08-13 criterion added
- [ ] **Process: label truth** - labels and numbers match the source content the graphic summarizes
  - log: 2026-08-13 criterion added
- [ ] **Process: ambiguity adjudication** - intentional layering vs overlap defect, decorative density vs clutter: judged by the model, never the CLI
  - log: 2026-08-13 criterion added
- [x] **Ship = floor AND judgment** - a graphic ships when the CLI floor passes AND the generative review accepts; a CLI PASS alone is never a ship decision
  - log: 2026-08-13 doctrine set by the Star Colonel
