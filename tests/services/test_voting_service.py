"""Tests for VotingService."""

import pytest
from services.voting_service import VotingService


class TestVotingServicePollVotes:
    """Tests for poll votes management."""

    def test_get_poll_votes_returns_empty_when_chat_not_set(self):
        service = VotingService()
        result = service.get_poll_votes(12345)
        assert result == {}

    def test_save_and_get_poll_votes_for_chat(self):
        service = VotingService()
        votes = {"option1": 5, "option2": 3}
        service.save_poll_votes(12345, 100, votes)
        result = service.get_poll_votes(12345, 100)
        assert result == {"option1": 5, "option2": 3}

    def test_get_poll_votes_returns_copy(self):
        service = VotingService()
        votes = {"option1": 5}
        service.save_poll_votes(12345, 100, votes)
        result = service.get_poll_votes(12345, 100)
        result["option2"] = 10
        assert service.get_poll_votes(12345, 100) == {"option1": 5}

    def test_clear_poll_votes_for_specific_message(self):
        service = VotingService()
        service.save_poll_votes(12345, 100, {"a": 1})
        service.save_poll_votes(12345, 200, {"b": 2})
        service.clear_poll_votes(12345, 100)
        assert service.get_poll_votes(12345, 100) == {}
        assert service.get_poll_votes(12345, 200) == {"b": 2}

    def test_clear_poll_votes_for_entire_chat(self):
        service = VotingService()
        service.save_poll_votes(12345, 100, {"a": 1})
        service.save_poll_votes(12345, 200, {"b": 2})
        service.clear_poll_votes(12345)
        assert service.get_poll_votes(12345) == {}

    def test_get_all_votes(self):
        service = VotingService()
        service.save_poll_votes(111, 1, {"a": 1})
        service.save_poll_votes(222, 2, {"b": 2})
        result = service.get_all_votes()
        assert 111 in result
        assert 222 in result


class TestVotingServiceFirstVoteFeature:
    """Tests for first-vote feature toggle."""

    def test_is_first_vote_enabled_initially_false(self):
        service = VotingService()
        assert service.is_first_vote_enabled(12345) is False

    def test_enable_first_vote(self):
        service = VotingService()
        service.enable_first_vote(12345)
        assert service.is_first_vote_enabled(12345) is True

    def test_enable_first_vote_idempotent(self):
        service = VotingService()
        service.enable_first_vote(12345)
        service.enable_first_vote(12345)
        assert service.get_first_vote_chats() == [12345]

    def test_disable_first_vote(self):
        service = VotingService()
        service.enable_first_vote(12345)
        service.disable_first_vote(12345)
        assert service.is_first_vote_enabled(12345) is False

    def test_disable_first_vote_nonexistent_does_not_raise(self):
        service = VotingService()
        service.disable_first_vote(99999)  # Should not raise

    def test_get_first_vote_chats(self):
        service = VotingService()
        service.enable_first_vote(111)
        service.enable_first_vote(222)
        result = service.get_first_vote_chats()
        assert result == [111, 222]

    def test_get_first_vote_chats_returns_copy(self):
        service = VotingService()
        service.enable_first_vote(111)
        result = service.get_first_vote_chats()
        result.append(222)
        assert service.get_first_vote_chats() == [111]


class TestVotingServiceFirstVoteData:
    """Tests for first-vote data tracking."""

    def test_get_first_vote_data_returns_empty_when_not_set(self):
        service = VotingService()
        result = service.get_first_vote_data(12345)
        assert result == {}

    def test_set_and_get_first_vote_data(self):
        service = VotingService()
        data = {100: "choice_a", 200: "choice_b"}
        service.set_first_vote_data(12345, data)
        result = service.get_first_vote_data(12345)
        assert result == {100: "choice_a", 200: "choice_b"}

    def test_record_first_vote(self):
        service = VotingService()
        service.record_first_vote(12345, 100, "option_a")
        assert service.has_user_voted(12345, 100) is True
        data = service.get_first_vote_data(12345)
        assert data[100] == "option_a"

    def test_has_user_voted_false_when_not_voted(self):
        service = VotingService()
        assert service.has_user_voted(12345, 100) is False

    def test_clear_first_vote_data(self):
        service = VotingService()
        service.record_first_vote(12345, 100, "option_a")
        service.clear_first_vote_data(12345)
        assert service.get_first_vote_data(12345) == {}

    def test_clear_first_vote_data_nonexistent_does_not_raise(self):
        service = VotingService()
        service.clear_first_vote_data(99999)  # Should not raise


class TestVotingServiceBulkLoading:
    """Tests for bulk loading methods."""

    def test_load_votes(self):
        service = VotingService()
        data = {111: {1: {"a": 1}}, 222: {2: {"b": 2}}}
        service.load_votes(data)
        assert service.get_poll_votes(111, 1) == {"a": 1}
        assert service.get_poll_votes(222, 2) == {"b": 2}

    def test_load_first_vote(self):
        service = VotingService()
        service.load_first_vote([111, 222, 333])
        assert service.is_first_vote_enabled(111) is True
        assert service.is_first_vote_enabled(222) is True
        assert service.is_first_vote_enabled(333) is True

    def test_load_first_vote_data(self):
        service = VotingService()
        data = {111: {100: "choice_a"}, 222: {200: "choice_b"}}
        service.load_first_vote_data(data)
        assert service.get_first_vote_data(111) == {100: "choice_a"}
        assert service.get_first_vote_data(222) == {200: "choice_b"}


class TestVotingServiceVoteWeights:
    """Tests for vote weights by Stellar address."""

    def test_get_vote_weights_returns_none_when_not_set(self):
        service = VotingService()
        result = service.get_vote_weights("GABCD...")
        assert result is None

    def test_set_and_get_vote_weights(self):
        service = VotingService()
        weights = {"@user1": 5, "@user2": 3, "NEED": {"50": 4, "75": 6, "100": 8}}
        service.set_vote_weights("GABCD...", weights)
        result = service.get_vote_weights("GABCD...")
        assert result == {"@user1": 5, "@user2": 3, "NEED": {"50": 4, "75": 6, "100": 8}}

    def test_get_vote_weights_returns_copy(self):
        service = VotingService()
        weights = {"@user1": 5}
        service.set_vote_weights("GABCD...", weights)
        result = service.get_vote_weights("GABCD...")
        result["@user2"] = 10
        assert service.get_vote_weights("GABCD...") == {"@user1": 5}

    def test_get_all_vote_weights(self):
        service = VotingService()
        service.set_vote_weights("ADDR1", {"@user1": 5})
        service.set_vote_weights("ADDR2", {"@user2": 3})
        result = service.get_all_vote_weights()
        assert "ADDR1" in result
        assert "ADDR2" in result

    def test_set_all_vote_weights_replaces_existing(self):
        service = VotingService()
        service.set_vote_weights("ADDR1", {"@user1": 5})
        service.set_all_vote_weights({"ADDR2": {"@user2": 3}})
        assert service.get_vote_weights("ADDR1") is None
        assert service.get_vote_weights("ADDR2") == {"@user2": 3}

    def test_get_user_vote_weight(self):
        service = VotingService()
        weights = {"@user1": 5, "@user2": 3}
        service.set_vote_weights("GABCD...", weights)
        assert service.get_user_vote_weight("GABCD...", "@user1") == 5
        assert service.get_user_vote_weight("GABCD...", "@user2") == 3

    def test_get_user_vote_weight_returns_none_for_unknown_user(self):
        service = VotingService()
        weights = {"@user1": 5}
        service.set_vote_weights("GABCD...", weights)
        assert service.get_user_vote_weight("GABCD...", "@unknown") is None

    def test_get_user_vote_weight_returns_none_for_unknown_address(self):
        service = VotingService()
        assert service.get_user_vote_weight("UNKNOWN", "@user1") is None
