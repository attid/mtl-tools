"""Tests for BotStateService."""

import pytest
from datetime import datetime
from services.bot_state_service import BotStateService


class TestBotStateServiceSyncState:
    """Tests for sync state management."""

    def test_get_sync_state_returns_default_when_key_not_set(self):
        service = BotStateService()
        result = service.get_sync_state("nonexistent", default="default_value")
        assert result == "default_value"

    def test_set_and_get_sync_state(self):
        service = BotStateService()
        service.set_sync_state("test_key", {"some": "data"})
        result = service.get_sync_state("test_key")
        assert result == {"some": "data"}

    def test_clear_sync_state(self):
        service = BotStateService()
        service.set_sync_state("test_key", "value")
        service.clear_sync_state("test_key")
        result = service.get_sync_state("test_key")
        assert result is None

    def test_clear_sync_state_nonexistent_key_does_not_raise(self):
        service = BotStateService()
        service.clear_sync_state("nonexistent")  # Should not raise


class TestBotStateServiceReboot:
    """Tests for reboot management."""

    def test_is_reboot_requested_initially_false(self):
        service = BotStateService()
        assert service.is_reboot_requested() is False

    def test_request_reboot(self):
        service = BotStateService()
        service.request_reboot()
        assert service.is_reboot_requested() is True

    def test_clear_reboot(self):
        service = BotStateService()
        service.request_reboot()
        service.clear_reboot()
        assert service.is_reboot_requested() is False


class TestBotStateServiceDecode:
    """Tests for decode tracking."""

    def test_needs_decode_initially_false(self):
        service = BotStateService()
        assert service.needs_decode(12345) is False

    def test_mark_needs_decode(self):
        service = BotStateService()
        service.mark_needs_decode(12345)
        assert service.needs_decode(12345) is True

    def test_mark_needs_decode_idempotent(self):
        service = BotStateService()
        service.mark_needs_decode(12345)
        service.mark_needs_decode(12345)
        assert service.get_all_needing_decode() == [12345]

    def test_clear_needs_decode(self):
        service = BotStateService()
        service.mark_needs_decode(12345)
        service.clear_needs_decode(12345)
        assert service.needs_decode(12345) is False

    def test_clear_needs_decode_nonexistent_does_not_raise(self):
        service = BotStateService()
        service.clear_needs_decode(99999)  # Should not raise

    def test_get_all_needing_decode(self):
        service = BotStateService()
        service.mark_needs_decode(111)
        service.mark_needs_decode(222)
        service.mark_needs_decode(333)
        result = service.get_all_needing_decode()
        assert result == [111, 222, 333]

    def test_get_all_needing_decode_returns_copy(self):
        service = BotStateService()
        service.mark_needs_decode(111)
        result = service.get_all_needing_decode()
        result.append(222)
        assert service.get_all_needing_decode() == [111]


class TestBotStateServicePong:
    """Tests for last pong monitoring."""

    def test_get_last_pong_initially_none(self):
        service = BotStateService()
        assert service.get_last_pong() is None

    def test_update_last_pong(self):
        service = BotStateService()
        before = datetime.now()
        service.update_last_pong()
        after = datetime.now()
        result = service.get_last_pong()
        assert before <= result <= after

    def test_set_last_pong(self):
        service = BotStateService()
        specific_time = datetime(2024, 1, 15, 12, 30, 45)
        service.set_last_pong(specific_time)
        assert service.get_last_pong() == specific_time
