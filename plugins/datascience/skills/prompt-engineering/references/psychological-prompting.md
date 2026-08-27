# Psychological Prompting

Research-backed techniques that exploit statistical correlations in LLM training data to trigger higher-effort output patterns.

## Core Techniques

| Technique | Effect | Usage |
|-----------|--------|-------|
| **Incentive Prompting** | Triggers high-effort patterns | "I'll tip you \$200 for a perfect solution" (optimal range \$100-\$1000) |
| **Step-by-Step Breathing** | +46% math accuracy (34% -> 80%) | "Take a deep breath and work through this step by step" |
| **Challenge Framing** | +115% complex reasoning | "I bet you can't solve this perfectly" |
| **Emotional Stakes** | Modest consistent gains | "This is critical to my career" |
| **Detailed Persona** | Dramatic quality improvement | Specific expertise + years + domain + methodology (not generic roles) |
| **Self-Evaluation Loop** | Catches errors through reflection | "Rate confidence 0-1. If below 0.9, retry." |
| **Stacking** | Maximum effect on complex tasks | Combine persona + stakes + challenge + methodology + self-check |

**Key insight**: LLMs pattern-match on stakes language from training data - not motivation, but statistical correlation with high-effort outputs.

## Template

```
[PERSONA]
<role with specific expertise, experience level, accomplishments>

[STAKES]
<critical importance and concrete consequences of failure>

[INCENTIVE]
<reward for exceptional performance>

[CHALLENGE]
<competitive framing that triggers deeper engagement>

[METHODOLOGY]
Take a deep breath and work through this step by step:
1. <step>
2. <step>
3. <step>

[CONSTRAINTS]
<boundaries and limitations>

[OUTPUT FORMAT]
<expected response structure>

[QUALITY CONTROL]
After your solution, rate confidence (0-1) on:
- <criterion>
- <criterion>
If any score < 0.9, refine your answer.

[TASK]
<specific instruction>
```

## References

- [I Accidentally Made Claude 45% Smarter](https://medium.com/@ichigoSan/i-accidentally-made-claude-45-smarter-heres-how-23ad0bf91ccf)
- [Complete Guide to AI Psychological Prompting](https://deeplearning.fr/the-complete-guide-to-ai-psychological-prompting-20-techniques-for-maximum-effectiveness/)
