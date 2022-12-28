import copy

from stellar_sdk import Keypair, Network, Server, Signer, TransactionBuilder, Asset, Account, SignerKey, \
    TransactionEnvelope
import json, math, mystellar

from settings import base_fee, private_sign

# https://stellar-sdk.readthedocs.io/en/latest/

#public_mtl = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
#public_fond = "GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS"
#public_distrib = "GB7NLVMVC6NWTIFK7ULLEQDF5CBCI2TDCO3OZWWSFXQCT7OPU3P4EOSR"
#public_collector = "GDASYWP6F44TVNJKZKQ2UEVZOKTENCJFTWVMP6UC7JBZGY4ZNB6YAVD4"
#public_bod_eur = "GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW"
#public_bod = "GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH"
#public_div = "GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ"


def cmd_get_new_vote_mtlcity():
    divider = 1000
    city_asset = Asset("MTLCITY", mystellar.public_city)

    cityarr = []
    mtl_vote = mystellar.cmd_gen_vote_list()

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
    result = []
    result.append(xdr)
    # print(f"xdr: {xdr}")
    return result


def gen_vote_xdr(public_key, vote_list, transaction=None, source=None):
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

    transaction.append_set_options_op(low_threshold=threshold, med_threshold=threshold, high_threshold=threshold,
                                      source=source)

    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")

    return xdr


def cmd_get_new_vote_mtl(public_key):
    if len(public_key) > 10:
        vote_list = mystellar.cmd_gen_vote_list()
        result = [gen_vote_xdr(public_key, vote_list)]
    else:
        vote_list = mystellar.cmd_gen_vote_list()
        vote_list1 = copy.deepcopy(vote_list)
        vote_list2 = copy.deepcopy(vote_list)
        vote_list3 = copy.deepcopy(vote_list)
        vote_list4 = copy.deepcopy(vote_list)
        vote_list5 = copy.deepcopy(vote_list)
        # print(vote_list)
        result = []
        transaction = TransactionBuilder(
            source_account=Server(horizon_url="https://horizon.stellar.org").load_account(mystellar.public_fund),
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
        sequence = transaction.source_account.sequence
        xdr = gen_vote_xdr(mystellar.public_fund, vote_list, transaction)
        xdr = gen_vote_xdr(mystellar.public_issuer, vote_list1, transaction, mystellar.public_issuer)
        xdr = gen_vote_xdr(mystellar.public_distributor, vote_list2, transaction, mystellar.public_distributor)
        xdr = gen_vote_xdr(mystellar.public_competition, vote_list3, transaction, mystellar.public_competition)
        xdr = gen_vote_xdr(mystellar.public_adm, vote_list5, transaction, mystellar.public_adm)
        # return sequence because every build inc number
        transaction.source_account.sequence = sequence
        transaction.set_timeout(60*60*48)
        xdr = gen_vote_xdr(mystellar.public_pawnshop, vote_list4, transaction, mystellar.public_pawnshop)
        result.append(xdr)

    # print(gen_vote_xdr(public_new,vote_list2))

    return result


def update_multi_sign(account, only_show=False):
    from stellar_sdk import TransactionEnvelope
    server = Server(horizon_url="https://horizon.stellar.org")
    account_exchange = server.load_account(mystellar.public_exchange)

    threshold = 0
    xdr = cmd_get_new_vote_mtl(account)
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
        print(transaction.transaction)
        transaction2.set_timeout(60*60)
        print(transaction.transaction)

        transaction.transaction.operations.insert(0, transaction2.operations[0])


        if only_show:
            xdr = transaction.to_xdr()
            print(f"xdr: {xdr}")
        else:
            transaction.sign(private_sign)
            server.submit_transaction(transaction)


def update_multi_sign_all():
    update_multi_sign(mystellar.public_exchange)
    update_multi_sign(mystellar.public_fire)
    update_multi_sign(mystellar.public_bod_eur)
    update_multi_sign(mystellar.public_boss)


if __name__ == "__main__":
    pass
    #update_multi_sign_all()
    #update_multi_sign(mystellar.public_boss)
    # update_multi_sign(mystellar.public_bod_eur)
    # print(cmd_get_new_vote_mtlcity())
