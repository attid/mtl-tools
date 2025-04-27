
from other.config_reader import config
from other.stellar_tools import get_balances
from aiogram import Router, types
from aiogram import F
import re
import asyncio
from loguru import logger

from other.web_tools import http_session_manager
from other.aiogram_tools import HasRegex

router = Router()
router.message.filter(F.chat.id == -1002294641071)


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
        trustline_status = ""
        token_balance = ""
        # Определяем статус username
        username_presence = "Присутствует" if username != "Отсутствует" else "Отсутствует"
        is_active_member = ""

        # Получаем балансы
        balances = await get_balances(match_stellar.group(1))
        has_mtlap_trustline = "MTLAP" in balances
        token_balance_mtlap = balances.get("MTLAP", 0)
        has_mtlac_trustline = "MTLAC" in balances
        token_balance_mtlac = balances.get("MTLAC", 0)

        trustline_status_mtlap = "Открыта" if has_mtlap_trustline else "Не открыта"
        token_balance_status_mtlap = str(token_balance_mtlap)
        trustline_status_mtlac = "Открыта" if has_mtlac_trustline else "Не открыта"
        token_balance_status_mtlac = str(token_balance_mtlac)

        # Получаем рекомендации
        rec_count, recommenders = await get_bsn_recommendations(match_stellar.group(1))
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
            stellar_address=match_stellar.group(1),
            trustline_status_mtlap=trustline_status_mtlap,
            token_balance_status_mtlap=token_balance_status_mtlap,
            trustline_status_mtlac=trustline_status_mtlac,
            token_balance_status_mtlac=token_balance_status_mtlac,
            username_presence=username_presence,
            is_active_member=is_active_member,
            bsn_recommendations=bsn_recommendations
        )

        print(output_message)

        await message.answer(output_message)


def register_handlers(dp, bot):
    if config.test_mode:
        dp.include_router(router)
        logger.info('router secretary_mtl was loaded')


if __name__ == '__main__':
    print(asyncio.run(get_bsn_recommendations('GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2')))
