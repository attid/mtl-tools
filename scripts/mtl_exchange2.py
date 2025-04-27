from scripts.mtl_exchange import *

from stellar_sdk import TransactionBuilder, Network

from scripts.update_report import update_mmwb_report


async def move_token(source_account, destination_account, amount: str, asset):
    async with ServerAsync(
            horizon_url=config.horizon_url, client=AiohttpClient()
    ) as st_server:
        # Загрузка аккаунта
        account = await st_server.load_account(source_account)

        # Построение транзакции
        stellar_transaction = TransactionBuilder(source_account=account,
                                                 network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                                 base_fee=base_fee)

        stellar_transaction.append_payment_op(source=source_account,
                                              asset=asset,
                                              amount=amount,
                                              destination=destination_account)

        stellar_transaction.set_timeout(250)
        stellar_transaction = stellar_transaction.build()
        stellar_transaction.sign(get_private_sign())

        # xdr = stellar_transaction.to_xdr()
        # logger.info(f"xdr: {xdr}")

        # Отправка транзакции
        transaction_resp = await st_server.submit_transaction(stellar_transaction)

        return transaction_resp


async def exchange_token(source_account, destination_account, amount: str, source_asset, destination_asset):
    async with ServerAsync(
            horizon_url=config.horizon_url, client=AiohttpClient()
    ) as st_server:
        # Загрузка аккаунта
        account = await st_server.load_account(source_account)

        # Построение транзакции
        stellar_transaction = TransactionBuilder(source_account=account,
                                                 network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                                 base_fee=base_fee)

        stellar_transaction.append_path_payment_strict_send_op(source=source_account,
                                                               destination=destination_account,
                                                               send_asset=source_asset,
                                                               send_amount=amount,
                                                               dest_asset=destination_asset,
                                                               dest_min='1',
                                                               path=stellar_get_receive_path(source_asset, amount,
                                                                                             destination_asset))

        stellar_transaction.set_timeout(250)
        stellar_transaction = stellar_transaction.build()
        stellar_transaction.sign(get_private_sign())

        xdr = stellar_transaction.to_xdr()
        logger.debug(f"xdr: {xdr}")

        # Отправка транзакции
        transaction_resp = await st_server.submit_transaction(stellar_transaction)

        return transaction_resp


async def check_mm(session: Session):
    # balances = await get_balances(MTLAddresses.public_exchange_usdm_xlm)
    # amount = float(balances.get('USDM', 0))
    # if amount > 12000:
    #     amount = str(round(amount - 11000))
    #     await move_token(MTLAddresses.public_exchange_usdm_xlm, MTLAddresses.public_exchange_usdm_usdc,
    #                      amount, MTLAssets.usdm_asset)
    #     db_send_admin_message(session, f'{amount} USDM was moved usdm_xlm - usdm_usdc')
    #     logger.info(f'{amount} USDM was moved usdm_xlm - usdm_usdc')
    #
    # balances = await get_balances(MTLAddresses.public_exchange_usdm_usdc)
    # amount = float(balances.get('USDM', 0))
    # if amount > 20000:
    #     amount = str(round(amount - 19000))
    #     await move_token(MTLAddresses.public_exchange_usdm_usdc, MTLAddresses.public_exchange_eurmtl_usdm,
    #                      amount, MTLAssets.usdm_asset)
    #     db_send_admin_message(session, f'{amount} USDM was moved usdm_usdc - eurmtl_usdm')
    #     logger.info(f'{amount} USDM was moved usdm_usdc - eurmtl_usdm')
    # amount = float(balances.get('USDC', 0))
    # if amount > 12000:
    #     amount = str(round(amount - 11000))
    #     await exchange_token(MTLAddresses.public_exchange_usdm_usdc, MTLAddresses.public_exchange_usdm_xlm,
    #                          amount, MTLAssets.usdc_asset, MTLAssets.xlm_asset)
    #     db_send_admin_message(session, f'{amount} USDC was moved to XLM \n usdm_usdc - usdm_xlm')
    #     logger.info(f'{amount} USDC was moved to XLM \n usdm_usdc - usdm_xlm')

    await update_mmwb_report(session)


async def check_mmwb(session: Session):
    balances = await get_balances(MTLAddresses.public_wallet)
    amount = float(balances.get('USDM', 0))
    if amount < 2000:
        db_send_admin_message(session, f'{amount} USDM bad sum')
        logger.info(f'{amount} USDM bad sum')

    amount = float(balances.get('XLM', 0))
    if amount < 500:
        db_send_admin_message(session, f'{amount} XLM bad sum')
        logger.info(f'{amount} XLM bad sum')

    amount = float(balances.get('SATSMTL', 0))
    if amount < 500000:
        db_send_admin_message(session, f'{amount} SATSMTL bad sum')
        logger.info(f'{amount} SATSMTL bad sum')

    async with aiohttp.ClientSession() as httpsession:
        async with httpsession.get('https://apilist.tronscan.org/api/account?'
                                   'address=TJaGpx1zVVmKgYwSdeSr6YmsuDcHHhgZDS') as resp:
            json_resp = await resp.json()
            for token in json_resp['tokens']:
                if token['tokenAbbr'] == 'USDT':
                    if float(token['amount']) < 1000:
                        db_send_admin_message(session, f'{token["amount"]} {token["tokenAbbr"]} bad sum')
                        logger.info(f'{token["amount"]} {token["tokenAbbr"]} bad sum')
                if token['tokenAbbr'] == 'trx':
                    if float(token['amount']) < 500:
                        db_send_admin_message(session, f'{token["amount"]} {token["tokenAbbr"]} bad sum')
                        logger.info(f'{token["amount"]} {token["tokenAbbr"]} bad sum')


if __name__ == "__main__":

    # asyncio.run(check_mmwb(quik_pool()))

    # exit()#

    # remove orders
    # xdr = stellar_remove_orders(MTLAddresses.public_exchange_usdm_usdc, None)
    # stellar_sync_submit(stellar_sign(xdr, config.private_sign.get_secret_value()))

    asyncio.run(move_token(source_account=MTLAddresses.public_exchange_usdm_usdc,
                           destination_account='GCWJOBIPJQRZLFGQ5RQKE4J3H2QXHAOHCFVDM3FH37APAM3QXQR7POOL',
                           amount='9800', asset=MTLAssets.usdm_asset,
                           ))


    # asyncio.run(exchange_token(source_account=MTLAddresses.public_exchange_usdm_sats,
    #                            destination_account=MTLAddresses.public_exchange_pool,
    #                            amount='500', source_asset=MTLAssets.eurmtl_asset,
    #                            destination_asset=MTLAssets.usdc_asset))

    # asyncio.run(update_main_report(quik_pool()))
    # for x in [MTLAddresses.public_exchange_eurmtl_xlm,
    #           MTLAddresses.public_exchange_eurmtl_btc,
    #           MTLAddresses.public_exchange_eurmtl_sats,
    #           MTLAddresses.public_exchange_eurmtl_usdm,
    #           MTLAddresses.public_exchange_usdm_usdc,
    #           MTLAddresses.public_exchange_mtl_xlm,
    #           MTLAddresses.public_exchange_usdm_xlm
    #           ]:
    #     stellar_sync_submit(stellar_sign(
    #         stellar_add_trustline(x,
    #                               asset_code=MTLAssets.aqua_asset.code,
    #                               asset_issuer=MTLAssets.aqua_asset.issuer),
    #         get_private_sign()))
