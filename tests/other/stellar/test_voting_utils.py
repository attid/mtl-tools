# tests/other/stellar/test_voting_utils.py
"""Tests for MTL voting and delegation logic."""

from other.mytypes import MyShareHolder
import other.stellar.voting_utils as voting_utils

normalize_vote_weights = voting_utils.normalize_vote_weights


def make_shareholder(account_id: str, balance_rect: float) -> MyShareHolder:
    return MyShareHolder(account_id=account_id, balance_rect=balance_rect)


class TestApplyMtlDelegations:
    def test_blacklisted_source_cannot_delegate_balance(self):
        source = make_shareholder("GBLACKLISTED", 1_000)
        target = make_shareholder("GTARGET", 500)

        voting_utils.apply_mtl_delegations(
            [source, target],
            {source.account_id: target.account_id},
            {source.account_id: True},
        )

        assert source.balance == 0
        assert target.balance == 500
        assert target.balance_delegated == 0

    def test_delegation_to_blacklisted_target_removes_source_balance(self):
        source = make_shareholder("GSOURCE", 1_000)
        target = make_shareholder("GBLACKLISTED", 500)

        voting_utils.apply_mtl_delegations(
            [source, target],
            {source.account_id: target.account_id},
            {target.account_id: True},
        )

        assert source.balance == 0
        assert target.balance == 0

    def test_delegation_chain_with_blacklisted_account_is_a_sink(self):
        source = make_shareholder("GSOURCE", 1_000)
        intermediate = make_shareholder("GINTERMEDIATE", 700)
        blocked_target = make_shareholder("GBLACKLISTED", 500)
        final_target = make_shareholder("GFINAL", 900)
        delegations = {
            source.account_id: intermediate.account_id,
            intermediate.account_id: blocked_target.account_id,
            blocked_target.account_id: final_target.account_id,
        }

        voting_utils.apply_mtl_delegations(
            [source, intermediate, blocked_target, final_target],
            delegations,
            {blocked_target.account_id: True},
        )

        assert source.balance == 0
        assert intermediate.balance == 0
        assert blocked_target.balance == 0
        assert final_target.balance == 900
        assert final_target.balance_delegated == 0

    def test_valid_delegation_keeps_existing_transfer_behavior(self):
        source = make_shareholder("GSOURCE", 1_000)
        target = make_shareholder("GTARGET", 500)
        delegations = {source.account_id: target.account_id}

        voting_utils.apply_mtl_delegations([source, target], delegations, {})

        assert source.balance == 0
        assert target.balance == 1_500
        assert target.balance_delegated == 1_000
        assert delegations == {source.account_id: target.account_id}

    def test_multistep_delegation_does_not_count_delegated_balance_twice(self):
        source = make_shareholder("GSOURCE", 1_000)
        intermediate = make_shareholder("GINTERMEDIATE", 700)
        target = make_shareholder("GTARGET", 500)
        delegations = {
            source.account_id: intermediate.account_id,
            intermediate.account_id: target.account_id,
        }

        voting_utils.apply_mtl_delegations(
            [intermediate, source, target],
            delegations,
            {},
        )

        assert source.balance == 0
        assert intermediate.balance == 0
        assert target.balance == 2_200
        assert target.balance_delegated == 1_700

    def test_delegation_cycle_without_blacklist_terminates(self):
        first = make_shareholder("GFIRST", 1_000)
        second = make_shareholder("GSECOND", 500)

        voting_utils.apply_mtl_delegations(
            [first, second],
            {first.account_id: second.account_id, second.account_id: first.account_id},
            {},
        )

        assert first.balance + second.balance == 1_500


class TestNormalizeVoteWeights:
    """Tests for normalize_vote_weights pure function."""

    def test_major_holder_within_target_range(self):
        """With typical distribution, major holder should be within 33-40%."""
        balances = [50000, 20000, 15000, 10000, 5000]
        weights = normalize_vote_weights(balances)
        total = sum(weights)
        major_share = weights[0] / total
        assert 0.33 <= major_share <= 0.40, f"Major share {major_share:.2%} outside 33-40%"

    def test_dominant_holder(self):
        """Normalize a dominant holder while preserving the minimum weight."""
        balances = [80000, 5000, 5000, 5000, 5000, 1]
        weights = normalize_vote_weights(balances)
        total = sum(weights)

        assert 0.33 <= weights[0] / total <= 0.40
        assert weights[-1] == 1

    def test_equal_balances(self):
        """Equal balances should produce equal weights."""
        balances = [10000, 10000, 10000, 10000]
        weights = normalize_vote_weights(balances)
        assert all(w == weights[0] for w in weights)

    def test_two_holders(self):
        """With two holders the function should still work."""
        balances = [70000, 30000]
        weights = normalize_vote_weights(balances)
        total = sum(weights)
        assert total > 0
        major_share = weights[0] / total
        assert 0.33 <= major_share <= 0.70  # two holders — cannot go below 50% naturally

    def test_many_small_holders(self):
        """With many small holders around one big, should hit 33-40%."""
        balances = [30000] + [2000] * 20
        weights = normalize_vote_weights(balances)
        total = sum(weights)
        major_share = weights[0] / total
        assert 0.33 <= major_share <= 0.40, f"Major share {major_share:.2%} outside 33-40%"

    def test_realistic_distribution(self):
        """Simulate a realistic MTL distribution."""
        balances = [45000, 25000, 18000, 12000, 8000, 6000, 4000, 3000, 2000, 1000]
        weights = normalize_vote_weights(balances)
        total = sum(weights)
        major_share = weights[0] / total
        assert 0.33 <= major_share <= 0.40, f"Major share {major_share:.2%} outside 33-40%"

    def test_balanced_distribution_skips_power_law_normalization(self):
        """Keep proportional weights when the largest holder is already below 40%."""
        balances = [9503, 9172, 8744, 6666, 5519, 2694, 1600, 1501, 1337, 1074, 1060, 957, 866, 649, 530, 500]

        weights = normalize_vote_weights(balances)

        assert weights == [19, 18, 17, 13, 11, 6, 4, 3, 3, 3, 3, 2, 2, 2, 2, 1]

    def test_preserves_ordering(self):
        """Weights should preserve the balance ordering (descending)."""
        balances = [50000, 30000, 20000, 10000, 5000]
        weights = normalize_vote_weights(balances)
        for i in range(len(weights) - 1):
            assert weights[i] >= weights[i + 1], f"Weight ordering violated at index {i}"

    def test_all_weights_positive(self):
        """All weights should be positive for positive balances."""
        balances = [50000, 20000, 10000, 5000, 1000]
        weights = normalize_vote_weights(balances)
        assert all(w > 0 for w in weights)

    def test_zero_balances(self):
        """All-zero balances should return all-zero weights."""
        balances = [0, 0, 0]
        weights = normalize_vote_weights(balances)
        assert weights == [0, 0, 0]

    def test_single_holder(self):
        """Single holder should get all votes."""
        balances = [50000]
        weights = normalize_vote_weights(balances)
        assert len(weights) == 1
        assert weights[0] > 0

    def test_custom_target_range(self):
        """Custom target range should be respected."""
        balances = [50000, 20000, 15000, 10000, 5000]
        weights = normalize_vote_weights(balances, target_min=0.25, target_max=0.30)
        total = sum(weights)
        major_share = weights[0] / total
        assert 0.25 <= major_share <= 0.30, f"Major share {major_share:.2%} outside 25-30%"

    def test_output_length_matches_input(self):
        """Output list should have same length as input."""
        balances = [50000, 20000, 15000]
        weights = normalize_vote_weights(balances)
        assert len(weights) == len(balances)


def test_vote_distribution_limit_accepts_any_largest_share_up_to_forty_percent():
    assert voting_utils.is_vote_distribution_within_limit([19, 18, 17, 13, 11, 6, 4, 3, 3, 3, 3, 2, 2, 2, 2, 1])
    assert voting_utils.is_vote_distribution_within_limit([40, 30, 20, 10])
    assert not voting_utils.is_vote_distribution_within_limit([41, 30, 20, 9])
