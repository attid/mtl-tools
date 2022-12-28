#!/usr/bin/python3
import fdb
from loguru import logger
#logger.add("check_stellar", rotation="1 MB")

# https://fdb.readthedocs.io/en/v2.0/ from datetime import timedelta, datetime
def connect_db():
    return fdb.connect(dsn='127.0.0.1:mtl', user='SYSDBA', password='sysdba', charset='UTF8')


@logger.catch
def execsql0(con, sql, param=None):
    cur = con.cursor()
    if param == None:
        cur.execute(sql)
    else:
        cur.execute(sql, param)
    try:
        return cur.fetchall()
    except:
        return []


@logger.catch
def free_db(con):
    con.close()
    del (con)


@logger.catch
def execsql(sql, param=None):
    con = connect_db()
    result = execsql0(con, sql, param)
    con.commit()
    free_db(con)
    return result


@logger.catch
def execsql1(sql, param=None, default=''):
    result = execsql(sql, param)
    if len(result) > 0:
        return result[0][0]
    else:
        return default


@logger.catch
def many_insert(sql, param):
    con = connect_db()
    cur = con.cursor()
    cur.executemany(sql, param)
    con.commit()
    free_db(con)
    return


def send_admin_message(msg):
    execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)', (84131737, msg, 0))


logger.add(send_admin_message, level='WARNING')

# if __name__ == "__main__":
#    memo = 'test'
#    print(execsql(f"insert into T_DIV_LIST (MEMO) values ('{memo}') returning ID")[0][0])
# print(execsql("select first 100 * from cards")) card = '123' print(execsql(f"select count(1) from employee e where e.barcode = '{card}'")[0][0])
# from loguru import logger logger = app_logger.get_logger("bod_exchange") logger.info(['eurmtl_sum',eurmtl_sum,'xlm_sum',xlm_sum])
