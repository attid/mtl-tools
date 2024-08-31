import asyncio
import re

from utils.dialog import talk_check_spam


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


if __name__ == '__main__':
    test = '''
ТРЕБУЮТСЯ ЛЮДИ НА УДАЛЁНУЮ ЗАНЯТОСТЬ с хорошей оплатой


— 1-2 часа в день
— Места ограничены

Пиши + в лс
'''

    print(contains_spam_phrases(test))
    print(asyncio.run(talk_check_spam(test)))
