import sys
from dataclasses import dataclass, field

import sentry_sdk

from utils.gspread_tools import get_all_data_from_mmwb_config, get_one_data_mm_from_report
from utils.stellar_utils import *

max_eurmtl = 10000.0  # max offer
# max_btcmtl = 0.1  # max offer
# max_satsmtl = 1000000  # max offer
sats_cost = 100000000
# min_xlm = 50.0
persent_eurmtl = 1.03  # 1.03 =  5% наценки
persent_btc = 1.01  #
persent_xlm = 1.03  #
persent_usdc = 1.002  # 0.975 for fund exchange
persent_cost = 1.01  # 1% изменения цены для обновления
persent_btc_cost = 1.001  # 0,1% изменения цены для обновления


@dataclass
class AddressConfig:
    account_id: str = field(default=None)
    asset_a: Asset = field(default=None)
    asset_b: Asset = field(default=None)
    price: float = field(default=0.0)


# server = Server(horizon_url="http://158.58.231.224:8000/")
# server = Server(horizon_url="https://horizon.publicnode.org")
server = Server(horizon_url=config.horizon_url)


def get_offers(address: str):
    call = server.offers().for_account(address).limit(200).call()

    records = {}
    for record in call['_embedded']['records']:
        selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
        buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
        pair_name = f'{selling_name}-{buying_name}'

        if pair_name not in records:
            records[pair_name] = [record]
        else:
            records[pair_name].append(record)

    return records


def get_sum(amount, max_value):
    return int(amount) if amount < max_value else max_value


async def update_offers(update_config):
    offers = get_offers(update_config.address)
    balances = await get_balances(update_config.address)
    balances['XLM'] = float(balances['XLM']) - 50  # оставляем минимум 50
    amount_a = get_sum(float(balances[update_config.asset_a.code]), update_config.max_a)
    amount_b = get_sum(float(balances[update_config.asset_b.code]), update_config.max_b)
    await update_offer(account_key=update_config.address, price_min=update_config.price_min,
                       price_max=update_config.price_max,
                       price=update_config.price_a, selling_asset=update_config.asset_a,
                       buying_asset=update_config.asset_b,
                       amount=amount_a, check_persent=update_config.check_persent,
                       record=offers.get(f'{update_config.asset_a.code}-{update_config.asset_b.code}'))

    await update_offer(account_key=update_config.address, price_min=1 / update_config.price_max,
                       price_max=1 / update_config.price_min,
                       price=update_config.price_b, selling_asset=update_config.asset_b,
                       buying_asset=update_config.asset_a,
                       amount=amount_b, check_persent=update_config.check_persent,
                       record=offers.get(f'{update_config.asset_b.code}-{update_config.asset_a.code}'))


@logger.catch
async def update_offer(account_key, price_min, price_max, price, selling_asset, buying_asset, amount,
                       check_persent, record):
    test_record = {'id': '1086147610', 'paging_token': '1086147610',
                   'seller': 'GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7',
                   'selling': {'asset_type': 'native'},
                   'buying': {'asset_type': 'credit_alphanum12', 'asset_code': 'EURMTL',
                              'asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'},
                   'amount': '20000.0000000', 'price_r': {'n': 557511, 'd': 5000000},
                   'price': '0.1115022', 'last_modified_ledger': 43210436,
                   'last_modified_time': '2022-10-21T08:15:53Z'}
    account = server.load_account(account_key)
    offer_id = int(record["id"]) if record else 0
    current_amount = float(record["amount"]) if record else 0
    current_price = float(record["price_r"]['n']) / float(record["price_r"]['d']) if record else 0

    stellar_transaction = None
    # if offer and bad price need zero offer
    if (price > price_max) or (price < price_min):
        if offer_id > 0:
            logger.info(f'need cancel {selling_asset.code} for {buying_asset.code} price {price} amount {amount}')
            stellar_transaction = TransactionBuilder(source_account=account,
                                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                                     base_fee=base_fee)
            stellar_transaction.append_manage_sell_offer_op(selling=selling_asset, buying=buying_asset, amount='0',
                                                            price=Price.from_raw_price('1'), offer_id=offer_id)
        sentry_sdk.capture_message(f'bad price {price} out of range {price_min} - {price_max}')
        logger.info(f'bad price {price} out of range {price_min} - {price_max}')
    elif (amount > 0) and (price > 0) and (
            (price > current_price * check_persent) or (price * check_persent < current_price) or
            (amount > current_amount * 1.1) or (amount * 1.1 < current_amount)):
        logger.info(f'need sale {selling_asset.code} for {buying_asset.code} price {price} amount {amount}')
        stellar_transaction = TransactionBuilder(source_account=account,
                                                 network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                                 base_fee=base_fee)
        stellar_transaction.append_manage_sell_offer_op(selling=selling_asset, buying=buying_asset, amount=str(amount),
                                                        price=Price.from_raw_price(str(price)), offer_id=offer_id)
    if stellar_transaction:
        stellar_transaction.set_timeout(250)
        stellar_transaction = stellar_transaction.build()
        stellar_transaction.sign(get_private_sign())
        xdr = stellar_transaction.to_xdr()
        logger.info(f"xdr: {xdr}")

        server.submit_transaction(stellar_transaction)


@logger.catch
def fire_mtl(account, amount):
    stellar_transaction = TransactionBuilder(source_account=account,
                                             network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                             base_fee=base_fee)
    stellar_transaction.append_payment_op(destination=MTLAssets.mtl_asset.issuer, asset=MTLAssets.mtl_asset,
                                          amount=str(amount))
    stellar_transaction = stellar_transaction.build()
    stellar_transaction.sign(get_private_sign())
    xdr = stellar_transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    server.submit_transaction(stellar_transaction)


@logger.catch
async def check_fire(cost_fire):
    account_fire = server.load_account(MTLAddresses.public_fire)
    # get balance
    balances = await get_balances(MTLAddresses.public_fire)

    sum_eurmtl = float(balances['EURMTL'])
    sum_mtl = float(balances['MTL'])
    logger.info(['fire', 'sum_eurmtl', sum_eurmtl, 'sum_mtl', sum_mtl])

    # get offers
    rq = requests.get(f'{config.horizon_url}/accounts/{MTLAddresses.public_fire}/offers').json()
    # print(json.dumps(rq["_embedded"]["records"], indent=4))
    records = {}
    if len(rq["_embedded"]["records"]) > 0:
        for record in rq["_embedded"]["records"]:
            selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
            buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
            records[f'{selling_name}-{buying_name}'] = record

    await update_offer(account_key=account_fire.account, price_min=1 / 5, price_max=1 / 3,
                       price=round(1 / cost_fire, 5),
                       selling_asset=MTLAssets.eurmtl_asset, buying_asset=MTLAssets.mtl_asset, amount=sum_eurmtl,
                       check_persent=1.01,
                       record=records.get('EURMTL-MTL'))

    if sum_mtl > 0:
        fire_mtl(account_fire, sum_mtl)


async def get_asset_spread(selling_asset: Asset, buying_asset: Asset):
    """
    Возвращает минимальную цену продажи и максимальную цену покупки между двумя ассетами.
    :param selling_asset: Ассет, который продается.
    :param buying_asset: Ассет, который покупается.
    :return: Кортеж из двух элементов (min_sell_price, max_buy_price).
    """
    # Запрашиваем ордера на продажу
    sell_offers_call = server.offers().for_selling(selling_asset).for_buying(buying_asset).limit(200).order(
        desc=True).call()
    sell_offers = sell_offers_call['_embedded']['records']
    # Запрашиваем ордера на покупку
    buy_offers_call = server.offers().for_selling(buying_asset).for_buying(selling_asset).limit(200).order(
        desc=True).call()
    buy_offers = buy_offers_call['_embedded']['records']

    # Определяем минимальную цену продажи и максимальную цену покупки
    min_sell_price = min([float(offer['price']) for offer in sell_offers], default=None)
    max_buy_price = max([1 / float(offer['price']) for offer in buy_offers], default=None)

    return min_sell_price, max_buy_price


def remove_ladder_orders(account_id, offers):
    """
    Удаляет указанные ордера для заданного адреса.

    :param account_id: Публичный ключ адреса, с которого будут удаляться ордера.
    :param offers: Список ордеров, которые нужно удалить.
    """
    root_account = Server(horizon_url=config.horizon_url).load_account(account_id)
    transaction = TransactionBuilder(source_account=root_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)

    for offer in offers:
        transaction.append_manage_sell_offer_op(
            selling=Asset(offer['selling'].get('asset_code', 'XLM'), offer['selling'].get('asset_issuer')),
            buying=Asset(offer['buying'].get('asset_code', 'XLM'), offer['buying'].get('asset_issuer')),
            amount='0',
            price='1',
            offer_id=int(offer['id']))

    if transaction.operations:
        transaction = transaction.build()
        transaction.sign(get_private_sign())
        # print(transaction.to_xdr())
        server.submit_transaction(transaction)

    return True


def is_close_offer_exist(current_offers, asset_a, asset_b, target_price, price_range):
    """
    Проверяет, существует ли ордер на продажу в заданном диапазоне цен.

    :param current_offers: Список текущих ордеров.
    :param asset_a: Ассет продажи.
    :param asset_b: Ассет покупки.
    :param target_price: Целевая цена для проверки.
    :param price_range: Диапазон цен для сравнения.
    :return: True, если существует ордер в диапазоне, иначе False.
    """
    # Предполагаем, что current_offers - это словарь, где ключ - это пара "АссетПродажи-АссетПокупки",
    # а значение - список ордеров для этой пары.
    pair_key = f"{asset_a.code}-{asset_b.code}"
    orders_for_pair = current_offers.get(pair_key, [])

    for order in orders_for_pair:
        order_price = float(order["price"])
        lower_bound = target_price * (1 - price_range)
        upper_bound = target_price * (1 + price_range)
        if lower_bound <= order_price <= upper_bound:
            return True  # Найден ордер в заданном диапазоне

    return False


async def place_ladder_orders(account_id, asset_a, asset_b, price, offset, step, ladder_length, max_leverage_amount):
    """
    Функция для выставления ордеров лесенкой.

    :param account_id: Адрес, на котором будут выставляться ордера.
    :param asset_a: Токен А.
    :param asset_b: Токен Б.
    :param price: Начальная цена.
    :param offset: Отступ от начальной цены в процентах.
    :param step: Шаг между ордерами в процентах.
    :param ladder_length: Длина лесенки (количество ордеров).
    :param max_leverage_amount: Максимальная сумма, которая может быть вложена в один ордер.
    """
    offset_decimal = offset / 100
    step_decimal = step / 100

    ladder_length = int(ladder_length)
    balances = await get_balances(account_id)
    available_a = float(balances.get(asset_a.code, 0))
    amount_per_order = round(max_leverage_amount / ladder_length)
    max_ladder_length = int(available_a / amount_per_order)

    current_offers = get_offers(account_id)

    prices = [round(price * (1 + offset_decimal + i * step_decimal), 5) for i in range(ladder_length)]
    prices_start = str(prices)
    if ladder_length > max_ladder_length:
        prices = prices[-max_ladder_length:]
    logger.info(f'prices: {prices_start} -> {prices}')

    max_price = max(prices)
    min_price = min(prices)
    inverse_max_price = 1 / max_price

    to_close_offers = []

    for offer in current_offers.get(f'{asset_a.code}-{asset_b.code}', []):
        offer_price = float(offer['price'])
        offer_amount = float(offer['amount'])
        if offer_price > max_price or offer_price < min_price or offer_amount > amount_per_order:
            to_close_offers.append(offer)

    # Добавляем шаг для обработки обратных офферов
    for offer in current_offers.get(f'{asset_b.code}-{asset_a.code}', []):
        offer_price = float(offer['price'])
        if offer_price < inverse_max_price:
            to_close_offers.append(offer)

    if to_close_offers:
        remove_ladder_orders(account_id, to_close_offers)

    balances = await get_balances(account_id)
    available_a = float(balances.get(asset_a.code, 0))

    root_account = Server(horizon_url=config.horizon_url).load_account(account_id=account_id)
    transaction = TransactionBuilder(source_account=root_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)

    for price in reversed(prices):
        required_amount_a = amount_per_order

        if available_a >= required_amount_a:
            # Проверяем наличие близкого ордера
            if not is_close_offer_exist(current_offers, asset_a, asset_b, price, step_decimal):
                # Если близкого ордера нет, добавляем операцию в транзакцию
                transaction.append_manage_sell_offer_op(selling=asset_a, buying=asset_b,
                                                        amount=str(required_amount_a), price=str(price)
                                                        )
                available_a -= required_amount_a
                logger.debug(
                    f'Добавлена операция ордера: {asset_a.code} -> {asset_b.code}, Цена: {price}, Количество: {required_amount_a}')
            else:
                logger.debug(
                    f'Ордер {asset_a.code}-{asset_b.code} в диапазоне {price * (1 - step_decimal)} - {price * (1 + step_decimal)} уже существует.')
        else:
            sentry_sdk.capture_message(f'Недостаточно средств для выставления '
                                       f'ордера по цене {price} токены {asset_a.code}-{asset_b.code} средств {available_a}', )
            break

    if transaction.operations:
        transaction = transaction.build()
        transaction.sign(get_private_sign())
        try:
            server.submit_transaction(transaction)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.error(f'Не удалось выставить ордер: {e}')
            xdr = stellar_remove_orders(account_id, None)
            if xdr:
                try:
                    stellar_sync_submit(stellar_sign(xdr, get_private_sign()))
                except Exception as e:
                    logger.error(f'Не удалось отменить ордер: {e}')
                    logger.info(xdr)

    return True


async def check_exchange():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    parameters = {
        'symbol': 'XLM,BTC,EURS,EURT,EURC',  # Примерный список символов
        'convert': 'USDT'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': config.coinmarketcap.get_secret_value(),
    }

    response = requests.get(url, headers=headers, params=parameters)
    data = response.json()
    # print(data)

    xlm_usdt = data['data']['XLM']['quote']['USDT']['price']
    btc_usdt = data['data']['BTC']['quote']['USDT']['price']
    eurs_usdt = data['data']['EURS']['quote']['USDT']['price']
    eur_eur = 1.01
    eur_usdt = eurs_usdt * eur_eur  # Увеличиваем на 1%

    start_configs = [
        # EURMTL - XLM
        AddressConfig(account_id=MTLAddresses.public_exchange_eurmtl_xlm,
                      asset_a=MTLAssets.eurmtl_asset, asset_b=MTLAssets.xlm_asset,
                      price=eur_usdt * (1 / xlm_usdt)
                      ),
        # USDM - SATS
        AddressConfig(account_id=MTLAddresses.public_exchange_usdm_sats,
                      asset_a=MTLAssets.usdm_asset, asset_b=MTLAssets.satsmtl_asset,
                      price=(1 * sats_cost) / btc_usdt
                      ),
        # EURMTL - USDM
        AddressConfig(account_id=MTLAddresses.public_exchange_eurmtl_usdm,
                      asset_a=MTLAssets.eurmtl_asset, asset_b=MTLAssets.usdm_asset,
                      price=eur_usdt
                      ),
        # USDM - USDC
        AddressConfig(account_id=MTLAddresses.public_exchange_usdm_usdc,
                      asset_a=MTLAssets.usdm_asset, asset_b=MTLAssets.usdc_asset,
                      price=1
                      ),
        # USDM - XLM
        AddressConfig(account_id=MTLAddresses.public_exchange_usdm_xlm,
                      asset_a=MTLAssets.usdm_asset, asset_b=MTLAssets.xlm_asset,
                      price=1 / xlm_usdt
                      ),
        # EURMTL - EURC
        AddressConfig(account_id=MTLAddresses.public_exchange_eurmtl_eurc,
                      asset_a=MTLAssets.eurmtl_asset, asset_b=MTLAssets.eurc_asset,
                      price=eur_eur
                      ),

    ]

    await check_exchange_run(start_configs)


async def check_exchange_run(start_configs: list[AddressConfig]):
    config_data = await get_all_data_from_mmwb_config()

    for start_config in start_configs:
        matching_config = next((item for item in config_data[1:] if item[1] == start_config.account_id), None)
        if matching_config:
            lever_a, lever_b, offset_percent, steps, step_percent, min_stop_loss, max_stop_loss = [
                float(value.replace(',', '.')) for value in [
                    matching_config[6], matching_config[7], matching_config[8], matching_config[9],
                    matching_config[10], matching_config[11], matching_config[12]
                ]
            ]

            if start_config.price < min_stop_loss or start_config.price > max_stop_loss:
                logger.debug(
                    f"Цена {start_config.price} вышла из диапазона для {start_config.account_id}. Отменяем ордера.")
                # вызов функции для отмены ордеров
                xdr = stellar_remove_orders(start_config.account_id, None)
                if xdr:
                    stellar_sync_submit(stellar_sign(xdr, get_private_sign()))
            else:
                logger.debug(f"Цена {start_config.price} в диапазоне для {start_config.account_id}. Обновляем ордера.")
                # вызов функции для создания лесенки ордеров в прямом направлении
                await place_ladder_orders(account_id=start_config.account_id, asset_a=start_config.asset_a,
                                          asset_b=start_config.asset_b, price=start_config.price,
                                          offset=offset_percent, step=step_percent, ladder_length=steps,
                                          max_leverage_amount=lever_a)

                # расчет обратной цены для второго набора ордеров
                reverse_price = 1 / start_config.price

                # вызов функции для создания лесенки ордеров в обратном направлении
                await place_ladder_orders(account_id=start_config.account_id, asset_a=start_config.asset_b,
                                          asset_b=start_config.asset_a, price=reverse_price,
                                          offset=offset_percent, step=step_percent, ladder_length=steps,
                                          max_leverage_amount=lever_b)
        else:
            sentry_sdk.capture_message(
                f"Не удалось найти конфигурацию для {start_config.account_id}. Отменяем ордера.")
            xdr = stellar_remove_orders(start_config.account_id, None)
            if xdr:
                stellar_sync_submit(stellar_sign(xdr, get_private_sign()))


async def check_exchange_one():
    _, mtlfarm_usd = await get_one_data_mm_from_report()
    _, _, mtl_market_xlm = await get_asset_swap_spread(MTLAssets.mtl_asset, MTLAssets.xlm_asset)

    start_configs = [
        # MTL - XLM
        AddressConfig(account_id=MTLAddresses.public_exchange_mtl_xlm,
                      asset_a=MTLAssets.mtl_asset, asset_b=MTLAssets.xlm_asset,
                      price=mtl_market_xlm
                      ),
        # mtlfarm - XLM
        AddressConfig(account_id=MTLAddresses.public_exchange_usdm_mtlfarm,
                      asset_a=MTLAssets.usdm_asset, asset_b=MTLAssets.mtlfarm_asset,
                      price=1 / mtlfarm_usd
                      ),

    ]

    await check_exchange_run(start_configs)
    await check_exchange_run(start_configs)


async def check_exchange_test():
    # url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    # parameters = {
    #     'symbol': 'XLM,BTC,EURS,EURT,EURC',  # Примерный список символов
    #     'convert': 'USDT'
    # }
    # headers = {
    #     'Accepts': 'application/json',
    #     'X-CMC_PRO_API_KEY': config.coinmarketcap.get_secret_value(),
    # }
    #
    # response = requests.get(url, headers=headers, params=parameters)
    # data = response.json()
    #
    # xlm_usdt = data['data']['XLM']['quote']['USDT']['price']

    eur_eur = 1.01
    start_configs = [
        # EURMTL - EURC
        AddressConfig(account_id=MTLAddresses.public_exchange_eurmtl_eurc,
                      asset_a=MTLAssets.eurmtl_asset, asset_b=MTLAssets.eurc_asset,
                      price=eur_eur
                      ),

    ]

    await check_exchange_run(start_configs)


if __name__ == "__main__":
    logger.add("mtl_exchange.log", rotation="1 MB", level="WARNING")

    sentry_sdk.init(
        dsn=config.sentry_report_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

    if 'check_exchange' in sys.argv:
        asyncio.run(check_exchange())
    elif 'one_exchange' in sys.argv:
        asyncio.run(check_exchange_one())
    else:
        print('need more parameters')
        # asyncio.run(check_exchange())
        asyncio.run(check_exchange_one())
        # asyncio.run(check_exchange_test())

    # place_ladder_orders(account_id=MTLAddresses.public_exchange_usdm_xlm, asset_a=MTLAssets.usdm_asset,
    #                     asset_b=MTLAssets.xlm_asset, price=7.7, offset=2, step=1, ladder_length=5,
    #                     max_leverage_amount=100)
    # place_ladder_orders(account_id=MTLAddresses.public_exchange_usdm_xlm, asset_a=MTLAssets.xlm_asset,
    #                     asset_b=MTLAssets.usdm_asset, price=1 / 7.7, offset=2, step=1, ladder_length=5,
    #                     max_leverage_amount=100)
