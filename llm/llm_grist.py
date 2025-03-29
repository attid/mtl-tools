import os
import json
import requests
from dotenv import load_dotenv

from llm.llm_main import LangChainManager
from other.config_reader import config

load_dotenv()

API_BASE_URL = "https://montelibero.getgrist.com/api/docs/aYk6cpKAp9CDPJe51sP3AT/tables/Users/records"
HEADERS = {
    "Authorization": f"Bearer {config.grist_token}",
    "Accept": "application/json"
}

def get_all_users(full=False):
    """
    Получает список всех пользователей.

    Параметры:
      full (bool): Флаг, указывающий, нужно ли получить полные данные пользователей.

    Возвращает:
      str: JSON-строка с данными пользователей в следующем формате:

          {
              "records": [
                  {
                      "id": <номер>,
                      "fields": { ... }
                  },
                  ...
              ]
          }

    Пример:
      {
        "records": [
          {
            "id": 1,
            "fields": {
              "Telegram": "username",
              "TGID": 123456,
              "Stellar": "GABCD...",
              ...
            }
          },
          ...
        ]
      }
    """
    try:
        response = requests.get(API_BASE_URL, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        return json.dumps(data, indent=2, ensure_ascii=False)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})

def get_user_by_tgid(tgid: int):
    """
    Получает информацию о пользователе по его Telegram ID.

    Параметры:
      tgid (int): Telegram ID пользователя.

    Возвращает:
      str: JSON-строка с данными пользователя. Если пользователь не найден,
           возвращается JSON-строка с описанием ошибки.

    Пример:
      {
        "records": [
          {
            "id": 1,
            "fields": {
              "Telegram": "username",
              "TGID": 123456,
              "Stellar": "GABCD...",
              ...
            }
          }
        ]
      }
    """
    try:
        params = {"filter": json.dumps({"TGID": [tgid]})}
        response = requests.get(API_BASE_URL, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        if not data.get("records"):
            return json.dumps({"error": f"Пользователь с TGID {tgid} не найден"}, indent=2, ensure_ascii=False)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    tools = [get_all_users, get_user_by_tgid]
    llm = LangChainManager(tools=tools)
    llm.debug = True
    r = llm.stream('дай инфу по юзеру 5853032078')
    print(r)
    print(llm.calc_costs())
