import inspect
from contextlib import suppress

from other.aiogram_tools import add_text, answer_text_file, is_admin, multi_answer, multi_reply
from other.global_data import global_data, is_skynet_admin


class FakeAsyncMethod:
    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self._calls = []

    async def __call__(self, *args, **kwargs):
        self._calls.append((args, kwargs))
        if self.side_effect is not None:
            result = self.side_effect(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        return self.return_value

    @property
    def called(self):
        return len(self._calls) > 0

    @property
    def call_count(self):
        return len(self._calls)

    @property
    def call_args(self):
        return self._calls[-1] if self._calls else None

    @property
    def call_args_list(self):
        return list(self._calls)

    def assert_called_once(self):
        assert self.call_count == 1, f"Expected 1 call, got {self.call_count}"

    def assert_called(self):
        assert self.call_count > 0, "Expected at least one call, got 0"

    def assert_not_called(self):
        assert self.call_count == 0, f"Expected 0 calls, got {self.call_count}"

    def assert_not_awaited(self):
        self.assert_not_called()

    def assert_awaited_once_with(self, *args, **kwargs):
        self.assert_called_once()
        last_args, last_kwargs = self.call_args
        assert last_args == args and last_kwargs == kwargs, (
            f"Expected args={args}, kwargs={kwargs}, got args={last_args}, kwargs={last_kwargs}"
        )

    def assert_awaited_once(self):
        self.assert_called_once()


class FakeSyncMethod:
    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self._calls = []

    def __call__(self, *args, **kwargs):
        self._calls.append((args, kwargs))
        if self.side_effect is not None:
            return self.side_effect(*args, **kwargs)
        return self.return_value

    @property
    def called(self):
        return len(self._calls) > 0

    @property
    def call_count(self):
        return len(self._calls)

    @property
    def call_args(self):
        return self._calls[-1] if self._calls else None

    def assert_called_once(self):
        assert self.call_count == 1, f"Expected 1 call, got {self.call_count}"

    def assert_called(self):
        assert self.call_count > 0, "Expected at least one call, got 0"

    def assert_not_called(self):
        assert self.call_count == 0, f"Expected 0 calls, got {self.call_count}"


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.flushed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def flush(self):
        self.flushed = True

    def close(self):
        pass

    def add(self, obj):
        return None

    def execute(self, *args, **kwargs):
        return FakeResult()

    def query(self, *args, **kwargs):
        return FakeQuery()


class FakeResult:
    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []


class FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []


class FakeWebResponse:
    def __init__(self, data):
        self.data = data


class FakeMongoConfig:
    def __init__(self):
        self._values = {}
        self.save_bot_value = FakeAsyncMethod(side_effect=self._save_bot_value)
        self.load_bot_value = FakeAsyncMethod(side_effect=self._load_bot_value)
        self.get_chat_dict_by_key = FakeAsyncMethod(return_value={})
        self.get_chat_ids_by_key = FakeAsyncMethod(return_value=[])
        self.add_user_to_chat = FakeAsyncMethod(return_value=True)
        self.remove_user_from_chat = FakeAsyncMethod(return_value=True)

    async def _save_bot_value(self, key, bot_value_type, value):
        self._values[(key, bot_value_type)] = value
        return True

    async def _load_bot_value(self, key, bot_value_type, default=None):
        return self._values.get((key, bot_value_type), default)


class FakeLocalizationService:
    def get_text(self, user_id, key, params=()):
        return key


class TestUtilsService:
    def __init__(self):
        self.sleep_and_delete_calls = []
        self.multi_reply_calls = []
        self.multi_answer_calls = []
        self.answer_text_file_calls = []

    async def sleep_and_delete(self, message, seconds=None):
        self.sleep_and_delete_calls.append((message, seconds))
        with suppress(Exception):
            await message.delete()

    async def multi_reply(self, message, text):
        self.multi_reply_calls.append((message, text))
        return await multi_reply(message, text)

    async def multi_answer(self, message, text):
        self.multi_answer_calls.append((message, text))
        return await multi_answer(message, text)

    async def answer_text_file(self, message, text, filename=None):
        self.answer_text_file_calls.append((message, text, filename))
        return await answer_text_file(message, text, filename=filename)

    async def is_admin(self, message, chat_id=None):
        return await is_admin(message, chat_id=chat_id)

    def is_skynet_admin(self, message):
        return is_skynet_admin(message)

    def add_text(self, lines, num_line, text):
        return add_text(lines, num_line, text)


class FakeConfigService:
    def __init__(self):
        self._bot_values = {}
        self._chat_dict = {}
        self._chat_lists = {}
        self._no_first_link = set()
        self._full_data = set()
        self._user_status = {}
        self.save_bot_value = FakeAsyncMethod(side_effect=self._save_bot_value)
        self.load_bot_value = FakeAsyncMethod(side_effect=self._load_bot_value)
        self.get_chat_dict_by_key = FakeAsyncMethod(side_effect=self._get_chat_dict_by_key)
        self.get_chat_ids_by_key = FakeAsyncMethod(side_effect=self._get_chat_ids_by_key)
        self.add_user_to_chat = FakeAsyncMethod(side_effect=self._add_user_to_chat)
        self.remove_user_from_chat = FakeAsyncMethod(side_effect=self._remove_user_from_chat)

    async def _save_bot_value(self, key, bot_value_type, value):
        self._bot_values[(key, bot_value_type)] = value
        return True

    async def _load_bot_value(self, key, bot_value_type, default=None):
        return self._bot_values.get((key, bot_value_type), default)

    async def _get_chat_dict_by_key(self, key, is_int=False):
        data = self._chat_dict.get(key, {})
        if is_int:
            return {int(k): v for k, v in data.items()}
        return data

    async def _get_chat_ids_by_key(self, key):
        return list(self._chat_lists.get(key, []))

    async def _add_user_to_chat(self, chat_id, user_id):
        self._chat_lists.setdefault(chat_id, set()).add(user_id)
        return True

    async def _remove_user_from_chat(self, chat_id, user_id):
        if chat_id in self._chat_lists:
            self._chat_lists[chat_id].discard(user_id)
        return True

    def check_user(self, user_id):
        return self._user_status.get(user_id, 0)

    def set_user_status(self, user_id, status):
        self._user_status[user_id] = status

    def is_no_first_link(self, chat_id):
        return chat_id in self._no_first_link

    def add_no_first_link(self, chat_id):
        self._no_first_link.add(chat_id)

    def remove_no_first_link(self, chat_id):
        self._no_first_link.discard(chat_id)

    def is_full_data(self, chat_id):
        return chat_id in self._full_data

    def set_full_data(self, chat_id, enabled=True):
        if enabled:
            self._full_data.add(chat_id)
        else:
            self._full_data.discard(chat_id)


class FakeAIService:
    def __init__(self):
        self.talk = FakeAsyncMethod(return_value="")
        self.generate_image = FakeAsyncMethod(return_value=[])
        self.talk_get_comment = FakeAsyncMethod(return_value="")
        self.add_task_to_google = FakeAsyncMethod(return_value="")


class FakeTalkService:
    def __init__(self):
        self.answer_notify_message = FakeAsyncMethod(return_value=None)


class FakeAntispamService:
    def __init__(self):
        self.check_spam = FakeAsyncMethod(return_value=False)
        self.combo_check_spammer = FakeAsyncMethod(return_value=False)
        self.lols_check_spammer = FakeAsyncMethod(return_value=False)
        self.delete_and_log_spam = FakeAsyncMethod(return_value=True)
        self.set_vote = FakeAsyncMethod(return_value=True)


class FakePollService:
    def __init__(self):
        self._polls = {}
        self._mtla_polls = {}
        self.save_poll = FakeAsyncMethod(side_effect=self._save_poll)
        self.load_poll = FakeAsyncMethod(side_effect=self._load_poll)
        self.save_mtla_poll = FakeAsyncMethod(side_effect=self._save_mtla_poll)
        self.load_mtla_poll = FakeAsyncMethod(side_effect=self._load_mtla_poll)

    async def _save_poll(self, chat_id, message_id, poll_data):
        self._polls[(chat_id, message_id)] = poll_data
        return True

    async def _load_poll(self, chat_id, message_id):
        return self._polls.get((chat_id, message_id), {})

    async def _save_mtla_poll(self, poll_id, poll_data):
        self._mtla_polls[poll_id] = poll_data
        return True

    async def _load_mtla_poll(self, poll_id):
        return self._mtla_polls.get(poll_id, {})


class FakeGSpreadService:
    def __init__(self):
        self.get_all_mtlap = FakeAsyncMethod(return_value=[])
        self.get_update_mtlap_skynet_row = FakeAsyncMethod(return_value=None)
        self.find_user = FakeAsyncMethod(return_value=[])
        self.check_bim = FakeAsyncMethod(return_value="")
        self.copy_a_table = FakeAsyncMethod(return_value=("", ""))
        self.update_a_table_first = FakeAsyncMethod(return_value=None)
        self.update_a_table_vote = FakeAsyncMethod(return_value=[])
        self.check_vote_table = FakeAsyncMethod(return_value=([], []))
        self.check_credentials = FakeAsyncMethod(return_value=(True, "token refreshed"))


class FakeGristService:
    def __init__(self):
        self.load_table_data = FakeAsyncMethod(return_value=[])
        self.patch_data = FakeAsyncMethod(return_value=None)


class FakeWebService:
    def __init__(self):
        self.get = FakeAsyncMethod(return_value=FakeWebResponse(data={}))


class FakeMtlService:
    def __init__(self):
        self.check_consul_mtla_chats = FakeAsyncMethod(return_value=[])


class FakeStellarService:
    def __init__(self):
        self.check_fee = FakeSyncMethod(return_value="")
        self.decode_xdr = FakeAsyncMethod(return_value=[])
        self.show_bim = FakeAsyncMethod(return_value="")
        self.get_balances = FakeAsyncMethod(return_value={})
        self.send_payment_async = FakeAsyncMethod(return_value={})
        self.sign = FakeSyncMethod(return_value="")
        self.async_submit = FakeAsyncMethod(return_value=None)
        self.find_public_key = FakeSyncMethod(return_value=None)
        self.check_mtlap = FakeAsyncMethod(return_value="")
        self.get_mtlap_votes = FakeAsyncMethod(return_value={})
        self.stop_all_exchange = FakeSyncMethod(return_value=None)
        self.address_id_to_username = FakeAsyncMethod(return_value="@user")


class FakeAirdropService:
    def __init__(self):
        self.check_records = FakeAsyncMethod(return_value=[])
        self.load_configs = FakeAsyncMethod(return_value=[])
        self.log_payment = FakeAsyncMethod(return_value=None)


class FakeReportService:
    def __init__(self):
        self.update_airdrop = FakeAsyncMethod(return_value=None)


class FakeModerationService:
    def __init__(self):
        self.ban_user = FakeAsyncMethod(side_effect=self._ban_user)
        self.unban_user = FakeAsyncMethod(side_effect=self._unban_user)
        self._user_status = {}
        self._user_ids = {}

    async def _ban_user(self, session, chat_id, user_id, bot, revoke_messages=True):
        await bot.ban_chat_member(chat_id, user_id, revoke_messages=revoke_messages)
        self._user_status[user_id] = 2
        return True

    async def _unban_user(self, session, chat_id, user_id, bot):
        await bot.unban_chat_member(chat_id, user_id)
        self._user_status[user_id] = 0
        return True

    def check_user_status(self, user_id):
        return self._user_status.get(user_id, 0)

    def get_user_id(self, session, username):
        if isinstance(username, str):
            if username.isdigit() or (username.startswith("-") and username[1:].isdigit()):
                return int(username)
            if username.startswith("@"):
                return self._user_ids.get(username[1:], 0)
        return self._user_ids.get(username, 0)

    def set_user_id(self, username, user_id):
        self._user_ids[username] = user_id


class FakeGroupService:
    def __init__(self):
        self.get_members = FakeAsyncMethod(return_value=[])
        self.check_membership = FakeAsyncMethod(return_value=True)
        self.enforce_entry_channel = FakeAsyncMethod(return_value=(True, None))
        self.ping_piro = FakeAsyncMethod(return_value=None)


class FakeAirdropConfigItem:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestAppContext:
    def __init__(self, bot, dispatcher):
        self.bot = bot
        self.dispatcher = dispatcher
        self.localization_service = FakeLocalizationService()
        self.utils_service = TestUtilsService()
        self.config_service = FakeConfigService()
        self.ai_service = FakeAIService()
        self.talk_service = FakeTalkService()
        self.antispam_service = FakeAntispamService()
        self.poll_service = FakePollService()
        self.gspread_service = FakeGSpreadService()
        self.grist_service = FakeGristService()
        self.web_service = FakeWebService()
        self.mtl_service = FakeMtlService()
        self.stellar_service = FakeStellarService()
        self.airdrop_service = FakeAirdropService()
        self.report_service = FakeReportService()
        self.moderation_service = FakeModerationService()
        self.group_service = FakeGroupService()
        self.admin_id = 123456


# ============================================================================
# Protocol-compatible fake implementations for clean architecture
# ============================================================================

class FakeStellarSDK:
    """
    Fake implementation of IStellarSDK Protocol for testing.

    Provides test helpers to set up expected responses and verify interactions.
    """

    def __init__(
        self,
        accounts: dict = None,
        balances: dict = None,
        holders: dict = None,
    ):
        from decimal import Decimal
        self._accounts = accounts or {}
        self._balances = balances or {}
        self._holders = holders or {}
        self._submitted_transactions: list = []

    async def get_account(self, address: str):
        return self._accounts.get(address)

    async def get_balances(self, address: str):
        return self._balances.get(address, {})

    async def get_holders(self, asset, limit: int = 200):
        key = f"{asset.code}:{asset.issuer}"
        return self._holders.get(key, [])[:limit]

    async def submit_transaction(self, xdr: str):
        self._submitted_transactions.append(xdr)
        return {"hash": f"fake_hash_{len(self._submitted_transactions)}"}

    def sign_transaction(self, xdr: str):
        return f"signed_{xdr}"

    # Test helpers
    def set_balance(self, address: str, asset: str, amount):
        from decimal import Decimal
        if address not in self._balances:
            self._balances[address] = {}
        self._balances[address][asset] = Decimal(str(amount))

    def set_holders(self, asset, holders: list):
        key = f"{asset.code}:{asset.issuer}"
        self._holders[key] = holders

    def get_submitted_transactions(self):
        return self._submitted_transactions.copy()


class FakeFinanceRepositoryProtocol:
    """Fake implementation of IFinanceRepository Protocol."""

    def __init__(self):
        self.div_lists = {}
        self.payments = {}
        self.transactions = []
        self.watch_list = []

    def get_div_list(self, list_id: int):
        return self.div_lists.get(list_id)

    def get_payments(self, list_id: int, pack_count: int):
        return self.payments.get(list_id, [])[:pack_count]

    def count_unpacked_payments(self, list_id: int):
        return len(self.payments.get(list_id, []))

    def save_transaction(self, list_id: int, xdr: str):
        self.transactions.append({"list_id": list_id, "xdr": xdr})
        return True

    def get_watch_list(self):
        return self.watch_list.copy()


class FakeConfigRepositoryProtocol:
    """Fake implementation of IConfigRepository Protocol."""

    def __init__(self):
        self.config = {}

    def save_bot_value(self, chat_id: int, chat_key: str, chat_value):
        self.config[(chat_id, chat_key)] = chat_value
        return True

    def load_bot_value(self, chat_id: int, chat_key: str, default_value=None):
        return self.config.get((chat_id, chat_key), default_value)

    def get_chat_ids_by_key(self, chat_key: str):
        return [k[0] for k in self.config.keys() if k[1] == chat_key]


class FakeChatsRepositoryProtocol:
    """Fake implementation of IChatsRepository Protocol."""

    def __init__(self):
        self.users = {}
        self.chats = []

    def get_all_chats(self):
        return self.chats.copy()

    def add_user_to_chat(self, chat_id: int, member):
        return True

    def remove_user_from_chat(self, chat_id: int, user_id: int):
        return True

    def get_user_id(self, username: str):
        for uid, user in self.users.items():
            if getattr(user, 'username', None) == username:
                return uid
        return None

    def get_user_by_id(self, user_id: int):
        return self.users.get(user_id)

    def save_user_type(self, user_id: int, user_type: int):
        if user_id not in self.users:
            self.users[user_id] = type('User', (), {'user_type': user_type, 'user_id': user_id})()
        else:
            self.users[user_id].user_type = user_type
        return True

