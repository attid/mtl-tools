from datetime import datetime
from threading import Lock
from loguru import logger

from aiogram.types import Message, ChatMemberUpdated, CallbackQuery

from services.database_service import DatabaseService
from other.constants import MTLChats, BotValueTypes


class LogQuery:
    def __init__(self, user_id: int, log_operation: str, log_operation_info: str):
        self.user_id = user_id
        self.log_operation = log_operation
        self.log_operation_info = log_operation_info
        self.log_dt = datetime.now()


class GlobalData:
    votes = {}
    welcome_messages = {}
    welcome_button = {}
    delete_income = {}
    notify_join = {}
    notify_message = {}
    name_list = {}
    users_list = {}
    users_lock = Lock()

    @classmethod
    def check_user(cls, user_id: int) -> int:
        """Возвращает статус пользователя из списка или -1 если не найден"""
        with cls.users_lock:
            user_type = cls.users_list.get(user_id, -1)
            logger.debug(f"Check user {user_id}: type {user_type}")
            return user_type

    @classmethod
    def add_user(cls, user_id: int, user_type: int) -> int:
        """Возвращает статус пользователя из списка или -1 если не найден"""
        with cls.users_lock:
            cls.users_list[user_id] = user_type
            logger.debug(f"Add user {user_id}: type {user_type}")
            return user_type

    info_cmd = {}
    # info_cmd = {'/my_cmd': {'info': 'my_cmd use', 'cmd_type': 0, 'cmd_list': 'my_cmd'}'}
    # type 0 none
    # type 1 in list
    # type 2 in dict
    # type 3 in dict with dict users
    admins = {}
    alert_me = {}
    sync = {}
    topic_admins = {}
    topic_mute = {}
    join_request_captcha = []
    skynet_admins = []
    skynet_img = []
    auto_all = []
    reply_only = []
    captcha = []
    listen = []
    full_data = []
    no_first_link = []
    save_last_message_date = []
    last_pong_response: datetime = datetime.now()
    need_decode = []
    first_vote = []
    first_vote_data = {}
    moderate = []
    entry_channel = {}
    mongo_config: DatabaseService
    reboot = False


global_data = GlobalData()
global_data.mongo_config = DatabaseService()
global_tasks = []


def is_skynet_admin(event: Message | ChatMemberUpdated | CallbackQuery):
    return f'@{event.from_user.username.lower()}' in global_data.skynet_admins


def is_topic_admin(event: Message | ChatMemberUpdated | CallbackQuery):
    if not event.message_thread_id:
        return False
    chat_thread_key = f"{event.chat.id}-{event.message_thread_id}"
    if chat_thread_key not in global_data.topic_admins:
        return False
    return f'@{event.from_user.username.lower()}' in global_data.topic_admins[chat_thread_key]


def float2str(f) -> str:
    if isinstance(f, str):
        f = f.replace(',', '.')
        f = float(f)
    s = "%.7f" % f
    while len(s) > 1 and s[-1] in ('0', '.'):
        l = s[-1]
        s = s[0:-1]
        if l == '.':
            break
    return s


def str2float(f) -> float:
    return float(float2str(f))


def update_command_info(command_name: str, info: str, cmd_type: int = 0, cmd_list: str = ''):
    def decorator(func):
        global_data.info_cmd[command_name] = {'info': info,
                                              'cmd_type': cmd_type,
                                              'cmd_list': cmd_list}
        return func

    return decorator


adv_text = '''
<b>*********************************************************<br>
рекламная пауза:<br>
     Покупайте токены MTL<br>
*********************************************************</b>
'''