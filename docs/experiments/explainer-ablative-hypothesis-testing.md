# Ablative hypothesis testing

The method used throughout the cross-lingual grounding experiment: frame each component (feature, signal, model layer, unit of capacity) as a falsifiable hypothesis, then test it by ablation - change that one component, hold everything else fixed, measure the delta. Examples drawn from `BENCHMARK.md`.

## What it is

A controlled experiment that isolates one component's contribution by running the system with vs without it.

- **One change** - only the component under test moves
- **Everything else fixed** - same data, split, metric, and other components
- **Delta = contribution** - the score difference is causally attributable to that one component
- **Answers** - "what is this piece actually doing?"

## Why called "ablation"

From Latin *ablatio*, "a carrying away / removal", borrowed from sciences where it means physically removing material.

- **Medicine** - to ablate tissue is to surgically remove it (cardiac ablation destroys faulty tissue)
- **Geology / aerospace** - material worn or melted away (a glacier ablates; a heat shield ablates on re-entry)
- **ML** - "surgically remove" a part and see what breaks; a drop means it was load-bearing, no change means it was not

## How it works

Two directions, both ablation, differing only in the starting point; the control is what turns a number into evidence.

- **Subtractive (leave-one-out)** - remove component X from the full system; `contribution = full - without_X`; answers "is X necessary?"
- **Additive (add-one-in)** - add X to a baseline; `lift = base+X - base`; answers "does X earn its place?"
- **The control** - only one thing differs between runs, so nothing else can explain the delta

## Worked example - feature ablation (Round 6)

Three candidate features, each added to the same lexical baseline, scored under the same leave-one-source-out split.

```
base (lexical)          LOSO 0.837   <- everything held fixed
base + H1 rarity        LOSO 0.834   -> -0.003 (nothing)
base + H2 span          LOSO 0.838   -> +0.001 (nothing)
base + H3 specificity   LOSO 0.845   -> +0.008 (the real lift)
base + all              LOSO 0.838   -> dead features dilute the live one
```

- **Isolation** - rows 1 and 4 differ only by `specificity`, so +0.008 is that feature's effect, not luck
- **Honest basis** - this is what licenses the claim "specificity helped"

## Worked example - capacity ablation (the scissors)

Vary one axis - model capacity - with features held fixed, to isolate what flexibility buys.

- **Ladder** - logistic → linear+interactions → GBT depth-2 → GBT depth-4
- **In-fold** - rises monotonically to 0.996 (memorisation)
- **Out-of-fold** - peaks at small capacity, then falls (the overfit "scissors")
- **Verdict** - the ceiling is data, not model

## Ablation as hypothesis testing

Each component is a falsifiable hypothesis stated before the run, so the result is a verdict not a fishing expedition.

- **Statement** - what the component should contribute and why (the mechanism)
- **Test** - the ablation (add/remove, fixed everything else, chosen split)
- **Expected** - a number to beat (e.g. raise LOSO by >= 0.005)
- **Falsifier** - the result that kills it (e.g. "adds < 0.005 and does not narrow the generalisation gap")
- **Round 6** - H3 confirmed (lifted LOSO, narrowed the LOLO-to-LOSO gap = generalises); H1 falsified ("adds < 0.005 over recall"), dropped

## Reading an ablation table

- **Compare rows differing by exactly one component** - that difference is the only thing the delta can be about
- **Right metric, right split** - macro-F1 (imbalance-robust) under leave-one-source-out (the generalisation that matters), not accuracy in-distribution
- **A near-zero delta is informative** - the component adds nothing beyond what is already present; a result, not a failure

## Pitfalls

- **Correlated components hide value** - removing either of two redundant features shows no drop; "no drop" is not "no value" (H1 rarity looked neutral only because recall already encoded content presence)
- **Adding everything dilutes** - redundant features spread model weight and lower out-of-fold score (`base + all` < `base + H3`); ablation argues for parsimony
- **Wrong split flatters** - an in-distribution split rewards memorisation; hold out the unit you must generalise to (here, whole source documents)
- **Order / interaction effects** - a component's value depends on what else is present; subtractive and additive ablation can disagree, full picture needs both

## Why it matters here

The grounding study is a chain of ablations - each signal, model class, decomposition variant and feature added or removed against a fixed baseline and split.

- **Every BENCHMARK claim is controlled** - "specificity helps", "NLI is unnecessary", "trees overfit", "decomposition over-flags" each rest on a one-component comparison
- **The difference** - a measured result versus a guess
