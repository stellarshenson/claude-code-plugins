# Rephrase and Respond

Have the model rephrase the question before answering to improve comprehension.

## Technique

Ask the model to restate the problem in its own words before solving it. This forces deeper processing of the input and catches misunderstandings early.

## When to use

- Ambiguous requirements
- Complex multi-part questions
- When the model keeps misinterpreting the task
- Technical specifications that need precise understanding

## Template

```
[TASK]
<problem description>

[METHODOLOGY]
Before solving:
1. Rephrase this problem in your own words
2. Identify the key constraints
3. State what a correct solution looks like
4. Then solve it
```

## References

- [Rephrase and Respond: Let Large Language Models Ask Better Questions for Themselves](https://arxiv.org/abs/2311.04205) (Deng et al. 2023)
