# Execution Plan - Fix gspread delete_row AttributeError

Fixing `AttributeError: 'AsyncioGspreadWorksheet' object has no attribute 'delete_row'` caused by `gspread` library update where `delete_row` was removed in favor of `delete_rows`.

## Proposed Changes

### `other/gspread_tools.py`

- Replace `await wks.delete_row(2)` with `await wks.delete_rows(2)` at line 491.
- Replace `await wks.delete_row(data.row)` with `await wks.delete_rows(data.row)` at line 531.

## Verification Plan

### Automated Tests
- I'll try to create a small test script that mocks `AsyncioGspreadWorksheet` to verify the fix doesn't cause syntax errors and uses the correct method name.
- Since it requires Google API credentials for real integration tests, I'll rely on static analysis and mocking.

### Manual Verification
- Run `just lint` to ensure no new linting errors.
- Run `just types` to ensure type checking passes (if `gspread-asyncio` types are available).

## Checklist
- [ ] Research and confirm `delete_rows` is the correct replacement.
- [ ] Update `other/gspread_tools.py`.
- [ ] Verify with a mock test.
- [ ] Run `just lint`.
- [ ] Move plan to completed.
