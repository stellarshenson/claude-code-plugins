# Section overviews

Every `## Section` header carries its overview in the SAME markdown cell, above the first code cell. Prose when the content is a single idea, 3-5 bullets when it is naturally listy.

## Prose form

`## Configuration` ->

> Training hyperparameters for the ModernBERT contrastive run. Lower temperature increases discrimination but risks gradient instability; larger effective batch size improves contrastive learning but requires more memory.

Names what the section does, then the trade-off a reader needs to judge the values.

## Bullet form

`## Evaluation` ->

> Reports the four metrics tracked across iterations:
> - **Accuracy** on the held-out test split
> - **F1 macro** to weight rare classes equally
> - **Latency p95** measured on a 1k-row sample
> - **Memory peak** captured via `torch.cuda.max_memory_allocated`

One line of framing, then one bullet per item, each stating what it measures and why that one.
