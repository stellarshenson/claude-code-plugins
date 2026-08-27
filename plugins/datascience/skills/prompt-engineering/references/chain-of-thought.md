# Chain of Thought Prompting

Force the model to show its reasoning step by step before arriving at a conclusion.

## Technique

Add "Let's think step by step" or explicitly structure the reasoning chain:
1. State the problem
2. Identify the relevant information
3. Work through the logic
4. Arrive at the conclusion

## When to use

- Mathematical reasoning
- Multi-step logic problems
- Code debugging (trace execution flow)
- Complex data analysis (explain each transformation)

## Template

```
[TASK]
<problem description>

[METHODOLOGY]
Think through this step by step:
1. First, identify what we know
2. Then, determine what we need to find
3. Work through the logic
4. Verify the result
```

## References

- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) (Wei et al. 2022)
