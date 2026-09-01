import pytest
from datetime import datetime, timezone
from types import SimpleNamespace

from tests.fakes import FakeAsyncMethod, FakeSession
import scripts.check_stellar as check_stellar
from other.grist_tools import (
    GRIST_BASE_URL,
    GristAPI,
    MTLGrist,
    RELY_GRIST_BASE_URL,
    grist_manager,
    rely_grist_manager,
)
from other.web_tools import HTTPSessionManager


def make_async_session_pool(session):
    class Pool:
        def __call__(self):
            return self

        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    return Pool()


def test_mtl_grist_bindings_use_audited_documents():
    expected_access_ids = {
        "NOTIFY_ACCOUNTS": "f3ETcoWEkzvkcUnQJtv5tm",
        "NOTIFY_ASSETS": "f3ETcoWEkzvkcUnQJtv5tm",
        "NOTIFY_TREASURY": "f3ETcoWEkzvkcUnQJtv5tm",
        "MTLA_CHATS": "x4r7WiFKsJREzXS4vowwqj",
        "MTLA_COUNCILS": "x4r7WiFKsJREzXS4vowwqj",
        "MTLA_USERS": "x4r7WiFKsJREzXS4vowwqj",
        "MTLA_Corporates": "x4r7WiFKsJREzXS4vowwqj",
        "SP_USERS": "hpZWKq729vw2D5AkG7oYYz",
        "SP_CHATS": "hpZWKq729vw2D5AkG7oYYz",
        "MAIN_CHAT_INCOME": "khWn5KMRbfUQQoaPydjhGt",
        "MAIN_CHAT_OUTCOME": "khWn5KMRbfUQQoaPydjhGt",
        "GRIST_access": "1sd6z3cHUPVQSgvyy7iARy",
        "GRIST_use_log": "1sd6z3cHUPVQSgvyy7iARy",
        "EURMTL_users": "3Fk4hjCv847GBx8ZTCPN2Y",
        "EURMTL_accounts": "3Fk4hjCv847GBx8ZTCPN2Y",
        "EURMTL_assets": "3Fk4hjCv847GBx8ZTCPN2Y",
        "CONFIG_auto_clean": "vpjoUZvH6WRcS7Es8n1UZv",
        "MTLA_AIRDROP": "r4r5Lhy2QJ7bvNs4ut1ATV",
        "MTLA_CONFIG": "r4r5Lhy2QJ7bvNs4ut1ATV",
        "MTL_ADMINS": "ePz5LKsFPmhe5XCC4z7akA",
        "MTL_ADMINS_MEDIA": "ePz5LKsFPmhe5XCC4z7akA",
        "MTL_ADMINS_AGORA_TEAM": "ePz5LKsFPmhe5XCC4z7akA",
        "MTL_ADMINS_AGORA_TOPICS": "ePz5LKsFPmhe5XCC4z7akA",
    }

    assert {name: getattr(MTLGrist, name).access_id for name in expected_access_ids} == expected_access_ids
    assert {getattr(MTLGrist, name).base_url for name in expected_access_ids} == {GRIST_BASE_URL}
    assert GRIST_BASE_URL == "https://grist.eurmtl.me/api/docs"
    assert RELY_GRIST_BASE_URL == "https://mtl-rely.getgrist.com/api/docs"
    assert rely_grist_manager is not grist_manager
    assert rely_grist_manager.token != grist_manager.token


@pytest.mark.asyncio
async def test_cmd_check_bot_uses_async_session_for_alerts(monkeypatch):
    session = FakeSession()
    pool = make_async_session_pool(session)
    messages = []

    class FakeMessageRepository:
        def __init__(self, repo_session):
            self.session = repo_session

        async def async_add_message(self, chat_id, text, use_alarm=0, update_id=None, button_json=None, topic_id=0):
            messages.append(
                {
                    "session": self.session,
                    "chat_id": chat_id,
                    "text": text,
                    "topic_id": topic_id,
                }
            )

    monkeypatch.setattr(check_stellar, "MessageRepository", FakeMessageRepository)
    monkeypatch.setattr(check_stellar, "get_balances", FakeAsyncMethod(return_value={"XLM": "50"}))
    monkeypatch.setattr(check_stellar, "EXCHANGE_BOTS", [])
    monkeypatch.setattr(check_stellar, "stellar_get_orders_sum", FakeAsyncMethod(return_value=100000))

    await check_stellar.cmd_check_bot(pool)

    assert messages == [
        {
            "session": session,
            "chat_id": check_stellar.MTLChats.SignGroup,
            "text": "Внимание Баланс MyMTLWallet меньше 100 !",
            "topic_id": 0,
        }
    ]
    assert session.committed is True


@pytest.mark.asyncio
async def test_grist_upload_users_uses_mocked_put_for_chats_info(mock_grist, grist_server_config, monkeypatch):
    monkeypatch.setattr(MTLGrist.MAIN_CHAT_INCOME, "base_url", f"{grist_server_config['url']}/api/docs")
    test_grist_manager = GristAPI(HTTPSessionManager(), token="test-grist-token")
    monkeypatch.setattr(check_stellar, "grist_manager", test_grist_manager)
    user = SimpleNamespace(
        user_id=42,
        username="alice",
        full_name="Alice Example",
        created_at=datetime(2026, 8, 31, 12, 30, tzinfo=timezone.utc),
        left_at=None,
    )

    await check_stellar.grist_upload_users(MTLGrist.MAIN_CHAT_INCOME, [user])

    put_request = next(request for request in mock_grist.requests if request["method"] == "PUT")
    assert put_request["doc_id"] == "khWn5KMRbfUQQoaPydjhGt"
    assert put_request["table"] == "Main_chat_income"
    assert put_request["json"] == {
        "records": [
            {
                "require": {"user_id": 42},
                "fields": {
                    "user_id": 42,
                    "username": "alice",
                    "full_name": "Alice Example",
                    "income_at": "31.08.2026 12:30:00",
                    "left_at": None,
                },
            }
        ]
    }
    await test_grist_manager.session_manager.close()
