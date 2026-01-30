"""Tests for NotificationService."""

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
    """Tests for alert me methods (per-user subscriptions)."""

    def test_user_not_subscribed_by_default(self):
        service = NotificationService()
        assert service.is_user_subscribed(123, 456) is False
        assert service.get_alert_users(123) == []

    def test_add_and_check_alert_user(self):
        service = NotificationService()
        service.add_alert_user(123, 456)

        assert service.is_user_subscribed(123, 456) is True
        assert 456 in service.get_alert_users(123)

    def test_remove_alert_user(self):
        service = NotificationService()
        service.add_alert_user(123, 456)
        service.remove_alert_user(123, 456)

        assert service.is_user_subscribed(123, 456) is False

    def test_toggle_alert_user(self):
        service = NotificationService()

        # First toggle subscribes
        result = service.toggle_alert_user(123, 456)
        assert result is True
        assert service.is_user_subscribed(123, 456) is True

        # Second toggle unsubscribes
        result = service.toggle_alert_user(123, 456)
        assert result is False
        assert service.is_user_subscribed(123, 456) is False

    def test_get_all_alerts_returns_copy(self):
        service = NotificationService()
        service.add_alert_user(1, 100)
        service.add_alert_user(2, 200)

        all_alerts = service.get_all_alerts()

        assert all_alerts == {1: [100], 2: [200]}


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
        # alert_me stores user lists, not configs
        data = {1: [100, 200], 2: [300]}

        service.load_alert_me(data)

        assert service.get_alert_users(1) == [100, 200]
        assert service.get_alert_users(2) == [300]

    def test_load_creates_copy_of_data(self):
        service = NotificationService()
        data = {1: "config"}

        service.load_notify_join(data)
        data[2] = "new_config"

        assert service.get_join_notify_config(2) is None
