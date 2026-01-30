# tests/services/test_channel_link_service.py
"""Tests for ChannelLinkService."""

from services.channel_link_service import ChannelLinkService


class TestChannelLinkService:
    """Tests for channel link operations."""

    def test_get_user_for_channel_returns_none_for_unknown(self):
        service = ChannelLinkService()
        assert service.get_user_for_channel(-1001234567890) is None

    def test_link_and_get_channel(self):
        service = ChannelLinkService()
        service.link_channel(-1001234567890, 123456)

        assert service.get_user_for_channel(-1001234567890) == 123456

    def test_link_channel_overwrites_existing(self):
        service = ChannelLinkService()
        service.link_channel(-1001234567890, 123456)
        service.link_channel(-1001234567890, 789012)

        assert service.get_user_for_channel(-1001234567890) == 789012

    def test_unlink_channel_returns_true_if_linked(self):
        service = ChannelLinkService()
        service.link_channel(-1001234567890, 123456)

        result = service.unlink_channel(-1001234567890)

        assert result is True
        assert service.get_user_for_channel(-1001234567890) is None

    def test_unlink_channel_returns_false_if_not_linked(self):
        service = ChannelLinkService()

        result = service.unlink_channel(-1001234567890)

        assert result is False

    def test_is_linked_returns_true_for_linked_channel(self):
        service = ChannelLinkService()
        service.link_channel(-1001234567890, 123456)

        assert service.is_linked(-1001234567890) is True

    def test_is_linked_returns_false_for_unknown_channel(self):
        service = ChannelLinkService()

        assert service.is_linked(-1001234567890) is False

    def test_get_all_links_returns_copy(self):
        service = ChannelLinkService()
        service.link_channel(-1001234567890, 123456)
        service.link_channel(-1009876543210, 789012)

        links = service.get_all_links()
        links[-1001111111111] = 999999  # Modify the copy

        # Original should be unchanged
        assert service.get_user_for_channel(-1001111111111) is None
        assert len(service.get_all_links()) == 2

    def test_get_all_links_returns_all_links(self):
        service = ChannelLinkService()
        service.link_channel(-1001234567890, 123456)
        service.link_channel(-1009876543210, 789012)

        links = service.get_all_links()

        assert links == {
            -1001234567890: 123456,
            -1009876543210: 789012,
        }

    def test_load_from_dict_with_string_keys(self):
        service = ChannelLinkService()

        # JSON storage uses string keys
        service.load_from_dict({
            "-1001234567890": 123456,
            "-1009876543210": 789012,
        })

        assert service.get_user_for_channel(-1001234567890) == 123456
        assert service.get_user_for_channel(-1009876543210) == 789012

    def test_load_from_dict_replaces_existing(self):
        service = ChannelLinkService()
        service.link_channel(-1001234567890, 111111)

        service.load_from_dict({"-1009876543210": 222222})

        assert service.get_user_for_channel(-1001234567890) is None
        assert service.get_user_for_channel(-1009876543210) == 222222

    def test_load_from_dict_empty(self):
        service = ChannelLinkService()
        service.link_channel(-1001234567890, 123456)

        service.load_from_dict({})

        assert service.get_user_for_channel(-1001234567890) is None
        assert len(service.get_all_links()) == 0
