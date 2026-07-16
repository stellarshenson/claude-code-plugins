# Craft canon - popular-science writing and visuals

**Single source of truth.** This file is the shared standard for two skills in two different plugins: the `datascience:popular-science` writer composes from it, and the `popular-science` adversary in `devils-advocate:adversarial-review` reviews against it. The link is deliberately cross-plugin - the canon stays with the writer, and the adversary reaches across to it, so install both plugins to get the pair. Edit HERE and both inherit the change - neither keeps a private copy. When the adversary runs without tools (Mode 1) this file is appended to its prompt; with tools (Mode 2) it reads this file directly.

The industry best practices to write to, and the anti-patterns to avoid, distilled from the field's standard references (cited below).

## Writing - best practices
- **Hook then nut graf** - the lede earns the second sentence; the nut graf lands early (not always right after the lede) and states the story in a nutshell - what it is, why it matters (The Open Notebook, "Nailing the Nut Graf")
- **Ladder of abstraction** - climb both ways: scenic detail (show - zoom in) and summary meaning (tell - zoom out). Good writing constantly ascends and descends it (Hayakawa; The Open Notebook, "Using the Ladder of Abstraction")
- **One idea per sentence** - verbs over nominalisations ("we investigated X", not "the investigation of X"); short paragraphs, one beat each; white space is oxygen on a screen
- **Explain a term once, plainly** - the first time it appears; or leave it out if it is not core to the story (National Geographic, "On jargon")
- **Concreteness** - every abstraction gets one anchor: an image, a number the reader can see, a person making a choice
- **Claim + provenance + number** - a bare claim is weak; the named research team and the hard figure sell it. Pair every empirical assertion with `(Author, year)` (or an honest "our model finds") AND the demonstrated number - the effect size, the sample, the comparison
- **Analogy after the concept, not before** - introduce the comparison once the reader has the idea; a premature analogy confuses. Anchor it in something culturally familiar (National Geographic / The Open Notebook, "Building Bridges")
- **Head-to-tail transitions** - echo a word or idea from a paragraph's last sentence in the next paragraph's first, so the seams disappear (The Open Notebook, "Good Transitions")
- **Structure before drafting** - outline what each paragraph does before writing prose; most writing problems are structure problems, not sentence problems (Ed Yong, craft interview)
- **The kicker** - end on a line that lands: short words, a callback to the opening image or question, full circle with a twist. The best endings echo the beginning in an essential but surprising way (The Open Notebook, "Good Endings: How to Write a Kicker"). Then conclusions, then next steps where the work continues
- **Emphasis and resting points** - lift the single most load-bearing line of a section into a *pull quote* (lift-out / call-out): a sentence pulled from the body and set apart - larger, italic, centred - to draw the eye and give the reader a place to pause. Bold a few load-bearing phrases in the running prose. Both are seasoning: a handful across a whole piece, on the lines that carry the argument, never a page of them (magazine layout; NN/g, emphasis and scannability)

## Writing - anti-patterns
- **Jargon as a flex** - convoluted prose reads as hiding a weak grasp, not as authority
- **Synonym-swapping a technical term** - keep one name for one thing
- **The wall of text** - six-plus-line blocks the eye slides off; split into one-beat paragraphs
- **Argument dumped as bullets** - and its mirror, a genuine list buried inside a paragraph. Prose for an argument, a list for a set of distinct items
- **The buried lede** - throat-clearing or a definition before the hook
- **An ending that stops** - a limp restatement, no callback, no forward hook
- **The naked claim** - an assertion with neither a named source nor a number, asking the reader to just believe it
- **Emphasis inflation** - bold scattered through every paragraph, or a pull quote every screen; when everything is emphasised nothing is. Reserve both for the few lines that bear the weight

## Visuals - best practices
- **Match the chart to the message** - deviation, correlation, ranking, distribution, change-over-time, part-to-whole, magnitude, spatial, flow (FT Visual Vocabulary)
- **Maximise data-ink; erase chartjunk** - every mark earns its place (Tufte)
- **Direct labels** - label on the data, not via a legend the eye must match back (NN/G, "Clutter-Free")
- **One message per figure** - annotate the takeaway so the caption reads the chart without the body text
- **Redundant encoding** - never colour alone; pair with shape / label / pattern; colourblind- and greyscale-safe
- **Graphical integrity** - honest axes, honest area; the visual's magnitude matches the data's (Tufte's lie factor)

## Visuals - anti-patterns
- 3-D bars or pies, drop shadows, decorative gradients - distort perception, add nothing
- Truncated or dual y-axis that inflates a thin effect
- Rainbow / jet colourmap; colour carrying the only meaning, dead in greyscale
- A legend of a dozen near-identical hues the reader must decode
- Overplotting; labels too small to read; a table dressed up as a picture

## Best-in-class references
Write and design to this bar; when you need it, pull a strong example and dimension the gap:
- **Writing** - Quanta Magazine, Scientific American, The Atlantic science, Nautilus, Aeon
- **Visuals** - NYT Graphics (scrollytelling, "Snow Fall"), FT Visual Journalism (the charticle, Visual Vocabulary), The Economist Graphic Detail, Our World in Data, Information is Beautiful, Datawrapper Blog, Pew Research, Mona Chalabi

## Calibration - what a strong passage looks like
The "myths" register: name the myth, break it with a NAMED source and a HARD number, close on a witty turn. A claim alone is weak; the research team and the numbers sell the story.
- "The myth of the baby bonus - that a big enough cheque will do it. Cash buys a brief flurry of births ... and then the effect evaporates. Korea spent on the order of USD 270 billion over twenty years and watched its birth rate fall in every one of them."
- "In the model a birth in a low-fertility country happens roughly only when both partners want it (Doepke & Kindermann, 2019) ... The lever is fairness, not nostalgia."

Each carries all three - the claim, its provenance or its number, and a last line that lands (the callback / turn, e.g. "The exit is not the leak - it is the valve"). The full annotated exemplar is in `examples/myths-calibration.md`; mirror its shape, not its topic.

## Sources
- The Open Notebook - [Good Beginnings](https://www.theopennotebook.com/2015/07/14/good-beginnings/), [Nailing the Nut Graf](https://www.theopennotebook.com/2014/04/29/nailing-the-nut-graf/), [Using the Ladder of Abstraction](https://www.theopennotebook.com/2023/05/30/using-the-ladder-of-abstraction-to-elevate-science-stories/), [Building Bridges (analogies)](https://www.theopennotebook.com/2025/03/11/building-bridges-crafting-analogies-to-help-guide-your-readers/), [Good Transitions](https://www.theopennotebook.com/2018/09/25/good-transitions-a-guide-to-cementing-stories-together/), [Good Endings: How to Write a Kicker](https://www.theopennotebook.com/2015/11/24/good-endings-how-to-write-a-kicker-your-editor-and-your-readers-will-love/), [Steering sources away from jargon](https://www.theopennotebook.com/2025/05/13/come-again-how-to-steer-scientist-sources-away-from-jargon/)
- National Geographic - [On jargon, and why it matters in science writing](https://www.nationalgeographic.com/science/article/on-jargon-and-why-it-matters-in-science-writing); Ed Yong - [craft interview](https://magazine.catapult.co/dont-write-alone/stories/interview-with-journalist-ed-yong-writing-process-advice-for-science-writers)
- Nielsen Norman Group - [Clutter-Free charts](https://www.nngroup.com/articles/clutter-charts/), [Contrast in charts](https://www.nngroup.com/articles/contrast-charts/); Tufte - graphical integrity, data-ink ratio, chartjunk
- Financial Times - [Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary); Datawrapper - [Academy](https://www.datawrapper.de/academy); [Data Visualisation Catalogue](https://datavizcatalogue.com/)

Deeper writer references (not part of the shared review standard): `structures.md` (article structure templates), `imagery.md` (visual patterns + galleries), `../examples/teardowns.md` (annotated exemplar articles).
