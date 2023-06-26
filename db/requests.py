import re
from datetime import timedelta
from sys import argv
from typing import List, Dict, cast
from sqlalchemy import select, and_, case, distinct
from sqlalchemy.orm import Session
from db.models import *
from utils.global_data import BotValueTypes, MTLChats


def cmd_save_bot_value(session, chat_id: int, chat_key: int, chat_value: any):
    """
    Update or insert a record in the BOT_TABLE.

    :param session: SQLAlchemy DB session
    :param chat_id: The ID of the chat
    :param chat_key: The key of the chat
    :param chat_value: The value of the chat
    """
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


def cmd_load_bot_value(session, chat_id: int, chat_key: int, default_value: any = ''):
    """
    Get a chat_value by chat_id and chat_key from the BOT_TABLE.

    :param session: SQLAlchemy DB session
    :param chat_id: The ID of the chat
    :param chat_key: The key of the chat
    :param default_value: The default value to return if no record was found
    :return: The chat_value or default_value if no record was found
    """
    result = session.query(BotTable.chat_value).filter(
        and_(BotTable.chat_id == chat_id, BotTable.chat_key == chat_key)).first()
    return result[0] if result else default_value


def get_chat_ids_by_key(session: Session, chat_key: int) -> List[int]:
    """
    Get list of chat IDs by a specific chat key.

    :param session: SQLAlchemy DB session
    :param chat_key: The key of the chat
    :return: List of chat IDs where the provided key exists
    """
    result = session.query(BotTable.chat_id).filter(BotTable.chat_key == chat_key).all()
    return [row[0] for row in result]


def get_chat_dict_by_key(session: Session, chat_key: int) -> Dict[int, str]:
    """
    Get dictionary of chat IDs and corresponding values by a specific chat key.

    :param session: SQLAlchemy DB session
    :param chat_key: The key of the chat
    :return: Dictionary with chat IDs as keys and corresponding values as values for the provided chat key
    """
    result = session.query(BotTable.chat_id, BotTable.chat_value).filter(BotTable.chat_key == chat_key).all()
    return {row[0]: row[1] for row in result}


def cmd_save_bot_user(session: Session, user_id: int, user_name: str):
    """
    Update or insert a user in the bot_users table.

    :param session: SQLAlchemy DB session
    :param user_id: The ID of the user
    :param user_name: The name of the user
    """
    user = session.query(BotUsers).filter(BotUsers.user_id == user_id).first()
    if user is None:
        # Create a new user
        new_user = BotUsers(user_id=user_id, user_name=user_name)
        session.add(new_user)
    else:
        # Update existing user
        user.user_name = user_name
    session.commit()


def cmd_load_user_id(session, user_name: str) -> int:
    """
    Get a user_id by user_name from the bot_users table.

    :param session: SQLAlchemy DB session
    :param user_name: The name of the user
    :return: The user_id or 0 if no user was found
    """
    result = session.query(BotUsers.user_id).filter(BotUsers.user_name == user_name).first()
    return result[0] if result else 0


def cmd_load_new_message(session: Session) -> list[TMessage]:
    """
    Load new messages from the database

    :param session: SQLAlchemy DB session
    :return: List of TMessage objects that haven't been sent yet (can be empty)
    """
    result = session.execute(select(TMessage).where(TMessage.was_send == 0).limit(10))
    return cast(list[TMessage], result.scalars().all())


def cmd_save_url(session, chat_id, msg_id, msg):
    url = extract_url(msg)
    cmd_save_bot_value(session, chat_id, BotValueTypes.PinnedUrl, url)
    cmd_save_bot_value(session, chat_id, BotValueTypes.PinnedId, msg_id)


def extract_url(msg, surl='eurmtl.me'):
    if surl:
        url = re.search("(?P<url>https?://" + surl + "[^\s]+)", msg).group("url")
    else:
        url = re.search("(?P<url>https?://[^\s]+)", msg).group("url")
    return url


def exec_total_user_div(session: Session) -> float:
    stmt = (
        select(func.sum(TPayments.user_div))
        .select_from(TPayments)
        .join(TDivList, and_(TDivList.id == TPayments.id_div_list))
        .where(TDivList.pay_type == 1)
    )

    return session.execute(stmt).scalar()


def get_div_list(session: Session, list_id: int) -> TDivList:
    """
    Fetch t_div_list

    :param session: SQLAlchemy DB session
    :param list_id: the id of the list
    :return: TDivList
    """
    return cast(TDivList, session.query(TDivList).filter(TDivList.id == list_id).first())


def get_payments(session: Session, list_id: int, pack_count: int) -> List[TPayments]:
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


def count_unpacked_payments(session: Session, list_id: int):
    """
    Count the number of unpacked payments for a given list id

    :param session: SQLAlchemy DB session
    :param list_id: the id of the list
    :return: the number of unpacked payments
    """
    count = session.query(func.count('*')).filter(TPayments.was_packed == 0, TPayments.id_div_list == list_id).scalar()
    return count


def cmd_count_unsent_transactions(session: Session, list_id: int) -> int:
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


def get_watch_list(session: Session):
    """
    Fetch accounts from t_watch_list and mymtlwalletbot

    :param session: SQLAlchemy DB session
    :return: Tuple of accounts
    """
    from_watch_list = session.query(TWatchList.account).all()
    from_mymtlwalletbot = session.query(MyMtlWalletBot.public_key).all()

    result = tuple(record[0] for record in from_watch_list + from_mymtlwalletbot)
    return result


def get_first_100_ledgers(session: Session) -> List[TLedgers]:
    """
    Get the first 100 ledgers, ordered by ledger number

    :param session: SQLAlchemy DB session
    :return: List of TLedgers objects
    """
    result = session.execute(select(TLedgers).order_by(TLedgers.ledger).limit(100))
    return cast(List[TLedgers], result.scalars().all())


def get_ledger(session: Session, ledger_id: int) -> TLedgers:
    """
    Get a ledger with a specific ID

    :param session: SQLAlchemy DB session
    :param ledger_id: The ID of the ledger to retrieve
    :return: A TLedgers object
    """
    result = session.execute(select(TLedgers).filter(TLedgers.ledger == ledger_id))
    return cast(TLedgers, result.scalars().first())


def cmd_add_message(session: Session, user_id: int, text: str, use_alarm: int = 0, update_id: int = None,
                    button_json: str = None) -> None:
    """
    Insert a new message into the t_message table.

    :param session: SQLAlchemy DB session
    :param user_id: The ID of the user
    :param text: The message text
    :param use_alarm: The alarm usage flag (default is 0)
    :param update_id:
    :param button_json:
    """
    new_message = TMessage(user_id=user_id, text=text, use_alarm=use_alarm, update_id=update_id,
                           button_json=button_json)
    session.add(new_message)
    session.commit()


def get_new_effects_for_token(session: Session, token: str, last_id: str, amount: float) -> list[
    TOperations]:
    """
    Get the first 10 operations with ID greater than the given ID and with a token either in code1 or code2,
    and the amount in amount1 or amount2 is greater than the given amount.

    :param session: SQLAlchemy DB session
    :param token: The token string
    :param last_id: The last ID string
    :param amount: The amount as a float
    :return: A list of TOperations objects satisfying the condition
    """
    assert len(token) <= 32, "Length of 'token' should not exceed 32 characters"

    result = (
        session.query(TOperations)
        .filter(TOperations.id > last_id)
        .filter(
            (TOperations.code1 == token) & (func.cast(TOperations.amount1, Float) > amount) |
            (TOperations.code2 == token) & (func.cast(TOperations.amount2, Float) > amount)
        )
        .order_by(TOperations.id)
        .limit(10)
        .all()
    )

    return cast(list[TOperations], result)


def get_operations(session, last_id, limit=3000) -> List[TOperations]:
    """
    Получает записи из таблицы t_operations, где id больше заданного значения.

    Args:
        session: SQLAlchemy session object
        last_id (int): значение id, от которого нужно начать выборку.
        limit (int): максимальное количество возвращаемых записей. По умолчанию 3000.

    Returns:
        List[TOperations]: список объектов TOperations, представляющих записи в базе данных.
    """
    query = session.query(TOperations). \
        filter(TOperations.id > last_id). \
        order_by(TOperations.id). \
        limit(limit)

    records = query.all()

    return records


def send_admin_message(session: Session, msg: str):
    cmd_add_message(session, MTLChats.ITolstov, msg)


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


def get_wallet_stats(session: Session):
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


def get_log_count(session, operation_type):
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


def get_wallet_info(session):
    """
    Получает информацию об кошельках из таблицы mymtlwalletbot, где user_id больше 100 и need_delete равно 0.

    Args:
        session: SQLAlchemy session object

    Returns:
        result: Список кортежей с информацией о кошельках.
    """
    result = session.query(
        MyMtlWalletBot.public_key,
        MyMtlWalletBot.free_wallet,
        MyMtlWalletBot.default_wallet,
        MyMtlWalletBot.last_use_day,
    ).filter(
        MyMtlWalletBot.user_id > 100,
        MyMtlWalletBot.need_delete == 0,
    ).all()

    return result


def save_exception(msg: str):
    # msg = quote(msg)[:4000]
    # msg = msg.replace('<','[').replace('>',']')[:4000]
    # execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)', (84131737, msg, 0))
    from quik_pool import quik_pool
    send_admin_message(quik_pool(), f'Exception was {argv} ({type(msg)})')
    # add text to file error.txt
    with open('error.txt', 'a') as f:
        f.write(f"{argv} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        f.write(msg)
        f.write('\n')
        f.write('******************************************************************************\n')


if __name__ == '__main__':
    from quik_pool import quik_pool

    print(get_wallet_stats(quik_pool()))

    # print(get_new_effects_for_token(session=quik_pool(),
    #                                token='MTL',
    #                                last_id='1',
    #                               amount=1))
