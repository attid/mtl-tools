from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from loguru import logger
from sqlalchemy.orm import Session

from other.global_data import global_data

router = Router()


def _get_commands_dict(app_context):
    """Get commands dict from DI service or fallback to global_data."""
    if app_context and app_context.command_registry:
        # Convert CommandInfo objects to legacy format for compatibility
        commands = app_context.command_registry.get_all_commands()
        return {
            name: {
                'info': cmd.description,
                'cmd_type': cmd.cmd_type,
                'cmd_list': cmd.cmd_list[0] if cmd.cmd_list else ''
            }
            for name, cmd in commands.items()
        }
    return global_data.info_cmd


def _check_alert_me(app_context, chat_id: int, user_id: int) -> bool:
    """Check if user has alert_me enabled for the chat using DI service or fallback."""
    if app_context and app_context.notification_service:
        alert_config = app_context.notification_service.get_alert_config(chat_id)
        if alert_config and isinstance(alert_config, list):
            return user_id in alert_config
        return False
    # Fallback to global_data
    if chat_id in global_data.alert_me:
        alert_list = global_data.alert_me[chat_id]
        if isinstance(alert_list, list):
            return user_id in alert_list
    return False


def _get_attr_list(app_context, attr_name: str):
    """Get attribute list from app_context services or fallback to global_data."""
    # For alert_me, use notification_service
    if attr_name == 'alert_me':
        if app_context and app_context.notification_service:
            return app_context.notification_service.get_all_alerts()
        return global_data.alert_me
    # For other attributes, fallback to global_data
    return getattr(global_data, attr_name, {})


@router.inline_query()
async def inline_handler(inline_query: InlineQuery, session: Session, app_context=None):
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

    # Use DI services when available, fallback to global_data for backward compatibility
    commands_dict = _get_commands_dict(app_context)

    for key, value in commands_dict.items():
        if (key.upper().find(query_text) > -1) or (value['info'].upper().find(query_text) > -1):
            ico = ""
            if (value["cmd_type"] > 0) and (chat_id < 0):
                attr_list = _get_attr_list(app_context, value["cmd_list"])
                if value["cmd_type"] in (1, 2):
                    ico = "🟢 " if chat_id in attr_list else "🔴 "
                if value["cmd_type"] in (3,):
                    # For cmd_type 3, check nested structure: {chat_id: [user_ids]}
                    in_list = False
                    if chat_id in attr_list:
                        if isinstance(attr_list[chat_id], list):
                            in_list = user_id in attr_list[chat_id]
                    ico = "🟢 " if in_list else "🔴 "

            answers.append(InlineQueryResultArticle(
                id=str(len(answers)),
                title=ico + value['info'],
                description=key,
                input_message_content=InputTextMessageContent(message_text=key)
            ))
    return await inline_query.answer(answers[:50], cache_time=60, switch_pm_text=switch_text, switch_pm_parameter="xz")


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router inline was loaded')
