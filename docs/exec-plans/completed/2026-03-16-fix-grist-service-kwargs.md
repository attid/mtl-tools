# Execution Plan - Fix GristService keyword arguments

Fixing `TypeError: GristService.load_table_data() got an unexpected keyword argument 'filter_dict'`.

## Proposed Changes

### `services/external_services.py`

- Update `GristService.load_table_data` to match the interface definition in `services/interfaces/external.py`.
- Ensure it accepts `filter_dict` and `sort` keyword arguments and passes them to `grist_manager.load_table_data`.

## Verification Plan

### Manual Verification
- Run `just test` to ensure it works.
- Run `just types` to ensure pyright is happy with the signature.

## Checklist
- [ ] Update `GristService.load_table_data`.
- [ ] Run types check.
- [ ] Move plan to completed.
