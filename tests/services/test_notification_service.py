"""Tests for NotificationService."""

import pytest
from services.notification_service import NotificationService


class TestNotificationServiceJoinNotify:
    """Tests for join notification methods."""

    def test_is_join_notify_enabled_returns_false_when_not_set(self):
        service = NotificationService()
        assert service.is_join_notify_enabled(123) is False

    def test_set_and_get_join_notify_config(self):
        service = NotificationService()
        config = {"channel_id": 456, "template": "Welcome!"}

        service.set_join_notify(123, config)

        assert service.is_join_notify_enabled(123) is True
        assert service.get_join_notify_config(123) == config

    def test_disable_join_notify(self):
        service = NotificationService()
        service.set_join_notify(123, {"enabled": True})

        service.disable_join_notify(123)

        assert service.is_join_notify_enabled(123) is False
        assert service.get_join_notify_config(123) is None

    def test_get_all_join_notify_returns_copy(self):
        service = NotificationService()
        service.set_join_notify(1, "config1")
        service.set_join_notify(2, "config2")

        all_configs = service.get_all_join_notify()

        assert all_configs == {1: "config1", 2: "config2"}
        # Verify it's a copy
        all_configs[3] = "config3"
        assert service.get_join_notify_config(3) is None


class TestNotificationServiceMessageNotify:
    """Tests for message notification methods."""

    def test_is_message_notify_enabled_returns_false_when_not_set(self):
        service = NotificationService()
        assert service.is_message_notify_enabled(123) is False

    def test_set_and_get_message_notify_config(self):
        service = NotificationService()
        config = {"keywords": ["urgent", "help"]}

        service.set_message_notify(123, config)

        assert service.is_message_notify_enabled(123) is True
        assert service.get_message_notify_config(123) == config

    def test_disable_message_notify(self):
        service = NotificationService()
        service.set_message_notify(123, {"enabled": True})

        service.disable_message_notify(123)

        assert service.is_message_notify_enabled(123) is False


class TestNotificationServiceAlertMe:
    """Tests for alert me methods."""

    def test_has_alert_returns_false_when_not_set(self):
        service = NotificationService()
        assert service.has_alert(123) is False

    def test_set_and_get_alert_config(self):
        service = NotificationService()
        config = {"pattern": ".*mention.*"}

        service.set_alert_config(123, config)

        assert service.has_alert(123) is True
        assert service.get_alert_config(123) == config

    def test_remove_alert(self):
        service = NotificationService()
        service.set_alert_config(123, {"pattern": "test"})

        service.remove_alert(123)

        assert service.has_alert(123) is False
        assert service.get_alert_config(123) is None

    def test_get_all_alerts_returns_copy(self):
        service = NotificationService()
        service.set_alert_config(1, "alert1")
        service.set_alert_config(2, "alert2")

        all_alerts = service.get_all_alerts()

        assert all_alerts == {1: "alert1", 2: "alert2"}


class TestNotificationServiceBulkLoading:
    """Tests for bulk loading methods."""

    def test_load_notify_join(self):
        service = NotificationService()
        data = {1: "config1", 2: "config2"}

        service.load_notify_join(data)

        assert service.get_join_notify_config(1) == "config1"
        assert service.get_join_notify_config(2) == "config2"

    def test_load_notify_message(self):
        service = NotificationService()
        data = {1: "msg_config1", 2: "msg_config2"}

        service.load_notify_message(data)

        assert service.get_message_notify_config(1) == "msg_config1"
        assert service.get_message_notify_config(2) == "msg_config2"

    def test_load_alert_me(self):
        service = NotificationService()
        data = {1: "alert1", 2: "alert2"}

        service.load_alert_me(data)

        assert service.get_alert_config(1) == "alert1"
        assert service.get_alert_config(2) == "alert2"

    def test_load_creates_copy_of_data(self):
        service = NotificationService()
        data = {1: "config"}

        service.load_notify_join(data)
        data[2] = "new_config"

        assert service.get_join_notify_config(2) is None
