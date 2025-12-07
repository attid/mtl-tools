"""
Rely Router Module

This module handles the /deal command for managing collaborative deals in Telegram groups.
It integrates with Grist to store deal information, participants, and their contributions.

Main features:
- Create deals based on message URLs
- Track participants and their contribution amounts
- Prevent modifications to checked/closed deals
- Send notifications to a dedicated deal management chat
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.utils.text_decorations import markdown_decoration
from loguru import logger

from other.grist_tools import GristTableConfig, grist_manager
from other.loguru_tools import safe_catch_async
from other.global_data import update_command_info

router = Router()

RELY_DEAL_CHAT_ID = -1003363491610 # rely
#RELY_DEAL_CHAT_ID = -1001767165598 #test group

GRIST_ACCESS_ID = "kceNjvoEEihSsc8dQ5vZVB"
GRIST_BASE_URL = "https://mtl-rely.getgrist.com/api/docs"


@update_command_info('/deal', 'Добавить участника в сделку RELY (реплаем на сообщение)')
@router.message(
    Command(commands=["deal"]),
    F.reply_to_message,
    F.text,
    F.chat.type != ChatType.PRIVATE,
    F.forward_date.is_(None),
)
@safe_catch_async
async def deal_command(message: types.Message, command: CommandObject, bot: Bot):
    """
    Handle the /deal command for adding participants to collaborative deals.

    This command must be used as a reply to a message in a group chat (not private chats).
    The replied-to message becomes the identifier for the deal.

    Command format: /deal <amount>
    Example: /deal 0.5

    Workflow:
    1. Parse and validate the amount parameter
    2. Extract the message URL from the replied-to message
    3. Get or create the deal for that message URL
    4. Get or create the holder for the user
    5. Add the participant entry to the deal
    6. Send confirmation or error messages

    Args:
        message: The incoming Telegram message containing the command
        command: Parsed command object with arguments
        bot: The Telegram Bot instance

    Filters:
        - Must be a /deal command
        - Must be a reply to another message
        - Must be in a group/supergroup (not private chat)
        - Must contain text

    User feedback:
        - Success: Confirms deal ID and participant entry details
        - Error: Provides specific error messages for different failure scenarios
    """
    if not command.args:
        await message.reply("Пожалуйста, укажите параметр. Формат: /deal 0.1")
        return

    try:
        amount = DealCommandArgumentParser().parse_amount(command.args)
    except ArgumentParsingError as e:
        await message.answer(str(e))
        return

    assert message.reply_to_message
    message_url = message.reply_to_message.get_url()

    if not message_url:
        await message.reply("Доступно только для сообщений в суппергруппах. Обратитесь к оператору.")
        return

    if not message.from_user:
        logger.warning("Received a message with no sender information.")
        return

    tg_username = message.from_user.username if message.from_user.username else f"id_{message.from_user.id}"
    tg_user_id = message.from_user.id

    deal_repository = GristDealRepository()
    deal_participant_repository = GristDealParticipantRepository()
    holder_repository = GristHolderRepository()
    deal_service = DealService(deal_repository, deal_participant_repository, holder_repository, bot)

    try:
        deal, participant_entry = await deal_service.process_deal_entry(
            message_url=message_url,
            tg_username=tg_username,
            tg_user_id=tg_user_id,
            amount=amount
        )
        await message.reply(
            f"Сделка '{deal.id}' по сообщению успешно обработана. "
            f"Ваша запись (ID: {participant_entry.id}) с параметром {participant_entry.amount} добавлена."
        )
        logger.info(f"Deal {deal.id} processed for user @{tg_username} with amount {amount}")

    except DealIsCheckedError as e:
        logger.warning(f"Attempt to modify a checked deal by {message.from_user.username}: {e}")
        await message.reply(str(e))
    except ParticipantEntryError as e:
        logger.warning(f"Attempt to add a duplicate participant entry by {message.from_user.username}: {e}")
        await message.reply(str(e))
    except RepositoryError as e:
        logger.error(f"Error processing deal command: {e}")
        await message.reply("Произошла ошибка при обработке сделки. Пожалуйста, обратитесь к оператору.")
        await deal_service.send_error_notification(e, message)


@update_command_info('/resolve', 'Закрыть сделку RELY (можно реплаем на сообщение сделки)')
@router.message(
    Command(commands=["resolve"]),
    F.text,
    F.chat.type != ChatType.PRIVATE,
    F.forward_date.is_(None),
)
@safe_catch_async
async def resolve_command(message: types.Message, command: CommandObject, bot: Bot):
    """
    Handle the /resolve command for closing deals.

    Command format: /resolve [additional text]
    Example: /resolve все готово
    """
    if not message.from_user:
        logger.warning("Received a /resolve message with no sender information.")
        return

    # Get user info
    tg_username = message.from_user.username if message.from_user.username else f"id_{message.from_user.id}"
    user_display = f"@{tg_username}" if not tg_username.startswith("id_") else tg_username

    # Extract additional text
    additional_text = None
    if command.args:
        split_message = message.md_text.strip().split(' ')
        additional_text = ' '.join(split_message[1:])

    # Get the URL of the current /resolve message
    resolve_message_url = message.get_url()
    if not resolve_message_url:
        await message.reply("Доступно только для сообщений в суппергруппах. Обратитесь к оператору.")
        return

    # Get replied message URL if this is a reply
    replied_message_url = None
    if message.reply_to_message:
        replied_message_url = message.reply_to_message.get_url()

    # Process resolve through service
    deal_repository = GristDealRepository()
    deal_participant_repository = GristDealParticipantRepository()
    holder_repository = GristHolderRepository()
    deal_service = DealService(deal_repository, deal_participant_repository, holder_repository, bot)

    try:
        await deal_service.process_resolve(
            user_display=user_display,
            replied_message_url=replied_message_url,
            resolve_message_url=resolve_message_url,
            additional_text=additional_text
        )
        # Set reaction on success
        try:
            await message.react([types.ReactionTypeEmoji(emoji="👍")])
        except Exception as e:
            logger.warning(f"Failed to set reaction on resolve message: {e}")
    except RepositoryError as e:
        logger.error(f"Error processing resolve command: {e}")
        await message.reply("Произошла ошибка при отправке уведомления. Пожалуйста, обратитесь к оператору.")


class ArgumentParsingError(Exception):
    """
    Exception raised when command arguments cannot be parsed correctly.

    This is raised when the user provides invalid input to the /deal command,
    such as non-numeric values or amounts that don't meet the minimum threshold.
    """
    pass


class DealCommandArgumentParser:
    """
    Parser for command arguments from the /deal command.

    Handles validation and conversion of user input into appropriate data types.
    """

    @staticmethod
    def parse_amount(args_string: str) -> Decimal:
        """
        Parse and validate the amount argument from the command string.

        Args:
            args_string: Raw string argument from the command (e.g., "0.5" or "1,5")

        Returns:
            Decimal: The validated amount as a Decimal object

        Raises:
            ArgumentParsingError: If the amount is invalid, non-numeric, or <= 0.1
        """
        try:
            amount = Decimal(args_string.strip().replace(",", "."))
            if amount < Decimal("0.1"):
                raise ArgumentParsingError("Сумма меньше 0.1 не допускается.")
            return amount
        except (ValueError, TypeError, InvalidOperation):
            raise ArgumentParsingError("Неверный формат параметра. Пожалуйста, используйте число, например: /deal 0.2")


class RepositoryError(Exception):
    """
    Base exception for all repository-related errors.

    This serves as the parent class for all errors that occur during
    interactions with the Grist database.
    """
    pass


class DealIsCheckedError(RepositoryError):
    """
    Exception raised when attempting to modify a deal that has been marked as checked.

    Once a deal is checked/closed, no further modifications (adding participants,
    changing amounts) are allowed.
    """
    pass


class DealCreationError(RepositoryError):
    """
    Exception raised when a new deal cannot be created in Grist.

    This may occur due to API errors, network issues, or database constraints.
    """
    pass


class DealRetrievalError(RepositoryError):
    """
    Exception raised when a deal cannot be retrieved from Grist.

    This may occur when attempting to fetch a newly created deal or
    when the Grist API returns unexpected data.
    """
    pass


class ParticipantEntryError(RepositoryError):
    """
    Exception raised for errors related to participant entries.

    This includes duplicate entry attempts, creation failures, or retrieval issues.
    """
    pass


class HolderCreationError(RepositoryError):
    """
    Exception raised when a new holder (user) cannot be created in Grist.

    This may occur due to API errors, network issues, or database constraints.
    """
    pass


class HolderRetrievalError(RepositoryError):
    """
    Exception raised when a holder (user) cannot be retrieved from Grist.

    This may occur when attempting to fetch a newly created holder or
    when the Grist API returns unexpected data.
    """
    pass


@dataclass
class Holder:
    """
    Represents a deal participant/holder.

    Attributes:
        tg_username: Telegram username (or 'id_{user_id}' if username not available)
        id: Unique identifier in the Grist Holders table
    """
    tg_username: str
    id: int


@dataclass
class Deal:
    """
    Represents a collaborative deal linked to a Telegram message.

    Attributes:
        url: URL of the Telegram message that initiated the deal
        id: Unique identifier in the Grist Deals table
        checked: Whether the deal has been closed/finalized (prevents further modifications)
    """
    url: str
    id: int
    checked: bool = False


@dataclass
class DealParticipantEntry:
    """
    Represents a participant's contribution to a specific deal.

    Attributes:
        deal_id: ID of the associated deal
        holder_id: ID of the participant/holder
        amount: Contribution amount as a Decimal
        id: Unique identifier in the Grist Conditions table (None until persisted)
    """
    deal_id: int
    holder_id: int
    amount: Decimal
    id: Optional[int] = None


class GristDealRepository:
    """
    Repository for managing Deal entities in Grist.

    Handles CRUD operations for deals stored in the Grist 'Deals' table.
    """

    def __init__(self):
        """Initialize the repository with Grist configuration for the Deals table."""
        self._table_config = GristTableConfig(
            access_id=GRIST_ACCESS_ID,
            table_name="Deals",
            base_url=GRIST_BASE_URL,
        )

    async def get_or_create_deal(self, message_url: str) -> tuple[Deal, bool]:
        """
        Retrieve an existing deal by message URL or create a new one.

        Args:
            message_url: The Telegram message URL that identifies the deal

        Returns:
            tuple[Deal, bool]: A tuple of (Deal object, is_new flag), where is_new
                              is True if the deal was just created

        Raises:
            DealRetrievalError: If unable to load deal data from Grist
            DealCreationError: If unable to create a new deal
        """
        deal = await self._get_deal_by_url(message_url)
        if deal:
            return deal, False

        new_deal = await self._create_deal(message_url)
        return new_deal, True

    async def _get_deal_by_url(self, message_url: str) -> Optional[Deal]:
        """
        Retrieve a deal from Grist by its message URL.

        Args:
            message_url: The Telegram message URL to search for

        Returns:
            Optional[Deal]: The Deal object if found, None otherwise

        Raises:
            DealRetrievalError: If the Grist API call fails
        """
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
        """
        Create a new deal in Grist.

        Args:
            message_url: The Telegram message URL for the new deal

        Returns:
            Deal: The newly created Deal object

        Raises:
            DealCreationError: If unable to create the deal in Grist
            DealRetrievalError: If unable to retrieve the newly created deal
        """
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
    """
    Repository for managing Holder (participant) entities in Grist.

    Handles CRUD operations for holders stored in the Grist 'Holders' table.
    It supports finding holders by Telegram ID or username, and updates their information.
    """

    def __init__(self):
        """Initialize the repository with Grist configuration for the Holders table."""
        self._table_config = GristTableConfig(
            access_id=GRIST_ACCESS_ID,
            table_name="Holders",
            base_url=GRIST_BASE_URL,
        )

    async def get_or_create_holder(self, tg_username: str, tg_user_id: int) -> Holder:
        """
        Retrieve an existing holder by Telegram ID or username, or create a new one.
        If a holder is found, it will be updated with the latest tg_user_id and tg_username if they differ.

        Search Priority:
        1. by tg_user_id (TGID column)
        2. by tg_username (Lowercase column)

        Args:
            tg_username: The user's current Telegram username.
            tg_user_id: The user's Telegram ID.

        Returns:
            Holder: The existing or newly created Holder object.

        Raises:
            HolderRetrievalError: If unable to load holder data from Grist.
            HolderCreationError: If unable to create or update a new holder.
        """
        holder_record = await self._get_holder_record_by_telegram_id(tg_user_id)
        if not holder_record:
            cleaned_username = tg_username.strip().strip('@').lower()
            holder_record = await self._get_holder_record_by_username(cleaned_username)

        if holder_record:
            updates = {}
            if str(holder_record.get("TGID")) != str(tg_user_id):
                updates["TGID"] = tg_user_id
            
            new_telegram_handle = f"@{tg_username}"
            if holder_record.get("Telegram") != new_telegram_handle:
                updates["Telegram"] = new_telegram_handle
            
            if updates:
                await self._update_holder_record(holder_record["id"], updates)

            updated_username = updates.get("Telegram", holder_record["Telegram"])
            return Holder(id=holder_record["Number"], tg_username=updated_username)

        return await self._create_holder(tg_username, tg_user_id)

    async def _get_holder_record_by_telegram_id(self, tg_user_id: int) -> Optional[dict]:
        """Retrieve a holder record from Grist by their Telegram ID."""
        records = await grist_manager.fetch_data(
            self._table_config,
            filter_dict={"TGID": [tg_user_id]}
        )
        if records is None:
            logger.info("Failed to load holder data from Grist by TGID.")
            return None
        return records[0] if records else None

    async def _get_holder_record_by_username(self, tg_username: str) -> Optional[dict]:
        """Retrieve a holder record from Grist by their Telegram username."""
        records = await grist_manager.fetch_data(
            self._table_config,
            filter_dict={"Lowercase": [tg_username]}
        )
        if records is None:
            logger.info("Failed to load holder data from Grist by username.")
            return None
        return records[0] if records else None

    async def _update_holder_record(self, record_id: int, fields: dict):
        """Update a holder record in Grist."""
        try:
            await grist_manager.patch_data(
                table=self._table_config,
                json_data={"records": [{"id": record_id, "fields": fields}]}
            )
        except Exception as e:
            raise HolderCreationError(f"Failed to update holder record {record_id} in Grist: {e}") from e

    async def _create_holder(self, tg_username: str, tg_user_id: int) -> Holder:
        """Create a new holder in Grist."""
        try:
            await grist_manager.post_data(
                table=self._table_config,
                json_data={
                    "records": [
                        {
                            "fields": {
                                "Telegram": f"@{tg_username}",
                                "TGID": tg_user_id
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            raise HolderCreationError(f"Failed to create holder in Grist: {e}") from e

        created_holder_record = await self._get_holder_record_by_telegram_id(tg_user_id)
        if not created_holder_record:
            raise HolderCreationError("Failed to retrieve newly created holder.")

        return Holder(id=created_holder_record["Number"], tg_username=created_holder_record["Telegram"])


class GristDealParticipantRepository:
    """
    Repository for managing participant entries in deals.

    Handles CRUD operations for participant contributions stored in the
    Grist 'Conditions' table.
    """

    def __init__(self):
        """Initialize the repository with Grist configuration for the Conditions table."""
        self._table_config = GristTableConfig(
            access_id=GRIST_ACCESS_ID,
            table_name="Conditions",
            base_url=GRIST_BASE_URL,
        )

    async def _get_participant_entry(self, deal_id: int, holder_id: int) -> Optional[DealParticipantEntry]:
        """
        Retrieve a participant's entry for a specific deal.

        Args:
            deal_id: The ID of the deal
            holder_id: The ID of the participant/holder

        Returns:
            Optional[DealParticipantEntry]: The entry if found, None otherwise

        Raises:
            ParticipantEntryError: If the Grist API call fails
        """
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
        """
        Add a new participant entry to a deal.

        Args:
            deal_id: The ID of the deal
            holder_id: The ID of the participant/holder
            amount: The contribution amount

        Returns:
            DealParticipantEntry: The newly created participant entry

        Raises:
            ParticipantEntryError: If the participant already has an entry in this deal,
                                  or if the creation fails
        """
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
    """
    Service layer for managing deal operations.

    Coordinates between repositories and handles business logic for deal creation,
    participant management, and notifications.
    """

    def __init__(self, deal_repo: GristDealRepository, participant_repo: GristDealParticipantRepository,
                 holder_repo: GristHolderRepository, bot: Bot):
        """
        Initialize the DealService with required repositories and bot.

        Args:
            deal_repo: Repository for deal operations
            participant_repo: Repository for participant entry operations
            holder_repo: Repository for holder operations
            bot: Telegram Bot instance for sending notifications
        """
        self._deal_repo = deal_repo
        self._participant_repo = participant_repo
        self._holder_repo = holder_repo
        self._bot = bot

    async def _send_creation_notification(self, deal: Deal):
        """
        Send a notification to the deal management chat when a new deal is created.

        Args:
            deal: The newly created Deal object
        """
        text = f"Создана новая сделка #{deal.id}\n{deal.url}"
        try:
            await self._bot.send_message(RELY_DEAL_CHAT_ID, text)
            logger.info(f"Уведомление о создании сделки #{deal.id} отправлено.")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о сделке #{deal.id}: {e}")

    async def send_error_notification(self, error: Exception, message: types.Message):
        """
        Send an error notification to the deal management chat.

        Args:
            error: The exception that occurred
            message: The Telegram message that triggered the error
        """
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

    async def process_deal_entry(self, message_url: str, tg_username: str, tg_user_id: int, amount: Decimal) -> tuple[
        Deal, DealParticipantEntry]:
        """
        Process a new deal entry from a participant.

        This method orchestrates the entire deal entry workflow:
        1. Validates input parameters
        2. Gets or creates the deal from the message URL
        3. Checks if the deal is still open (not checked)
        4. Sends notification if it's a new deal
        5. Gets or creates the holder/participant
        6. Adds the participant entry to the deal

        Args:
            message_url: The Telegram message URL identifying the deal
            tg_username: The Telegram username of the participant
            tg_user_id: The Telegram user ID of the participant
            amount: The contribution amount

        Returns:
            tuple[Deal, DealParticipantEntry]: The deal and the newly created participant entry

        Raises:
            ValueError: If required parameters are missing or invalid
            DealIsCheckedError: If attempting to add a participant to a closed deal
            RepositoryError: If any database operation fails
        """
        if not message_url:
            raise ValueError("Message URL is required.")
        if not tg_username:
            raise ValueError("Telegram username is required.")
        if not tg_user_id:
            raise ValueError("Telegram user ID is required.")
        if amount <= 0:
            raise ValueError("Amount must be greater than 0.")

        deal, is_new = await self._deal_repo.get_or_create_deal(message_url)

        if deal.checked:
            raise DealIsCheckedError("Нельзя добавить участника, сделка уже закрыта.")

        if is_new:
            await self._send_creation_notification(deal)

        holder = await self._holder_repo.get_or_create_holder(tg_username, tg_user_id)

        participant_entry = await self._participant_repo.add_participant_entry(
            deal_id=deal.id,
            holder_id=holder.id,
            amount=amount
        )
        return deal, participant_entry

    async def process_resolve(
        self,
        user_display: str,
        replied_message_url: Optional[str],
        resolve_message_url: str,
        additional_text: Optional[str]
    ):
        """
        Process a resolve request for closing a deal.

        This method:
        1. Looks up the deal by replied message URL if available
        2. Determines the deal identifier (ID, URL, or "???")
        3. Formats and sends notification to operator chat, preserving text entities
           by converting them to Markdown.

        Args:
            user_display: User display name (e.g., "@username" or "id_123")
            replied_message_url: URL of the message being replied to (None if not a reply)
            resolve_message_url: URL of the message with /resolve command
            additional_text: Optional comment text from the command, pre-formatted as Markdown.

        Raises:
            RepositoryError: If database operation fails
        """
        # Determine the deal identifier
        deal_identifier = "???"

        if replied_message_url:
            try:
                deal = await self._deal_repo._get_deal_by_url(replied_message_url)
                if deal:
                    deal_identifier = f"#{deal.id}"
                else:
                    deal_identifier = replied_message_url
            except DealRetrievalError as e:
                logger.error(f"Error looking up deal for /resolve command: {e}")
                deal_identifier = replied_message_url

        # Format the notification message
        notification_text = markdown_decoration.quote(f"{user_display} закрывает сделку {deal_identifier}")
        if additional_text:
            notification_text += f" с комментарием\n> {additional_text}"
        notification_text += markdown_decoration.quote(f"\n\n\n{resolve_message_url}")

        # Send notification to operator chat
        try:
            await self._bot.send_message(
                RELY_DEAL_CHAT_ID, 
                notification_text, 
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
            logger.info(f"Resolve notification sent for deal {deal_identifier} by {user_display}")
        except Exception as e:
            logger.error(f"Failed to send resolve notification: {e}")
            raise RepositoryError(f"Failed to send resolve notification: {e}") from e


def register_handlers(dp, bot):
    """
    Register the rely router and its handlers with the dispatcher.

    This function is called during bot initialization to attach the
    /deal command handler to the main dispatcher.

    Args:
        dp: The aiogram Dispatcher instance
        bot: The Telegram Bot instance (not currently used but kept for consistency)

    Raises:
        RuntimeError: If any repository health check fails
    """
    dp.include_router(router)
    logger.info("router rely was loaded")
