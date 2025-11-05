import re
from contextlib import suppress
from datetime import timedelta
from enum import Enum
from sys import argv
from typing import List, cast, Optional

from loguru import logger
from sqlalchemy import select, and_, case, distinct, desc, cast as sql_cast, Date, func, Float
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import count

from shared.infrastructure.database.models import *
from other.global_data import MTLChats


def db_save_bot_value_ext(session: Session, chat_id: int, chat_key: int | Enum, chat_value: any):
    """
    Update or insert a record in the BOT_TABLE.

    :param session: SQLAlchemy DB session
    :param chat_id: The ID of the chat
    :param chat_key: The key of the chat
    :param chat_value: The value of the chat
    """
    chat_key = chat_key if isinstance(chat_key, int) else chat_key.value
    record = session.query(BotTable).filter(and_(BotTable.chat_id == chat_id, BotTable.chat_key == chat_key)).first()
    if chat_value is None:
        # If the chat_value is None and the record exists, delete the record
        if record is not None:
            session.delete(record)
    else:
        if record is None:
            # Create a new record
            new_record = BotTable(chat_id=chat_id, chat_key=chat_key, chat_value=chat_value)
            session.add(new_record)
        else:
            # Update existing record
            record.chat_value = chat_value
    session.commit()


def db_load_bot_value_ext(session: Session, chat_id: int, chat_key: int | Enum, default_value: any = ''):
    """
    Get a chat_value by chat_id and chat_key from the BOT_TABLE.

    :param session: SQLAlchemy DB session
    :param chat_id: The ID of the chat
    :param chat_key: The key of the chat
    :param default_value: The default value to return if no record was found
    :return: The chat_value or default_value if no record was found
    """
    chat_key = chat_key if isinstance(chat_key, int) else chat_key.value
    result = session.query(BotTable.chat_value).filter(
        and_(BotTable.chat_id == chat_id, BotTable.chat_key == chat_key)).first()
    return result[0] if result else default_value


#
#
# def db_get_chat_ids_by_key(session: Session, chat_key: int) -> List[int]:
#     """
#     Get list of chat IDs by a specific chat key.
#
#     :param session: SQLAlchemy DB session
#     :param chat_key: The key of the chat
#     :return: List of chat IDs where the provided key exists
#     """
#     result = session.query(BotTable.chat_id).filter(BotTable.chat_key == chat_key).all()
#     return [row[0] for row in result]
#
#
# def db_get_chat_dict_by_key(session: Session, chat_key: int, return_json=False) -> Dict[int, str | list]:
#     """
#     Get dictionary of chat IDs and corresponding values by a specific chat key.
#
#     :param return_json: if True, return the list as JSON
#     :param session: SQLAlchemy DB session
#     :param chat_key: The key of the chat
#     :return: Dictionary with chat IDs as keys and corresponding values as values for the provided chat key
#     """
#     result = session.query(BotTable.chat_id, BotTable.chat_value).filter(BotTable.chat_key == chat_key).all()
#     if return_json:
#         return {row[0]: json.loads(row[1]) for row in result}
#     else:
#         return {row[0]: row[1] for row in result}


def db_save_bot_user(session: Session, user_id: int, user_name: str | None, user_type: int = 0):
    """
    Update or insert a user in the bot_users table.

    :param session: SQLAlchemy DB session
    :param user_id: The ID of the user
    :param user_name: The name of the user
    :param user_type: The type of the user, default is 0
    """
    user = session.query(BotUsers).filter(BotUsers.user_id == user_id).first()
    if user is None:
        # Create a new user
        new_user = BotUsers(user_id=user_id, user_name=user_name, user_type=user_type)
        session.add(new_user)
    else:
        # Update existing user
        if user_name:
            user.user_name = user_name
        user.user_type = user_type
    session.commit()


def db_get_user_id(session: Session, user_name: str) -> int:
    """
    Get a user_id by user_name or numeric ID from the bot_users table.

    :param session: SQLAlchemy DB session
    :param user_name: The name of the user (prefixed with @) or numeric user ID
    :return: The user_id
    :raises ValueError: If the user is not found or the input format is invalid
    """
    if user_name.startswith('@'):
        username = user_name[1:]
        result = session.query(BotUsers.user_id).filter(BotUsers.user_name == username).first()
        if not result:
            raise ValueError(f"User @{username} not found in the database.")
        return result[0]
    else:
        try:
            return int(user_name)
        except ValueError:
            raise ValueError("Invalid user ID or username format. Use a numeric ID or @username.")


def db_load_bot_users(session: Session) -> List[BotUsers]:
    """
    Retrieve a list of BotUsers objects filtered by user_name from the bot_users table.

    :param session: SQLAlchemy DB session
    :return: A list of BotUsers objects
    """
    result = session.query(BotUsers).all()
    return result


def db_load_new_message(session: Session) -> list[TMessage]:
    """
    Load new messages from the database

    :param session: SQLAlchemy DB session
    :return: List of TMessage objects that haven't been sent yet (can be empty)
    """
    result = session.execute(select(TMessage).where(TMessage.was_send == 0).limit(10))
    return cast(list[TMessage], result.scalars().all())


def extract_url(msg, surl='eurmtl.me'):
    try:
        if surl:
            pattern = rf"https?://{surl}[^\s]+"
        else:
            pattern = r"https?://[^\s]+"

        search_result = re.search(pattern, msg)

        if search_result:
            return search_result.group(0)  # Извлекаем URL
        else:
            return None  # URL не найден
    except Exception as e:
        logger.error(f"Ошибка при извлечении URL: {e}")
        return None


def db_get_total_user_div(session: Session) -> float:
    stmt = (
        select(func.sum(TPayments.user_div))
        .select_from(TPayments)
        .join(TDivList, and_(TDivList.id == TPayments.id_div_list))
        .where(TDivList.pay_type == 1)
    )

    return session.execute(stmt).scalar()


def db_get_div_list(session: Session, list_id: int) -> TDivList:
    """
    Fetch t_div_list

    :param session: SQLAlchemy DB session
    :param list_id: the id of the list
    :return: TDivList
    """
    return cast(TDivList, session.query(TDivList).filter(TDivList.id == list_id).first())


def db_get_payments(session: Session, list_id: int, pack_count: int) -> List[TPayments]:
    """
    Fetch first pack_count payments from T_PAYMENTS table where WAS_PACKED = 0 and ID_DIV_LIST = list_id

    :param session: SQLAlchemy DB session
    :param list_id: the id of the list
    :param pack_count: the number of records to fetch
    :return: List of TPayments objects
    """
    payments = session.query(TPayments).filter(
        TPayments.was_packed == 0,
        TPayments.id_div_list == list_id
    ).limit(pack_count).all()

    return cast(List[TPayments], payments)


def db_count_unpacked_payments(session: Session, list_id: int):
    """
    Count the number of unpacked payments for a given list id

    :param session: SQLAlchemy DB session
    :param list_id: the id of the list
    :return: the number of unpacked payments
    """
    count = session.query(func.count('*')).filter(TPayments.was_packed == 0, TPayments.id_div_list == list_id).scalar()
    return count


def db_count_unsent_transactions(session: Session, list_id: int) -> int:
    """
    Count unsent transactions for a specific list in the TTransaction table.

    :param session: SQLAlchemy DB session
    :param list_id: ID of the list
    :return: Count of unsent transactions
    """
    result = session.execute(
        select(func.count()).where(and_(TTransaction.was_send == 0, TTransaction.id_div_list == list_id))
    )
    return result.scalar()


def cmd_load_transactions(session: Session, list_id: int) -> List[TTransaction]:
    """
    Load transactions from the TTransaction table that were not sent and belong to a specific list.

    :param session: SQLAlchemy DB session
    :param list_id: ID of the list
    :return: List of TTransaction instances (can be empty)
    """
    result = session.execute(
        select(TTransaction).where(and_(TTransaction.was_send == 0, TTransaction.id_div_list == list_id))
    )
    return cast(List[TTransaction], result.scalars().all())


def db_get_watch_list(session: Session):
    """
    Fetch accounts from t_watch_list and mymtlwalletbot

    :param session: SQLAlchemy DB session
    :return: Tuple of accounts
    """
    from_watch_list = session.query(TWatchList.account).all()
    from_mymtlwalletbot = session.query(MyMtlWalletBot.public_key).where(MyMtlWalletBot.need_delete == 0).all()

    result = tuple(record[0] for record in from_watch_list + from_mymtlwalletbot)
    return result


def add_to_watchlist(session: Session, public_keys: list):
    """
    Add public keys to the T_WATCH_LIST if they're not already present

    :param session: SQLAlchemy DB session
    :param public_keys: list of public keys to be added
    """
    # Fetch current watch list
    current_watch_list = db_get_watch_list(session)

    # Identify new public keys that are not in the watch list
    new_keys = [key for key in public_keys if key not in current_watch_list]

    # Add new keys to the T_WATCH_LIST
    for key in new_keys:
        new_watchlist_entry = TWatchList(account=key)
        session.add(new_watchlist_entry)

    # Commit the new entries to the DB
    session.commit()


def db_get_first_100_ledgers(session: Session) -> List[TLedgers]:
    """
    Get the first 100 ledgers, ordered by ledger number

    :param session: SQLAlchemy DB session
    :return: List of TLedgers objects
    """
    result = session.execute(select(TLedgers).order_by(TLedgers.ledger).limit(100))
    return cast(List[TLedgers], result.scalars().all())


def db_get_ledger(session: Session, ledger_id: int) -> TLedgers:
    """
    Get a ledger with a specific ID

    :param session: SQLAlchemy DB session
    :param ledger_id: The ID of the ledger to retrieve
    :return: A TLedgers object
    """
    result = session.execute(select(TLedgers).filter(TLedgers.ledger == ledger_id))
    return cast(TLedgers, result.scalars().first())


def db_get_ledger_count(session: Session) -> int:
    """
    Get the total number of ledgers in the table

    :param session: SQLAlchemy DB session
    :return: The count of ledgers (integer)
    """
    result = session.execute(select(count()).select_from(TLedgers))
    return cast(int, result.scalar())


def db_cmd_add_message(session: Session, user_id: int, text: str, use_alarm: int = 0, update_id: int = None,
                       button_json: str = None, topic_id: int = 0) -> None:
    """
    Insert a new message into the t_message table.

    :param topic_id: The ID of the topic
    :param session: SQLAlchemy DB session
    :param user_id: The ID of the user
    :param text: The message text
    :param use_alarm: The alarm usage flag (default is 0)
    :param update_id:
    :param button_json:
    """
    logger.info(f"db_cmd_add_message: {text}")
    new_message = TMessage(user_id=user_id, text=text, use_alarm=use_alarm, update_id=update_id,
                           button_json=button_json, topic_id=topic_id)
    session.add(new_message)
    session.commit()


def db_get_new_effects_for_token(session: Session, token: str, last_id: str, amount: float) -> list[TOperations]:
    """
    Get the first 10 operations with ID greater than the given ID and with a token either in code1 or code2,
    and the amount in amount1 or amount2 is greater than the given amount.
    If last_id is '-1', return the single most recent record with the maximum ID.

    :param session: SQLAlchemy DB session
    :param token: The token string
    :param last_id: The last ID string, or '-1' for the most recent record
    :param amount: The amount as a float
    :return: A list of TOperations objects satisfying the condition
    """
    assert len(token) <= 32, "Length of 'token' should not exceed 32 characters"

    base_query = (
        session.query(TOperations)
        .filter(TOperations.operation != 'trustline_created')
        .filter(
            (TOperations.code1 == token) & (func.cast(TOperations.amount1, Float) > amount) |
            (TOperations.code2 == token) & (func.cast(TOperations.amount2, Float) > amount)
        )
    )

    if last_id == '-1':
        result = (
            base_query
            .order_by(desc(TOperations.id))
            .limit(1)
            .all()
        )
    else:
        result = (
            base_query
            .filter(TOperations.id > last_id)
            .order_by(TOperations.id)
            .limit(10)
            .all()
        )

    return cast(list[TOperations], result)


def db_get_operations(session: Session, last_id: Optional[str] = None, limit: int = 3000) -> List[TOperations]:
    """
    Получает записи из таблицы t_operations, где id больше заданного значения.
    Если last_id равно None, возвращает последнюю по дате операцию.

    Args:
        session: SQLAlchemy session object
        last_id (Optional[str]): значение id, от которого нужно начать выборку.
        limit (int): максимальное количество возвращаемых записей. По умолчанию 3000.

    Returns:
        List[TOperations]: список объектов TOperations, представляющих записи в базе данных.
    """
    if last_id is None:
        # Если last_id None, ищем последнюю запись по дате.
        last_record = session.query(TOperations).order_by(TOperations.dt.desc()).first()
        return [last_record] if last_record else []

    query = session.query(TOperations). \
        filter(TOperations.id > last_id). \
        order_by(TOperations.id). \
        limit(limit)

    records = query.all()

    return records


def db_send_admin_message(session: Session, msg: str):
    db_cmd_add_message(session, MTLChats.ITolstov, msg)


def get_mmwb_use_date(session: Session, address: str) -> datetime:
    """
    Get the last usage date for a specific address.

    :param session: SQLAlchemy DB session
    :param address: Address string to search
    :return: Date of last usage
    """
    result = session.query(func.max(MyMtlWalletBot.last_use_day)).filter(
        and_(MyMtlWalletBot.need_delete == 0, MyMtlWalletBot.public_key == address)).scalar()
    return result


def db_get_wallet_stats(session: Session):
    """
    Получает статистические данные по кошелькам из таблицы Mymtlwalletbot.

    :param session: SQLAlchemy DB сессия
    :return: Кортеж с четырьмя значениями:
             - Количество уникальных пользователей (user_id)
             - Сумма всех значений в поле free_wallet
             - Количество кошельков, у которых use_pin равен 10
             - Количество кошельков, у которых use_pin не равен 10 и free_wallet равен 0
    """
    record = session.query(
        func.count(distinct(MyMtlWalletBot.user_id)),
        func.sum(MyMtlWalletBot.free_wallet),
        func.sum(case((MyMtlWalletBot.use_pin == 10, 1), else_=0)),
        func.sum(case((and_(MyMtlWalletBot.use_pin != 10, MyMtlWalletBot.free_wallet == 0), 1), else_=0))
    ).filter(
        and_(MyMtlWalletBot.need_delete == 0, MyMtlWalletBot.user_id > 0)
    ).first()

    return record


def db_get_log_count(session, operation_type):
    """
    Получить количество записей в логе для заданного типа операции за последний день.

    Args:
        session: SQLAlchemy session object
        operation_type (str): Тип операции, для которой нужно подсчитать записи.

    Returns:
        int: Количество записей.
    """

    # текущая дата и время
    now = datetime.now()

    # дата и время одного дня назад
    one_day_ago = now - timedelta(days=1)

    # Количество записей
    log_count = session.query(func.count(MyMtlWalletBotLog.log_id)). \
        filter(MyMtlWalletBotLog.log_operation == operation_type,
               MyMtlWalletBotLog.log_dt.between(one_day_ago, now)). \
        scalar()

    return log_count


def db_get_wallet_info(session) -> List[MyMtlWalletBot]:
    """
    Получает информацию об кошельках из таблицы mymtlwalletbot, где user_id больше 100 и need_delete равно 0.

    Args:
        session: SQLAlchemy session object

    Returns:
        result: Список кортежей с информацией о кошельках.
    """
    result = session.query(
        MyMtlWalletBot
    ).filter(
        MyMtlWalletBot.user_id > 100,
        MyMtlWalletBot.need_delete == 0,
    ).all()

    return result


def db_save_exception(msg: str):
    # msg = quote(msg)[:4000]
    # msg = msg.replace('<','[').replace('>',']')[:4000]
    # execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)', (84131737, msg, 0))
    from quik_pool import quik_pool
    db_send_admin_message(quik_pool(), f'Exception was {argv} ({type(msg)})')
    # add text to file error.txt
    with open('error.txt', 'a') as f:
        f.write(f"{argv} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        f.write(msg)
        f.write('\n')
        f.write('******************************************************************************\n')


def db_save_message(session: Session, user_id: int, username: str, chat_id: int, thread_id: int, text: str,
                    summary_id: int = None) -> None:
    """
    Insert a new message into the t_saved_messages table.

    :param session: SQLAlchemy DB session
    :param user_id: The ID of the user
    :param username: The username
    :param chat_id: The ID of the chat
    :param thread_id: The ID of the thread
    :param text: The message text
    :param summary_id: The ID of the summary
    """
    new_message = TSavedMessages(user_id=user_id, username=username, chat_id=chat_id,
                                 thread_id=thread_id, text=text[:4000], summary_id=summary_id)
    session.add(new_message)
    session.commit()


def db_get_messages_without_summary(session, chat_id: int, thread_id: int, dt: datetime = None) -> List[TSavedMessages]:
    """
    Получает записи из таблицы TSavedMessages, где summary_id равно None,
    и переданные параметры chat_id и thread_id равны значениям в записях.

    Args:
        session: SQLAlchemy session object
        chat_id: Идентификатор чата
        thread_id: Идентификатор тренда
        dt: Дата, по умолчанию сегодня

    Returns:
        result: Список объектов TSavedMessages, удовлетворяющих заданным условиям.
    """
    if dt is None:
        dt = datetime.today()

    result = session.query(
        TSavedMessages
    ).filter(
        TSavedMessages.chat_id == chat_id,
        TSavedMessages.thread_id == thread_id,
        TSavedMessages.dt.between(dt.date(), dt.date() + timedelta(days=1)),
        TSavedMessages.summary_id.is_(None)
    )

    return result.all()


def db_add_summary(session, text: str, summary_id: int = None) -> TSummary:
    """
    Insert a new record in the TSummary table.

    :param session: SQLAlchemy DB session
    :param text: The text of the record
    :param summary_id: The summary_id of the record
    """
    # Create a new record
    new_record = TSummary(text=text, summary_id=summary_id)
    session.add(new_record)

    return new_record


def db_get_summary(session, chat_id: int, thread_id: int, dt: datetime = None) -> List[TSummary]:
    """
    Находит summary_id в таблице TSavedMessages по заданным параметрам chat_id, thread_id, и dt,
    и возвращает все соответствующие записи из таблицы TSummary.

    Args:
        session: SQLAlchemy session object
        chat_id: Идентификатор чата
        thread_id: Идентификатор тренда
        dt: Дата, по умолчанию сегодня

    Returns:
        result: Список объектов TSummary, удовлетворяющих заданным условиям.
    """
    if dt is None:
        dt = datetime.today()

    summary_ids = session.query(
        TSavedMessages.summary_id
    ).filter(
        TSavedMessages.chat_id == chat_id,
        TSavedMessages.thread_id == thread_id,
        TSavedMessages.dt.between(dt.date(), dt.date() + timedelta(days=1))
    ).distinct().all()

    summary_ids = [id[0] for id in summary_ids if id[0] is not None]  # unpack the ids and remove None

    summaries = session.query(
        TSummary
    ).filter(
        TSummary.id.in_(summary_ids)
    )

    return summaries.all()


def db_get_last_trade_operation(session: Session, asset_code='MTL', minimal_sum=0) -> float:
    stmt = (
        select(TOperations)
        .where(
            (TOperations.operation == 'trade') &
            (
                    and_((TOperations.code1 == asset_code), (TOperations.code2 == 'EURMTL'),
                         (sql_cast(TOperations.amount1, Float).__gt__(minimal_sum))) |
                    and_((TOperations.code1 == 'EURMTL'), (TOperations.code2 == asset_code),
                         (sql_cast(TOperations.amount2, Float).__gt__(minimal_sum)))
            )
        )
        .order_by(desc(TOperations.dt))
        .limit(1)
    )

    result = session.execute(stmt)
    with suppress(NoResultFound):
        operation = result.scalar_one()

        if operation.code2 == asset_code:
            rate = float(operation.amount1) / float(operation.amount2)
        else:
            rate = float(operation.amount2) / float(operation.amount1)

        return round(rate, 2)
    return 0


def db_update_user_chat_date(session: Session, user_id: int, chat_id: int):
    """
    Insert or update a BotUserChats record with the given user_id and chat_id.

    :param session: SQLAlchemy session.
    :param user_id: User ID.
    :param chat_id: Chat ID.
    """
    existing_record = session.query(BotUserChats).filter(
        BotUserChats.user_id == user_id,
        BotUserChats.chat_id == chat_id
    ).first()

    if existing_record:
        existing_record.dt_last = datetime.now()
    else:
        new_record = BotUserChats(user_id=user_id, chat_id=chat_id, dt_last=datetime.now())
        session.add(new_record)

    session.commit()


def db_get_operations_by_asset(session: Session, asset_code, dt_filter) -> List[TOperations]:
    query = (session.query(TOperations)
             .filter((TOperations.code1 == asset_code) | (TOperations.code2 == asset_code))
             .filter(sql_cast(TOperations.dt, Date) == dt_filter))
    records = query.all()
    return records


if __name__ == '__main__':
    from quik_pool import quik_pool

    text = 'text ' * 1000
    print(len(text))
    db_save_message(session=quik_pool(), user_id=1, username='username', thread_id=1, text=text, chat_id=1)

#    print(db_get_operations_by_asset(quik_pool(), 'USDM', datetime.now().date()))

# print(db_get_new_effects_for_token(session=quik_pool(),
#                                token='MTL',
#                                last_id='1',
#                               amount=1))
