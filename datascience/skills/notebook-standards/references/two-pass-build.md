# Two-pass build

Resource for the `notebook-standards` skill. How the compute pass and the interpretation pass divide, and where a conclusion lands. The SKILL.md Two-pass build section carries the rule and the shape a conclusion takes; this carries the mechanics.

## The two passes

- **Pass 1 - compute** - run the cells that generate the data and numbers: load, process, train / infer, collect metrics into variables and to disk. No conclusions yet - writing them while the numbers are still moving produces text that has to be redone
- **Pass 2 - interpret** - revisit the executed notebook and add the reasoning: a conclusion for each result, plus a graph for every load-bearing number (per Figures) demonstrating the specific feature or phenomenon the number claims

## Where a conclusion lands

- A markdown cell after the result, or Rich text in the output cell directly under its graph
- A headline number never stands without the sentence saying what it means
- The headline figure or verdict wears the notebook's semantic palette (per Colours) so the deciding number stands out on a skim - meaning-bearing, never decoration

## More passes

A surprising number earns another compute-then-interpret pass, not an unexplained value. The count is a floor, not a target: two passes is the minimum that separates measurement from meaning, and a result that raises a question has not finished its second pass.
