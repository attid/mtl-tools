# tests/middlewares/test_user_resolver.py
"""Tests for UserResolverMiddleware."""

import datetime
import pytest
from unittest.mock import MagicMock, AsyncMock

from aiogram import types

from middlewares.user_resolver import UserResolverMiddleware
from services.channel_link_service import ChannelLinkService
from services.skyuser import SkyUser


def _build_message(
    chat_id: int,
    from_user: types.User | None = None,
    sender_chat: types.Chat | None = None,
    text: str = "test",
) -> types.Message:
    """Build a test message."""
    return types.Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=types.Chat(id=chat_id, type="supergroup", title="Group"),
        from_user=from_user,
        sender_chat=sender_chat,
        text=text,
    )


def _build_callback_query(
    from_user: types.User | None = None,
) -> types.CallbackQuery:
    """Build a test callback query."""
    return types.CallbackQuery(
        id="cb1",
        from_user=from_user,
        chat_instance="ci1",
        data="test_data",
    )


class TestUserResolverMiddleware:
    """Tests for user resolution logic."""

    def test_resolve_user_id_from_from_user(self):
        """When from_user exists, use from_user.id."""
        channel_link_service = ChannelLinkService()
        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        user = types.User(id=123456, is_bot=False, first_name="Test", username="testuser")
        message = _build_message(chat_id=-100123, from_user=user)

        resolved = middleware._resolve_user(message)

        assert isinstance(resolved, SkyUser)
        assert resolved.user_id == 123456
        assert resolved.username == "testuser"

    def test_resolve_user_id_from_sender_chat_linked(self):
        """When sender_chat exists and is linked, return the linked user_id."""
        channel_link_service = ChannelLinkService()
        channel_link_service.link_channel(-1001234567890, 999888)

        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        sender_chat = types.Chat(id=-1001234567890, type="channel", title="Test Channel")
        message = _build_message(chat_id=-100123, sender_chat=sender_chat)

        resolved = middleware._resolve_user(message)

        assert resolved.user_id == 999888

    def test_resolve_user_id_from_sender_chat_not_linked(self):
        """When sender_chat exists but is not linked, return None."""
        channel_link_service = ChannelLinkService()

        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        sender_chat = types.Chat(id=-1001234567890, type="channel", title="Test Channel")
        message = _build_message(chat_id=-100123, sender_chat=sender_chat)

        resolved = middleware._resolve_user(message)

        assert resolved.user_id is None

    def test_resolve_user_id_no_from_user_no_sender_chat(self):
        """When neither from_user nor sender_chat exists, return None."""
        channel_link_service = ChannelLinkService()

        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        message = _build_message(chat_id=-100123)

        resolved = middleware._resolve_user(message)

        assert resolved.user_id is None

    def test_resolve_user_id_from_callback_query(self):
        """CallbackQuery should resolve from from_user."""
        channel_link_service = ChannelLinkService()

        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        user = types.User(id=555666, is_bot=False, first_name="Test")
        callback_query = _build_callback_query(from_user=user)

        resolved = middleware._resolve_user(callback_query)

        assert resolved.user_id == 555666

    def test_resolve_user_id_for_generic_event_with_from_user(self):
        """Generic event with from_user attribute should resolve correctly."""
        channel_link_service = ChannelLinkService()

        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        # Create a mock event with from_user attribute
        mock_event = MagicMock()
        mock_event.from_user = types.User(id=777888, is_bot=False, first_name="Test")

        resolved = middleware._resolve_user(mock_event)

        assert resolved.user_id == 777888

    def test_resolve_from_channel_no_service(self):
        """When channel_link_service is None, return None."""
        app_context = MagicMock()
        app_context.channel_link_service = None

        middleware = UserResolverMiddleware(app_context, MagicMock())

        resolved = middleware._resolve_from_channel(-1001234567890)

        assert resolved is None

    @pytest.mark.asyncio
    async def test_middleware_adds_skyuser_to_data(self):
        """Middleware should add skyuser to data dict."""
        channel_link_service = ChannelLinkService()

        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        user = types.User(id=123456, is_bot=False, first_name="Test")
        message = _build_message(chat_id=-100123, from_user=user)

        handler = AsyncMock(return_value="handler_result")
        data = {}

        result = await middleware(handler, message, data)

        assert isinstance(data["skyuser"], SkyUser)
        assert result == "handler_result"
        handler.assert_awaited_once_with(message, data)

    @pytest.mark.asyncio
    async def test_middleware_with_channel_message(self):
        """Middleware should resolve channel messages through channel_link_service."""
        channel_link_service = ChannelLinkService()
        channel_link_service.link_channel(-1001234567890, 777888)

        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        sender_chat = types.Chat(id=-1001234567890, type="channel", title="Test Channel")
        message = _build_message(chat_id=-100123, sender_chat=sender_chat)

        handler = AsyncMock(return_value="ok")
        data = {}

        await middleware(handler, message, data)

        assert isinstance(data["skyuser"], SkyUser)

    def test_from_user_takes_priority_over_sender_chat(self):
        """When both from_user and sender_chat exist, from_user should be used."""
        channel_link_service = ChannelLinkService()
        channel_link_service.link_channel(-1001234567890, 999888)

        app_context = MagicMock()
        app_context.channel_link_service = channel_link_service

        middleware = UserResolverMiddleware(app_context, MagicMock())

        user = types.User(id=123456, is_bot=False, first_name="Test")
        sender_chat = types.Chat(id=-1001234567890, type="channel", title="Test Channel")
        message = _build_message(chat_id=-100123, from_user=user, sender_chat=sender_chat)

        resolved = middleware._resolve_user(message)

        # from_user takes priority
        assert resolved.user_id == 123456
