import requests
import json


from llm.llm_main import LangChainManager

HORIZON_URL = 'https://horizon.stellar.org'
EURMTL_ISSUER = 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'


#@tool
def get_account_info(account_id: str):
    """
    Получает информацию об аккаунте Stellar и его балансах.

    Параметры:
      account_id (str): Идентификатор аккаунта Stellar.

    Возвращает:
      str: JSON-строку с информацией об аккаунте в следующем формате:

          {
              "account_id": <account_id: str>,
              "balances": [
                  "XLM: <баланс>",
                  "<asset_code>-<asset_issuer>: <баланс>",
                  ...
              ]
          }

    Пример:
      {
        "account_id": "GABCD12345...",
        "balances": [
            "XLM: 1000.0",
            "USD-GDUKMGUGDZQK6YH5S3...",
        ]
      }
    """
    try:
        response = requests.get(f"{HORIZON_URL}/accounts/{account_id}")
        response.raise_for_status()
        data = response.json()
        balances = data.get("balances", [])
        formatted_balances = []
        for balance in balances:
            if balance.get("asset_type") == "native":
                formatted_balances.append(f"XLM: {balance.get('balance', '')}")
            else:
                asset_code = balance.get("asset_code", "")
                asset_issuer = balance.get("asset_issuer", "")
                formatted_balances.append(f"{asset_code}-{asset_issuer}: {balance.get('balance', '')}")
        result = {
            "account_id": account_id,
            "balances": formatted_balances
        }
        return json.dumps(result, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})


#@tool
def get_price_in_eurmtl(asset_code: str, asset_issuer: str):
    """
    Получает курс токена по отношению к EURMTL.

    Параметры:
      asset_code (str): Код токена (например, ITC).
      asset_issuer (str): Stellar ID эмитента токена.

    Возвращает:
      str: JSON-строку с информацией о курсе в следующем формате:

          {
            "asset": <asset_code: str>,
            "price": "1 <asset_code> = <курс> EURMTL",
            "raw_price": <курс: float>
          }

      В случае, если путь для обмена не найден, возвращается:

          {
            "error": "Не удалось получить курс <asset_code>/EURMTL"
          }

    Пример:
      {
        "asset": "ITC",
        "price": "1 ITC = 8.1234567 EURMTL",
        "raw_price": 8.1234567
      }
    """
    try:
        params = {
            "source_amount": "1",
            "destination_assets": f"{asset_code}:{asset_issuer}",
            "source_asset_type": "credit_alphanum12",
            "source_asset_issuer": EURMTL_ISSUER,
            "source_asset_code": "EURMTL",
        }
        response = requests.get(f"{HORIZON_URL}/paths/strict-send", params=params)
        response.raise_for_status()
        data = response.json()
        records = data.get("_embedded", {}).get("records", [])
        if not records:
            return json.dumps({"error": f"Не удалось получить курс {asset_code}/EURMTL"})
        # Выбираем первый найденный путь обмена
        path = records[0]
        destination_amount = float(path.get("destination_amount", 0))
        if destination_amount == 0:
            return json.dumps({"error": "Получено недопустимое значение destination_amount"})
        price = 1 / destination_amount
        result = {
            "asset": asset_code,
            "price": f"1 {asset_code} = {price:.7f} EURMTL",
            "raw_price": price
        }
        return json.dumps(result, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    tools = [get_account_info, get_price_in_eurmtl]
    llm = LangChainManager(tools=tools)
    llm.debug = True
    r = llm.stream('Сколько ЮЗДМ на счету у пользователя с адресом GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI?')
    print(r)
    print(llm.calc_costs())
    r = llm.stream('Сколько это в EURMTL?')
    print(r)
    print(llm.calc_costs())
