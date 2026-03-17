# Execution Plan - Fix Concurrent Vote Updates in GSpread

Preventing race conditions in `gs_update_a_table_vote` when multiple users vote simultaneously.

## Problem Analysis

The function `gs_update_a_table_vote` performs several steps:
1. `wks.find` to check for existing votes.
2. `wks.delete_rows` to remove old votes.
3. `wks.col_values(1)` to find the next empty row.
4. `wks.update` to add the new vote.

When 2-3 users press buttons simultaneously, they might all see the same `len(record)` and attempt to write to the same row, or one might delete a row that another just added, or they might write to rows that Shift after a deletion.

## Proposed Changes

### `other/gspread_tools.py`

- Implement a global lock dictionary for table UUIDs to ensure only one update happens per table at a time.
- Use `asyncio.Lock` to synchronize access within the process.

## Verification Plan

### Automated Tests
- Create a test script that spawns multiple concurrent calls to `gs_update_a_table_vote` (mocked) to verify locking behavior.

### Manual Verification
- Verify with `just lint`.

## Checklist
- [ ] Add `_gspread_locks` dictionary.
- [ ] Wrap `gs_update_a_table_vote` logic in a lock.
- [ ] Verify locking logic.
- [ ] Move plan to completed.
