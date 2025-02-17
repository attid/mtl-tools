import sys
from other.stellar_tools import get_balances
from datetime import datetime, timedelta
from aiogram import Router, types, Bot
from aiogram import F
import re
import asyncio
from loguru import logger

from other.global_data import global_data, MTLChats


router = Router()
router.message.filter(F.chat.id == -1002328459105)

@router.message(F.text.regexp(r'.*#ID\d+'), F.text.regexp(r'.*G[A-Z0-9]{30,}'))
async def handle_address_messages(message: types.Message):
    logger.info("handle_address_messages triggered!") # Добавлено для отладки
    logger.debug(f"Секретарь MTLA получил сообщение от {message.from_user.id} в чате {message.chat.id}: {message.text}")
    match_id = re.search(r'#ID(\d+)', message.text)
    match_stellar = re.search(r'(G[A-Z0-9]{30,})', message.text)

    if match_id and match_stellar:
        logger.info("ID и Stellar-адрес найдены!") # Добавлено для отладки
        logger.info(f"Найденные параметры: ID: {match_id.group(1)}, Адрес стелара: {match_stellar.group(1)}")

        username = ""
        user_id = f"#ID{match_id.group(1)}"
        trustline_status = ""
        token_balance = ""
        username_presence = ""
        is_active_member = ""
        bsn_recommendations = ""
        action_message = ""

        balances = await get_balances(match_stellar.group(1))
        has_mtlap_trustline = "MTLAP" in balances
        token_balance_mtlap = balances.get("MTLAP", 0)
        has_mtlac_trustline = "MTLAC" in balances
        token_balance_mtlac = balances.get("MTLAC", 0)

        trustline_status_mtlap = "Открыта" if has_mtlap_trustline else "Не открыта"
        token_balance_status_mtlap = str(token_balance_mtlap)
        trustline_status_mtlac = "Открыта" if has_mtlac_trustline else "Не открыта"
        token_balance_status_mtlac = str(token_balance_mtlac)


        message_template = "Новый запрос на вступление в МТЛА!\n\n" \
                           "Юзернейм: {username}\n" \
                           "Юзер ID: {user_id}\n" \
                           "Стеллар адрес: {stellar_address}\n\n" \
                           "**Результаты проверок:**\n\n" \
                           f"Линия доверия к MTLAP: {trustline_status_mtlap}\n" \
                           f"Баланс токенов MTLAP: {token_balance_status_mtlap}\n" \
                           f"Линия доверия к MTLAC: {trustline_status_mtlac}\n" \
                           f"Баланс токенов MTLAC: {token_balance_status_mtlac}\n" \
                           "Наличие юзернейма: {username_presence}\n" \
                           "Активный член МТЛАП: {is_active_member}\n" \
                           "BSN рекомендации: {bsn_recommendations}\n\n" \
                           "**Действие:**\n\n" \
                           "{action_message}\n\n" \
                           "---\n\n"

        output_message = message_template.format(
            username=username,
            user_id=user_id,
            stellar_address=match_stellar.group(1),
            trustline_status_mtlap=trustline_status_mtlap,
            token_balance_status_mtlap=token_balance_status_mtlap,
            trustline_status_mtlac=trustline_status_mtlac,
            token_balance_status_mtlac=token_balance_status_mtlac,
            username_presence=username_presence,
            is_active_member=is_active_member,
            bsn_recommendations=bsn_recommendations,
            action_message=action_message,
        )
        logger.info(f"Сообщение для пользователя: {output_message}")

        await message.answer(output_message)


# @router.message()
# async def test(message: types.Message):
#     print(message.text)

def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router secretary_mtl was loaded')