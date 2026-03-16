# Execution Plan - Adjust vote weight target for major holder

Reducing the target share for the major token holder from the middle of the range (36.5%) closer to the lower bound (33.5%) to limit their influence to ~33% in multisig voting.

## Proposed Changes

### `other/stellar/voting_utils.py`

- Modify `normalize_vote_weights` function.
- Change `target_mid = (target_min + target_max) / 2` to `target_mid = target_min + 0.005`.
- This ensures the algorithm targets ~33.5% instead of 36.5%.

## Verification Plan

### Manual Verification
- Run `just test` to ensure existing tests pass.
- Run `just lint` to verify syntax.

## Checklist
- [ ] Update `normalize_vote_weights`.
- [ ] Run tests.
- [ ] Move plan to completed.
