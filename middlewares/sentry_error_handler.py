import sys

from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent
from sentry_sdk import capture_exception, push_scope


async def sentry_error_handler(event: ErrorEvent, state: FSMContext):
    # Получение информации о состоянии FSM
    data = await state.get_data()
    user_id = event.update.message.from_user.id if event.update.message else None

    # Дополнительные данные для Sentry
    with push_scope() as scope:
        scope.set_context("aiogram", {"state": data})
        scope.set_user({"id": user_id})
        capture_exception(event.exception)

    if 'test' in sys.argv:
        raise event.exception
