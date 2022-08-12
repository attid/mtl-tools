#!/usr/bin/python3
import fdb


# https://fdb.readthedocs.io/en/v2.0/ from datetime import timedelta, datetime
def connect_db():
    return fdb.connect(dsn='127.0.0.1:mtl', user='SYSDBA', password='sysdba', charset='UTF8')


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


def free_db(con):
    con.close()
    del (con)


def execsql(sql, param=None):
    con = connect_db()
    result = execsql0(con, sql, param)
    con.commit()
    free_db(con)
    return result


def execsql1(sql, param=None, default=''):
    result = execsql(sql, param)
    if len(result) > 0:
        return result[0][0]
    else:
        return default


def manyinsert(sql, param):
    con = connect_db()
    cur = con.cursor()
    cur.executemany(sql, param)
    con.commit()
    free_db(con)
    return

# if __name__ == "__main__":
#    memo = 'test'
#    print(execsql(f"insert into T_DIV_LIST (MEMO) values ('{memo}') returning ID")[0][0])
# print(execsql("select first 100 * from cards")) card = '123' print(execsql(f"select count(1) from employee e where e.barcode = '{card}'")[0][0])
# import app_logger logger = app_logger.get_logger("bod_exchange") logger.info(['eurmtl_sum',eurmtl_sum,'xlm_sum',xlm_sum])
