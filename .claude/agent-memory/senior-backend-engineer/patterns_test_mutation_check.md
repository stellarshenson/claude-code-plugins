---
name: patterns-test-mutation-check
description: verify new tests can actually fail by breaking the source one edit at a time; clear __pycache__ and bound the run
metadata:
  type: feedback
---

When a brief says "each test must be able to fail", prove it: revert-copy the source, apply
one targeted mutation, run the suite, confirm the *intended* test fails, restore.

**Why:** assertions written from a passing implementation are easy to make vacuous - a
threshold copied from the observed value can never fire. Mutation checks caught real coverage
here and cost about 5s per mutation.
**How to apply:**
- Clear `__pycache__` between mutations. A length-neutral restore inside one second can serve
  stale bytecode and give a false green.
- Wrap each run in `timeout`. A mutation can remove a loop bound and hang - here, replacing a
  fade with a constant made the row generator loop forever and burned the 2-minute budget.
- Prefer mutations that keep the program terminating (flatten an emitted value) over ones that
  remove a termination condition.
