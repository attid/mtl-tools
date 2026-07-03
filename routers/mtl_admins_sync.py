from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from services.app_context import AppContext
from services.mtl_admins_sync_service import MtlAdminsSyncService, chunk_text, format_sync_report
from services.skyuser import SkyUser

router = Router()


@router.message(Command(commands=["sync_mtl_admins"]))
async def cmd_sync_mtl_admins(message: Message, app_context: AppContext, skyuser: SkyUser):
    if not skyuser or not skyuser.is_skynet_admin():
        text = skyuser.admin_denied_text("You are not my admin.") if skyuser else "You are not admin."
        await message.reply(text)
        return False

    await message.reply("Синхронизация MTL admins началась...")
    service = MtlAdminsSyncService()
    result = await service.sync(message.bot, admin_service=app_context.admin_service if app_context else None)

    for chunk in chunk_text(format_sync_report(result), limit=4000):
        await message.answer(chunk)

    logger.info(
        "mtl_admins_sync completed media_checked={} media_skipped={} created={} updated={} issues={}",
        result.media_checked,
        result.media_skipped,
        result.created,
        result.updated,
        len(result.issues),
    )


def register_handlers(dp, bot):
    dp.include_router(router)
