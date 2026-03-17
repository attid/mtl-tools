# Execution Plan - Add GSpread testing utilities

Add a utility function to write specific values to a given cell in a Google Sheet to facilitate testing.

## Proposed Changes

1.  **`other/gspread_tools.py`**:
    - Add a new async function `gs_write_cell_value(document_id: str, sheet_name: str, cell: str, value: str | int | float)`.
    - It should authorize using `agcm`, open the document by ID, select the worksheet by name, and update the specified cell with the provided value.

## Verification Plan

- Lint and type check all changed files.
