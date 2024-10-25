import asyncio
import re

import aiohttp
from loguru import logger

from utils.dialog import talk_check_spam
from utils.global_data import global_data


def is_mixed_word(word):
    # Проверяем наличие русских букв
    contains_cyrillic = bool(re.search('[а-яА-Я]', word))
    # Проверяем наличие цифр
    contains_digit = bool(re.search('[0-9@]', word))
    # Проверяем наличие латинских букв
    contains_latin = bool(re.search('[a-zA-Z]', word))

    # Считаем слово "смешанным", если оно содержит русские буквы и (цифры или латинские буквы)
    return contains_cyrillic and (contains_digit or contains_latin)


spam_phrases = [
    "команду",
    "команда",
    "доход",
    "без опыта",
    "лс",
    "личку",
    "прибыль",
    "проект",
    "предложение",
    "тестирование",
    "день",
    "заработка",
    "заработок",
    "процент",
    "пишите",
    "18",
    "связки"
    "зарабатывать",
    "подробности"
]

for i in range(1, 20):
    spam_phrases.append(f'{i}oo')
    spam_phrases.append(f'{i}оо')


def contains_spam_phrases(text, phrases=None, threshold=3):
    if phrases is None:
        phrases = spam_phrases

    words = re.findall(r'\b\w+\b', text.lower())

    count = sum(phrase in words for phrase in phrases)
    if '+' in text:
        count += 1
    # print(f'count: {count}')
    return count >= threshold


async def combo_check_spammer(user_id):
    try:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f'https://api.cas.chat/check?user_id={user_id}', timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            # return data.get('result', False)
                            return True
                    else:
                        logger.error(f"API request failed with status code: {response.status}")
            except aiohttp.ClientError as e:
                logger.error(f"Network error occurred: {str(e)}")
            except asyncio.TimeoutError:
                logger.error("Request timed out")
    except Exception as e:
        logger.error(f"Unexpected error in combo_check_spam: {str(e)}")
    return False


if __name__ == '__main__':
    test = '''
Ищу людей, кто заинтересован в дополнительном доходе, онлайн формат, от 18 лет. За деталями обращайтесь в лс
'''

    # print(contains_spam_phrases(test))
    # print(asyncio.run(talk_check_spam(test)))
    print(asyncio.run(combo_check_spammer(5953807506)))
    print(asyncio.run(combo_check_spammer(84131737)))
