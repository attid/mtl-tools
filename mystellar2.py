import asyncio
import copy

from stellar_sdk import Network, Server, TransactionBuilder, Asset, Account
import json, math, mystellar

from settings import base_fee, private_sign


# https://stellar-sdk.readthedocs.io/en/latest/

# public_mtl = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
# public_fond = "GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS"
# public_distrib = "GB7NLVMVC6NWTIFK7ULLEQDF5CBCI2TDCO3OZWWSFXQCT7OPU3P4EOSR"
# public_collector = "GDASYWP6F44TVNJKZKQ2UEVZOKTENCJFTWVMP6UC7JBZGY4ZNB6YAVD4"
# public_bod_eur = "GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW"
# public_bod = "GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH"
# public_div = "GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ"


async def cmd_get_new_vote_mtlcity():
    divider = 1000
    city_asset = Asset("MTLCITY", mystellar.public_city)

    cityarr = []
    mtl_vote = await mystellar.cmd_gen_mtl_vote_list()

    #################
    server = Server(horizon_url="https://horizon.stellar.org")
    response = server.assets().for_code('MTL').for_issuer(mystellar.public_issuer).limit(200).call()

    json_dump = json.dumps(response)
    response_json = json.loads(json_dump)
    mtlamount = response_json["_embedded"]["records"][0]["amount"]
    mtlamount = int(mtlamount[0:mtlamount.find('.')])
    #################
    server = Server(horizon_url="https://horizon.stellar.org")
    response = server.accounts().for_asset(city_asset).limit(200).call()

    json_dump = json.dumps(response)
    response_json = json.loads(json_dump)
    accounts = response_json["_embedded"]["records"]
    for account in accounts:
        balances = account["balances"]
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == "MTLCITY":
                    bls = balance["balance"]
                    bli = int(bls[0:bls.find('.')])
                    lg = round(math.log2((bli + 0.001) / divider)) + 1
                    if account["account_id"] == mystellar.public_fund:
                        cityinfond = bli
                    else:  # fond dont have voce
                        cityarr.append([account["account_id"], bli, lg, 0])

    cityarr.sort(key=lambda k: k[1], reverse=True)
    # 2
    bigarr = []

    for arr in mtl_vote:
        if int(arr[1]) > 100:
            bigarr.append(arr)
    bigarr.sort(key=lambda k: k[1], reverse=True)
    # 3
    # add big mtl to city
    for arr in bigarr:
        retrieved_elements = list(filter(lambda x: arr[0] == x[0], cityarr))
        if len(retrieved_elements) == 0:
            cityarr.append([arr[0], 0, 0, 0])
    # add fond tocken to users
    for arr in cityarr:
        retrieved_elements = list(filter(lambda x: arr[0] == x[0], bigarr))
        if len(retrieved_elements) > 0:
            # print(retrieved_elements)
            # print(f'{arr[1]} lalala {arr[1] + (cityinfond/mtlamount*retrieved_elements[0][1])}')
            arr[1] = arr[1] + (cityinfond / mtlamount * retrieved_elements[0][1])
    # 4
    bigarr = []

    for arr in cityarr:
        if int(arr[1]) > 100:
            bigarr.append([arr[0], int(arr[1]), round(math.log2(int(arr[1]) / divider)) + 1, 0])
    bigarr.sort(key=lambda k: k[1], reverse=True)
    # 5
    # узнать кто в подписантах
    server = Server(horizon_url="https://horizon.stellar.org")
    source_account = server.load_account(mystellar.public_city)
    mtlcitysequence = source_account.sequence

    sg = source_account.load_ed25519_public_key_signers()
    for s in sg:
        bfound = False
        # print(s)
        for arr in bigarr:
            if arr[0] == s.account_id:
                arr[3] = s.weight
                bfound = True
        if bfound == False:
            bigarr.append([s.account_id, 0, 0, s.weight])
    # 6
    # delete blecklist user
    bl = mystellar.cmd_getblacklist()
    for arr in bigarr:
        if bl.get(arr[0]) != None:
            bigarr.remove(arr)
        # retrieved_elements = list(filter(lambda x: arr[0] == x[1], bl))
        # if len(retrieved_elements) > 0:
        #    bigarr.remove(arr)
        # print(f'delete {arr}')

    # up user to delete
    bigarr2 = []
    delcount = 0

    for arr in bigarr:
        if (int(arr[2]) == 0) & (int(arr[3]) > 0):
            bigarr2.append(arr)
            bigarr.remove(arr)
            delcount += 1

    bigarr2.extend(bigarr)

    while len(bigarr2) > 20 + delcount:
        arr = bigarr2.pop(20 + delcount)
        if arr[3] > 0:
            delcount += 1
            bigarr2.insert(0, [arr[0], 0, 0, arr[3]])
    bigarr = bigarr2

    # 7
    root_account = Account(mystellar.public_city, sequence=mtlcitysequence)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    ithreshold = 0

    for arr in bigarr:
        if (int(arr[2]) != int(arr[3])):
            transaction.append_ed25519_public_key_signer(arr[0], int(arr[2]))
        ithreshold += int(arr[2])

    ithreshold = ithreshold // 2 + 1

    transaction.append_set_options_op(low_threshold=ithreshold, med_threshold=ithreshold, high_threshold=ithreshold)

    transaction = transaction.build()
    xdr = transaction.to_xdr()
    result = [xdr]
    # print(f"xdr: {xdr}")
    return result


def gen_vote_xdr(public_key, vote_list, transaction=None, source=None, remove_master=False):
    # узнать кто в подписантах
    server = Server(horizon_url="https://horizon.stellar.org")
    source_account = server.load_account(public_key)

    sg = source_account.load_ed25519_public_key_signers()

    for s in sg:
        bfound = False
        for arr in vote_list:
            if arr[0] == s.account_id:
                arr[3] = s.weight
                bfound = True
        if (bfound == False) and (s.account_id != public_key):
            vote_list.append([s.account_id, 0, 0, s.weight])

    vote_list.sort(key=lambda k: k[2], reverse=True)

    # up user to delete
    tmp_list = []
    del_count = 0

    for arr in vote_list:
        if (int(arr[2]) == 0) & (int(arr[3]) > 0):
            tmp_list.append(arr)
            vote_list.remove(arr)
            del_count += 1

    tmp_list.extend(vote_list)

    while len(tmp_list) > 20 + del_count:
        arr = tmp_list.pop(20 + del_count)
        if arr[3] > 0:
            del_count += 1
            tmp_list.insert(0, [arr[0], 0, 0, arr[3]])

    vote_list = tmp_list
    # 5
    server = Server(horizon_url="https://horizon.stellar.org")
    source_account = server.load_account(public_key)
    root_account = Account(public_key, sequence=source_account.sequence)
    if transaction is None:
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
        transaction.set_timeout(60 * 60 * 48)
    threshold = 0

    for arr in vote_list:
        if int(arr[2]) != int(arr[3]):
            transaction.append_ed25519_public_key_signer(arr[0], int(arr[2]), source=source)
        threshold += int(arr[2])

    threshold = threshold // 2 + 1

    if remove_master:
        transaction.append_set_options_op(low_threshold=threshold, med_threshold=threshold, high_threshold=threshold,
                                          source=source, master_weight=0)
    else:
        transaction.append_set_options_op(low_threshold=threshold, med_threshold=threshold, high_threshold=threshold,
                                          source=source)

    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")

    return xdr


async def cmd_get_new_vote_all_mtl(public_key, remove_master=False):
    if len(public_key) > 10:
        vote_list = await mystellar.cmd_gen_mtl_vote_list()
        result = [gen_vote_xdr(public_key, vote_list, remove_master=remove_master, source=public_key)]
    else:
        vote_list = await mystellar.cmd_gen_mtl_vote_list()
        vote_list1 = copy.deepcopy(vote_list)
        vote_list2 = copy.deepcopy(vote_list)
        vote_list3 = copy.deepcopy(vote_list)
        vote_list4 = copy.deepcopy(vote_list)
        vote_list5 = copy.deepcopy(vote_list)
        vote_list6 = copy.deepcopy(vote_list)
        # print(vote_list)
        result = []
        transaction = TransactionBuilder(
            source_account=Server(horizon_url="https://horizon.stellar.org").load_account(mystellar.public_issuer),
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
        sequence = transaction.source_account.sequence
        xdr = gen_vote_xdr(mystellar.public_issuer, vote_list, transaction)
        xdr = gen_vote_xdr(mystellar.public_adm, vote_list2, transaction, mystellar.public_adm, remove_master=True)
        xdr = gen_vote_xdr(mystellar.public_fund_defi, vote_list3, transaction, mystellar.public_fund_defi,
                           remove_master=True)
        xdr = gen_vote_xdr(mystellar.public_fund_city, vote_list4, transaction, mystellar.public_fund_city,
                           remove_master=True)
        xdr = gen_vote_xdr(mystellar.public_fund_mabiz, vote_list5, transaction, mystellar.public_fund_mabiz,
                           remove_master=True)
        # return sequence because every build inc number
        transaction.source_account.sequence = sequence
        transaction.set_timeout(60 * 60 * 48)
        xdr = gen_vote_xdr(mystellar.public_pawnshop, vote_list6, transaction, mystellar.public_pawnshop)
        result.append(xdr)

    # print(gen_vote_xdr(public_new,vote_list2))

    return result


async def update_multi_sign(public_key, second_master_key=None, only_show=False):
    # get data
    fund_account = await mystellar.stellar_get_account(mystellar.public_issuer)
    print(fund_account['signers'])
    threshold = max(fund_account['thresholds']['low_threshold'], fund_account['thresholds']['med_threshold'],
                    fund_account['thresholds']['high_threshold'])
    print(threshold)
    new_signers = []
    for signer in fund_account['signers']:
        if not signer['key'] in (mystellar.public_issuer, mystellar.public_itolstov):
            new_signers.append([signer['key'], signer['weight']])

    new_signers.sort(key=lambda k: k[1], reverse=True)
    print(new_signers)
    print(len(new_signers))
    if second_master_key:
        if len(new_signers) > 18:
            new_signers.pop(18)
        print(new_signers)
        new_signers.append([second_master_key, threshold + 1])

    new_signers.append([mystellar.public_sign, threshold + 1])

    print(new_signers)
    new_signers_dic = {}
    for signer in new_signers:
        new_signers_dic[signer[0]] = signer[1]

    user_account = await mystellar.stellar_get_account(public_key)
    exist_signers_dic = {}
    for signer in user_account['signers']:
        if not signer['key'] in (public_key,):
            exist_signers_dic[signer['key']] = signer['weight']

    update_signers = []
    # remove bad
    for signer in exist_signers_dic:
        if not signer in new_signers_dic:
            update_signers.append([signer, 0])

    # update other
    for signer in new_signers_dic:
        if signer in exist_signers_dic:
            if new_signers_dic[signer] != exist_signers_dic[signer]:
                update_signers.append([signer, new_signers_dic[signer]])
        else:
            update_signers.append([signer, new_signers_dic[signer]])

    print(update_signers)
    if len(update_signers) > 0:
        transaction = TransactionBuilder(
            source_account=Server(horizon_url="https://horizon.stellar.org").load_account(public_key),
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
            base_fee=base_fee)
        for signer in update_signers:
            transaction.append_ed25519_public_key_signer(account_id=signer[0], weight=signer[1])
        transaction.append_set_options_op(high_threshold=threshold, med_threshold=threshold, low_threshold=threshold)
        transaction.set_timeout(60 * 60)

        transaction = transaction.build()
        if only_show:
            xdr = transaction.to_xdr()
            print(f"xdr: {xdr}")
        else:
            transaction.sign(private_sign)
            await mystellar.stellar_async_submit(transaction.to_xdr())


async def update_multi_sign_old(account, only_show=False):
    from stellar_sdk import TransactionEnvelope
    server = Server(horizon_url="https://horizon.stellar.org")
    account_exchange = server.load_account(mystellar.public_sign)

    threshold = 0
    xdr = await cmd_get_new_vote_all_mtl(account)
    transaction = TransactionEnvelope.from_xdr(xdr[0], network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)

    for operation in transaction.transaction.operations:
        if operation.high_threshold:
            threshold = operation.high_threshold
        if operation.signer and operation.signer.signer_key.encoded_signer_key in (
                mystellar.public_itolstov, mystellar.public_sign):
            transaction.transaction.operations.remove(operation)
    for operation in transaction.transaction.operations:
        if operation.high_threshold:
            threshold = operation.high_threshold
        if operation.signer and operation.signer.signer_key.encoded_signer_key in (
                mystellar.public_itolstov, mystellar.public_sign):
            transaction.transaction.operations.remove(operation)

    if threshold > 0 and len(transaction.transaction.operations) > 2:
        transaction2 = TransactionBuilder(source_account=account_exchange,
                                          network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                          base_fee=base_fee)
        transaction2.append_ed25519_public_key_signer(account_id=mystellar.public_sign, weight=threshold * 2)
        # print(transaction.transaction)
        transaction2.set_timeout(60 * 60)
        # print(transaction.transaction)

        transaction.transaction.operations.insert(0, transaction2.operations[0])

        if only_show:
            xdr = transaction.to_xdr()
            print(f"xdr: {xdr}")
        else:
            transaction.sign(private_sign)
            server.submit_transaction(transaction)


async def update_multi_sign_all():
    for bot in mystellar.exchange_bots:
        await update_multi_sign(bot)
    await update_multi_sign(mystellar.public_fire)
    await update_multi_sign(mystellar.public_bod_eur)
    await update_multi_sign(mystellar.public_boss)


async def get_required_signers(public_key):
    # Шаг 1: Получаем данные по адресу public_key и запоминаем master ключи
    user_account = await mystellar.stellar_get_account(public_key)
    master_keys = {}
    for key, value in user_account['data'].items():
        if key.startswith('master_key_'):
            key_parts = key.split('_')
            weight = int(key_parts[2])
            master_keys[mystellar.decode_data_value(value)] = weight

    # Если master_keys пуст, добавляем public_key с весом 15
    if not master_keys:
        master_keys[public_key] = 15

    # Шаг 2: Получаем всех подписантов mystellar.public_fund и проверяем наличие существующих подписей
    fund_account = await mystellar.stellar_get_account(mystellar.public_issuer)
    new_signers = []
    # existing_signers = set([signer['key'] for signer in user_account['signers']])
    for signer in fund_account['signers']:
        if signer['key'] in master_keys:
            pass
        elif signer['key'] == mystellar.public_issuer:
            pass
        else:
            new_signers.append([signer['key'], signer['weight']])

    # Шаг 3: Удаляем адреса из master_keys
    new_signers = [signer for signer in new_signers if signer[0] not in master_keys]

    # Сортируем new_signers по числу голосов
    new_signers.sort(key=lambda x: x[1], reverse=True)

    # Удаляем самые слабые голоса, чтобы общее количество записей не превышало 20
    while len(new_signers) + len(master_keys) > 20:
        new_signers.pop()

    # Возвращаем словарь с требуемыми подписантами и их весами
    required_signers = {key: 1 for key, _ in new_signers}
    required_signers.update(master_keys)

    return required_signers


async def update_signers_on_blockchain(public_key, required_signers):
    # Шаг 1: Получаем данные по адресу public_key и сохраняем текущих подписантов
    user_account = await mystellar.stellar_get_account(public_key)
    current_signers = {signer['key']: signer['weight'] for signer in user_account['signers']}
    current_signers.pop(public_key)

    # Шаг 2: Готовим транзакцию
    transaction = TransactionBuilder(
        source_account=Server(horizon_url="https://horizon.stellar.org").load_account(public_key),
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=mystellar.base_fee)

    # Шаг 3: Добавляем и удаляем подписантов
    for key, weight in current_signers.items():
        if key not in required_signers:
            transaction.append_ed25519_public_key_signer(account_id=key, weight=0)

    for key, weight in required_signers.items():
        if key not in current_signers:
            if key == public_key:
                transaction.append_set_options_op(master_weight=weight)
            else:
                transaction.append_ed25519_public_key_signer(account_id=key, weight=weight)

    if user_account['thresholds']['high_threshold'] < 15:
        transaction.append_set_options_op(high_threshold=15, med_threshold=15, low_threshold=15)

    # Устанавливаем пороги и таймаут
    transaction.set_timeout(60 * 60)

    # Отправляем транзакцию
    transaction = transaction.build()
    if len(transaction.transaction.operations) > 0:
        return transaction.to_xdr()


async def create_many():
    new_account = 'GCOJHUKGHI6IATN7AIEK4PSNBPXIAIZ7KB2AWTTUCNIAYVPUB2DMCITY'
    old_account = 'GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3'
    transaction = TransactionBuilder(
        source_account=Server(horizon_url="https://horizon.stellar.org").load_account(old_account),
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=mystellar.base_fee)
    # Устанавливаем пороги и таймаут
    transaction.set_timeout(60 * 60 * 48)
    # transaction.append_create_account_op(new_account, '100')
    balances = await mystellar.get_balances(old_account, return_assets=True)
    for asset in balances:
        # transaction.append_change_trust_op(asset=asset, source=new_account)
        if balances.get(asset, 0) > 0:
            transaction.append_payment_op(asset=asset, destination=new_account, amount=str(balances[asset]),
                                          source=old_account)
        # transaction.append_change_trust_op(asset=asset, source=old_account, limit='0')

    # copy_xdr = transaction.build().to_xdr()
    # узнать кто в подписантах
    server = Server(horizon_url="https://horizon.stellar.org")
    issuer_account = server.load_account(mystellar.public_issuer)

    sg = issuer_account.load_ed25519_public_key_signers()

    # for s in sg:
    #   if s.weight > 0:
    #       transaction.append_ed25519_public_key_signer(s.account_id, s.weight, source=new_account)

    # transaction.append_set_options_op(low_threshold=issuer_account.thresholds.high_threshold,
    #                                 med_threshold=issuer_account.thresholds.high_threshold,
    #                                 high_threshold=issuer_account.thresholds.high_threshold,
    #                                 source=new_account, master_weight=0)
    # transaction.append_account_merge_op(destination=mystellar.public_issuer, source=old_account)

    # new_xdr = mystellar.stellar_add_xdr(copy_xdr, voice_xdr[0])

    return transaction.build().to_xdr()


if __name__ == "__main__":
    # update USDM
    # print(gen_vote_xdr(mystellar.public_usdm, asyncio.run(mystellar.cmd_gen_usdm_vote_list())))

    # print(asyncio.run(create_many()))
    print(asyncio.run(cmd_get_new_vote_all_mtl('')))
    # print(asyncio.run(mystellar.stellar_get_account('GB2ZUCM6YWQET4HHLJKMQP7FGUES4TF32VCUYHVNICGNVISAXBSARGUN')))
    # print(asyncio.run(get_required_signers('GBYH3M3REQM3WQOJY26FYORN23EXY22FWBHVZ74TT5GYOF22IIA7YSOX')))
    # print(asyncio.run(get_required_signers('GB2ZUCM6YWQET4HHLJKMQP7FGUES4TF32VCUYHVNICGNVISAXBSARGUN')))
    # print(asyncio.run(get_required_signers(mystellar.public_itolstov)))
    # print(asyncio.run(update_signers_on_blockchain('GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI',asyncio.run(get_required_signers('GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI')))))
    # print(vote_list)
    # result = [gen_vote_xdr(public_key, vote_list)]
    # print(gen_vote_xdr(mystellar.public_fund))
    # print(asyncio.run(update_multi_sign('GDPHAKGLJ3B56BK4CZ2VMTYEDI6VZ2CTHUHSFAFSPGSTJHZEI3ATOKEN',
    #                                    only_show=True, second_master_key='GCPT3X4FJBMUBR5AIB7SEUQX7HJ4XX3K4TNI2J7WIHMHMFGDMRRJJVWL')))
    pass
