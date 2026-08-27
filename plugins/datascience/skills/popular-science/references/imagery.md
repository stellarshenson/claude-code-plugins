# Imagery - how the figures should look

How the visuals in a best-in-class explainer look, and where to set the bar. The shared `craft-canon.md` carries the review-level visual rules; this file is the writer's deeper guide. Generate figures via `svg-infographics:svg-designer` - hand it the one message and the data.

## How it should look - patterns of great explainer graphics
- **Annotated-takeaway chart** - one focused chart, a bold title that STATES the insight, callout boxes on the key values, an arrow linking text to the point; the reader gets the finding before studying the graphic ([Storytelling with Data](https://www.storytellingwithcharts.com/blog/context-is-key-using-data-visualization-annotation-and-labels-effectively/))
- **Small multiples** - 3-6 identical-scale mini charts in a logical grid (time, geography, rank); compare many dimensions without overplotting ([CDC COVE](https://www.cdc.gov/cove/data-visualization-types/small-multiples.html))
- **Direct-labeled line chart** - series labels at the line ends, no legend; colour distinguishes, no back-and-forth scanning ([Data design standards](https://xdgov.github.io/data-design-standards/components/labels))
- **One-message bar** - one highlighted bar, the rest greyscale; caption states the finding; direct value labels, minimal axes ([Economist design](https://www.consultantsmind.com/2019/11/09/economist-graphs/))
- **Before/after dual** - two side-by-side charts, same scale and layout, two time points; instant visual read of the change ([NN/g contrast](https://www.nngroup.com/articles/contrast-charts/))
- **Scrollytelling reveal** - static narrative text while the chart animates / filters / highlights on scroll; guide interpretation step by step, then open to exploration ([The Pudding](https://pudding.cool/process/how-to-make-dope-shit-part-3/))

## Chart-selection frameworks
- **FT Visual Vocabulary** - 40+ chart types organized by message: deviation, correlation, ranking, distribution, change-over-time, part-to-whole, magnitude, spatial, flow ([repo](https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary))
- **Data Visualisation Catalogue** - 60+ types searchable by function (comparison, distribution, trend, composition) ([site](https://datavizcatalogue.com/))
- **Datawrapper Academy** - "which chart should I use" decision flow + design/accessibility guidance ([academy](https://www.datawrapper.de/academy))

## Best-in-class galleries - compare against these
- **Our World in Data** - source-transparent, reusable educational charts ([site](https://ourworldindata.org/))
- **NYT Graphics** - scrollytelling and interactive narrative, editorial rigor ([graphics](https://www.nytimes.com/graphics))
- **FT Visual Journalism** - consistent design system, minimal chartjunk, reproducible templates ([chart-doctor](https://github.com/Financial-Times/chart-doctor))
- **The Economist Graphic Detail** - simple selection, strategic colour, bold titles, mobile-first ([sample teardown](https://www.thedataschool.co.uk/johann-shin/visual-storytelling-done-right-5-lessons-from-the-economist/))
- **Reuters Graphics** - real-time, data-driven breaking-news explainers ([gallery](https://graphics.thomsonreuters.com/))
- **The Pudding** - scrollytelling data essays, animated reveals ([site](https://pudding.cool/))
- **Information is Beautiful** - design-forward infographic gallery ([site](https://informationisbeautiful.net/))

## The non-negotiables (mirror of the canon's visual rules)
- Match the chart to the message; one message per figure; annotate the takeaway
- Maximise data-ink, erase chartjunk; direct labels over legends
- Honest axes (no truncation, no misleading dual axis); colourblind- and greyscale-safe with redundant encoding
- Never: 3-D charts, rainbow/jet colourmap, many-slice pies, tiny labels, a table dressed as a picture
- Always cite the data source, date and method on the figure ([Our World in Data](https://ourworldindata.org/redesigning-our-interactive-data-visualizations))
