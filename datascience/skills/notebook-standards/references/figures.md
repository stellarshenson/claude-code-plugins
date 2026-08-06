# Figures - what to chart, and how it lands

Resource for the `notebook-standards` skill. Carries what counts as a load-bearing number, why a figure is evidence rather than decoration, the caption rule, the inline-display mechanics, and the export spec used when the user asks for a file. SKILL.md keeps the defaults - plots render inline because the `.ipynb` is the artefact, no figure goes to disk unless the user explicitly asks, and every load-bearing number gets a figure.

## What counts as load-bearing

Every conclusion the notebook argues for, and every headline statistic it rests on, is SHOWN. Incidental or diagnostic values stay text-only.

- **Distributions** - the shape behind any summary statistic
- **Class balance** - the split a metric is computed over
- **Metric vs baseline** - the comparison a claim of improvement rests on
- **Sweeps** - a parameter varied across its range
- **Ablations** - what each component contributes
- **Error breakdowns** - where the failures concentrate
- **Before/after** - the state either side of a change

## Claim vs evidence

- **A printed number is a claim** - the figure is the evidence a reader checks at a glance
- **It travels** - the figure is what survives into a report or a deck; the printed line does not
- **Incidental values stay text** - a diagnostic print earns no chart

## Caption

- **Figure earns its caption** - the surrounding markdown states what the reader should see in it: the gap, the shift, the outlier
- **Why** - conclusion and its evidence sit together, so neither is read alone

## Inline display

- **End the plotting cell with `plt.show()`** - or let the figure be the cell's last expression
- **Result** - the rendered image is captured in the notebook output, which is the artefact

## Export (only when requested)

Section 9 Save/Export covers model and data artefacts, not figures. When the user explicitly asks for a figure file:

- **Named path** - `reports/figures/<name>.png`
- **`dpi`** - 150+
- **`bbox_inches="tight"`** - trims surrounding whitespace
- **Keep the inline `plt.show()` as well** - export is in addition to the inline figure, never instead of it

`savefig` call, background / transparency, vector formats: `matplotlib.md` → Saving.
