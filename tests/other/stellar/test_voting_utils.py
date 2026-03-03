# tests/other/stellar/test_voting_utils.py
"""Tests for vote weight normalization logic."""

from other.stellar.voting_utils import normalize_vote_weights


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
        """Even with one very dominant holder, result should be close to target."""
        balances = [80000, 5000, 5000, 5000, 5000]
        weights = normalize_vote_weights(balances)
        total = sum(weights)
        # May not fit perfectly but should be best effort
        assert total > 0
        assert weights[0] > 0

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
