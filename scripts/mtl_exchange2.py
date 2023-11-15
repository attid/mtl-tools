from scripts.mtl_exchange import *

from stellar_sdk import TransactionBuilder, Network

from scripts.update_report import update_mmwb_report


async def move_token(source_account, destination_account, amount: str, asset):
    async with ServerAsync(
            horizon_url="https://horizon.stellar.org", client=AiohttpClient()
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
            horizon_url="https://horizon.stellar.org", client=AiohttpClient()
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

        # xdr = stellar_transaction.to_xdr()
        # logger.info(f"xdr: {xdr}")

        # Отправка транзакции
        transaction_resp = await st_server.submit_transaction(stellar_transaction)

        return transaction_resp


async def check_mm(session: Session):
    balances = await get_balances(MTLAddresses.public_exchange_usdm_xlm)
    amount = float(balances.get('USDM', 0))
    if amount > 12000:
        amount = str(round(amount - 11000))
        await move_token(MTLAddresses.public_exchange_usdm_xlm, MTLAddresses.public_exchange_usdm_usdc,
                         amount, MTLAssets.usdm_asset)
        db_send_admin_message(session, f'{amount} USDM was moved usdm_xlm - usdm_usdc')
        logger.info(f'{amount} USDM was moved usdm_xlm - usdm_usdc')

    balances = await get_balances(MTLAddresses.public_exchange_usdm_usdc)
    amount = float(balances.get('USDM', 0))
    if amount > 20000:
        amount = str(round(amount - 19000))
        await move_token(MTLAddresses.public_exchange_usdm_usdc, MTLAddresses.public_exchange_eurmtl_usdm,
                         amount, MTLAssets.usdm_asset)
        db_send_admin_message(session, f'{amount} USDM was moved usdm_usdc - eurmtl_usdm')
        logger.info(f'{amount} USDM was moved usdm_usdc - eurmtl_usdm')
    amount = float(balances.get('USDC', 0))
    if amount > 12000:
        amount = str(round(amount - 11000))
        await exchange_token(MTLAddresses.public_exchange_usdm_usdc, MTLAddresses.public_exchange_usdm_xlm,
                             amount, MTLAssets.usdc_asset, MTLAssets.xlm_asset)
        db_send_admin_message(session, f'{amount} USDC was moved to XLM \n usdm_usdc - usdm_xlm')
        logger.info(f'{amount} USDC was moved to XLM \n usdm_usdc - usdm_xlm')

    await update_mmwb_report(session)


if __name__ == "__main__":
    from db.quik_pool import quik_pool

    # remove orders
    # xdr = stellar_remove_orders(MTLAddresses.public_exchange_usdm_xlm, None)
    # stellar_sync_submit(stellar_sign(xdr, config.private_sign.get_secret_value()))


    asyncio.run(move_token(source_account=MTLAddresses.public_exchange_eurmtl_usdm,
                          destination_account=MTLAddresses.public_exchange_usdm_xlm,
                          amount='12000', asset=MTLAssets.usdm_asset,
                          ))

    # asyncio.run(exchange_token(source_account=MTLAddresses.public_exchange_eurmtl_btc,
    #                             destination_account=MTLAddresses.public_exchange_usdm_xlm,
    #                             amount='0.02', source_asset=MTLAssets.btcmtl_asset,
    #                             destination_asset=MTLAssets.xlm_asset))


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
