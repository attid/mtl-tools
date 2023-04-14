import asyncio
import datetime
import os
import random

import openai
from google.cloud import dialogflow
from async_openai import OpenAI, settings, CompletionResponse
from settings import opanaikey

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "mtl-skynet-talks.json"


# https://dialogflow.cloud.google.com/#/editAgent/mtl-skynet-hldy/

async def talk(session_id, msg):
    return await talk_open_ai_async(msg)


def talk_old(session_id, msg):
    project_id = 'mtl-skynet-hldy'
    language_code = 'RU'

    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    # print("Session path: {}\n".format(session))

    text_input = dialogflow.TextInput(text=msg[:240])
    query_input = dialogflow.QueryInput()  # text=text_input

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )

    if len(response.query_result.fulfillment_text) > 2:
        return response.query_result.fulfillment_text
    else:
        return "Žao mi je što ne razumijem."

    # print("=" * 20)
    # print("Query text: {}".format(response.query_result.query_text))
    # print(
    #     "Detected intent: {} (confidence: {})\n".format(
    #        response.query_result.intent.display_name,
    #        response.query_result.intent_detection_confidence,
    #    )
    # )
    #    print("Fulfillment text: {}\n".format(response.query_result.fulfillment_text))


def talk_open_ai(msg):
    openai.organization = "org-Iq64OmMI81NWnwcPtn72dc7E"
    openai.api_key = opanaikey
    # print(openai.Model.list())

    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=msg,
        temperature=0.7,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    story = response['choices'][0]['text']
    return story


async def talk_open_ai_async(msg):
    OpenAI.configure(
        api_key=opanaikey,
        organization="org-Iq64OmMI81NWnwcPtn72dc7E",
        debug_enabled=False,
    )

    r = await OpenAI.completions.async_create(
        prompt=msg,
        max_tokens=2048,
        stream=True
    )
    story = r.text
    return story


gor = (
    ("Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"),
    ("Расположение звезд ", "Расположение планет ", "Марс ", "Венера ", "Луна ", "Млечный путь ", "Астральные карта ",
     "Юпитер ", "Плутон ", "Сатурн ",),
    ("говорит вам ", "советует вам ", "предлагает вам ", "предрекает вам ", "благоволит вас ", "рекомендует вам ",
     "очень рекомендует вам ", "намекает вам ", "требует от вас ",),
    ("выпить пива", "напиться в хлам", "выпить никшечко", "выпить нефильтрованного никшечко", "выпить темного никшечко",
     "выпыть хугардена", "сегодня не пить =(", "хорошо приглядывать за орешками", "выпить чего по крепче",
     "пить сегодня с хорошей закуской", "поберечь печень", "нагрузить печень", "выпить ракии", "выпить дуньки",
     "выпить лозы", "выпить каспии", "сообразить на троих",)
)

lang_dict = {}


def get_horoscope() -> list:
    if datetime.date.today() == lang_dict.get('horoscope_date'):
        return lang_dict.get('horoscope', ['Ошибка при получении =('])
    else:
        today_dic = [""]
        s3 = ""
        lang_dict['horoscope_date'] = datetime.date.today()
        horoscope = ["Гороскоп на сегодня"]
        for s in gor[0]:
            horoscope.append(f'**{s}**')
            while s3 in today_dic:
                s3 = random.choice(gor[3])
            today_dic.append(s3)

            g = (random.choice(gor[1]) + random.choice(gor[2]) + s3)
            while g in horoscope:
                g = (random.choice(gor[1]) + random.choice(gor[2]) + s3)
            horoscope.append(g)

        horoscope.append("")
        horoscope.append("Желаю всем хорошего дня! 🍺🍺🍺")
        lang_dict['horoscope'] = horoscope
        return horoscope


if __name__ == "__main__":
    pass
    # print(talk(9, 'Как выглядит марс ?'))
    print(asyncio.run(talk_open_ai_async('Как выглядит марс ?')))
