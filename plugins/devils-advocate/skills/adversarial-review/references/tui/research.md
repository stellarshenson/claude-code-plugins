# tui research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Dock overlap
- [Textual Layout guide](https://textual.textualize.io/guide/layout/) - docked widget leaves layout; same-edge docks overlap

## Minimal chrome
- [Nielsen heuristic 8](https://www.nngroup.com/articles/ten-usability-heuristics/) - no irrelevant or rarely needed information

## Binding order
- [Textual Input guide](https://textual.textualize.io/guide/input/) - bindings searched focused widget → App; priority bindings checked first

## Event bubbling
- [Textual Events guide](https://textual.textualize.io/guide/events/) - input events bubble up; `stop()` halts; `prevent_default()` skips base handlers

## Key modes
- [NN/g Modes 2019](https://www.nngroup.com/articles/modes/) - same key, different result → show active mode; avoid if slip loses work

## Escape precedence
- [APG Combobox](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/) - Escape closes popup first; clears input only when popup hidden

## Initial highlight
- [APG Listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/) - nothing selected → first option focused; else selected option

## Type-ahead
- [APG Listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/) - type-ahead for all listboxes, esp. >7 options; moves focus by name prefix

## Match highlight
- [NN/g Search Suggestions 2018](https://www.nngroup.com/articles/site-search-suggestions/): "If, instead, your suggested search feature will suggest popular queries that contain the user's text anywhere in the query, it's best to highlight the user's query". Rule: match anywhere → style typed span; append-completion → style appended part. Tell: contains-filter, no styled span; completion list bolding typed prefix.

## Colour alone
- [WCAG 2.2 SC 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) - colour never only visual means of conveying information (A)

## Text contrast
- [WCAG 2.2 SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) - text ≥4.5:1 on its background, highlight band too (AA)

## Truecolor detection
- [termstandard colors](https://github.com/termstandard/colors) - COLORTERM=truecolor|24bit signals 24-bit; not forwarded via sudo/ssh

## Non-TTY output
- [clig.dev](https://clig.dev/) - not a TTY → no colour, animation, prompts; honour NO_COLOR

## Empty states
- [NN/g Empty States 2021](https://www.nngroup.com/articles/empty-state-interface-design/) - system status, learning cue, direct pathway

## Headless tests
- [Textual Testing guide](https://textual.textualize.io/guide/testing/) - `run_test`, `Pilot.press`, snapshots; default size (80, 24)

Unsourced: path truncation end
