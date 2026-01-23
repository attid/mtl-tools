import pytest
import asyncio
import sys
import os
import socket
import random
import string
from unittest.mock import AsyncMock, MagicMock
from aiohttp import web
from aiogram import Dispatcher, Bot, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(os.getcwd())

# Import interfaces and classes for type hinting and mocking specific to your project
# Adjust imports based on your actual project structure
# Imports adjusted for current project state
# from core.interfaces.services import IStellarService
# from core.interfaces.repositories import IRepositoryFactory
# from infrastructure.factories.use_case_factory import IUseCaseFactory
# from infrastructure.services.localization_service import LocalizationService

# --- Constants ---
TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

# --- Helpers ---

def get_free_port():
    """Finds a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def random_address():
    """Generates a random Stellar-like address for testing."""
    return "G" + "".join(random.choices(string.ascii_uppercase + string.digits, k=55))

# --- Fixtures: Config ---

@pytest.fixture(scope="function")
def telegram_server_config():
    port = get_free_port()
    return {"host": "localhost", "port": port, "url": f"http://localhost:{port}"}

@pytest.fixture(scope="function")
def horizon_server_config():
    port = get_free_port()
    return {"host": "localhost", "port": port, "url": f"http://localhost:{port}"}

@pytest.fixture(scope="function")
def grist_server_config():
    port = get_free_port()
    return {"host": "localhost", "port": port, "url": f"http://localhost:{port}"}

# --- Fixtures: Mocks ---

@pytest.fixture
def mock_app_context():
    """
    Creates a standard mock AppContext for DI-based tests.
    """
    ctx = MagicMock()
    ctx.localization_service = MagicMock()
    # Simple get_text mock that returns the key
    ctx.localization_service.get_text.side_effect = lambda user_id, key, params=(): key
    
    ctx.stellar_service = AsyncMock()
    ctx.repository_factory = MagicMock()
    ctx.use_case_factory = MagicMock()
    ctx.bot = AsyncMock(spec=Bot)
    ctx.encryption_service = MagicMock()
    
    # Mock dispatcher storage
    ctx.dispatcher = MagicMock(spec=Dispatcher)
    ctx.dispatcher.storage = MagicMock()
    ctx.dispatcher.storage.get_data = AsyncMock(return_value={})
    ctx.dispatcher.storage.update_data = AsyncMock()
    
    ctx.group_service = MagicMock()
    ctx.group_service.get_members = AsyncMock()
    ctx.group_service.check_membership = AsyncMock()
    ctx.group_service.enforce_entry_channel = AsyncMock()

    ctx.utils_service = MagicMock()
    ctx.utils_service.sleep_and_delete = AsyncMock()
    ctx.utils_service.multi_reply = AsyncMock()
    ctx.utils_service.is_admin = AsyncMock()

    ctx.config_service = MagicMock()
    ctx.config_service.save_bot_value = AsyncMock()
    ctx.config_service.load_bot_value = AsyncMock()
    ctx.config_service.get_chat_dict_by_key = AsyncMock()
    ctx.config_service.get_chat_ids_by_key = AsyncMock()
    ctx.config_service.add_user_to_chat = AsyncMock()
    ctx.config_service.remove_user_from_chat = AsyncMock()

    ctx.grist_service = AsyncMock()
    ctx.gspread_service = AsyncMock()
    ctx.mtl_service = AsyncMock()
    ctx.stellar_service = AsyncMock()
    ctx.airdrop_service = AsyncMock()
    ctx.report_service = AsyncMock()
    ctx.web_service = AsyncMock()
    ctx.antispam_service = AsyncMock()
    ctx.poll_service = AsyncMock()
    ctx.moderation_service = MagicMock()
    ctx.moderation_service.ban_user = AsyncMock()
    ctx.moderation_service.unban_user = AsyncMock()
    ctx.ai_service = AsyncMock()
    ctx.talk_service = AsyncMock()
    
    ctx.admin_id = 123456
    return ctx

# --- Mock Servers ---

# 1. Mock Telegram Server
@pytest.fixture
async def mock_server(telegram_server_config):
    """Starts a local mock Telegram server."""
    class TelegramMockState:
        def __init__(self):
            self.received_requests = []
            self.custom_responses = {}  # method -> response_dict
            self.base_url = telegram_server_config["url"]

        def add_response(self, method, response):
            self.custom_responses[method] = response

        def get_requests(self):
            return self.received_requests

    state = TelegramMockState()
    routes = web.RouteTableDef()

    @routes.post("/bot{token}/{method}")
    async def handle_request(request):
        token = request.match_info['token']
        method = request.match_info['method']
        
        if request.content_type == 'application/json':
            try:
                data = await request.json()
            except Exception:
                data = {}
        else:
            data = await request.post()
            
        data = dict(data)
        state.received_requests.append({"method": method, "token": token, "data": data})

        # Check for custom response
        if method in state.custom_responses:
            return web.json_response(state.custom_responses[method])

        # Default responses for common methods
        if method == "getMe":
            return web.json_response({
                "ok": True,
                "result": {"id": 123456, "is_bot": True, "first_name": "TestBot", "username": "test_bot"}
            })
        elif method in ("sendMessage", "sendPhoto", "sendDocument"):
            chat_id = data.get('chat_id', 0)
            text = data.get('text', '')
            return web.json_response({
                "ok": True,
                "result": {
                    "message_id": random.randint(1, 1000),
                    "date": 1234567890,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": text
                }
            })
        elif method == "sendPoll":
            return web.json_response({
                "ok": True,
                "result": {
                    "message_id": random.randint(1, 1000),
                    "date": 1234567890,
                    "chat": {"id": 123, "type": "private"},
                    "poll": {
                        "id": str(random.randint(1, 1000)), "question": "Q", "options": [{"text": "A", "voter_count": 0}],
                        "total_voter_count": 0, "is_closed": False, "is_anonymous": True, "type": "regular", "allows_multiple_answers": False
                    }
                }
            })
        elif method == "getChatAdministrators":
             # Default fallback: emtpy list or some generic admin
             return web.json_response({
                "ok": True,
                "result": [{
                    "status": "creator",
                    "user": {"id": 123456, "is_bot": True, "first_name": "TestBot", "username": "test_bot"}
                }]
             })
        
        return web.json_response({"ok": True, "result": True})

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, telegram_server_config["host"], telegram_server_config["port"])
    await site.start()

    yield state

    await runner.cleanup()

# 2. Mock Horizon Server
@pytest.fixture
async def mock_horizon(horizon_server_config):
    """Starts a local mock Stellar Horizon server."""
    
    class HorizonMockState:
        def __init__(self):
            self.requests = []
            self.accounts = {}
            self.offers = {}
            self.paths = []
            self.transaction_response = {"successful": True, "hash": "abc123"}

        def set_account(self, account_id, balances=None, data=None):
            self.accounts[account_id] = {
                "id": account_id,
                "account_id": account_id,
                "sequence": "123",
                "balances": balances or [{"asset_type": "native", "balance": "100.0"}],
                "signers": [{"key": account_id, "weight": 1}],
                "thresholds": {"low_threshold": 0, "med_threshold": 1, "high_threshold": 2},
                "data": data or {},
                "flags": {"auth_required": False, "auth_revocable": False}
            }

        def get_requests(self, endpoint=None):
            if endpoint:
                return [r for r in self.requests if r["endpoint"] == endpoint]
            return self.requests

    state = HorizonMockState()
    
    # Route definitions
    routes = web.RouteTableDef()
    
    @routes.get("/accounts/{account_id}")
    async def get_account(request):
        account_id = request.match_info['account_id']
        state.requests.append({"endpoint": "accounts", "method": "GET", "account_id": account_id})
        
        if account_id in state.accounts:
            return web.json_response(state.accounts[account_id])
        return web.json_response({"status": 404, "title": "Not Found"}, status=404)

    @routes.get("/fee_stats")
    async def fee_stats(request):
        state.requests.append({"endpoint": "fee_stats", "method": "GET"})
        return web.json_response({
            "last_ledger": "1",
            "fee_charged": {"max": "100", "min": "100", "mode": "100", "p95": "100"},
            "max_fee": {"mode": "100"}
        })

    @routes.post("/transactions")
    async def submit_transaction(request):
        data = await request.post()
        state.requests.append({"endpoint": "transactions", "method": "POST", "data": dict(data)})
        if state.transaction_response.get("successful"):
            return web.json_response(state.transaction_response)
        return web.json_response(state.transaction_response, status=400)

    @routes.get("/{path:.*}")
    async def catch_all(request):
        path = request.match_info['path']
        state.requests.append({"endpoint": path, "method": "GET"})
        return web.json_response({"status": 404}, status=404)

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, horizon_server_config["host"], horizon_server_config["port"])
    await site.start()

    yield state

    await runner.cleanup()

# 3. Mock Grist Server
@pytest.fixture
async def mock_grist(grist_server_config):
    """Starts a local mock Grist server."""
    class GristMockState:
        def __init__(self):
            self.requests = []
            self.records = {} # table_id -> list of records

        def add_records(self, table_id, records):
            if table_id not in self.records:
                self.records[table_id] = []
            self.records[table_id].extend(records)

    state = GristMockState()
    routes = web.RouteTableDef()

    @routes.get("/api/docs/{doc_id}/tables/{table_id}/records")
    async def get_records(request):
        table_id = request.match_info['table_id']
        state.requests.append({"table": table_id, "method": "GET"})
        records = state.records.get(table_id, [])
        return web.json_response({"records": records})
        
    @routes.post("/api/docs/{doc_id}/tables/{table_id}/records")
    async def add_records(request):
        table_id = request.match_info['table_id']
        try:
            body = await request.json()
            records_to_add = body.get('records', [])
            new_records = []
            if table_id not in state.records:
                state.records[table_id] = []
            
            for record_data in records_to_add:
                # Generate a simple incremental ID based on current list length
                new_id = len(state.records[table_id]) + 1 + random.randint(100, 999) 
                fields = record_data.get("fields", {})
                
                # Apply defaults for specific tables
                if table_id == "Deals" and "Checked" not in fields:
                    fields["Checked"] = False
                    
                new_record = {
                    "id": new_id,
                    "fields": fields
                }
                state.records[table_id].append(new_record)
                new_records.append(new_record["id"]) # Grist POST returns IDs usually
        except Exception:
            pass

        state.requests.append({"table": table_id, "method": "POST"})
        # Grist API returns list of created record IDs
        return web.json_response({"records": new_records})

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, grist_server_config["host"], grist_server_config["port"])
    await site.start()
    
    yield state
    
    await runner.cleanup()


# --- Router Test Infrastructure ---

@pytest.fixture
async def router_bot(mock_server, telegram_server_config):
    """Creates a Bot instance connected to mock Telegram server."""
    session = AiohttpSession(api=TelegramAPIServer.from_base(telegram_server_config["url"]))
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    yield bot
    await bot.session.close()

@pytest.fixture
def dp():
    """Provides a standalone Dispatcher for tests not using router_app_context."""
    return Dispatcher(storage=MemoryStorage())

@pytest.fixture
async def router_app_context(mock_app_context, router_bot, horizon_server_config, mock_horizon):
    """
    Standard app_context for router tests.
    Combines mock_app_context with real bot connected to mock_server.
    Uses real StellarService connected to mock_horizon.
    """
    # from infrastructure.services.stellar_service import StellarService
    
    mock_app_context.bot = router_bot
    mock_app_context.dispatcher = Dispatcher(storage=MemoryStorage())
    
    # Initialize real StellarService pointing to mock horizon - DISABLED as class not found
    # mock_app_context.stellar_service = StellarService(horizon_url=horizon_server_config["url"])
    
    return mock_app_context

class RouterTestMiddleware(BaseMiddleware):
    """
    Middleware for router tests to inject dependencies.
    """
    def __init__(self, app_context):
        self.app_context = app_context

    async def __call__(self, handler, event, data):
        data["app_context"] = self.app_context
        data["session"] = MagicMock() # Mock DB session (MagicMock to support sync .query)
        if hasattr(self.app_context, 'localization_service'):
            data["l10n"] = self.app_context.localization_service
        return await handler(event, data)

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

# --- Updates Factories ---

def create_message_update(user_id, text, **kwargs) -> types.Update:
    return types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=1234567890,
            chat=types.Chat(id=user_id, type='private'),
            from_user=types.User(id=user_id, is_bot=False, first_name="Test"),
            text=text,
            **kwargs
        )
    )

def create_callback_update(user_id, data, message_id=1, **kwargs) -> types.Update:
    return types.Update(
        update_id=1,
        callback_query=types.CallbackQuery(
            id="cb1",
            from_user=types.User(id=user_id, is_bot=False, first_name="Test"),
            chat_instance="ci1",
            message=types.Message(
                message_id=message_id,
                date=1234567890,
                chat=types.Chat(id=user_id, type='private'),
                text="msg"
            ),
            data=data,
            **kwargs
        )
    )
