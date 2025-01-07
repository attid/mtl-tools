import sentry_sdk

from utils.global_data import BotValueTypes
from utils.stellar_utils import *
from db.models import TLedgers, TOperations
from db.quik_pool import quik_pool

watch_list = []


########################################################################################################################
########################################################################################################################
########################################################################################################################

async def extra_run():
    # create queue
    queue = asyncio.Queue()

    # create task
    master1_task = asyncio.create_task(master_update_list(f'master1', quik_pool))
    master2_task = asyncio.create_task(master_get_new_ledgers(f'master2', queue, quik_pool))
    # wait for a little while to allow master_get_new_ledgers to populate the queue
    # await asyncio.sleep(15)

    tasks = [master1_task, master2_task]
    for i in range(10):
        task = asyncio.create_task(worker_get_ledger(f'worker-{i}', queue, quik_pool))
        tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=True)


########################################################################################################################
########################################################################################################################
########################################################################################################################

async def master_update_list(name, session_pool):
    while True:
        global watch_list
        with session_pool() as session:
            watch_list = db_get_watch_list(session)
        logger.info(f'{name} watch_list was update {len(watch_list)}')
        await asyncio.sleep(60 * 60 * 1)


########################################################################################################################
########################################################################################################################
########################################################################################################################

async def master_get_new_ledgers(name, queue: asyncio.Queue, session_pool):
    global watch_list
    # load old ledger
    while len(watch_list) == 0:
        logger.info(f'{name} watch_list is empty')
        await asyncio.sleep(10)

    while True:
        if queue.empty():
            # put data
            with session_pool() as session:
                resend_data = db_get_first_100_ledgers(session)
            if len(resend_data) > 0:
                logger.info(f'{name} load {len(resend_data)} from old')
            for record in resend_data:
                queue.put_nowait(record.ledger)
        # find new ledgers
        try:
            with session_pool() as session:
                await asyncio.wait_for(load_from_stellar(name, queue, session), timeout=60)
        except asyncio.exceptions.TimeoutError:
            pass
        except Exception as e:
            logger.warning(f'{name} failed {type(e)}')
        await asyncio.sleep(20)


async def load_from_stellar(name, queue, session):
    saved_ledger = int(db_load_bot_value_ext(quik_pool(), 0, BotValueTypes.LastLedger, '45407700'))
    async with aiohttp.ClientSession() as httpsession:
        async with httpsession.get(config.horizon_url) as resp:
            json_resp = await resp.json()
            core_latest_ledger = int(json_resp['history_latest_ledger'])
            if core_latest_ledger > saved_ledger:
                for i in range(saved_ledger + 1, core_latest_ledger + 1):
                    logger.info(f'{name} new ledger found {i}')
                    ledger = TLedgers(i)
                    session.add(ledger)
                    queue.put_nowait(ledger.ledger)
                    session.commit()

                db_save_bot_value_ext(quik_pool(), 0, BotValueTypes.LastLedger, core_latest_ledger)


########################################################################################################################
########################################################################################################################
########################################################################################################################

async def worker_get_ledger(name, queue: asyncio.Queue, session_pool):
    while True:  # not queue.empty():
        ledger_id: int = await queue.get()
        try:
            logger.info(f'{name} {ledger_id} start')
            with session_pool() as session:
                ledger = db_get_ledger(session, ledger_id)
                await asyncio.wait_for(
                    cmd_check_ledger(start_ledger_id=ledger_id, session=session), timeout=60)
                session.delete(ledger)
                session.commit()
                logger.info(f'{name} {ledger_id} checked')
        except asyncio.exceptions.TimeoutError as timeout_err:
            logger.info(f'{name} {ledger_id} timeout error: {timeout_err}')
        except Exception as e:
            logger.error(f'{name} {ledger_id} failed with {type(e).__name__}: {e}')

        # Сообщение очереди, для обработки "рабочего элемента".
        queue.task_done()
        # print(f'{name} {ledger} end')


async def cmd_check_ledger(start_ledger_id=None, session: Session = None):
    global watch_list

    if start_ledger_id:
        ledger_id = start_ledger_id
    else:
        ledger_id = int(db_load_bot_value_ext(quik_pool(), 0, BotValueTypes.LastLedger, '45407700'))
    max_ledger_id = ledger_id + 17

    while max_ledger_id > ledger_id:
        ledger_data = []
        logger.info(f'ledger_id {ledger_id}')
        effects = []
        async with ServerAsync(
                horizon_url=config.horizon_url  # , client=AiohttpClient(request_timeout=5)
        ) as server:
            call_builder = server.effects().for_ledger(ledger_id).limit(200)
            page_records = await call_builder.call()

            while page_records["_embedded"]["records"]:
                effects.extend(page_records["_embedded"]["records"])
                page_records = await call_builder.next()

        if len(effects) > 0:
            data = decode_effects_records(effects, ledger_id)
            if len(data) > 0:
                ledger_data.extend(data)

        for data in ledger_data:
            try:
                session.add(
                    TOperations(dt=data[0], operation=data[1], amount1=data[2], code1=data[3], amount2=data[4],
                                code2=data[5], from_account=data[6], for_account=data[7], transaction_hash=data[8],
                                memo=data[9], id=data[10], ledger=data[11]
                                )
                )  # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token', 'ledger']]]
                session.commit()
            except Exception as e:
                session.rollback()
                logger.warning(f'ledger_data {data} failed {type(e)}')
        # logger.info(f'ledger_data {ledger_data}')
        return


def decode_effects_records(records, ledger):
    global watch_list
    result = []
    for record in records:
        try:
            if record['type'] in ('liquidity_pool_trade', 'account_created', 'claimable_balance_sponsorship_removed',
                                  'claimable_balance_created', 'signer_updated', 'account_thresholds_updated',
                                  'signer_created', 'signer_removed', 'trustline_flags_updated', 'trustline_authorized',
                                  'trustline_authorized_to_maintain_liabilities', 'trustline_sponsorship_created',
                                  'claimable_balance_claimant_created', 'claimable_balance_sponsorship_created',
                                  'trustline_deauthorized', 'account_flags_updated', 'liquidity_pool_deposited',
                                  'account_removed', 'account_sponsorship_created', 'data_sponsorship_created',
                                  'signer_sponsorship_created', 'account_home_domain_updated', 'liquidity_pool_removed',
                                  'trustline_sponsorship_removed', 'liquidity_pool_withdrew', 'liquidity_pool_created',
                                  'account_inflation_destination_updated', 'sequence_bumped',
                                  'signer_sponsorship_removed',
                                  'account_sponsorship_removed', 'liquidity_pool_revoked',
                                  'claimable_balance_clawed_back'):
                continue
            if record['type'] == 'account_debited':
                if record['account'] in watch_list or record.get('asset_issuer') in watch_list:
                    # account_debited
                    # 'id': '0193165308029165569-0000000002', 'paging_token': '193165308029165569-2', 'account': 'GAO6SHKSQ3T3COGUWM3PYW4TELCFKCC57OOSM7QFZP6UA5OSDDNCTZPS',
                    # 'type': 'account_debited', 'type_i': 3, 'created_at': '2023-02-16T14:50:53Z', 'asset_type': 'native', 'amount': '0.0655842'}
                    op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                    result.append([op_date, record['type'], record['amount'],
                                   record.get('asset_code', 'XLM'), None, None, None, record.get('account'), None, '',
                                   record['paging_token'], ledger])
                continue

            if record['type'] == 'account_credited':
                if record['account'] in watch_list or record.get('asset_issuer') in watch_list:
                    # account_credited
                    # 'id': '0193165308029046787-0000000001', 'paging_token': '193165308029046787-1', 'account': 'GBVOXZ3W3ECRPABUNXAW6UWZZ7D7MOW5RQZWBKW3NJZC33JEKO55LXXD',
                    # 'type': 'account_credited', 'type_i': 2, 'created_at': '2023-02-16T14:50:53Z', 'asset_type': 'credit_alphanum12', 'asset_code': 'GOLDRESERVE',
                    # 'asset_issuer': 'GBVOXZ3W3ECRPABUNXAW6UWZZ7D7MOW5RQZWBKW3NJZC33JEKO55LXXD', 'amount': '2427.0000000'}
                    op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                    result.append([op_date, record['type'], record['amount'],
                                   record.get('asset_code', 'XLM'), None, None, None, record.get('account'), None, '',
                                   record['paging_token'], ledger])
                continue

            if record['type'] == 'trade':
                if record['account'] in watch_list or record['seller'] in watch_list or record.get(
                        'sold_asset_issuer') in watch_list or record.get('bought_asset_issuer') in watch_list:
                    # trade
                    # 'id': '0193165308029235201-0000000001', 'paging_token': '193165308029235201-1', 'account': 'GBKGNJW7NYSHKFR3RQECSSB2ZD74SVCAOOJEUINPNK3Q2S5JDS3FFMGX',
                    # 'type': 'trade', 'type_i': 33, 'created_at': '2023-02-16T14:50:53Z', 'seller': 'GDXID5C7CB3HRT7OHPNTYO2A53UUQB7EPKTZAMV3HTOPKE5JYJFT2P7P',
                    # 'offer_id': '1186493974', 'sold_amount': '690.8303426', 'sold_asset_type': 'credit_alphanum4', 'sold_asset_code': 'EURV',
                    # 'sold_asset_issuer': 'GDB6ZOJ46MDSERVTH2B7P6C4LEAWU3UDJZLPUFERROEDV774U4AQIG5G', 'bought_amount': '737.1159935', 'bought_asset_type': 'credit_alphanum4',
                    # 'bought_asset_code': 'USDV', 'bought_asset_issuer': 'GDB6ZOJ46MDSERVTH2B7P6C4LEAWU3UDJZLPUFERROEDV774U4AQIG5G'}
                    op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                    result.append([op_date, record['type'], record['sold_amount'],
                                   record.get('sold_asset_code', 'XLM'), record['bought_amount'],
                                   record.get('bought_asset_code', 'XLM'), record.get('seller'), record.get('account'),
                                   None, '', record['paging_token'], ledger])
                continue
            if record['type'] == 'claimable_balance_claimed':
                if record['account'] in watch_list:
                    # claimable_balance_claimed
                    # 'id': '0193165308029046786-0000000001', 'paging_token': '193165308029046786-1', 'account': 'GCHGRZLYXNTMRIICT2RK6OMABNP7RSNWL7GQCI5MKH5YGOVMUUWTPNGG',
                    # 'type': 'claimable_balance_claimed', 'type_i': 52, 'created_at': '2023-02-16T14:50:53Z', 'asset': 'GOLDRESERVE:GBVOXZ3W3ECRPABUNXAW6UWZZ7D7MOW5RQZWBKW3NJZC33JEKO55LXXD',
                    # 'balance_id': '00000000bbd6448ce50c7ae88ac7237fb3e83f6ca9b0326093de06508080d9cccf96c460', 'amount': '2427.0000000'}
                    op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                    result.append([op_date, record['type'], record['amount'],
                                   record['asset'].split(':')[0], None, None, None, record.get('account'), None, '',
                                   record['paging_token'], ledger])
                continue
            if record['type'] in ('trustline_created', 'trustline_removed', 'trustline_updated'):
                if record['account'] in watch_list or record.get('asset_issuer') in watch_list:
                    #
                    #                 'id': '0204586519423287297-0000000001', 'paging_token': '204586519423287297-1',
                    #                 'account': 'GAD5AXOFSGNY2RXBML3GM3F5KVNPD23GVOETGPZ4SDG3YUGUS6VHFTYN', 'type': '',
                    #                 'type_i': 20, 'created_at': '2023-08-13T09:01:33Z', 'asset_type': 'credit_alphanum4',
                    #                 'asset_code': 'USDT', 'asset_issuer': 'GDH5GBPOIFMNH3IMTVINEPTPCNF6MI4CXRSZNA2S3BEUY7KPBIPST6VU',
                    # 'limit': '922337203685.4775807'}
                    op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                    result.append([op_date, record['type'], record['limit'],
                                   record.get('asset_code', 'XLM'), None, None, None, record.get('account'), None, '',
                                   record['paging_token'], ledger])
                    if record.get('type') in (
                            'trustline_created', 'trustline_removed'):  # trustline_created notyfication
                        result.append([op_date, record['type'], record['limit'], record.get('asset_code', 'XLM'), None,
                                       None, None, record.get('asset_issuer'), None, '',
                                       record['paging_token'] + 'x', ledger])

                continue
            if record['type'] in ('data_created', 'data_removed', 'data_updated'):
                if record['account'] in watch_list:
                    #          'id': '0204588950375407617-0000000001', 'paging_token': '204588950375407617-1',
                    #          'account': 'GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI', 'type': 'data_created', 'type_i': 40,
                    #          'created_at': '2023-08-13T10:00:30Z', 'name': 'mtl_delegate',
                    #          'value': 'R0RMVEg0S0tNQTRSMkpHS0E3WEtJNURMSEpCVVQ0MkQ1UkhWSzZTUzZZSFpaTEhWTENXSkFZWEk='
                    op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                    data_value = decode_data_value(record['value']) if record.get('value') else None
                    result.append([op_date, record['type'], None,
                                   record.get('name'), None, data_value, None, record.get('account'), None, '',
                                   record['paging_token'], ledger])
                    # if len(data_value) == 56:

                continue
        except Exception as e:
            logger.error(f"{type(e).__name__}: {e}")

        logger.info(f"{record['type']}, {record}")  ##

    return result


if __name__ == "__main__":
    logger.add("logs/check_ledger.log", rotation="1 MB", level="WARNING")
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    asyncio.run(extra_run())
