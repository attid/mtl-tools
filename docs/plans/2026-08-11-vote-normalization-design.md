# Conditional MTL Vote Normalization Design

## Context

The primary MTL vote calculation converts proportional balances into integer
weights with `ceil(balance * 100 / total_balance)`. This intentionally keeps a
minimum weight of one for every eligible participant with a positive balance.

The current implementation always applies a power-law transformation intended
for distributions dominated by the largest holder. For a balanced distribution,
the transformation can increase the total weight substantially without reaching
its target share. The production distribution observed on 2026-08-11 changed
weights from a base total of 109 to a transformed total of 304 while leaving the
largest holder at 21.71%.

## Design

The proportional integer weights remain the canonical first calculation. The
largest holder's share is calculated against the sum of those integer weights.

- If the largest share is at most 40%, return the proportional weights unchanged.
- If the largest share exceeds 40%, apply the existing power-law normalization
  and retain its target near 33.5%.
- Preserve the existing best-effort behavior for distributions where the target
  cannot be reached.

This keeps the minimum weight of one, preserves ordering, and limits behavioral
change to the input class for which the power-law calculation was designed.

## Verification

Pure unit tests cover the observed balanced production distribution, a dominant
holder, minimum weight preservation, and ordering. The focused voting utility
tests and the full project quality checks must pass before completion.
