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
from stellar_sdk import Asset

from other.aiogram_tools import HasRegex
from other.constants import MTLChats
from other.grist_tools import (AirdropConfigItem, grist_check_airdrop_records,
                               grist_load_airdrop_configs, grist_log_airdrop_payment)
from other.stellar import get_balances, send_payment_async

router = Router()
router.message.filter(F.chat.id == -1002294641071)

AIRDROP_SOURCE_ADDRESS = "GCUBKDGH4PG6LN43XNZT3FYQBHMAJ4DPPXJ46YDAKAQDUJY3QRPMDROP"


class AirdropCallbackData(CallbackData, prefix="aird"):
    action: str
    message_id: int
    config_id: int


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


def build_request_keyboard(message_id: int, configs: list[AirdropConfigItem]) -> InlineKeyboardMarkup:
    rows = []
    for config_item in configs:
        label = f"Отправить {config_item.amount} {config_item.asset_code}"
        rows.append([InlineKeyboardButton(
            text=label,
            callback_data=AirdropCallbackData(
                action="send",
                message_id=message_id,
                config_id=config_item.record_id,
            ).pack(),
        )])
    rows.append([InlineKeyboardButton(
        text="Убрать кнопки",
        callback_data=AirdropCallbackData(
            action="remove",
            message_id=message_id,
            config_id=0,
        ).pack()
    )])
    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def build_confirmation_keyboard(username: Optional[str]) -> InlineKeyboardMarkup:
    label = username or "admin"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"✅ {label}", callback_data="👀")]]
    )


async def build_trustline_checks(stellar_address: str, stellar_service=None) -> list[str]:
    asset_codes = ("MTL", "USDM", "EURMTL")
    try:
        if stellar_service:
            balances = await stellar_service.get_balances(stellar_address)
        else:
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


async def check_source_balance(source_address: str, asset_code: str, amount: str, stellar_service=None) -> tuple[bool, str]:
    try:
        if stellar_service:
            balances = await stellar_service.get_balances(source_address)
        else:
            balances = await get_balances(source_address)
    except Exception as exc:
        logger.error(f"Не удалось получить балансы источника {source_address}: {exc}")
        return False, "Не удалось получить балансы источника"

    if not balances or asset_code not in balances:
        return False, f"На источнике нет трастлайна к {asset_code}"

    try:
        needed_amount = float(amount)
    except (TypeError, ValueError):
        return False, "Некорректная сумма аирдропа"

    balance_value = float(balances[asset_code])
    if balance_value < needed_amount:
        return False, (
            f"Недостаточно средств на источнике: баланс {balance_value} {asset_code}, "
            f"нужно {amount} {asset_code}"
        )

    return True, ""


def build_airdrop_asset(config_item: AirdropConfigItem) -> Asset:
    asset_code = config_item.asset_code.strip()
    asset_issuer = config_item.asset_issuer.strip()
    if asset_code.upper() == "XLM":
        return Asset.native()
    if not asset_issuer:
        raise ValueError("Asset issuer is required for non-XLM assets")
    return Asset(asset_code, asset_issuer)


async def process_airdrop_payment(callback: types.CallbackQuery, message_id: int,
                                  request_data: dict, config_item: AirdropConfigItem, app_context=None):
    try:
        asset = build_airdrop_asset(config_item)
    except ValueError as exc:
        logger.error(f"Некорректный конфиг аирдропа: {exc}")
        await callback.message.answer("Конфиг аирдропа некорректный. Проверьте данные в Grist.")
        return

    balance_ok, balance_message = await check_source_balance(
        AIRDROP_SOURCE_ADDRESS,
        config_item.asset_code,
        config_item.amount,
        app_context.stellar_service if app_context else None
    )
    if not balance_ok:
        await callback.message.answer(balance_message)
        return

    try:
        if app_context:
            tx_result = await app_context.stellar_service.send_payment_async(
                source_address=AIRDROP_SOURCE_ADDRESS,
                destination=request_data["stellar_address"],
                asset=asset,
                amount=config_item.amount,
            )
        else:
            tx_result = await send_payment_async(
                source_address=AIRDROP_SOURCE_ADDRESS,
                destination=request_data["stellar_address"],
                asset=asset,
                amount=config_item.amount,
            )
    except Exception as exc:
        logger.error(f"Ошибка при отправке аирдропа: {exc}")
        await callback.message.answer("Не удалось отправить аирдроп. Проверьте логи.")
        return

    tx_hash = tx_result.get("hash") or tx_result.get("id") or ""
    try:
        if app_context:
            await app_context.airdrop_service.log_payment(
                tg_id=request_data["tg_id"],
                public_key=request_data["stellar_address"],
                nickname=request_data["username"],
                tx_hash=tx_hash,
                amount=float(config_item.amount),
                currency=config_item.asset_code
            )
        else:
            await grist_log_airdrop_payment(
                tg_id=request_data["tg_id"],
                public_key=request_data["stellar_address"],
                nickname=request_data["username"],
                tx_hash=tx_hash,
                amount=float(config_item.amount),
                currency=config_item.asset_code
            )
    except Exception as exc:
        logger.error(f"Не удалось записать аирдроп в Grist: {exc}")

    confirmation_keyboard = build_confirmation_keyboard(callback.from_user.username or str(callback.from_user.id))
    await callback.message.edit_reply_markup(reply_markup=confirmation_keyboard)
    airdrop_requests.pop(message_id, None)

    if tx_hash:
        await callback.message.answer(
            f"Перевод {config_item.amount} {config_item.asset_code} отправлен. "
            f"https://viewer.eurmtl.me/transaction/{tx_hash}"
        )


@router.message(HasRegex((r'#ID\d+', r'G[A-Z0-9]{50,}')))
async def handle_address_messages(message: types.Message, app_context=None):
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
    trustline_checks = await build_trustline_checks(stellar_address, app_context.stellar_service if app_context else None)
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

    if app_context:
        results.extend(await app_context.airdrop_service.check_records(tg_id, stellar_address))
        configs = await app_context.airdrop_service.load_configs()
    else:
        results.extend(await grist_check_airdrop_records(tg_id, stellar_address))
        configs = await grist_load_airdrop_configs()
    if not configs:
        results.append("Нет активных конфигураций аирдропа в таблице CONFIG")

    header_lines = [
        "Новый запрос!",
        "",
        f"Юзернейм: {username_display}",
        f"Юзер ID: {user_id}",
        f"Стеллар адрес: {stellar_address}",
        f'BSN: <a href="https://bsn.expert/accounts/{stellar_address}">bsn.expert</a>',
        "",
        "<b>Результаты проверок:</b>",
        "",
    ]

    output_message = '\n'.join(header_lines + results)
    sent_message = await message.answer(output_message, parse_mode="HTML", disable_web_page_preview=True)

    keyboard = build_request_keyboard(sent_message.message_id, configs)
    await sent_message.edit_reply_markup(reply_markup=keyboard)

    airdrop_requests[sent_message.message_id] = {
        "stellar_address": stellar_address,
        "tg_id": tg_id,
        "username": username or "",
        "configs": {item.record_id: item for item in configs},
    }


@router.callback_query(AirdropCallbackData.filter())
async def handle_airdrop_callback(callback: types.CallbackQuery, callback_data: AirdropCallbackData, app_context=None):
    action = callback_data.action
    message_id = callback_data.message_id
    config_id = callback_data.config_id
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
        config_item = request_data.get("configs", {}).get(config_id)
        if not config_item:
            await callback.answer("Конфиг не найден", show_alert=True)
            return
        await process_airdrop_payment(callback, message_id, request_data, config_item, app_context)


def register_handlers(dp, bot):
    #if config.test_mode:
    dp.include_router(router)
    logger.info('router airdrops was loaded')


if __name__ == '__main__':
    print(asyncio.run(print('GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2')))
