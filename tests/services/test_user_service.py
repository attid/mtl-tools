# tests/services/test_user_service.py
"""Tests for UserService."""

import pytest
from services.user_service import UserService
from tests.fakes import FakeChatsRepositoryProtocol


class TestNameCache:
    """Tests for name caching methods."""

    def test_cache_name_and_get(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.cache_name("123", "Alice")
        assert service.get_cached_name("123") == "Alice"

    def test_get_cached_name_returns_none_for_missing(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        assert service.get_cached_name("nonexistent") is None

    def test_cache_name_with_stellar_address(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        address = "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        service.cache_name(address, "StellarUser")
        assert service.get_cached_name(address) == "StellarUser"

    def test_cache_name_overwrites_existing(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.cache_name("123", "OldName")
        service.cache_name("123", "NewName")
        assert service.get_cached_name("123") == "NewName"

    def test_load_name_cache_bulk(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        names = {
            "123": "Alice",
            "456": "Bob",
            "GADDR1": "Charlie",
        }
        service.load_name_cache(names)

        assert service.get_cached_name("123") == "Alice"
        assert service.get_cached_name("456") == "Bob"
        assert service.get_cached_name("GADDR1") == "Charlie"

    def test_load_name_cache_replaces_existing(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.cache_name("old_key", "OldValue")
        service.load_name_cache({"new_key": "NewValue"})

        assert service.get_cached_name("old_key") is None
        assert service.get_cached_name("new_key") == "NewValue"

    def test_load_name_cache_creates_copy(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        names = {"123": "Alice"}
        service.load_name_cache(names)

        # Modify original dict
        names["123"] = "Modified"
        names["456"] = "NewUser"

        # Service should not be affected
        assert service.get_cached_name("123") == "Alice"
        assert service.get_cached_name("456") is None

    def test_get_all_names_returns_copy(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        service.cache_name("123", "Alice")
        service.cache_name("456", "Bob")

        all_names = service.get_all_names()
        assert all_names == {"123": "Alice", "456": "Bob"}

        # Modify returned dict
        all_names["999"] = "Hacker"

        # Service should not be affected
        assert service.get_cached_name("999") is None

    def test_get_all_names_empty(self):
        repo = FakeChatsRepositoryProtocol()
        service = UserService(repo)

        assert service.get_all_names() == {}
