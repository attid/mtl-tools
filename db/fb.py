# #!/usr/bin/python3
# from sys import argv
# from urllib.parse import quote
#
# import fdb
# from loguru import logger
# from numpy import amax
#
#
# # logger.add("check_stellar", rotation="1 MB")
#
# # https://fdb.readthedocs.io/en/v2.0/ from datetime import timedelta, datetime
# def connect_db():
#     # return fdb.connect(dsn='127.0.0.1/3051:mtl', user='SYSDBA', password='sysdba', charset='UTF8')
#     return fdb.connect(dsn='127.0.0.1:mtl', user='SYSDBA', password='sysdba', charset='UTF8')
#
#
# @logger.catch
# def execsql_con(con, sql, param=None):
#     cur = con.cursor()
#     if param == None:
#         cur.execute(sql)
#     else:
#         cur.execute(sql, param)
#     try:
#         return cur.fetchall()
#     except:
#         return []
#
#
# @logger.catch
# def free_db(con):
#     con.close()
#     del (con)
#
#
# @logger.catch
# def execsql(sql, param=None):
#     con = connect_db()
#     result = execsql_con(con, sql, param)
#     con.commit()
#     free_db(con)
#     return result
#
#
# @logger.catch
# def execsql1(sql, param=None, default=''):
#     result = execsql(sql, param)
#     if result is None:
#         return default
#     elif len(result) > 0:
#         return result[0][0]
#     else:
#         return default
#
#
# @logger.catch
# def many_insert(sql, param):
#     con = connect_db()
#     cur = con.cursor()
#     cur.executemany(sql, param)
#     con.commit()
#     free_db(con)
#     return
#
#
# def send_admin_message(msg: str):
#     execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)',
#             (84131737, msg, 0))
#
#
# def save_exception(msg: str):
#     # msg = quote(msg)[:4000]
#     # msg = msg.replace('<','[').replace('>',']')[:4000]
#     # execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)', (84131737, msg, 0))
#     execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)',
#             (84131737, f'Exception was {argv}', 0))
#     # add text to file error.txt
#     with open('error.txt', 'a') as f:
#         f.write(f'{argv}')
#         f.write(msg)
#         f.write('\n')
#         f.write('******************************************************************************\n')
#
#
# logger.add(save_exception, level='WARNING', format="{time} {level} {message}")
#
#
# def get_watch_list():
#     result = ()
#     for record in execsql('select account from t_watch_list'):
#         result += (record[0],)
#     for record in execsql('select m.public_key from mymtlwalletbot m'):
#         result += (record[0],)
#     return result
#
#
# def get_mmwb_accounts():
#     result = []
#     for record in execsql('select m.public_key from mymtlwalletbot m where m.need_delete = 0 and m.user_id > 1'):
#         result.append(record[0])
#     return result
#
#
# def get_mmwb_use_date(address):
#     return execsql1('select max(m.last_use_day) from mymtlwalletbot m where m.need_delete = 0 and m.public_key = ?',
#                     (address,), None)
#
#
# if __name__ == "__main__":
#     print(get_new_effects_for_token('EURMTL', '', '190205555871641601-10', 900))
#     pass
