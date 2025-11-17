import asyncio
import html
import re
from typing import Optional

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from other.aiogram_tools import HasRegex
from other.config_reader import config
from other.global_data import MTLChats
from other.grist_tools import grist_check_airdrop_records, grist_log_airdrop_payment
from other.stellar_tools import get_balances, MTLAssets, send_payment_async
from other.web_tools import http_session_manager

router = Router()
router.message.filter(F.chat.id == -1002294641071)

AIRDROP_SOURCE_ADDRESS = "GCUBKDGH4PG6LN43XNZT3FYQBHMAJ4DPPXJ46YDAKAQDUJY3QRPMDROP"
AIRDROP_SEND_AMOUNT = "2"


class AirdropCallbackData(CallbackData, prefix="aird"):
    action: str
    message_id: int


airdrop_requests: dict[int, dict] = {}


async def check_membership(bot: Bot, chat_id: int, user_id: int) -> tuple[bool, types.User | None]:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_member = member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
        ]
        return is_member, member.user
    except TelegramBadRequest:
        return False, None


def build_request_keyboard(message_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=f"Отправить {AIRDROP_SEND_AMOUNT} USDM",
                callback_data=AirdropCallbackData(action="send", message_id=message_id).pack()
            ),
            InlineKeyboardButton(
                text="Убрать кнопки",
                callback_data=AirdropCallbackData(action="remove", message_id=message_id).pack()
            ),
        ]]
    )


def build_confirmation_keyboard(username: Optional[str]) -> InlineKeyboardMarkup:
    label = username or "admin"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"✅ {label}", callback_data="👀")]]
    )


async def build_trustline_checks(stellar_address: str) -> list[str]:
    asset_codes = ("MTL", "USDM", "EURMTL")
    try:
        balances = await get_balances(stellar_address)
    except Exception as exc:
        logger.warning(f"Не удалось получить балансы для {stellar_address}: {exc}")
        return ["Не удалось получить данные о трастлайнах"]

    checks: list[str] = []
    for code in asset_codes:
        if balances and code in balances:
            balance_value = balances[code]
            checks.append(f"Линия доверия к {code}: открыта (баланс {balance_value})")
        else:
            checks.append(f"Линия доверия к {code}: не открыта")
    return checks


async def process_airdrop_payment(callback: types.CallbackQuery, message_id: int, request_data: dict):
    try:
        tx_result = await send_payment_async(
            source_address=AIRDROP_SOURCE_ADDRESS,
            destination=request_data["stellar_address"],
            asset=MTLAssets.usdm_asset,
            amount=AIRDROP_SEND_AMOUNT,
        )
    except Exception as exc:
        logger.error(f"Ошибка при отправке аирдропа: {exc}")
        await callback.message.answer("Не удалось отправить аирдроп. Проверьте логи.")
        return

    tx_hash = tx_result.get("hash") or tx_result.get("id") or ""
    try:
        await grist_log_airdrop_payment(
            tg_id=request_data["tg_id"],
            public_key=request_data["stellar_address"],
            nickname=request_data["username"],
            tx_hash=tx_hash,
            amount=float(AIRDROP_SEND_AMOUNT),
        )
    except Exception as exc:
        logger.error(f"Не удалось записать аирдроп в Grist: {exc}")

    confirmation_keyboard = build_confirmation_keyboard(callback.from_user.username or str(callback.from_user.id))
    await callback.message.edit_reply_markup(reply_markup=confirmation_keyboard)
    airdrop_requests.pop(message_id, None)

    if tx_hash:
        await callback.message.answer(
            f"Перевод {AIRDROP_SEND_AMOUNT} USDM отправлен. https://stellar.expert/explorer/public/tx/{tx_hash}"
        )


async def get_bsn_recommendations(address: str) -> tuple[int, list]:
    """
    Gets recommendations for an address from BSN API
    
    :param address: Stellar address
    :return: (number of recommendations, list of recommenders)
    """
    url = f"https://bsn.mtla.me/accounts/{address}?tag=RecommendToMTLA"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    try:
        response = await http_session_manager.get_web_request('GET', url, headers=headers, return_type='json')
        if response.status == 200:
            data = response.data
            recommendations = data.get('links', {}).get('income', {}).get('RecommendToMTLA', {}).get('links', {})
            recommenders = []
            if recommendations:
                for address, info in recommendations.items():
                    display_name = info.get('display_name', address)
                    recommenders.append(display_name)
            return len(recommenders), recommenders
        else:
            logger.error(f"Ошибка получения рекомендаций: статус {response.status}")
            return 0, []
    except Exception as e:
        logger.error(f"Ошибка при запросе рекомендаций: {e}")
        return 0, []


@router.message(HasRegex((r'#ID\d+', r'G[A-Z0-9]{50,}')))
async def handle_address_messages(message: types.Message):
    html_text = message.html_text or message.text or ''
    plain_text = message.text or ''
    id_matches = list(re.finditer(r'#ID(\d+)', html_text))
    match_id = id_matches[-1] if id_matches else None
    match_stellar = re.search(r'(G[A-Z0-9]{50,})', plain_text)
    username_match = re.search(r'\|[^|]*\|\s*(@\S+)', plain_text)

    if not (match_id and match_stellar):
        return

    user_id = match_id.group(1)
    tg_id = int(user_id)
    username = username_match.group(1) if username_match else None
    stellar_address = match_stellar.group(1)
    username_display = html.escape(username) if username else 'Отсутствует'

    results = []
    trustline_checks = await build_trustline_checks(stellar_address)
    results.extend(trustline_checks)
    chat_list = (
        (MTLChats.MonteliberoChanel, "канал Montelibero ru"),
        (MTLChats.MTLAAgoraGroup, "MTLAAgoraGroup"),
        (-1001429770534, "chat Montelibero ru"),
    )

    for chat_id, chat_name in chat_list:
        is_member, user = await check_membership(message.bot, chat_id, tg_id)
        if is_member:
            if user and user.username:
                results.append(f"Пользователь @{user.username} подписан на {chat_name}")
            else:
                results.append(f"Пользователь подписан на {chat_name}")
                results.append("<b>!Внимание: нет юзернейма!</b>")
        else:
            results.append(f"Пользователь не подписан на {chat_name}")

    results.extend(await grist_check_airdrop_records(tg_id, stellar_address))

    header_lines = [
        "Новый запрос!",
        "",
        f"Юзернейм: {username_display}",
        f"Юзер ID: {user_id}",
        f"Стеллар адрес: {stellar_address}",
        "",
        "<b>Результаты проверок:</b>",
        "",
    ]

    output_message = '\n'.join(header_lines + results)
    sent_message = await message.answer(output_message, parse_mode="HTML")

    keyboard = build_request_keyboard(sent_message.message_id)
    await sent_message.edit_reply_markup(reply_markup=keyboard)

    airdrop_requests[sent_message.message_id] = {
        "stellar_address": stellar_address,
        "tg_id": tg_id,
        "username": username or "",
    }


@router.callback_query(AirdropCallbackData.filter())
async def handle_airdrop_callback(callback: types.CallbackQuery, callback_data: AirdropCallbackData):
    action = callback_data.action
    message_id = callback_data.message_id
    request_data = airdrop_requests.get(message_id)

    if not request_data:
        await callback.answer("Данные не найдены", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    if action == "remove":
        airdrop_requests.pop(message_id, None)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("Кнопки убраны")
        return

    if action == "send":
        await callback.answer("ок выполняю, ожидайте")
        await process_airdrop_payment(callback, message_id, request_data)


def register_handlers(dp, bot):
    if config.test_mode:
        dp.include_router(router)
        logger.info('router secretary_mtl was loaded')


if __name__ == '__main__':
    print(asyncio.run(get_bsn_recommendations('GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2')))
