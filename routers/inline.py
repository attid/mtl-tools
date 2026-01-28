from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from loguru import logger
from sqlalchemy.orm import Session

from services.app_context import AppContext

router = Router()


def _get_commands_dict(app_context):
    """Get commands dict from DI service. Raises error if app_context not available."""
    if not app_context or not app_context.command_registry:
        raise ValueError("app_context with command_registry required")
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


def _check_alert_me(app_context, chat_id: int, user_id: int) -> bool:
    """Check if user has alert_me enabled for the chat using DI service."""
    if not app_context or not app_context.notification_service:
        raise ValueError("app_context with notification_service required")
    alert_config = app_context.notification_service.get_alert_config(chat_id)
    if alert_config and isinstance(alert_config, list):
        return user_id in alert_config
    return False


def _get_attr_list(app_context, attr_name: str):
    """Get attribute list from app_context services."""
    if not app_context:
        raise ValueError("app_context required")
    # For alert_me, use notification_service
    if attr_name == 'alert_me':
        if not app_context.notification_service:
            raise ValueError("app_context with notification_service required")
        return app_context.notification_service.get_all_alerts()
    # For other attributes, use feature_flags or config_service as appropriate
    # Return empty dict as safe default - the service should provide the data
    if app_context.feature_flags:
        return app_context.feature_flags.get_feature_list(attr_name)
    return {}


@router.inline_query()
async def inline_handler(inline_query: InlineQuery, session: Session, app_context: AppContext = None):
    try:
        if not app_context:
            logger.error("app_context is None in inline_handler!")
            return await inline_query.answer([], cache_time=60)

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

        # Empty query means show all commands
        show_all = len(query_text.strip()) == 0

        commands_dict = _get_commands_dict(app_context)

        for key, value in commands_dict.items():
            if show_all or (query_text in key.upper()) or (query_text in value['info'].upper()):
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
    except Exception as e:
        logger.exception(f"Error in inline_handler: {e}")
        return await inline_query.answer([], cache_time=60)


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router inline was loaded')
