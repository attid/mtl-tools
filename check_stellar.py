import sys
from datetime import datetime

import app_logger
import fb
from mystellar import cmd_check_new_transaction, cmd_check_new_asset_transaction, BotValueTypes, \
    cmd_check_last_operation, get_balances, public_fond, public_defi

if 'logger' not in globals():
    logger = app_logger.get_logger("check_stellar")

chat_id_test = -1001767165598
chat_id_signs = -1001239694752
chat_id_guarantors = -1001169382324
chat_id_defi = -1001876391583


def cmd_add_message(user_id, text, use_alarm=0):
    fb.execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)', (user_id, text, use_alarm))


def cmd_check_cron_transaction():
    # logger.info('cmd_check_new_transaction')
    # FUND
    result = cmd_check_new_transaction(ignore_operation=['CreateClaimableBalance'], stellar_address=public_fond,
                                       address_id=BotValueTypes.LastFondTransaction)
    if len(result) > 0:
        cmd_add_message(chat_id_signs, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_signs, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_signs, msg[0:4000])
    # DEFI
    result = cmd_check_new_transaction(ignore_operation=['CreateClaimableBalance'], stellar_address=public_defi,
                                       address_id=BotValueTypes.LastDefiTransaction)
    if len(result) > 0:
        cmd_add_message(chat_id_defi, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_defi, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_defi, msg[0:4000])

    # EURDEBT
    result = cmd_check_new_asset_transaction('EURDEBT', BotValueTypes.LastDebtTransaction)
    if len(result) > 0:
        cmd_add_message(chat_id_guarantors, "Получены новые транзакции для EURDEBT")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_guarantors, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_guarantors, msg[0:4000])
    # EURMTL
    result = cmd_check_new_asset_transaction('EURMTL', BotValueTypes.LastEurTransaction, 900, ['Payment'])
    if len(result) > 0:
        cmd_add_message(chat_id_guarantors, "Получены новые транзакции для EURMTL")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_guarantors, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_guarantors, msg[0:4000])
    # MTLRECT
    result = cmd_check_new_asset_transaction('MTLRECT', BotValueTypes.LastRectTransaction, -1, ['Payment'])
    if len(result) > 0:
        cmd_add_message(chat_id_signs, "Получены новые транзакции для MTLRECT")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_signs, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_signs, msg[0:4000])

    # MTL
    result = cmd_check_new_asset_transaction('MTL', BotValueTypes.LastMTLTransaction, 10,
                                             ['Payment', 'PathPaymentStrictSend', 'PathPaymentStrictReceive'])
    if len(result) > 0:
        cmd_add_message(chat_id_signs, "Получены новые транзакции для MTL")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_signs, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_signs, msg[0:4000])

    # MTLand
    result = cmd_check_new_asset_transaction('MTLand', BotValueTypes.LastMTLandTransaction, 10,
                                             ['Payment', 'PathPaymentStrictSend', 'PathPaymentStrictReceive'])
    if len(result) > 0:
        cmd_add_message(chat_id_signs, "Получены новые транзакции для MTLand")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_signs, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_signs, msg[0:4000])


def cmd_check_bot():
    # balance Wallet
    if int(get_balances('GB72L53HPZ2MNZQY4XEXULRD6AHYLK4CO55YTOBZUEORW2ZTSOEQ4MTL')['XLM']) < 100:
        cmd_add_message(chat_id_signs, 'Внимание Баланс MyMTLWallet меньше 100 !')

    # bot1
    dt = cmd_check_last_operation('GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7')
    now = datetime.now()
    delta = now - dt
    if delta.days > 0:
        cmd_add_message(chat_id_signs, 'Внимание по боту обмена 1 нет операций больше суток !')

    # bot2
    dt = cmd_check_last_operation('GAEFTFGQYWSF5T3RVMBSW2HFZMFZUQFBYU5FUF3JT3ETJ42NXPDWOO2F')
    now = datetime.now()
    delta = now - dt
    if delta.days > 0:
        cmd_add_message(chat_id_signs, 'Внимание по боту обмена 2 нет операций больше суток !')

    # key rate
    dt = fb.execsql1('select max(t.dt_add) from t_keyrate t', [], datetime.now())
    dt = datetime.combine(dt, datetime.min.time())
    now = datetime.now()
    delta = now - dt
    if delta.days > 0:
        cmd_add_message(chat_id_signs, 'Внимание начислению key rate нет операций больше суток !')


if __name__ == "__main__":
    if 'check_transaction' in sys.argv:
        cmd_check_cron_transaction()
    elif 'check_bot' in sys.argv:
        cmd_check_bot()
    else:
        print('need more parameters')
