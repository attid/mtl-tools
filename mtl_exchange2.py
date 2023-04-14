import requests
from stellar_sdk import Server
from mtl_exchange import update_offer
from mystellar import xlm_asset, usdc_asset, stellar_check_receive_sum, eurmtl_asset
from loguru import logger


# https://stellar-sdk.readthedocs.io/en/latest/

@logger.catch
def main():
    logger.add("mtl_exchange.log", rotation="1 MB")
    min_price = 5.0  # min max price in xlm
    max_price = 20.4
    max_eurmtl = 300.0  # max offer 202
    max_xlm = 3005.0
    min_xlm = 5.0
    persent_eurmtl = 1.04  # 3% наценки
    persent_xlm = 1.01  # 1% наценки
    persent_cost = 1.01  # 1% изменения цены для обновления
    public_mtl = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
    public_exchange2 = "GAEFTFGQYWSF5T3RVMBSW2HFZMFZUQFBYU5FUF3JT3ETJ42NXPDWOO2F"
    server = Server(horizon_url="https://horizon.stellar.org")
    account_exchange = server.load_account(public_exchange2)
    # get balance
    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange2}').json()
    # print(json.dumps(rq, indent=4))
    for balance in rq["balances"]:
        name = 'XLM' if balance["asset_type"] == 'native' else balance["asset_code"]
        balances[name] = balance["balance"]
    sum_eurmtl = float(balances['EURMTL'])
    sum_xlm = float(balances['XLM'])
    logger.info(['sum_eurmtl', sum_eurmtl, 'sum_xlm', sum_xlm])
    # get offers
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange2}/offers').json()
    # print(json.dumps(rq["_embedded"]["records"], indent=4))
    records = {}
    # if len(rq["_embedded"]["records"]) > 0:
    if len(rq["_embedded"]["records"]) > 0:
        for record in rq["_embedded"]["records"]:
            selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
            buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
            records[f'{selling_name}-{buying_name}'] = record
    # EUR cost
    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT').json()
    # print(rq)
    eur_cost = 1 / float(rq['price'])
    cost_usdc_xml = float(stellar_check_receive_sum(usdc_asset, '1', xlm_asset))
    cost_xlm_usdc = float(stellar_check_receive_sum(xlm_asset, '1', usdc_asset))
    cost_eurmtl_xml = cost_usdc_xml / eur_cost * persent_eurmtl
    cost_xlm_eurmtl = cost_xlm_usdc * eur_cost
    logger.info(['cost_usdc_xml', cost_usdc_xml, cost_eurmtl_xml,
                 'cost_xlm_usdc', cost_xlm_usdc, cost_xlm_eurmtl,
                 'eur_cost', eur_cost])
    sum_eurmtl = sum_eurmtl if sum_eurmtl < max_eurmtl else max_eurmtl
    sum_xlm = sum_xlm if sum_xlm < max_xlm else max_xlm
    sum_xlm -= min_xlm
    sum_xlm = round(sum_xlm, 3)
    update_offer(account=account_exchange, price_min=min_price, price_max=max_price, price=round(cost_eurmtl_xml, 5),
                 selling_asset=eurmtl_asset, buying_asset=xlm_asset, amount=sum_eurmtl, check_persent=persent_cost,
                 record=records.get('EURMTL-XLM'))
    update_offer(account=account_exchange, price_min=1 / max_price, price_max=1 / min_price,
                 price=round(cost_xlm_eurmtl, 5),
                 selling_asset=xlm_asset, buying_asset=eurmtl_asset, amount=sum_xlm, check_persent=persent_cost,
                 record=records.get('XLM-EURMTL'))
    print(1 / max_price, 1 / min_price, cost_xlm_eurmtl)


if __name__ == "__main__":
    main()
