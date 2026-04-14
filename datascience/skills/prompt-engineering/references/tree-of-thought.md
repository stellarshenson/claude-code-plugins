# Tree of Thought Prompting

Explore multiple reasoning paths in parallel, evaluate each, and select the best.

## Technique

Instead of a single chain of thought, branch into 2-3 alternative approaches, evaluate each, then converge on the best one. Mimics how experts consider alternatives before committing.

## When to use

- Design decisions with trade-offs
- Architecture choices
- Strategy selection
- Any problem where the first approach may not be best

## Template

```
[TASK]
<problem description>

[METHODOLOGY]
Consider 3 different approaches:

Approach A: <brief description>
- Pros: ...
- Cons: ...
- Predicted outcome: ...

Approach B: <brief description>
- Pros: ...
- Cons: ...
- Predicted outcome: ...

Approach C: <brief description>
- Pros: ...
- Cons: ...
- Predicted outcome: ...

[SELECTION]
Select the best approach with justification.
Explain why the others were rejected.
```

## References

- [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601) (Yao et al. 2023)
