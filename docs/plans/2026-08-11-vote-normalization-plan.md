# Conditional MTL Vote Normalization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Apply power-law vote normalization only when the largest holder's proportional integer share exceeds 40%.

**Architecture:** Keep `normalize_vote_weights` as the pure calculation boundary. Build proportional integer weights first, return them unchanged for already-safe distributions, and retain the existing transformation for dominant distributions.

**Tech Stack:** Python 3, pytest, ruff, pyright

---

### Task 1: Add the balanced-distribution regression

**Files:**
- Modify: `tests/other/stellar/test_voting_utils.py`
- Test: `tests/other/stellar/test_voting_utils.py`

**Step 1: Write the failing test**

Add a test using the observed balance distribution and assert that the result is
the direct proportional `ceil` calculation, including the final weight of one.

**Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/other/stellar/test_voting_utils.py -k balanced_distribution`

Expected: FAIL because the existing function always applies power-law normalization.

### Task 2: Add conditional normalization

**Files:**
- Modify: `other/stellar/voting_utils.py:165`
- Test: `tests/other/stellar/test_voting_utils.py`

**Step 1: Write minimal implementation**

After calculating `base_votes`, calculate the largest holder's share against the
base total and return `base_votes` when it does not exceed `target_max`.

**Step 2: Run the focused test to verify it passes**

Run: `uv run pytest -q tests/other/stellar/test_voting_utils.py -k balanced_distribution`

Expected: PASS.

**Step 3: Add boundary coverage**

Add tests proving that a dominant distribution is still normalized to the
existing target range and that a base weight of one remains one.

**Step 4: Run the voting utility tests**

Run: `uv run pytest -q tests/other/stellar/test_voting_utils.py`

Expected: PASS.

### Task 3: Verify the repository

**Files:**
- Modify: `docs/exec-plans/active/2026-08-11-conditional-vote-normalization.md`

**Step 1: Run quality checks**

Run: `just lint && just types && just test`

Expected: all commands pass.

**Step 2: Complete the execution plan**

Mark all checklist items complete and move the execution plan to
`docs/exec-plans/completed/`.
