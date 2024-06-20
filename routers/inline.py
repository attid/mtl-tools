from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from utils.global_data import global_data

router = Router()


@router.inline_query()
async def inline_handler(inline_query: InlineQuery):
    switch_text = "По Вашему запросу найдено :"
    answers = []
    for key, value in global_data.info_cmd.items():
        if (key.upper().find(inline_query.query.upper()) > -1) or (value.upper().find(inline_query.query.upper()) > -1):
            answers.append(InlineQueryResultArticle(
                id=str(len(answers)),
                title=value,
                description=key,
                input_message_content=InputTextMessageContent(message_text=key)
            ))
    return await inline_query.answer(answers[:50], cache_time=60, switch_pm_text=switch_text, switch_pm_parameter="xz")
