# ux-designer research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Cognitive load
- [Larson, Czerwinski 1998](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/chi98_webdesign.pdf) - Three levels slower than two; 32 items per level not slower
- [Rosenholtz, Li, Nakano 2007](https://doi.org/10.1167/7.2.17) - Clutter = item excess plus colour variability, slows search; cite mechanism, no number
- [NN/g Minimize Cognitive Load 2013](https://www.nngroup.com/articles/minimize-cognitive-load/) - Offload memory: redisplay entered values, never ask for them again

## Convention on small displays
- [ISO 9241-110 2020](https://cdn.standards.iteh.ai/samples/75258/1aa455483df543e2939a6a4f76194ef8/ISO-9241-110-2020.pdf): "Because the display space is not sufficient to provide the information necessary for self-descriptiveness a higher priority is assigned to achieving conformity with user expectations." Rule: where display space short (ISO example: smart watch), convention outranks on-screen explanation. Tell: finding demands helper text for convention-following control on small screen.

## Static text and tooltips
- [NN/g F-Pattern 2017](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/) - Scanners skip line ends; front-load constraints and warnings
- [Baymard Input Fields](https://baymard.com/learn/input-fields): "When provided with a formatting example on a telephone field, 89% of desktop test participants ignored that example and typed in a different variation." Rule: format example does not constrain input; accept all common formats. Tell: phone, card or date validation rejects variants of shown example.
- [Fluent 2 Tooltip](https://fluent2.microsoft.design/components/web/react/core/tooltip/usage) - Tooltip carries non-essential plaintext only; never success or error feedback
- [WAI-ARIA APG Tooltip](https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/) - role=tooltip referenced by aria-describedby; pattern lacks consensus, cite non-normative
- [NN/g Empty States 2021](https://www.nngroup.com/articles/empty-state-interface-design/) - Empty state shows status, learning cue, path to first action

## Consistency under load
- [Mendel, Pak, Drum 2011](https://doi.org/10.1177/1071181311551417): "the group using the inconsistent interface performed significantly worse only during the dual task portion". Rule: inconsistency cost measured only under dual task or high load. Tell: inconsistency in dense form, complex table, operator console = finding; same on simple screen = MINOR.
