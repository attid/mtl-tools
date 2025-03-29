import sys

from other.config_reader import config
from other.stellar_tools import get_balances
from datetime import datetime, timedelta
from aiogram import Router, types, Bot
from aiogram import F
import re
import asyncio
from loguru import logger
from aiogram.filters.callback_data import CallbackData

from other.global_data import global_data, MTLChats
from other.web_tools import http_session_manager
from other.aiogram_tools import HasRegex, HasText
from other.grist_tools import grist_manager
from other.mtl_tools import MTLGrist

router = Router()
router.message.filter(F.chat.id == -1002328459105)

# Словарь для хранения адресов по ID сообщения
stellar_addresses = {}
# Словарь для хранения информации о пользователях
user_info = {}

# Фабрика колбеков для кнопок
class MTLACallbackData(CallbackData, prefix="mtla"):
    action: str  # "mtlap" или "mtlac"
    message_id: int  # ID сообщения


async def get_bsn_recommendations(address: str) -> tuple[int, list]:
    """
    Получает рекомендации для адреса из BSN API
    
    :param address: Stellar адрес
    :return: (количество рекомендаций, список рекомендателей)
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


async def add_user_to_mtla_users(username: str, user_id: int, stellar_address: str, has_mtlap: bool = False):
    """
    Добавляет пользователя в таблицу MTLA_USERS в Grist
    
    :param username: Имя пользователя в Telegram
    :param user_id: ID пользователя в Telegram
    :param stellar_address: Stellar адрес пользователя
    :param has_mtlap: Имеет ли пользователь токен MTLAP
    :return: ID записи в Grist или None в случае ошибки
    """
    try:
        # Проверяем, существует ли уже пользователь с таким TGID
        existing_user = await grist_manager.load_table_data(MTLGrist.MTLA_USERS, filter_dict={"TGID": [user_id]})
        
        if existing_user:
            # Пользователь уже существует, не обновляем данные
            record_id = existing_user[0]['id']
            logger.info(f"Пользователь уже существует в MTLA_USERS: {username}, ID: {record_id}")
            return record_id
        else:
            # Создаем новую запись
            new_record = {
                "Telegram": username,
                "TGID": user_id,
                "Stellar": stellar_address,
                "Trustline": True,
                "MTLAP": 1 if has_mtlap else 0,
                "Want": True,
                "In_Assembly": False,
                "Has_verify": False
            }
            
            # Формируем данные для добавления в Grist
            json_data = {"records": [{"fields": new_record}]}
            
            # Добавляем запись в таблицу
            success = await grist_manager.post_data(MTLGrist.MTLA_USERS, json_data)
            
            if success:
                # Получаем ID новой записи
                updated_users = await grist_manager.load_table_data(MTLGrist.MTLA_USERS, filter_dict={"TGID": [user_id]})
                if updated_users:
                    record_id = updated_users[0]['id']
                    logger.info(f"Добавлен новый пользователь в MTLA_USERS: {username}, ID: {record_id}")
                    return record_id
                else:
                    logger.error("Не удалось найти добавленного пользователя")
                    return None
            else:
                logger.error("Не удалось добавить пользователя в MTLA_USERS")
                return None
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя в MTLA_USERS: {e}")
        return None


async def add_corporate_to_mtla_corporates(stellar_address: str, telegram_contact: str, name: str = ""):
    """
    Добавляет корпоративного пользователя в таблицу MTLA_Corporates в Grist
    
    :param stellar_address: Stellar адрес корпоративного пользователя
    :param telegram_contact: Контакт в Telegram
    :param name: Название организации (опционально)
    :return: ID записи в Grist или None в случае ошибки
    """
    try:
        # Проверяем, существует ли уже запись с таким Stellar адресом
        existing_corporate = await grist_manager.load_table_data(MTLGrist.MTLA_Corporates, filter_dict={"Stellar": [stellar_address]})
        
        if existing_corporate:
            # Корпоративный пользователь уже существует, не обновляем данные
            record_id = existing_corporate[0]['id']
            logger.info(f"Корпоративный пользователь уже существует в MTLA_Corporates: {stellar_address}, ID: {record_id}")
            return record_id
        else:
            # Создаем новую запись
            new_record = {
                "Stellar": stellar_address,
                "Telegram_Contact": telegram_contact,
                "MTLAC": 1,
                "Donor": False
            }
            if name:
                new_record["Name"] = name
            
            # Формируем данные для добавления в Grist
            json_data = {"records": [{"fields": new_record}]}
            
            # Добавляем запись в таблицу
            success = await grist_manager.post_data(MTLGrist.MTLA_Corporates, json_data)
            
            if success:
                # Получаем ID новой записи
                updated_corporates = await grist_manager.load_table_data(MTLGrist.MTLA_Corporates, filter_dict={"Stellar": [stellar_address]})
                if updated_corporates:
                    record_id = updated_corporates[0]['id']
                    logger.info(f"Добавлена новая корпоративная запись в MTLA_Corporates: {stellar_address}, ID: {record_id}")
                    return record_id
                else:
                    logger.error("Не удалось найти добавленную корпоративную запись")
                    return None
            else:
                logger.error("Не удалось добавить корпоративную запись в MTLA_Corporates")
                return None
    except Exception as e:
        logger.error(f"Ошибка при добавлении корпоративной записи в MTLA_Corporates: {e}")
        return None


@router.message(HasRegex((r'#ID\d+', r'G[A-Z0-9]{50,}')))
async def handle_address_messages(message: types.Message):
    # Находим последнее вхождение ID
    id_matches = list(re.finditer(r'#ID(\d+)', message.text))
    match_id = id_matches[-1] if id_matches else None

    # Находим Stellar адрес
    match_stellar = re.search(r'(G[A-Z0-9]{50,})', message.text)

    # Ищем username после второй вертикальной черты
    username_match = re.search(r'\|[^|]*\|\s*(@\S+)', message.text)

    if match_id and match_stellar:
        logger.info("ID и Stellar-адрес найдены!")
        logger.info(f"Найденные параметры: ID: {match_id.group(1)}, Адрес стелара: {match_stellar.group(1)}")

        username = username_match.group(1) if username_match else "Отсутствует"
        user_id = f"#ID{match_id.group(1)}"
        stellar_address = match_stellar.group(1)
        trustline_status = ""
        token_balance = ""
        # Определяем статус username
        username_presence = "Присутствует" if username != "Отсутствует" else "Отсутствует"
        is_active_member = ""
        action_message = ""

        # Получаем балансы
        balances = await get_balances(stellar_address)
        has_mtlap_trustline = "MTLAP" in balances
        token_balance_mtlap = balances.get("MTLAP", 0)
        has_mtlac_trustline = "MTLAC" in balances
        token_balance_mtlac = balances.get("MTLAC", 0)

        trustline_status_mtlap = "Открыта" if has_mtlap_trustline else "Не открыта"
        token_balance_status_mtlap = str(token_balance_mtlap)
        trustline_status_mtlac = "Открыта" if has_mtlac_trustline else "Не открыта"
        token_balance_status_mtlac = str(token_balance_mtlac)

        # Получаем рекомендации
        rec_count, recommenders = await get_bsn_recommendations(stellar_address)
        if rec_count > 0:
            bsn_recommendations = f"Есть {rec_count} рекомендаций от:\n" + "\n".join(f"- {r}" for r in recommenders)
        else:
            bsn_recommendations = "Рекомендации отсутствуют"

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
                           "BSN рекомендации: {bsn_recommendations}\n\n"

        output_message = message_template.format(
            username=username,
            user_id=user_id,
            stellar_address=stellar_address,
            trustline_status_mtlap=trustline_status_mtlap,
            token_balance_status_mtlap=token_balance_status_mtlap,
            trustline_status_mtlac=trustline_status_mtlac,
            token_balance_status_mtlac=token_balance_status_mtlac,
            username_presence=username_presence,
            is_active_member=is_active_member,
            bsn_recommendations=bsn_recommendations
        )

        print(output_message)

        # Отправляем сообщение и сохраняем его
        sent_message = await message.answer(output_message)
        
        # Сохраняем адрес в словаре по ID сообщения
        stellar_addresses[sent_message.message_id] = stellar_address
        
        # Создаем клавиатуру с двумя кнопками, используя фабрику колбеков
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Добавить MTLAP", 
                    callback_data=MTLACallbackData(action="mtlap", message_id=sent_message.message_id).pack()
                ),
                types.InlineKeyboardButton(
                    text="Добавить MTLAC", 
                    callback_data=MTLACallbackData(action="mtlac", message_id=sent_message.message_id).pack()
                )
            ]
        ])
        
        # Обновляем сообщение с клавиатурой
        await sent_message.edit_reply_markup(reply_markup=keyboard)

        # Сохраняем информацию о пользователе в словаре
        user_info[sent_message.message_id] = {
            "username": username,
            "user_id": int(match_id.group(1)) if match_id else None,
            "stellar_address": stellar_address
        }


@router.callback_query(MTLACallbackData.filter())
async def handle_mtla_callback(callback: types.CallbackQuery, callback_data: MTLACallbackData):
    # Получаем данные из колбека
    action = callback_data.action
    message_id = callback_data.message_id
    
    # Получаем адрес из словаря по ID сообщения
    stellar_address = stellar_addresses.get(message_id)
    
    if not stellar_address:
        await callback.answer("Ошибка: адрес не найден", show_alert=True)
        return
    
    action_text = "MTLAP" if action == "mtlap" else "MTLAC"
    
    # Создаем новую клавиатуру с одной кнопкой
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"👀 {callback.from_user.username}", callback_data="👀")]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer(f"Вы выбрали добавление {action_text}")
    
    # Получаем информацию о пользователе
    info = user_info.get(message_id, {})
    username = info.get("username", "Неизвестно")
    user_id = info.get("user_id")
    
    try:
        if action == "mtlap":
            # Добавляем пользователя в таблицу MTLA_USERS
            if user_id:
                record_id = await add_user_to_mtla_users(
                    username=username.replace("@", ""), 
                    user_id=user_id, 
                    stellar_address=stellar_address,
                    has_mtlap=True
                )
                logger.info(f"Пользователь добавлен в MTLA_USERS с ID: {record_id}")
            else:
                logger.error("Не удалось добавить пользователя в MTLA_USERS: отсутствует user_id")
        
        elif action == "mtlac":
            # Добавляем корпоративного пользователя в таблицу MTLA_Corporates
            record_id = await add_corporate_to_mtla_corporates(
                stellar_address=stellar_address,
                telegram_contact=username
            )
            logger.info(f"Корпоративный пользователь добавлен в MTLA_Corporates с ID: {record_id}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке колбека {action}: {e}")
    
    logger.info(f"Пользователь {callback.from_user.username} выбрал добавление {action_text} для адреса {stellar_address}")


def register_handlers(dp, bot):
    if config.test_mode:
        dp.include_router(router)
        logger.info('router secretary_mtl was loaded')


if __name__ == '__main__':
    print(asyncio.run(get_bsn_recommendations('GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2')))
