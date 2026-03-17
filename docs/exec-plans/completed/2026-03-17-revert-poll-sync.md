# Execution Plan - Revert auto-sync poll votes

Removing the Pyrogram poll sync logic because Telegram API prohibits bots from calling `messages.GetPollVotes` (`400 BOT_METHOD_INVALID`).

## Proposed Changes

1.  **`routers/polls.py`**:
    - Remove the try/except block that calls `pyro_get_poll_voters` and attempts to sync votes.
    - Remove the appended text about "Автоматически восстановлены голоса".
    - `grist_service` dependency can be removed if it's only used for sync.

2.  **`other/pyro_tools.py`**:
    - Remove the `pyro_get_poll_voters` function as it cannot be used by bots.

*(Note: We will leave `already_voted_addresses` in `gspread_tools.py` and `tests/fakes.py` as it's harmless and might be useful later if we implement a UserBot).*

## Verification Plan

- Lint and type check all changed files.
- Test with `just test`.
