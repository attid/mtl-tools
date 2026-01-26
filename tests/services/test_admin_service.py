# tests/services/test_admin_service.py
"""Tests for AdminManagementService."""

import pytest
from services.admin_service import AdminManagementService


class TestChatAdmins:
    """Tests for chat admin methods."""

    def test_is_chat_admin_returns_false_for_empty(self):
        service = AdminManagementService()
        assert service.is_chat_admin(123, 456) is False

    def test_set_and_get_chat_admins(self):
        service = AdminManagementService()
        service.set_chat_admins(123, [100, 200, 300])

        assert service.get_chat_admins(123) == [100, 200, 300]
        assert service.is_chat_admin(123, 100) is True
        assert service.is_chat_admin(123, 999) is False

    def test_add_chat_admin(self):
        service = AdminManagementService()
        service.add_chat_admin(123, 100)
        service.add_chat_admin(123, 200)
        service.add_chat_admin(123, 100)  # duplicate

        admins = service.get_chat_admins(123)
        assert admins == [100, 200]  # no duplicates

    def test_remove_chat_admin(self):
        service = AdminManagementService()
        service.set_chat_admins(123, [100, 200, 300])
        service.remove_chat_admin(123, 200)

        assert service.get_chat_admins(123) == [100, 300]

    def test_remove_nonexistent_admin_no_error(self):
        service = AdminManagementService()
        service.remove_chat_admin(123, 999)  # should not raise

    def test_get_chat_admins_returns_copy(self):
        service = AdminManagementService()
        service.set_chat_admins(123, [100, 200])

        admins = service.get_chat_admins(123)
        admins.append(999)

        assert 999 not in service.get_chat_admins(123)


class TestTopicAdmins:
    """Tests for topic admin methods."""

    def test_is_topic_admin_returns_false_for_empty(self):
        service = AdminManagementService()
        assert service.is_topic_admin(123, 1, 456) is False

    def test_set_and_get_topic_admins(self):
        service = AdminManagementService()
        service.set_topic_admins(123, 5, [100, 200])

        assert service.get_topic_admins(123, 5) == [100, 200]
        assert service.is_topic_admin(123, 5, 100) is True
        assert service.is_topic_admin(123, 5, 999) is False

    def test_topic_admins_separate_from_chat_admins(self):
        service = AdminManagementService()
        service.set_chat_admins(123, [100])
        service.set_topic_admins(123, 5, [200])

        assert service.is_chat_admin(123, 100) is True
        assert service.is_topic_admin(123, 5, 100) is False
        assert service.is_topic_admin(123, 5, 200) is True

    def test_add_topic_admin(self):
        service = AdminManagementService()
        service.add_topic_admin(123, 5, 100)
        service.add_topic_admin(123, 5, 100)  # duplicate

        assert service.get_topic_admins(123, 5) == [100]


class TestTopicMute:
    """Tests for topic mute methods."""

    def test_is_topic_muted_default_false(self):
        service = AdminManagementService()
        assert service.is_topic_muted(123, 5) is False

    def test_set_topic_mute(self):
        service = AdminManagementService()
        service.set_topic_mute(123, 5, True)

        assert service.is_topic_muted(123, 5) is True

    def test_unmute_topic(self):
        service = AdminManagementService()
        service.set_topic_mute(123, 5, True)
        service.set_topic_mute(123, 5, False)

        assert service.is_topic_muted(123, 5) is False


class TestSkynetAdmins:
    """Tests for skynet (bot-level) admin methods."""

    def test_is_skynet_admin_empty_username(self):
        service = AdminManagementService()
        assert service.is_skynet_admin("") is False
        assert service.is_skynet_admin(None) is False

    def test_set_skynet_admins(self):
        service = AdminManagementService()
        service.set_skynet_admins(["@admin1", "@admin2"])

        assert service.is_skynet_admin("@admin1") is True
        assert service.is_skynet_admin("admin1") is True  # without @
        assert service.is_skynet_admin("@unknown") is False

    def test_add_skynet_admin_normalizes_username(self):
        service = AdminManagementService()
        service.add_skynet_admin("admin1")  # without @
        service.add_skynet_admin("@admin2")

        admins = service.get_skynet_admins()
        assert "@admin1" in admins
        assert "@admin2" in admins

    def test_add_skynet_admin_no_duplicates(self):
        service = AdminManagementService()
        service.add_skynet_admin("@admin")
        service.add_skynet_admin("admin")  # same, without @

        assert len(service.get_skynet_admins()) == 1

    def test_get_skynet_admins_returns_copy(self):
        service = AdminManagementService()
        service.set_skynet_admins(["@admin1"])

        admins = service.get_skynet_admins()
        admins.append("@hacker")

        assert "@hacker" not in service.get_skynet_admins()


class TestBulkLoading:
    """Tests for bulk loading methods."""

    def test_load_admins(self):
        service = AdminManagementService()
        service.load_admins({123: [100, 200], 456: [300]})

        assert service.get_chat_admins(123) == [100, 200]
        assert service.get_chat_admins(456) == [300]

    def test_load_topic_admins(self):
        service = AdminManagementService()
        service.load_topic_admins({"123-5": [100], "123-6": [200]})

        assert service.get_topic_admins(123, 5) == [100]
        assert service.get_topic_admins(123, 6) == [200]
