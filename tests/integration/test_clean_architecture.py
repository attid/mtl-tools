# tests/integration/test_clean_architecture.py
"""Integration tests for clean architecture components."""

import pytest
from decimal import Decimal

from tests.fakes import (
    FakeStellarSDK,
    FakeConfigRepositoryProtocol,
    FakeChatsRepositoryProtocol,
)
from services.user_service import UserService
from services.config_service import ConfigService
from services.feature_flags import FeatureFlagsService, ChatFeatures
from shared.domain.user import UserType


class TestUserService:
    """Tests for UserService with DI."""

    def test_get_user_type_from_cache(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.preload_users({123: UserType.ADMIN.value})

        assert service.get_user_type(123) == UserType.ADMIN

    def test_get_user_type_from_repo(self):
        repo = FakeChatsRepositoryProtocol()
        repo.save_user_type(456, UserType.TRUSTED.value)
        service = UserService(repo)

        result = service.get_user_type(456)

        assert result == UserType.TRUSTED

    def test_get_user_type_returns_regular_for_unknown(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        result = service.get_user_type(999)

        assert result == UserType.REGULAR

    def test_is_admin(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.set_user_type(123, UserType.ADMIN)

        assert service.is_admin(123) is True
        assert service.is_admin(456) is False

    def test_is_superadmin(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.set_user_type(123, UserType.SUPERADMIN)

        assert service.is_superadmin(123) is True
        assert service.is_admin(123) is True  # superadmin is also admin

    def test_is_banned(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.set_user_type(123, UserType.BANNED)

        assert service.is_banned(123) is True
        assert service.is_banned(456) is False

    def test_is_trusted(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.set_user_type(123, UserType.TRUSTED)

        assert service.is_trusted(123) is True
        assert service.is_trusted(456) is False

    def test_ban_user(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.ban_user(123)

        assert service.is_banned(123) is True

    def test_unban_user(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)
        service.ban_user(123)

        service.unban_user(123)

        assert service.is_banned(123) is False
        assert service.get_user_type(123) == UserType.REGULAR

    def test_clear_cache(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.preload_users({123: UserType.ADMIN.value})
        assert service.get_cached_count() == 1

        service.clear_cache()

        assert service.get_cached_count() == 0

    def test_invalidate_user(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.preload_users({123: UserType.ADMIN.value, 456: UserType.TRUSTED.value})

        service.invalidate_user(123)

        assert service.get_cached_count() == 1


class TestConfigService:
    """Tests for ConfigService with DI."""

    def test_save_and_load_value(self):
        repo = FakeConfigRepositoryProtocol()
        service = ConfigService(repo)

        service.save_value(chat_id=100, key="captcha", value=True)
        result = service.load_value(chat_id=100, key="captcha")

        assert result is True

    def test_load_value_with_default(self):
        repo = FakeConfigRepositoryProtocol()
        service = ConfigService(repo)

        result = service.load_value(chat_id=100, key="unknown", default="default_val")

        assert result == "default_val"

    def test_get_config_cached(self):
        repo = FakeConfigRepositoryProtocol()
        service = ConfigService(repo)

        repo.save_bot_value(100, "captcha", True)
        repo.save_bot_value(100, "moderate", False)

        config1 = service.get_config(100)
        config2 = service.get_config(100)

        assert config1 is config2  # Same cached instance

    def test_cache_invalidation(self):
        repo = FakeConfigRepositoryProtocol()
        service = ConfigService(repo)

        service.save_value(100, "test", "value1")
        _ = service.get_config(100)  # Populate cache

        service.invalidate_cache(100)

        assert service.get_cached_count() == 0

    def test_is_feature_enabled(self):
        repo = FakeConfigRepositoryProtocol()
        service = ConfigService(repo)

        repo.save_bot_value(100, "captcha", True)
        repo.save_bot_value(100, "moderate", False)

        assert service.is_feature_enabled(100, "captcha") is True
        assert service.is_feature_enabled(100, "moderate") is False

    def test_get_chats_with_feature(self):
        repo = FakeConfigRepositoryProtocol()
        service = ConfigService(repo)

        repo.save_bot_value(100, "captcha", True)
        repo.save_bot_value(200, "captcha", True)
        repo.save_bot_value(300, "captcha", False)

        result = service.get_chats_with_feature("captcha")

        assert 100 in result
        assert 200 in result
        assert 300 not in result  # False value excluded


class TestFeatureFlagsService:
    """Tests for FeatureFlagsService."""

    def test_is_enabled(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        # Use flags_service.enable() which converts string to enum
        flags_service.enable(100, "captcha")

        assert flags_service.is_enabled(100, "captcha") is True
        assert flags_service.is_enabled(100, "moderate") is False

    def test_enable_feature(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        result = flags_service.enable(100, "moderate")

        assert result is True
        assert flags_service.is_enabled(100, "moderate") is True

    def test_disable_feature(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        flags_service.enable(100, "captcha")
        flags_service.disable(100, "captcha")

        assert flags_service.is_enabled(100, "captcha") is False

    def test_toggle_feature(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        # Toggle from False to True
        result1 = flags_service.toggle(100, "captcha")
        assert result1 is True
        assert flags_service.is_enabled(100, "captcha") is True

        # Toggle from True to False
        result2 = flags_service.toggle(100, "captcha")
        assert result2 is False
        assert flags_service.is_enabled(100, "captcha") is False

    def test_get_features(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        # Use flags_service.enable() which converts string to enum
        flags_service.enable(100, "captcha")
        flags_service.enable(100, "moderate")
        # reply_only defaults to False, no need to explicitly set

        features = flags_service.get_features(100)

        assert isinstance(features, ChatFeatures)
        assert features.chat_id == 100
        assert features.captcha is True
        assert features.moderate is True
        assert features.reply_only is False

    def test_get_chats_with_feature(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        flags_service.enable(100, "captcha")
        flags_service.enable(200, "captcha")

        result = flags_service.get_chats_with_feature("captcha")

        assert 100 in result
        assert 200 in result

    def test_invalid_feature_returns_false(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        assert flags_service.is_enabled(100, "invalid_feature") is False
        assert flags_service.set_feature(100, "invalid_feature", True) is False

    def test_convenience_methods(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        flags_service.enable(100, "captcha")
        flags_service.enable(100, "moderate")
        flags_service.enable(100, "no_first_link")
        flags_service.enable(100, "reply_only")
        flags_service.enable(100, "listen")
        flags_service.enable(100, "full_data")

        assert flags_service.is_captcha_enabled(100) is True
        assert flags_service.is_moderation_enabled(100) is True
        assert flags_service.is_no_first_link(100) is True
        assert flags_service.is_reply_only(100) is True
        assert flags_service.is_listening(100) is True
        assert flags_service.is_full_data(100) is True

    def test_cache_invalidation(self):
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        flags_service.enable(100, "captcha")
        _ = flags_service.get_features(100)  # Populate cache

        flags_service.invalidate_cache(100)

        assert flags_service.get_cached_count() == 0


class TestStellarIntegration:
    """Tests for Stellar components integration."""

    @pytest.mark.asyncio
    async def test_fake_stellar_sdk_balances(self):
        sdk = FakeStellarSDK()

        # Setup test data
        sdk.set_balance("GTEST1", "EURMTL", Decimal("1000"))
        sdk.set_balance("GTEST2", "EURMTL", Decimal("500"))

        # Verify balances
        bal1 = await sdk.get_balances("GTEST1")
        bal2 = await sdk.get_balances("GTEST2")

        assert bal1["EURMTL"] == Decimal("1000")
        assert bal2["EURMTL"] == Decimal("500")

    @pytest.mark.asyncio
    async def test_fake_stellar_sdk_submit_transaction(self):
        sdk = FakeStellarSDK()

        # Submit transaction
        result = await sdk.submit_transaction("test_xdr")

        assert "hash" in result
        assert len(sdk.get_submitted_transactions()) == 1

    @pytest.mark.asyncio
    async def test_fake_stellar_sdk_multiple_transactions(self):
        sdk = FakeStellarSDK()

        await sdk.submit_transaction("xdr1")
        await sdk.submit_transaction("xdr2")
        await sdk.submit_transaction("xdr3")

        transactions = sdk.get_submitted_transactions()
        assert len(transactions) == 3
        assert transactions[0] == "xdr1"
        assert transactions[1] == "xdr2"
        assert transactions[2] == "xdr3"

    def test_fake_stellar_sdk_sign_transaction(self):
        sdk = FakeStellarSDK()

        signed = sdk.sign_transaction("my_xdr")

        assert signed == "signed_my_xdr"


class TestServiceInteraction:
    """Tests for interaction between services."""

    def test_user_service_with_config_service(self):
        """Test that services work together through shared patterns."""
        config_repo = FakeConfigRepositoryProtocol()
        chats_repo = FakeChatsRepositoryProtocol()

        config_service = ConfigService(config_repo)
        user_service = UserService(chats_repo)
        flags_service = FeatureFlagsService(config_service)

        # Set up a chat with captcha
        flags_service.enable(100, "captcha")

        # Set up an admin user
        user_service.set_user_type(123, UserType.ADMIN)

        # Verify services work correctly
        assert flags_service.is_captcha_enabled(100) is True
        assert user_service.is_admin(123) is True

    def test_feature_flags_updates_propagate(self):
        """Test that feature flag changes update cache correctly."""
        config_repo = FakeConfigRepositoryProtocol()
        config_service = ConfigService(config_repo)
        flags_service = FeatureFlagsService(config_service)

        # Get features to populate cache
        features = flags_service.get_features(100)
        assert features.captcha is False

        # Enable captcha
        flags_service.enable(100, "captcha")

        # Cache should be updated
        features_updated = flags_service.get_features(100)
        assert features_updated.captcha is True
