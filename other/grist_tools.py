import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from loguru import logger
from other.config_reader import config
from other.utils import float2str
from other.web_tools import HTTPSessionManager

GRIST_BASE_URL = config.grist_base_url
RELY_GRIST_BASE_URL = config.rely_grist_base_url
RELY_GRIST_ACCESS_ID = "kceNjvoEEihSsc8dQ5vZVB"


@dataclass
class GristTableConfig:
    access_id: str
    table_name: str
    base_url: str = GRIST_BASE_URL


# Enum для таблиц
@dataclass
class MTLGrist:
    NOTIFY_ACCOUNTS = GristTableConfig("f3ETcoWEkzvkcUnQJtv5tm", "Accounts")
    NOTIFY_ASSETS = GristTableConfig("f3ETcoWEkzvkcUnQJtv5tm", "Assets")
    NOTIFY_TREASURY = GristTableConfig("f3ETcoWEkzvkcUnQJtv5tm", "Treasury")

    MTLA_CHATS = GristTableConfig("x4r7WiFKsJREzXS4vowwqj", "MTLA_CHATS")
    MTLA_COUNCILS = GristTableConfig("x4r7WiFKsJREzXS4vowwqj", "MTLA_COUNCILS")
    MTLA_USERS = GristTableConfig("x4r7WiFKsJREzXS4vowwqj", "Users")
    MTLA_Corporates = GristTableConfig("x4r7WiFKsJREzXS4vowwqj", "Corporates")

    SP_USERS = GristTableConfig("hpZWKq729vw2D5AkG7oYYz", "SP_USERS")
    SP_CHATS = GristTableConfig("hpZWKq729vw2D5AkG7oYYz", "SP_CHATS")

    MAIN_CHAT_INCOME = GristTableConfig("khWn5KMRbfUQQoaPydjhGt", "Main_chat_income")
    MAIN_CHAT_OUTCOME = GristTableConfig("khWn5KMRbfUQQoaPydjhGt", "Main_chat_outcome")

    GRIST_access = GristTableConfig("1sd6z3cHUPVQSgvyy7iARy", "Access")
    GRIST_use_log = GristTableConfig("1sd6z3cHUPVQSgvyy7iARy", "Use_log")

    EURMTL_users = GristTableConfig("3Fk4hjCv847GBx8ZTCPN2Y", "Users")
    EURMTL_accounts = GristTableConfig("3Fk4hjCv847GBx8ZTCPN2Y", "Accounts")
    EURMTL_assets = GristTableConfig("3Fk4hjCv847GBx8ZTCPN2Y", "Assets")

    CONFIG_auto_clean = GristTableConfig("vpjoUZvH6WRcS7Es8n1UZv", "Auto_clean")
    MTLA_AIRDROP = GristTableConfig("r4r5Lhy2QJ7bvNs4ut1ATV", "EUR_GNRL")
    MTLA_CONFIG = GristTableConfig("r4r5Lhy2QJ7bvNs4ut1ATV", "CONFIG")

    MTL_ADMINS = GristTableConfig("ePz5LKsFPmhe5XCC4z7akA", "MTL_Admins")
    MTL_ADMINS_MEDIA = GristTableConfig("ePz5LKsFPmhe5XCC4z7akA", "Media")
    MTL_ADMINS_AGORA_TEAM = GristTableConfig("ePz5LKsFPmhe5XCC4z7akA", "MTLA_Agora_Team")
    MTL_ADMINS_AGORA_TOPICS = GristTableConfig("ePz5LKsFPmhe5XCC4z7akA", "MTLA_Agora_Topics")


@dataclass(frozen=True)
class AirdropConfigItem:
    record_id: int
    amount: str
    asset_code: str
    asset_issuer: str
    priority: int


class GristAPI:
    def __init__(
        self,
        session_manager: Optional[HTTPSessionManager] = None,
        token: Optional[str] = None,
        *,
        use_default_token: bool = True,
    ):
        self.token = config.grist_token if token is None and use_default_token else token
        self.session_manager: HTTPSessionManager = session_manager or HTTPSessionManager()

    def _headers(self) -> Dict[str, str]:
        if not self.token:
            raise RuntimeError("Grist API token is not configured")
        return {"accept": "application/json", "Authorization": f"Bearer {self.token}"}

    async def fetch_data(
        self, table: GristTableConfig, sort: Optional[str] = None, filter_dict: Optional[Dict[str, List[Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Загружает данные из указанной таблицы Grist.

        Args:
            table: Конфигурация таблицы
            sort: Параметр сортировки
            filter_dict: Словарь фильтрации в формате {"column": [value1, value2]}
                        Пример: {"TGID": [123456789]}
        """
        from urllib.parse import quote

        headers = self._headers()
        url = f"{table.base_url}/{table.access_id}/tables/{table.table_name}/records"
        params = []

        if sort:
            params.append(f"sort={sort}")
        if filter_dict:
            # Преобразуем словарь в JSON и кодируем для URL
            filter_json = json.dumps(filter_dict)
            encoded_filter = quote(filter_json)
            params.append(f"filter={encoded_filter}")

        if params:
            url = f"{url}?{'&'.join(params)}"
        response = await self.session_manager.get_web_request(method="GET", url=url, headers=headers)

        match response.status:
            case 200 if isinstance(response.data, dict) and "records" in response.data:
                return [{"id": record["id"], **record["fields"]} for record in response.data["records"]]
            case _:
                raise Exception(f"Ошибка запроса: Статус {response.status}")

    async def put_data(self, table: GristTableConfig, json_data: Dict[str, Any]) -> bool:
        """
        Обновляет данные в указанной таблице Grist.
        """
        headers = self._headers()
        url = f"{table.base_url}/{table.access_id}/tables/{table.table_name}/records"
        response = await self.session_manager.get_web_request(method="PUT", url=url, headers=headers, json=json_data)

        match response.status:
            case 200:
                return True
            case _:
                raise Exception(f"Ошибка запроса: Статус {response.status}")

    async def patch_data(self, table: GristTableConfig, json_data: Dict[str, Any]) -> bool:
        """
        Частично обновляет данные в указанной таблице Grist.

        Args:
            table: Конфигурация таблицы Grist
            json_data: Данные для обновления в формате {"records": [{"fields": {...}}]}
        """
        headers = self._headers()
        url = f"{table.base_url}/{table.access_id}/tables/{table.table_name}/records"
        response = await self.session_manager.get_web_request(method="PATCH", url=url, headers=headers, json=json_data)

        match response.status:
            case 200:
                return True
            case _:
                raise Exception(f"Ошибка запроса: Статус {response.status}")

    async def post_data(self, table: GristTableConfig, json_data: Dict[str, Any]) -> bool:
        """
        Добавляет новые записи в указанную таблицу Grist.

        Args:
            table: Конфигурация таблицы Grist
            json_data: Данные для добавления в формате {"records": [{"fields": {...}}]}
        """
        headers = self._headers()
        url = f"{table.base_url}/{table.access_id}/tables/{table.table_name}/records"
        response = await self.session_manager.get_web_request(method="POST", url=url, headers=headers, json=json_data)

        match response.status:
            case 200:
                return True
            case _:
                raise Exception(f"Ошибка запроса: Статус {response.status}")

    async def load_table_data(
        self, table: GristTableConfig, sort: Optional[str] = None, filter_dict: Optional[Dict[str, List[Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Загружает данные из таблицы с обработкой ошибок.

        Args:
            table: Конфигурация таблицы
            sort: Параметр сортировки
            filter_dict: Словарь фильтрации в формате {"column": [value1, value2]}
                        Пример: {"TGID": [123456789]}
        """
        try:
            records = await self.fetch_data(table, sort, filter_dict)
            logger.info(f"Данные из таблицы {table.table_name} успешно загружены")
            return records
        except Exception as e:
            logger.warning(f"Ошибка при загрузке данных из таблицы {table.table_name}: {e}")
            return []


# Конфигурация
grist_session_manager = HTTPSessionManager()
grist_manager = GristAPI(grist_session_manager, token=config.grist_token)

rely_grist_session_manager = HTTPSessionManager()
rely_grist_manager = GristAPI(
    rely_grist_session_manager,
    token=config.rely_grist_token,
    use_default_token=False,
)


async def grist_check_airdrop_records(tg_id: Optional[int], public_key: Optional[str]) -> list[str]:
    """
    Checks MTLAirdrop register for TG ID and Stellar address matches.
    """
    results: list[str] = []
    table = MTLGrist.MTLA_AIRDROP

    if public_key:
        records = await grist_manager.load_table_data(table, filter_dict={"Public_key": [public_key]})
        if records:
            row_number = records[0].get("N") or records[0].get("id")
            results.append(f"Стеллар адрес найден в Airdrop строка {row_number}")
            return results

    if tg_id is not None:
        records = await grist_manager.load_table_data(table, filter_dict={"TG_ID": [tg_id]})
        if records:
            row_number = records[0].get("N") or records[0].get("id")
            results.append(f"Найден в Airdrop по ID строка {row_number}")
            return results

    results.append("Не найден в Airdrop")
    return results


async def grist_log_airdrop_payment(
    tg_id: int, public_key: str, nickname: str, tx_hash: str, amount: float, currency: str = "USDM"
) -> None:
    """
    Logs completed airdrop payment into MTLAirdrop register.
    """
    now = datetime.now(tz=timezone.utc)
    record = {
        "Currency": currency,
        "Amount": amount,
        "Public_key": public_key,
        "Nickname": nickname or "",
        "Time": now.strftime("%H:%M:%S"),
        "Date": now.date().isoformat(),
        "Transaction": f"https://viewer.eurmtl.me/transaction/{tx_hash}" if tx_hash else "",
        "TG_ID": tg_id,
    }
    json_data = {"records": [{"fields": record}]}
    try:
        await grist_manager.post_data(MTLGrist.MTLA_AIRDROP, json_data)
    except Exception as exc:
        logger.error(f"Failed to log airdrop payment to Grist: {exc}")


async def grist_load_airdrop_configs() -> list[AirdropConfigItem]:
    records = await grist_manager.load_table_data(
        MTLGrist.MTLA_CONFIG,
        sort="Priority",
        filter_dict={"Enabled": [True]},
    )
    configs: list[AirdropConfigItem] = []
    for record in records:
        record_id = record.get("id")
        amount_value = record.get("Amount")
        asset_code = (record.get("Asset_Code") or "").strip()
        asset_issuer = (record.get("Asset_Issuer") or "").strip()
        priority = record.get("Priority") or 0
        if not record_id or not amount_value or not asset_code:
            logger.warning(f"Skipping invalid airdrop config row: {record}")
            continue
        amount = float2str(amount_value)
        configs.append(
            AirdropConfigItem(
                record_id=record_id,
                amount=amount,
                asset_code=asset_code,
                asset_issuer=asset_issuer,
                priority=priority,
            )
        )
    configs.sort(key=lambda item: item.priority)
    return configs


async def main():
    # Пример загрузки данных с фильтрацией по TGUD
    users = await grist_manager.load_table_data(MTLGrist.MTLA_USERS, filter_dict={"TGID": [3344083]})
    if users:
        print(json.dumps(users, indent=2))
        print(users[0]["Stellar"])
    await grist_session_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
