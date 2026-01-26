# tests/shared/domain/test_user.py
import pytest
from shared.domain.user import User, UserType


def test_user_is_admin():
    admin = User(user_id=1, user_type=UserType.ADMIN)
    regular = User(user_id=2, user_type=UserType.REGULAR)

    assert admin.is_admin is True
    assert regular.is_admin is False


def test_user_is_trusted():
    trusted = User(user_id=1, user_type=UserType.TRUSTED)
    regular = User(user_id=2, user_type=UserType.REGULAR)
    admin = User(user_id=3, user_type=UserType.ADMIN)

    assert trusted.is_trusted is True
    assert regular.is_trusted is False
    assert admin.is_trusted is True  # Admin is also trusted


def test_user_is_banned():
    banned = User(user_id=1, user_type=UserType.BANNED)
    regular = User(user_id=2, user_type=UserType.REGULAR)

    assert banned.is_banned is True
    assert regular.is_banned is False


def test_user_is_superadmin():
    superadmin = User(user_id=1, user_type=UserType.SUPERADMIN)
    admin = User(user_id=2, user_type=UserType.ADMIN)

    assert superadmin.is_superadmin is True
    assert admin.is_superadmin is False


def test_user_is_immutable():
    user = User(user_id=1, username="test")

    with pytest.raises(Exception):  # FrozenInstanceError
        user.username = "changed"


def test_user_with_type():
    user = User(user_id=1, user_type=UserType.REGULAR)
    admin = user.with_type(UserType.ADMIN)

    assert user.user_type == UserType.REGULAR  # original unchanged
    assert admin.user_type == UserType.ADMIN
    assert admin.user_id == user.user_id


def test_user_with_username():
    user = User(user_id=1, username="old_name")
    updated = user.with_username("new_name")

    assert user.username == "old_name"  # original unchanged
    assert updated.username == "new_name"
    assert updated.user_id == user.user_id


def test_user_type_ordering():
    """Test that UserType values are ordered correctly."""
    assert UserType.BANNED < UserType.REGULAR
    assert UserType.REGULAR < UserType.TRUSTED
    assert UserType.TRUSTED < UserType.ADMIN
    assert UserType.ADMIN < UserType.SUPERADMIN
