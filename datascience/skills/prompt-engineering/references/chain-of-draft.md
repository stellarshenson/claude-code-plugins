# Chain of Draft Prompting

Generate multiple minimal drafts before committing to a full solution. Each draft is as short as possible while capturing the key reasoning step.

## Technique

Instead of verbose chain-of-thought where each step is a paragraph, produce ultra-concise drafts (5-10 words per step) that capture just the essential reasoning. This reduces token waste while preserving the accuracy gains of step-by-step thinking.

## When to use

- Tasks where chain-of-thought works but is too verbose
- Token-limited contexts where reasoning must be compact
- Multi-step problems where each step has a clear, short answer
- Math, logic, coding problems with discrete intermediate results

## Template

```
[TASK]
<problem description>

[METHODOLOGY]
Think through this using minimal drafts - each step in under 10 words:
Draft 1: <shortest possible capture of first reasoning step>
Draft 2: <shortest possible capture of next step>
Draft 3: <shortest possible capture of next step>
...
Final: <conclusion based on drafts>
```

## Example

Problem: "If a train leaves at 3pm going 60mph and another at 4pm going 90mph, when do they meet?"

```
Draft 1: 1hr head start = 60mi gap
Draft 2: closing speed = 90-60 = 30mph
Draft 3: 60mi / 30mph = 2hr
Final: 6pm
```

vs Chain of Thought which would produce 3 paragraphs for the same problem.

## Key insight

Chain-of-draft matches or surpasses chain-of-thought accuracy while using as little as **7.6% of the tokens**. The constraint is ~5 words per reasoning step, mimicking how humans draft concise intermediate thoughts that capture only essential information.

## References

- [Chain of Draft: Thinking Faster by Writing Less](https://arxiv.org/abs/2502.18600) (Xu, Xie, Zhao, He - Zoom Communications, 2025)
- [GitHub: sileix/chain-of-draft](https://github.com/sileix/chain-of-draft)
