# Self-Refine

Generate initial output, then critique and improve it iteratively.

## Technique

Three-step loop: generate -> feedback -> refine. The model produces an initial answer, evaluates its own output against criteria, then improves based on the self-critique.

## When to use

- Code generation (write, review, fix)
- Document drafting (write, critique, revise)
- Any task where first-pass quality matters less than final quality
- When you have clear evaluation criteria

## Template

```
[TASK]
<problem description>

[METHODOLOGY]
1. Generate initial solution
2. Critique your solution against these criteria:
   - <criterion 1>
   - <criterion 2>
   - <criterion 3>
3. List specific weaknesses found
4. Refine the solution to address each weakness
5. Repeat until no weaknesses remain
```

## References

- [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651) (Madaan et al. 2023)
