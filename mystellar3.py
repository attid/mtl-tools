import csv
import random
from datetime import date

import jsonpickle

from fb import get_watch_list
from mystellar import *


def save_transactions2(account_id):
    url = random.choice(['https://horizon.stellar.org', 'https://horizon.stellar.org'])
    print(url)
    cb_cb = Server(horizon_url=url).transactions().for_account(account_id).limit(
        200).order(False)
    transactions = []
    i = 0
    records = cb_cb.call()
    while len(records['_embedded']['records']) > 0:
        for record in records['_embedded']['records']:
            xdr = record['envelope_xdr']
            print(record['hash'])
            # if FeeBumpTransactionEnvelope.is_fee_bump_transaction_envelope(xdr):
            #    print(record['hash'])

            transaction = load_xdr(xdr)
            for operation in transaction.transaction.operations:
                op = json.loads(jsonpickle.encode(operation))
                op['transaction_hash'] = record['hash']
                op['date'] = record['created_at']
                op['source'] = op['source']['account_id'] if op['source'] else record['source_account']
                op['memo'] = record.get('memo', '')
                transactions.append(op)
        records = cb_cb.next()
        i += 1
        print(i)

    with open(f"{account_id}.json", "w") as fp:
        json.dump(transactions, fp, indent=2)
    #############################
    # with open('transactions.json', 'r', encoding='UTF-8') as fp:
    #    data = json.load(fp)
    # print(data)


def save_transactions3(account_id):
    with open(f'{account_id}.json', 'r', encoding='UTF-8') as fp:
        data = json.load(fp)
    operation_list = [
        ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо']]
    for operation in data:
        # date \ name \ sum \ code \ sum2 \ code2 \ source \ dest \hash \ memo
        op_name = operation['py/object'].split('.')[-1]
        source = operation.get('source', 'xz')
        # "date": "2021-04-23T07:36:53Z",
        op_date = datetime.strptime(operation['date'], '%Y-%m-%dT%H:%M:%SZ')
        if op_name == 'CreateAccount':
            operation_list.append([op_date, op_name, operation['starting_balance'], 'XLM', None, None,
                                   source, None, operation['transaction_hash'], operation['memo']])
            continue
        if op_name in ('ChangeTrust', 'ManageSellOffer', 'SetOptions', 'ManageBuyOffer', 'CreateClaimableBalance',
                       'CreatePassiveSellOffer', 'ManageData', 'ClaimClaimableBalance', 'AccountMerge'):
            continue
        if op_name == 'Payment':
            if account_id in (source, operation['destination']['account_id']):
                operation_list.append(
                    [op_date, op_name, operation['amount'].replace('.', ','), operation['asset']['code'], None, None,
                     source, operation['destination']['account_id'], operation['transaction_hash'],
                     operation['memo']])
            continue
        if op_name == 'PathPaymentStrictSend':
            if account_id in (source, operation['destination']['account_id']):
                operation_list.append([op_date, op_name, operation['send_amount'].replace('.', ','),
                                       operation['send_asset']['code'],
                                       operation['dest_min'].replace('.', ','), operation['dest_asset']['code'],
                                       source, operation['destination']['account_id'], operation['transaction_hash'],
                                       operation['memo']])
            continue
        if op_name == 'PathPaymentStrictReceive':
            if account_id in (source, operation['destination']['account_id']):
                operation_list.append([op_date, op_name, operation['send_max'].replace('.', ','),
                                       operation['send_asset']['code'],
                                       operation['dest_amount'].replace('.', ','), operation['dest_asset']['code'],
                                       source, operation['destination']['account_id'], operation['transaction_hash'],
                                       operation['memo']])
            continue

        print(operation)
        raise ValueError(
            f"Error. {operation['py/object']}\n{operation}"
        )

    with open(f'{account_id}.csv', 'w') as fp:
        writer = csv.writer(fp, delimiter=';')
        writer.writerows(operation_list)

    # transaction['date'] = datetime.datetime.strptime(transaction['date'], '%Y-%m-%dT%H:%M:%S.%fZ')
    # transaction['date'] = transaction['date'].strftime('%Y-%m-%d %H:%M:%S')


def save_trade(account_id, need_return=False, asset_code=None):
    operation_list = [
        ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо']]
    cb_cb = Server(horizon_url="https://horizon.stellar.org").effects().for_account(account_id).limit(
        200).order(False)
    i = 0
    records = cb_cb.call()
    while len(records['_embedded']['records']) > 0:
        for record in records['_embedded']['records']:
            op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            if record['type'] in (
                    'account_created', 'signer_created', 'signer_removed', 'account_credited', 'signer_updated',
                    'account_thresholds_updated', 'account_debited', 'trustline_created', 'account_removed',
                    'claimable_balance_sponsorship_created', 'claimable_balance_sponsorship_removed',
                    'account_inflation_destination_updated', 'liquidity_pool_trade', 'liquidity_pool_withdrew',
                    'claimable_balance_claimant_created', 'trustline_removed', 'liquidity_pool_deposited',
                    'claimable_balance_created', 'liquidity_pool_created', 'liquidity_pool_removed', 'data_created',
                    'account_home_domain_updated', 'data_updated', 'data_removed', 'trustline_updated'):
                continue
            # {'_links': {'operation': {'href': 'https://horizon.stellar.org/operations/171157199819792385'}, 'succeeds': {'href': 'https://horizon.stellar.org/effects?order=desc&cursor=171157199819792385-1'}, 'precedes': {'href': 'https://horizon.stellar.org/effects?order=asc&cursor=171157199819792385-1'}}, 'id': '0171157199819792385-0000000001', 'paging_token': '171157199819792385-1', 'account': 'GB7NLVMVC6NWTIFK7ULLEQDF5CBCI2TDCO3OZWWSFXQCT7OPU3P4EOSR', 'type': 'trade', 'type_i': 33, 'created_at': '2022-03-02T10:10:33Z', 'seller': 'GAKVQQD5HFSSXWN3E3K6QL573NQG5GJNFKW52RY6FPXH3CYVVADCDH4U', 'offer_id': '938800231', 'sold_amount': '30.0000000', 'sold_asset_type': 'credit_alphanum12', 'sold_asset_code': 'MTLand', 'sold_asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V', 'bought_amount': '30.0000000', 'bought_asset_type': 'credit_alphanum12', 'bought_asset_code': 'EURMTL', 'bought_asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}
            if record['type'] == 'trade':
                if asset_code is None or asset_code in (
                        record.get('sold_asset_code', 'XLM'), record.get('bought_asset_code', 'XLM')):
                    operation_list.append(
                        [op_date, 'trade-sale', record['sold_amount'].replace('.', ','),
                         record.get('sold_asset_code', 'XLM'),
                         record['bought_amount'].replace('.', ','), record.get('bought_asset_code', 'XLM'),
                         record['account'], record['seller']])
                continue
            # {'id': '0189755245730918401-0000000001', 'paging_token': '189755245730918401-1', 'account': 'GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7', 'type': 'claimable_balance_claimed', 'type_i': 52, 'created_at': '2022-12-25T19:59:04Z', 'asset': 'SATSMTL:GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V', 'balance_id': '0000000026c09b4d22cddd22b51d0240a88f0dd46bfe40580461a5b2c3f5a1a2176ab4ad', 'amount': '1.0000000'}
            if record['type'] == 'claimable_balance_claimed':
                token = str(record['asset'])[0:str(record['asset']).find(':')]
                if asset_code is None or asset_code == token:
                    operation_list.append(
                        [op_date, record['type'], record['amount'].replace('.', ','), token, None, None, None,
                         record['account']])
                continue
            raise ValueError(
                f"Error. {record['type']}\n{record}"
            )
        records = cb_cb.next()
        i += 1
        print(i)

    if need_return:
        return operation_list
    else:
        with open(f'{account_id}-trade.csv', 'w') as fp:
            writer = csv.writer(fp, delimiter=';')
            writer.writerows(operation_list)


def save_trade_token(asset: Asset):
    operation_list = [
        ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо']]
    address_list = []
    # s
    cb_cb = Server(horizon_url="https://horizon.stellar.org").offers().for_buying(asset).limit(
        200).order(False)
    i = 0
    records = cb_cb.call()
    while len(records['_embedded']['records']) > 0:
        for record in records['_embedded']['records']:
            address_list.append(record['seller'])
        records = cb_cb.next()
        i += 1
        print(i)
    # b
    cb_cb = Server(horizon_url="https://horizon.stellar.org").offers().for_selling(asset).limit(
        200).order(False)
    i = 0
    records = cb_cb.call()
    while len(records['_embedded']['records']) > 0:
        for record in records['_embedded']['records']:
            address_list.append(record['seller'])
        records = cb_cb.next()
        i += 1
        print(i)

    address_list = list(set(address_list))

    for address in address_list:
        operation_list.extend(save_trade(address, True, asset_code=asset.code))

        with open(f'{asset.code}-trade.csv', 'w') as fp:
            writer = csv.writer(fp, delimiter=';')
            writer.writerows(operation_list)


def get_ledger0(ledger):
    operations = Server(horizon_url="https://horizon.stellar.org").operations().for_ledger(ledger).limit(200).call()
    effects = Server(horizon_url="https://horizon.stellar.org").effects().for_ledger(ledger).limit(200).call()
    watch_list = get_watch_list()
    my_data = []
    print(watch_list)
    for record in operations['_embedded']['records']:
        # record = {'_links': {'self': {'href': 'https://horizon.stellar.org/operations/189837554483662854'}, 'transaction': {'href': 'https://horizon.stellar.org/transactions/6261e003140a9e013513c818510066c19eb8f5fbb7bd06c57dc8ce7a3476df62'}, 'effects': {'href': 'https://horizon.stellar.org/operations/189837554483662854/effects'}, 'succeeds': {'href': 'https://horizon.stellar.org/effects?order=desc&cursor=189837554483662854'}, 'precedes': {'href': 'https://horizon.stellar.org/effects?order=asc&cursor=189837554483662854'}}, 'id': '189837554483662854', 'paging_token': '189837554483662854', 'transaction_successful': True, 'source_account': 'GBQQTVNOJFGLDOU3DZMULOB2EVIVH2ZY2PDAHYOLH3L2FY7XHCNHQ46C', 'type': 'manage_sell_offer', 'type_i': 3, 'created_at': '2022-12-27T02:28:02Z', 'transaction_hash': '6261e003140a9e013513c818510066c19eb8f5fbb7bd06c57dc8ce7a3476df62', 'amount': '0.0000005', 'price': '0.0510000', 'price_r': {'n': 51, 'd': 1000}, 'buying_asset_type': 'credit_alphanum4', 'buying_asset_code': 'HBAR', 'buying_asset_issuer': 'GAY6LGJIUB6YOLBQ3NTYXQNRZCXVNTCTHBFXO3Z7AAKYACOPYFMDVS2L', 'selling_asset_type': 'native', 'offer_id': '0'}
        if record['type'] in ('manage_sell_offer', 'manage_buy_offer', 'set_options', 'change_trust', 'manage_data',
                              'create_claimable_balance', 'create_Passive_Sell_Offer', 'claim_claimable_balance',
                              'account_merge', 'allow_trust', 'clawback', 'liquidity_pool_deposit',
                              'begin_sponsoring_future_reserves', 'end_sponsoring_future_reserves'):
            continue

        if record['type'] in ('payment', 'path_payment_strict_send', 'path_payment_strict_receive', 'create_account'):
            print(record.get('source_account'), record.get('from'), record.get('to'))
            if record.get('source_account') in watch_list or record.get('from') in watch_list or record.get(
                    'to') in watch_list or record.get('asset_issuer') in watch_list or record.get(
                'claimant') in watch_list:
                op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо']]
                my_data.append(
                    [op_date, record['type'], record['amount'].replace('.', ','), record.get('asset_code', 'XLM'), None,
                     None,
                     record.get('from'), record.get('to'), record['transaction_hash'],
                     ''])
            continue
        print(record['type'], record)
    print(my_data)


watch_list = get_watch_list()


async def get_ledger(name, queue):
    while True:
        try:
            ledger = await queue.get()
            print(f'{name} {ledger} start')

            # check ledger
            if fb.execsql1('select count(*) from t_ledgers l where l.ledger = ?', (ledger,), 0) == 0:
                client = AiohttpClient(request_timeout=3 * 60)
                # url = random.choice(['https://horizon.stellar.org', 'https://horizon.publicnode.org'])
                url = 'https://horizon.publicnode.org'
                url = 'https://horizon.stellar.org'

                async with ServerAsync(
                        horizon_url=url, client=client
                ) as server:
                    call_builder = server.effects().for_ledger(ledger).limit(200)
                    effects = await call_builder.call()
                    while len(effects['_embedded']['records']) > 0:
                        data = decode_records(effects['_embedded']['records'], ledger)
                        if len(data) > 0:
                            # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token', 'ledger']]]
                            print(data)
                            fb.many_insert(
                                "insert into t_operations (dt, operation, amount1, code1, amount2, code2, from_account, for_account, transaction_hash, memo, id, ledger) "
                                "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                data)
                        effects = await call_builder.next()

                fb.execsql('insert into t_ledgers(ledger) values (?)', (ledger,))
            # Сообщение очереди, для обработки "рабочего элемента".
            queue.task_done()
        except Exception as ex:
            print(ex)
            await asyncio.sleep(60)

        print(f'{name} {ledger} end')


async def run_ledgers():
    # with open('report.json', 'r', encoding='UTF-8') as fp:
    #    report: dict = json.load(fp)
    logger.info(datetime.now().strftime('%d.%m.%Y %H:%M:%S'))

    # create queue
    queue = asyncio.Queue()

    # put data 44974803  --  44270000 - 45393264
    for key in range(45406800, 45407000):
        queue.put_nowait(key)

    # create task
    tasks = []
    for i in range(10):
        task = asyncio.create_task(get_ledger(f'worker-{i}', queue))
        tasks.append(task)

    # wait end data
    await queue.join()

    # cancel task
    for task in tasks:
        task.cancel()
    # wait
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(datetime.now().strftime('%d.%m.%Y %H:%M:%S'))


async def load_effects(account):
    # Получаем список операций по аккаунту
    client = AiohttpClient(request_timeout=3 * 60)
    url = random.choice(['https://horizon.stellar.org', 'https://horizon.publicnode.org'])

    async with ServerAsync(
            horizon_url=url, client=client
    ) as server:
        call_builder = server.effects().for_account(account).limit(200).order()
        effects = await call_builder.call()
        while len(effects['_embedded']['records']) > 0:
            data = decode_records(effects['_embedded']['records'], None)
            if len(data) > 0:
                # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token', 'ledger']]]
                #print(data)
                for record in data:
                    if record[0].date() < date(2022, 12, 31):
                        return
                    try:
                        fb.execsql(
                            "update or insert into t_operations (dt, operation, amount1, code1, amount2, code2, from_account, for_account, transaction_hash, memo, id, ledger) "
                            "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) matching (id)",
                            record)
                        print(record)
                    except Exception as ex:
                        print('ex')
            effects = await call_builder.next()


if __name__ == "__main__":
    #for a in watch_list:
    #    asyncio.run(load_effects(a))
    asyncio.run(run_ledgers())
    pass
