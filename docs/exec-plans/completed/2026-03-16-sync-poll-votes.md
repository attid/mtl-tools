# Execution Plan - Auto-sync missed poll votes on /apoll_check

Synchronize missed poll votes between Telegram (using Pyrogram) and Google Sheets when an admin runs `/apoll_check`.

## Problem Analysis

Due to race conditions, bot restarts, or network issues, some user votes in Telegram might not be recorded in the Google Sheet. Currently, admins can see who hasn't voted using `/apoll_check`, but fixing missed votes requires manual intervention.

## Proposed Changes

1.  **`other/pyro_tools.py`**:
    - Add a new function `pyro_get_poll_voters(chat_id: int, message_id: int) -> dict[int, list[bytes]]` using `messages.GetPollVotes`.
    - It should handle pagination (offset) and return a mapping of `user_id` to their chosen `option`s (as a list of option indexes).

2.  **`other/gspread_tools.py`**:
    - Modify `gs_check_vote_table` to not only return missing addresses but also return the list of addresses that *have* already voted (the `who_vote` list from the "Log" sheet). This allows the caller to know who is already processed.

3.  **`services/external_services.py`**:
    - Update `check_vote_table` signature to match the changes in `gs_check_vote_table`.

4.  **`routers/polls.py`**:
    - In `cmd_apoll_check_handler`:
        - Call the new `pyro_get_poll_voters` to get all actual votes from Telegram.
        - Load `MTLA_USERS` from Grist to map `user_id` to `Stellar` address.
        - Check which Stellar addresses from the Pyrogram votes are *missing* from the Google Sheet's "Log" list.
        - For each missing user, call `gspread_service.update_a_table_vote`.
        - Append a message to the bot's reply indicating which users were automatically restored.

## Verification Plan

- Lint and type check all changed files.
- Test the logic locally or via mock before applying.
