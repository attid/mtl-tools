import sys
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent
from loguru import logger
from sentry_sdk import capture_exception, push_scope


async def sentry_error_handler(event: ErrorEvent, state: FSMContext) -> None:
    if 'test' in sys.argv:
        logger.exception(f"Error catch: {event.exception} on update: {event.update}")

    data = await state.get_data()
    user_id = event.update.message.from_user.id if event.update.message else None

    with push_scope() as scope:
        scope.set_context("aiogram", {"state": data})
        scope.set_user({"id": user_id})
        capture_exception(event.exception)

