from datetime import datetime
from enum import Enum
from threading import Lock
from loguru import logger

from aiogram.types import Message, ChatMemberUpdated, CallbackQuery

from db.mongo import BotMongoConfig


class MTLChats:
    System = 0  # системный "чат" хранение всего подряд
    Poll = 1  # под опросы
    MTLA_Poll = -1  # под опросы MTLA
    Employment = -1001424237819  # чат поиска работы
    TestGroup = -1001767165598  # тестовая группа
    SignGroup = -1001239694752  # подписанты
    GuarantorGroup = -1001169382324  # Guarantors EURMTL
    DistributedGroup = -1001798357244  # distributed government
    ShareholderGroup = -1001269297637
    GroupAnonymousBot = 1087968824 # анонимный админ
    Channel_Bot = 136817688 # от всех каналов приходит с этим ID
    Telegram_Repost_Bot = 777000 # репост из канала в чат
    FARMGroup = -1001876391583
    LandLordGroup = -1001757912662
    SignGroupForChanel = -1001784614029
    USDMMGroup = -1001800264199
    ITolstov = 84131737
    Any = 191153115
    FCMGroup = -1001637378851
    MMWBGroup = -1001729647273
    FinGroup = -1001941169217
    EURMTLClubGroup = -1001707489173
    MonteliberoChanel = -1001009485608
    HelperChat = -1001466779498
    SpamGroup = -1002007280572
    CyberGroup = -1002079305671
    MTLAGroup = -1001892843127
    MTLAAgoraGroup = -1002032873651
    ClubFMCGroup = -1001777233595
    SerpicaGroup = -1001589557564


class BotValueTypes(Enum):
    PinnedUrl = 1
    LastFondTransaction = 2
    LastDebtTransaction = 3
    PinnedId = 4
    LastEurTransaction = 5
    LastRectTransaction = 6
    LastMTLTransaction = 7
    LastMTLandTransaction = 8
    LastFarmTransaction = 9
    LastFCMTransaction = 10
    LastLedger = 11
    LastMMWBTransaction = 12
    LastUSDMFundTransaction = 13
    LastFINFundTransaction = 14
    SkynetAdmins = 15
    Votes = 16
    All = 17
    AutoAll = 18
    DeleteIncome = 19
    WelcomeMessage = 20
    WelcomeButton = 21
    ReplyOnly = 22
    Captcha = 23
    StopExchange = 24
    LastTFMFundTransaction = 25
    Listen = 26
    FullData = 27
    NoFirstLink = 28
    Admins = 29
    AlertMe = 30
    Sync = 31
    SkynetImg = 32
    NeedDecode = 33
    SaveLastMessageDate = 34
    LastMTLATransaction = 35
    NotifyJoin = 36
    NotifyMessage = 37
    JoinRequestCaptcha = 38
    FirstVote = 39
    LastTransaction = 40


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
    need_decode = []
    first_vote = []
    first_vote_data = {}
    mongo_config: BotMongoConfig
    reboot = False


global_data = GlobalData()
global_data.mongo_config = BotMongoConfig()
global_tasks = []


def is_skynet_admin(event: Message | ChatMemberUpdated | CallbackQuery):
    return f'@{event.from_user.username.lower()}' in global_data.skynet_admins


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
