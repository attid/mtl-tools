import asyncio
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from loguru import logger

from other.config_reader import config
from other.grist_tools import GristTableConfig, grist_manager
from other.loguru_tools import safe_catch_async

router = Router()

RELY_DEAL_CHAT_ID = -1003113317571
#RELY_DEAL_CHAT_ID = -1001767165598

GRIST_ACCESS_ID = "kceNjvoEEihSsc8dQ5vZVB"
GRIST_BASE_URL = "https://mtl-rely.getgrist.com/api/docs"


@router.message(
    Command(commands=["deal"]),
    F.reply_to_message,
    F.text,
    F.chat.type != ChatType.PRIVATE,
)
@safe_catch_async
async def deal_command(message: types.Message, command: CommandObject, bot: Bot):
    if not command.args:
        await message.answer("Пожалуйста, укажите параметр. Формат: /deal 0.1")
        return

    try:
        amount = CommandArgumentParser().parse_amount(command.args)
    except ArgumentParsingError as e:
        await message.answer(str(e))
        return

    assert message.reply_to_message
    message_url = message.reply_to_message.get_url()

    if not message_url:
        await message.answer("Доступно только для сообщений в суппергруппах. Обратитесь к оператору.")
        return

    if not message.from_user:
        logger.warning("Received a message with no sender information.")
        return

    tg_username = message.from_user.username if message.from_user.username else f"id_{message.from_user.id}"

    deal_repository = GristDealRepository()
    deal_participant_repository = GristDealParticipantRepository()
    holder_repository = GristHolderRepository()
    deal_service = DealService(deal_repository, deal_participant_repository, holder_repository, bot)

    try:
        deal, participant_entry = await deal_service.process_deal_entry(
            message_url=message_url,
            tg_username=tg_username,
            amount=amount
        )
        await message.answer(
            f"Сделка '{deal.id}' по сообщению успешно обработана. "
            f"Ваша запись (ID: {participant_entry.id}) с параметром {participant_entry.amount} добавлена."
        )
        logger.info(f"Deal {deal.id} processed for user @{tg_username} with amount {amount}")

    except DealIsCheckedError as e:
        logger.warning(f"Attempt to modify a checked deal by {message.from_user.username}: {e}")
        await message.answer(str(e))
    except ParticipantEntryError as e:
        logger.warning(f"Attempt to add a duplicate participant entry by {message.from_user.username}: {e}")
        await message.answer(str(e))
    except RepositoryError as e:
        logger.error(f"Error processing deal command: {e}")
        await message.answer("Произошла ошибка при обработке сделки. Пожалуйста, обратитесь к оператору.")
        await deal_service.send_error_notification(e, message)


class ArgumentParsingError(Exception):
    """Base class for argument parsing errors."""
    pass


class CommandArgumentParser:
    @staticmethod
    def parse_amount(args_string: str) -> Decimal:
        try:
            amount = Decimal(args_string.strip().replace(",", "."))
            if amount <= Decimal("0.1"):
                raise ArgumentParsingError("Сумма 0.1 и меньше не допускается.")
            return amount
        except (ValueError, TypeError, InvalidOperation):
            raise ArgumentParsingError("Неверный формат параметра. Пожалуйста, используйте число, например: /deal 0.2")


class RepositoryError(Exception):
    """Base class for repository-related errors."""
    pass


class DealIsCheckedError(RepositoryError):
    """Raised when trying to modify a checked deal."""
    pass


class DealCreationError(RepositoryError):
    """Raised when a deal cannot be created."""
    pass


class DealRetrievalError(RepositoryError):
    """Raised when a deal cannot be retrieved."""
    pass


class ParticipantEntryError(RepositoryError):
    """Raised for errors related to participant entries."""
    pass


class HolderCreationError(RepositoryError):
    """Raised when a holder cannot be created."""
    pass


class HolderRetrievalError(RepositoryError):
    """Raised when a holder cannot be retrieved."""
    pass


@dataclass
class Holder:
    tg_username: str
    id: int


@dataclass
class Deal:
    url: str
    id: int
    checked: bool = False


@dataclass
class DealParticipantEntry:
    deal_id: int
    holder_id: int
    amount: Decimal
    id: int | None = None


class GristDealRepository:
    def __init__(self):
        self._table_config = GristTableConfig(
            access_id=GRIST_ACCESS_ID,
            table_name="Deals",
            base_url=GRIST_BASE_URL,
        )

    async def get_or_create_deal(self, message_url: str) -> tuple[Deal, bool]:
        """
        Находит сделку по URL или создает новую.
        Возвращает кортеж (Deal, is_new), где is_new - True, если сделка была только что создана.
        """
        deal = await self._get_deal_by_url(message_url)
        if deal:
            return deal, False

        new_deal = await self._create_deal(message_url)
        return new_deal, True

    async def _get_deal_by_url(self, message_url: str) -> Optional[Deal]:
        record_data = await grist_manager.load_table_data(
            self._table_config,
            filter_dict={"Message": [message_url]}
        )
        if record_data is None:
            raise DealRetrievalError("Failed to load deal data from Grist.")
        if record_data:
            record = record_data[0]
            return Deal(id=record["Number"], url=record["Message"], checked=record["Checked"])
        return None

    async def _create_deal(self, message_url: str) -> Deal:
        try:
            await grist_manager.post_data(
                table=self._table_config,
                json_data={
                    "records": [
                        {
                            "fields": {
                                "Message": message_url
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            raise DealCreationError(f"Failed to create deal in Grist: {e}") from e

        created_record = await self._get_deal_by_url(message_url)
        if not created_record:
            raise DealRetrievalError("Failed to retrieve newly created deal.")

        return created_record


class GristHolderRepository:
    def __init__(self):
        self._table_config = GristTableConfig(
            access_id=GRIST_ACCESS_ID,
            table_name="Holders",
            base_url=GRIST_BASE_URL,
        )

    async def get_or_create_holder(self, tg_username: str) -> Holder:
        holder = await self._get_holder_by_username(tg_username)
        if holder:
            return holder
        return await self._create_holder(tg_username)

    async def _get_holder_by_username(self, tg_username: str) -> Optional[Holder]:
        record_data = await grist_manager.load_table_data(
            self._table_config,
            filter_dict={"Telegram": [tg_username]}
        )
        if record_data is None:
            raise HolderRetrievalError("Failed to load holder data from Grist.")
        if record_data:
            record = record_data[0]
            return Holder(id=record["Number"], tg_username=record["Telegram"])
        return None

    async def _create_holder(self, tg_username: str) -> Holder:
        try:
            await grist_manager.post_data(
                table=self._table_config,
                json_data={
                    "records": [
                        {
                            "fields": {
                                "Telegram": tg_username
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            raise HolderCreationError(f"Failed to create holder in Grist: {e}") from e

        created_holder = await self._get_holder_by_username(tg_username)
        if not created_holder:
            raise HolderRetrievalError("Failed to retrieve newly created holder.")

        return created_holder


class GristDealParticipantRepository:
    def __init__(self):
        self._table_config = GristTableConfig(
            access_id=GRIST_ACCESS_ID,
            table_name="Conditions",
            base_url=GRIST_BASE_URL,
        )

    async def _get_participant_entry(self, deal_id: int, holder_id: int) -> Optional[DealParticipantEntry]:
        try:
            records = await grist_manager.fetch_data(
                table=self._table_config,
                filter_dict={
                    "Deal": [deal_id],
                    "Participant": [holder_id],
                }
            )
        except Exception as e:
            raise ParticipantEntryError(f"Failed to fetch participant entry from Grist: {e}") from e

        if not records:
            return None
        record = records[0]
        return DealParticipantEntry(
            id=record["id"],
            deal_id=record["Deal"],
            holder_id=record["Participant"],
            amount=Decimal(str(record["Amount"]))
        )

    async def add_participant_entry(self, deal_id: int, holder_id: int, amount: Decimal) -> DealParticipantEntry:
        existing_entry = await self._get_participant_entry(deal_id, holder_id)
        if existing_entry:
            raise ParticipantEntryError("Вы уже добавили запись в эту сделку. Нельзя обновить существующую запись.")

        json_data = {
            "records": [
                {
                    "fields": {
                        "Deal": deal_id,
                        "Participant": holder_id,
                        "Amount": str(amount),
                    }
                }
            ]
        }
        try:
            await grist_manager.post_data(
                table=self._table_config,
                json_data=json_data
            )
        except Exception as e:
            raise ParticipantEntryError(f"Failed to add participant entry in Grist: {e}") from e

        participant_entry = await self._get_participant_entry(deal_id, holder_id)
        if not participant_entry:
            raise ParticipantEntryError("Failed to retrieve participant entry after creation.")

        return participant_entry


class DealService:
    def __init__(self, deal_repo: GristDealRepository, participant_repo: GristDealParticipantRepository,
                 holder_repo: GristHolderRepository, bot: Bot):
        self._deal_repo = deal_repo
        self._participant_repo = participant_repo
        self._holder_repo = holder_repo
        self._bot = bot

    async def _send_creation_notification(self, deal: Deal):
        """Отправляет уведомление о создании новой сделки."""
        text = f"Создана новая сделка #{deal.id}\n{deal.url}"
        try:
            await self._bot.send_message(RELY_DEAL_CHAT_ID, text)
            logger.info(f"Уведомление о создании сделки #{deal.id} отправлено.")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о сделке #{deal.id}: {e}")

    async def send_error_notification(self, error: Exception, message: types.Message):
        """Отправляет уведомление об ошибке."""
        user_info = "User: Unknown"
        if message.from_user:
            user_info = f"User: @{message.from_user.username} (ID: {message.from_user.id})"
        error_info = f"Error: {error}"
        context_info = f"Original message: {message.reply_to_message.get_url()}" if message.reply_to_message else "No reply message."

        text = f"⚠️ Ошибка при обработке сделки ⚠️\n\n{user_info}\n{context_info}\n\n{error_info}"
        try:
            await self._bot.send_message(RELY_DEAL_CHAT_ID, text, disable_web_page_preview=True)
            logger.info("Уведомление об ошибке отправлено.")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление об ошибке: {e}")

    async def process_deal_entry(self, message_url: str, tg_username: str, amount: Decimal) -> tuple[
        Deal, DealParticipantEntry]:
        if not message_url:
            raise ValueError("Message URL is required.")
        if not tg_username:
            raise ValueError("Telegram username is required.")
        if amount <= 0:
            raise ValueError("Amount must be greater than 0.")

        deal, is_new = await self._deal_repo.get_or_create_deal(message_url)

        if deal.checked:
            raise DealIsCheckedError("Нельзя добавить участника, сделка уже закрыта.")

        if is_new:
            await self._send_creation_notification(deal)

        holder = await self._holder_repo.get_or_create_holder(tg_username)

        participant_entry = await self._participant_repo.add_participant_entry(
            deal_id=deal.id,
            holder_id=holder.id,
            amount=amount
        )
        return deal, participant_entry


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info("router rely was loaded")
