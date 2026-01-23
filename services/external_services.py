from other.grist_tools import grist_manager
from other.gspread_tools import gs_get_all_mtlap, gs_get_update_mtlap_skynet_row, gs_find_user
from other.mtl_tools import check_consul_mtla_chats
from other.stellar_tools import get_balances, send_payment_async
from other.grist_tools import grist_check_airdrop_records, grist_log_airdrop_payment, grist_load_airdrop_configs

class GristService:
    async def load_table_data(self, table_id):
        return await grist_manager.load_table_data(table_id)
    
    async def patch_data(self, table_id, data):
        return await grist_manager.patch_data(table_id, data)

class GSpreadService:
    async def get_all_mtlap(self):
        return await gs_get_all_mtlap()
    
    async def get_update_mtlap_skynet_row(self, results):
        return await gs_get_update_mtlap_skynet_row(results)

    async def find_user(self, user_id):
        return await gs_find_user(user_id)

    async def check_bim(self, user_id_or_name):
        from other.gspread_tools import gs_check_bim
        return await gs_check_bim(user_id_or_name)

class WebService:
    async def get(self, url, return_type='json'):
        from other.web_tools import http_session_manager
        return await http_session_manager.get_web_request('GET', url=url, return_type=return_type)

class MtlService:
    async def check_consul_mtla_chats(self, bot):
        return await check_consul_mtla_chats(bot)

class StellarService:
    async def get_balances(self, address, return_signers=False):
        return await get_balances(address, return_signers=return_signers)

    async def send_payment_async(self, source_address, destination, asset, amount):
        return await send_payment_async(source_address, destination, asset, amount)

    def check_fee(self):
        from other.stellar_tools import cmd_check_fee
        return cmd_check_fee()

    async def check_url_xdr(self, url, full_data=False):
        from other.stellar_tools import check_url_xdr
        return await check_url_xdr(url, full_data=full_data)

    async def decode_xdr(self, xdr, full_data=False):
        from other.stellar_tools import decode_xdr
        return await decode_xdr(xdr, full_data=full_data)

    async def show_bim(self, session):
        from other.stellar_tools import cmd_show_bim
        return await cmd_show_bim(session)

    async def get_cash_balance(self, chat_id):
        from other.stellar_tools import get_cash_balance
        return await get_cash_balance(chat_id)

    def create_list(self, session, name, type_id):
        from other.stellar_tools import cmd_create_list
        return cmd_create_list(session, name, type_id)

    async def calc_bim_pays(self, session, list_id):
        from other.stellar_tools import cmd_calc_bim_pays
        return await cmd_calc_bim_pays(session, list_id)

    def gen_xdr(self, session, list_id):
        from other.stellar_tools import cmd_gen_xdr
        return cmd_gen_xdr(session, list_id)

    async def send_by_list_id(self, session, list_id):
        from other.stellar_tools import cmd_send_by_list_id
        return await cmd_send_by_list_id(session, list_id)

    async def calc_divs(self, session, div_list_id, donate_list_id):
        from other.stellar_tools import cmd_calc_divs
        return await cmd_calc_divs(session, div_list_id, donate_list_id)

    async def calc_sats_divs(self, session, div_list_id):
        from other.stellar_tools import cmd_calc_sats_divs
        return await cmd_calc_sats_divs(session, div_list_id)

    async def get_new_vote_all_mtl(self, address):
        from other.stellar_tools import cmd_get_new_vote_all_mtl
        return await cmd_get_new_vote_all_mtl(address)

    async def get_btcmtl_xdr(self, amount, address, memo):
        from other.stellar_tools import get_btcmtl_xdr
        return await get_btcmtl_xdr(amount, address, memo)

    async def show_data(self, key):
        from other.stellar_tools import cmd_show_data
        return await cmd_show_data(key)

    async def get_damircoin_xdr(self, amount):
        from other.stellar_tools import get_damircoin_xdr
        return await get_damircoin_xdr(amount)

    async def calc_usdm_divs(self, session, list_id):
        from other.stellar_tools import cmd_calc_usdm_divs
        return await cmd_calc_usdm_divs(session, list_id)

    async def get_toc_xdr(self, amount):
        from other.stellar_tools import get_toc_xdr
        return await get_toc_xdr(amount)

    def find_public_key(self, text):
        from other.stellar_tools import find_stellar_public_key
        return find_stellar_public_key(text)

    async def check_mtlap(self, key):
        from other.stellar_tools import check_mtlap
        return await check_mtlap(key)

    async def get_agora_xdr(self):
        from other.stellar_tools import get_agora_xdr
        return await get_agora_xdr()

    async def get_chicago_xdr(self):
        from other.stellar_tools import get_chicago_xdr
        return await get_chicago_xdr()

    async def calc_usdm_usdm_divs(self, session, div_list_id, test_sum, test_for_address):
        from other.stellar_tools import cmd_calc_usdm_usdm_divs
        return await cmd_calc_usdm_usdm_divs(session, div_list_id, test_sum, test_for_address)

    async def async_submit(self, xdr):
        from other.stellar_tools import stellar_async_submit
        return await stellar_async_submit(xdr)

    def sign(self, xdr):
        from other.stellar_tools import stellar_sign
        return stellar_sign(xdr)

    async def calc_usdm_daily(self, session, list_id):
        from other.stellar_tools import cmd_calc_usdm_daily
        return await cmd_calc_usdm_daily(session, list_id)
        
    def stop_all_exchange(self):
        from other.stellar_tools import stellar_stop_all_exchange
        return stellar_stop_all_exchange()

    async def get_mtlap_votes(self):
        from other.stellar_tools import get_mtlap_votes
        return await get_mtlap_votes()

    async def address_id_to_username(self, address, full_data=False):
        from other.stellar_tools import address_id_to_username
        return await address_id_to_username(address, full_data=full_data)

class AirdropService:
    async def check_records(self, tg_id, public_key):
        return await grist_check_airdrop_records(tg_id, public_key)

    async def log_payment(self, tg_id, public_key, nickname, tx_hash, amount, currency="USDM"):
        return await grist_log_airdrop_payment(tg_id, public_key, nickname, tx_hash, amount, currency)

    async def load_configs(self):
        return await grist_load_airdrop_configs()

class ReportService:
    async def update_fest(self, session):
        from scripts.update_report import update_fest
        return await update_fest(session)

    async def update_airdrop(self):
        from scripts.update_report import update_airdrop
        return await update_airdrop()

class AntispamService:
    async def check_spam(self, message, session=None):
        from other.antispam_logic import check_spam
        return await check_spam(message, session)

    async def combo_check_spammer(self, message):
        from other.spam_cheker import combo_check_spammer
        return await combo_check_spammer(message)
    
    async def lols_check_spammer(self, message):
        from other.spam_cheker import lols_check_spammer
        return await lols_check_spammer(message)

    async def delete_and_log_spam(self, message, session=None, rules_name='spam'):
        from other.antispam_logic import delete_and_log_spam
        return await delete_and_log_spam(message, session, rules_name)
    
    async def set_vote(self, message):
        from other.antispam_logic import set_vote
        return await set_vote(message)

class PollService:
    async def save_poll(self, chat_id, message_id, poll_data):
        from other.global_data import global_data
        import json
        await global_data.mongo_config.save_bot_value(chat_id, -1 * message_id, json.dumps(poll_data))

    async def load_poll(self, chat_id, message_id):
        from other.global_data import global_data
        import json
        from routers.polls import empty_poll
        return json.loads(await global_data.mongo_config.load_bot_value(chat_id, -1 * message_id, empty_poll))

    async def save_mtla_poll(self, poll_id, poll_data):
        from other.global_data import global_data, MTLChats
        import json
        await global_data.mongo_config.save_bot_value(MTLChats.MTLA_Poll, int(poll_id), json.dumps(poll_data))

    async def load_mtla_poll(self, poll_id):
        from other.global_data import global_data, MTLChats
        import json
        from routers.polls import empty_poll
        return json.loads(await global_data.mongo_config.load_bot_value(MTLChats.MTLA_Poll, int(poll_id), empty_poll))

class GSpreadService:
    async def copy_a_table(self, title):
        from other.gspread_tools import gs_copy_a_table
        return await gs_copy_a_table(title)

    async def update_a_table_first(self, google_id, question, options, votes):
        from other.gspread_tools import gs_update_a_table_first
        return await gs_update_a_table_first(google_id, question, options, votes)

    async def update_a_table_vote(self, google_id, address, options):
        from other.gspread_tools import gs_update_a_table_vote
        return await gs_update_a_table_vote(google_id, address, options)

    async def check_vote_table(self, google_id):
        from other.gspread_tools import gs_check_vote_table
        return await gs_check_vote_table(google_id)

class GristService:
    async def load_table_data(self, table_id, filter_dict=None):
        from other.grist_tools import grist_manager
        return await grist_manager.load_table_data(table_id, filter_dict=filter_dict)

    async def patch_data(self, table_id, data):
        from other.grist_tools import grist_manager
        return await grist_manager.patch_data(table_id, data)

    async def post_data(self, table, json_data):
        from other.grist_tools import grist_manager
        return await grist_manager.post_data(table, json_data)

    async def fetch_data(self, table, filter_dict=None):
        from other.grist_tools import grist_manager
        return await grist_manager.fetch_data(table, filter_dict)

class ModerationService:
    async def ban_user(self, session, chat_id, user_id, bot, revoke_messages=True):
        from aiogram.exceptions import TelegramBadRequest
        from contextlib import suppress
        from start import add_bot_users
        with suppress(TelegramBadRequest):
            await bot.ban_chat_member(chat_id, user_id, revoke_messages=revoke_messages)
            add_bot_users(session, user_id, None, 2)
            return True
        return False

    async def unban_user(self, session, chat_id, user_id, bot):
        from aiogram.exceptions import TelegramBadRequest
        from contextlib import suppress
        from start import add_bot_users
        with suppress(TelegramBadRequest):
            if user_id > 0:
                await bot.unban_chat_member(chat_id, user_id)
            else:
                await bot.unban_chat_sender_chat(chat_id, user_id)
            add_bot_users(session, user_id, None, 0)
            return True
        return False

    def check_user_status(self, user_id):
        from other.global_data import global_data
        return global_data.check_user(user_id)

    def get_user_id(self, session, username):
        from db.repositories import ChatsRepository
        return ChatsRepository(session).get_user_id(username)

    def add_bot_user(self, session, user_id, username, user_type):
        from start import add_bot_users
        add_bot_users(session, user_id, username, user_type)

class AIService:
    async def generate_image(self, text):
        from other.open_ai_tools import generate_image
        return await generate_image(text)

    async def talk(self, chat_id, text, gpt4=False, googleit=False):
        from other.open_ai_tools import talk
        return await talk(chat_id, text, gpt4=gpt4, googleit=googleit)

    async def talk_get_comment(self, chat_id, text):
        from other.open_ai_tools import talk_get_comment
        return await talk_get_comment(chat_id, text)

    async def add_task_to_google(self, msg):
        from other.open_ai_tools import add_task_to_google
        return await add_task_to_google(msg)

    def get_horoscope(self):
        from other.open_ai_tools import get_horoscope
        return get_horoscope()

class ReportService:
    async def update_guarantors_report(self):
        from scripts.update_report import update_guarantors_report
        return await update_guarantors_report()

    async def update_main_report(self, session):
        from scripts.update_report import update_main_report
        return await update_main_report(session)

    async def update_donate_report(self, session):
        from scripts.update_report import update_donate_report
        return await update_donate_report(session)

    async def update_mmwb_report(self, session):
        from scripts.update_report import update_mmwb_report
        return await update_mmwb_report(session)

    async def update_bim_data(self, session):
        from scripts.update_report import update_bim_data
        return await update_bim_data(session)

class TalkService:
    def __init__(self, bot):
        self.bot = bot

    async def answer_notify_message(self, message):
        from other.global_data import global_data
        if (message.reply_to_message.from_user.id == self.bot.id
                and message.reply_to_message.reply_markup
                and message.reply_to_message.external_reply
                and message.reply_to_message.external_reply.chat.id in global_data.notify_message):
            info = message.reply_to_message.reply_markup.inline_keyboard[0][0].callback_data.split(':')
            if len(info) > 2 and info[0] == 'Reply':
                msg = await message.copy_to(chat_id=int(info[2]), reply_to_message_id=int(info[1]))
                if message.chat.username:
                    await self.bot.send_message(
                        chat_id=int(info[2]),
                        text=f'Ответ из чата @{message.chat.username}',
                        reply_to_message_id=msg.message_id
                    )

    async def remind(self, message, session, app_context=None):
        from other.global_data import global_data, BotValueTypes, is_skynet_admin
        from other.stellar_tools import cmd_alarm_url, send_by_list
        from other.text_tools import extract_url
        if message.reply_to_message and message.reply_to_message.forward_from_chat:
            alarm_list = cmd_alarm_url(extract_url(message.reply_to_message.text))
            msg = alarm_list + '\nСмотрите топик / Look at the topic message'
            await message.reply(text=msg)
            if alarm_list.find('@') != -1:
                if is_skynet_admin(message):
                    all_users = alarm_list.split()
                    url = f'https://t.me/c/1649743884/{message.reply_to_message.forward_from_message_id}'
                    await send_by_list(bot=self.bot, all_users=all_users, message=message, url=url, session=session)
        else:
            msg_id = await global_data.mongo_config.load_bot_value(message.chat.id, BotValueTypes.PinnedId)
            msg = await global_data.mongo_config.load_bot_value(message.chat.id,
                                                                BotValueTypes.PinnedUrl) + '\nСмотрите закреп / Look at the pinned message'
            await self.bot.send_message(message.chat.id, msg, reply_to_message_id=msg_id,
                                    message_thread_id=message.message_thread_id)

class GroupService:
    async def get_members(self, chat_id):
        from other.pyro_tools import get_group_members
        return await get_group_members(chat_id)

    async def remove_deleted_users(self, chat_id):
        from other.pyro_tools import remove_deleted_users
        return await remove_deleted_users(chat_id)

    async def enforce_entry_channel(self, bot, chat_id, user_id, required_channel):
        from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
        import asyncio
        is_member, _ = await self.check_membership(bot, required_channel, user_id)
            
        if is_member:
            return True, False

        try:
            await bot.unban_chat_member(chat_id, user_id)
            await asyncio.sleep(0.2)
            return False, True
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            from loguru import logger
            logger.warning(f'enforce_entry_channel failed for user {user_id} in chat {chat_id}: {exc}')
            return False, False

    async def run_entry_channel_check(self, bot, chat_id):
        from other.global_data import global_data
        import asyncio
        required_channel = global_data.entry_channel.get(chat_id)
        if not required_channel:
            raise ValueError('entry_channel setting is not enabled for this chat')

        members = await self.get_members(chat_id)

        checked_count = 0
        action_count = 0

        for member in members:
            if member.is_bot or member.is_admin:
                continue

            checked_count += 1

            membership_ok, action_applied = await self.enforce_entry_channel(bot, chat_id, member.user_id, required_channel)
            if membership_ok:
                await asyncio.sleep(0.1)
                continue

            if action_applied:
                action_count += 1

            await asyncio.sleep(0.5)

        return checked_count, action_count

    async def check_membership(self, bot, chat_id, user_id):
        from other.group_tools import check_membership
        return await check_membership(bot, chat_id, user_id)

    async def enforce_entry_channel(self, bot, chat_id, user_id, required_channel):
        from other.group_tools import enforce_entry_channel
        return await enforce_entry_channel(bot, chat_id, user_id, required_channel)

class UtilsService:
    async def sleep_and_delete(self, message, seconds=None):
        from other.aiogram_tools import cmd_sleep_and_delete
        return await cmd_sleep_and_delete(message, sleep_time=seconds)
        
    async def multi_reply(self, message, text):
        from other.aiogram_tools import multi_reply
        return await multi_reply(message, text)
        
    async def is_admin(self, message, chat_id=None):
        from other.global_data import is_admin
        return await is_admin(message, chat_id=chat_id)

    async def multi_reply(self, message, text):
        from other.aiogram_tools import multi_reply
        return await multi_reply(message, text)

    async def multi_answer(self, message, text):
        from other.aiogram_tools import multi_answer
        return await multi_answer(message, text)

    async def answer_text_file(self, message, text, filename=None):
        from other.aiogram_tools import answer_text_file
        return await answer_text_file(message, text, filename=filename)

    def add_text(self, lines, num_line, text):
        from other.aiogram_tools import add_text
        return add_text(lines, num_line, text)

    def is_skynet_admin(self, message):
        from other.global_data import is_skynet_admin
        return is_skynet_admin(message)

    def get_username_link(self, user):
        from other.aiogram_tools import get_username_link
        return get_username_link(user)

    async def parse_timedelta_from_message(self, message):
        from other.timedelta import parse_timedelta_from_message
        return await parse_timedelta_from_message(message)

class ConfigService:
    async def save_bot_value(self, key, bot_value_type, value):
        from other.global_data import global_data
        return await global_data.mongo_config.save_bot_value(key, bot_value_type, value)

    async def load_bot_value(self, key, bot_value_type, default=None):
        from other.global_data import global_data
        return await global_data.mongo_config.load_bot_value(key, bot_value_type, default)

    async def get_chat_dict_by_key(self, key, is_int=False):
        from other.global_data import global_data
        return await global_data.mongo_config.get_chat_dict_by_key(key, is_int)

    async def get_chat_ids_by_key(self, key):
        from other.global_data import global_data
        return await global_data.mongo_config.get_chat_ids_by_key(key)
        
    async def add_user_to_chat(self, chat_id, user_id):
        from other.global_data import global_data
        return await global_data.mongo_config.add_user_to_chat(chat_id, user_id)
        
    async def remove_user_from_chat(self, chat_id, user_id):
        from other.global_data import global_data
        return await global_data.mongo_config.remove_user_from_chat(chat_id, user_id)

    def check_user(self, user_id):
        from other.global_data import global_data
        return global_data.check_user(user_id)

    def is_no_first_link(self, chat_id):
        from other.global_data import global_data
        return chat_id in global_data.no_first_link
    
    def add_no_first_link(self, chat_id):
        from other.global_data import global_data
        if chat_id not in global_data.no_first_link:
            global_data.no_first_link.append(chat_id)

    def remove_no_first_link(self, chat_id):
        from other.global_data import global_data
        if chat_id in global_data.no_first_link:
            global_data.no_first_link.remove(chat_id)

    def is_full_data(self, chat_id):
        from other.global_data import global_data
        return chat_id in global_data.full_data
