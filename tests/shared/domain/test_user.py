import pytest
from shared.domain.user import User, AdminStatus, SpamStatus


def test_user_is_admin():
    admin = User(user_id=1, admin_status=AdminStatus.ADMIN)
    regular = User(user_id=2, admin_status=AdminStatus.REGULAR)

    assert admin.is_admin is True
    assert regular.is_admin is False


def test_user_is_superadmin():
    superadmin = User(user_id=1, admin_status=AdminStatus.SUPERADMIN)
    admin = User(user_id=2, admin_status=AdminStatus.ADMIN)

    assert superadmin.is_superadmin is True
    assert admin.is_superadmin is False


def test_user_is_good():
    good = User(user_id=1, spam_status=SpamStatus.GOOD)
    new = User(user_id=2, spam_status=SpamStatus.NEW)

    assert good.is_good is True
    assert new.is_good is False


def test_user_is_bad():
    bad = User(user_id=1, spam_status=SpamStatus.BAD)
    good = User(user_id=2, spam_status=SpamStatus.GOOD)

    assert bad.is_bad is True
    assert good.is_bad is False


def test_user_is_new():
    new = User(user_id=1, spam_status=SpamStatus.NEW)
    good = User(user_id=2, spam_status=SpamStatus.GOOD)

    assert new.is_new is True
    assert good.is_new is False


def test_user_is_immutable():
    user = User(user_id=1, username="test")

    with pytest.raises(Exception):  # FrozenInstanceError
        user.username = "changed"


def test_user_with_spam_status():
    user = User(user_id=1, spam_status=SpamStatus.NEW)
    good = user.with_spam_status(SpamStatus.GOOD)

    assert user.spam_status == SpamStatus.NEW  # original unchanged
    assert good.spam_status == SpamStatus.GOOD
    assert good.user_id == user.user_id


def test_user_with_admin_status():
    user = User(user_id=1, admin_status=AdminStatus.REGULAR)
    admin = user.with_admin_status(AdminStatus.ADMIN)

    assert user.admin_status == AdminStatus.REGULAR  # original unchanged
    assert admin.admin_status == AdminStatus.ADMIN
    assert admin.user_id == user.user_id


def test_user_with_username():
    user = User(user_id=1, username="old_name")
    updated = user.with_username("new_name")

    assert user.username == "old_name"  # original unchanged
    assert updated.username == "new_name"
    assert updated.user_id == user.user_id


def test_status_ordering():
    assert SpamStatus.NEW < SpamStatus.GOOD
    assert SpamStatus.GOOD < SpamStatus.BAD
    assert AdminStatus.REGULAR < AdminStatus.ADMIN
    assert AdminStatus.ADMIN < AdminStatus.SUPERADMIN
