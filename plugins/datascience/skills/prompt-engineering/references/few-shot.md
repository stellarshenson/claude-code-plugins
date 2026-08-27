# Few-Shot Prompting

Provide examples of the desired input-output pattern before the actual task.

## Technique

Show 2-5 examples of the exact format you want, then present the task. The model pattern-matches on the examples to produce consistent output.

## When to use

- Structured output (JSON, YAML, tables)
- Classification tasks
- Format-sensitive extraction
- When zero-shot produces inconsistent format

## Template

```
[EXAMPLES]
Input: <example input 1>
Output: <example output 1>

Input: <example input 2>
Output: <example output 2>

Input: <example input 3>
Output: <example output 3>

[TASK]
Input: <actual input>
Output:
```

## Variations

- **Zero-shot**: no examples, rely on instruction only
- **One-shot**: single example
- **Few-shot**: 2-5 examples (sweet spot)
- **Many-shot**: 10+ examples (diminishing returns, context waste)

## References

- [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) (Brown et al. 2020)
