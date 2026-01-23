from other.aiogram_tools import cmd_sleep_and_delete as original_sleep_and_delete

class TelegramUtilsService:
    async def sleep_and_delete(self, message, seconds):
        await original_sleep_and_delete(message, seconds)
