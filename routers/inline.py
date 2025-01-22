from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from other.global_data import global_data

router = Router()


@router.inline_query()
async def inline_handler(inline_query: InlineQuery):
    switch_text = "По Вашему запросу найдено :"
    answers = []
    query_text = inline_query.query.upper()
    query_arr = query_text.split(" ") if 0 < len(query_text) else []
    user_id = inline_query.from_user.id
    chat_id = 0
    if query_arr:
        try:
            if query_arr[0].startswith('-100'):
                chat_id = int(query_arr[0])
            else:
                chat_id = int(f'-100{query_arr[0]}')
            query_text = ' '.join(query_arr[1:])
        except ValueError:
            chat_id = 0

    if len(query_text) == 0:
        query_text = ' '

    for key, value in global_data.info_cmd.items():
        if (key.upper().find(query_text) > -1) or (value['info'].upper().find(query_text) > -1):
            ico = ""
            if (value["cmd_type"] > 0) and (chat_id < 0):
                attr_list = getattr(global_data, value["cmd_list"])
                if value["cmd_type"] in (1, 2):
                    ico = "🟢 " if chat_id in attr_list else "🔴 "
                if value["cmd_type"] in (3,):
                    #    if message.chat.id in global_data.alert_me and message.from_user.id in global_data.alert_me[message.chat.id]:
                    ico = "🟢 " if chat_id in attr_list and user_id in attr_list[chat_id] else "🔴 "

            answers.append(InlineQueryResultArticle(
                id=str(len(answers)),
                title=ico + value['info'],
                description=key,
                input_message_content=InputTextMessageContent(message_text=key)
            ))
    return await inline_query.answer(answers[:50], cache_time=60, switch_pm_text=switch_text, switch_pm_parameter="xz")
