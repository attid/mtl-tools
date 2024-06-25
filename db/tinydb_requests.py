import json
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any

import aiofiles
import asyncio
# from environs import Env
from pydantic import BaseModel
from asynctinydb import JSONStorage, TinyDB, Query
from asynctinydb.middlewares import CachingMiddleware

DB_FILE_NAME = os.path.join(os.path.dirname(__file__), 'skynet_config.json')


# class PrettyJSONStorage(JSONStorage):
#     """Custom JSON storage for TinyDB with pretty formatting."""
#
#     async def write(self, data):
#         with open(self._handle.name, 'w', encoding='utf8') as handle:
#             json.dump(data, handle, ensure_ascii=False, indent=4)


class BotTable(BaseModel):
    chat_id: int
    chat_key: int
    chat_value: str


class BotJsonConfig:
    def __init__(self):
        self.db = TinyDB(DB_FILE_NAME, storage=CachingMiddleware(JSONStorage))
        self.query = Query()
        @self.db.storage.on.write.post
        async def _print(ev, s, json_str):
            data = json.loads(json_str)
            # print('write', data)
            # json.dump(data, handle, ensure_ascii=False, indent=4)
            return json.dumps(data, ensure_ascii=False, indent=4)

    async def save_bot_value(self, chat_id: int, chat_key: int, chat_value: Any):
        result = await self.db.search((self.query.chat_id == chat_id) & (self.query.chat_key == chat_key))

        if chat_value is None:
            if result:
                await self.db.remove((self.query.chat_id == chat_id) & (self.query.chat_key == chat_key))
        else:
            if result:
                await self.db.update({'chat_value': str(chat_value)},
                                     (self.query.chat_id == chat_id) & (self.query.chat_key == chat_key))
            else:
                bot_entry = BotTable(
                    chat_id=chat_id,
                    chat_key=chat_key,
                    chat_value=str(chat_value)
                )
                await self.db.insert(bot_entry.model_dump())
        await self.db.storage.flush()

    async def load_bot_value(self, chat_id: int, chat_key: int, default_value: Any = ''):
        result = await self.db.search((self.query.chat_id == chat_id) & (self.query.chat_key == chat_key))
        return result[0].get('chat_value', default_value) if result else default_value

    async def get_chat_ids_by_key(self, chat_key: int) -> List[int]:
        results = await self.db.search(self.query.chat_key == chat_key)
        return [result['chat_id'] for result in results]

    async def get_chat_dict_by_key(self, chat_key: int, return_json=False) -> Dict[int, Any]:
        results = await self.db.search(self.query.chat_key == chat_key)
        if return_json:
            return {result['chat_id']: json.loads(result['chat_value']) for result in results}
        else:
            return {result['chat_id']: result['chat_value'] for result in results}


async def test_unit():
    bot_db = BotJsonConfig()

    # Вставка 5 записей
    await bot_db.save_bot_value(1, 101, 'Value 1')
    await bot_db.save_bot_value(2, 102, 'Value 2')
    await bot_db.save_bot_value(3, 103, 'Value 3')
    await bot_db.save_bot_value(4, 104, 'Value 4')
    await bot_db.save_bot_value(5, 105, 'Value 5')

    # Обновление пары записей
    await bot_db.save_bot_value(1, 101, 'Updated Value 1')
    await bot_db.save_bot_value(2, 102, 'Привет привет привет 2')

    # Удаление пары записей
    await bot_db.save_bot_value(3, 103, None)
    await bot_db.save_bot_value(4, 104, None)

    # Проверка корректности работы
    records = await bot_db.db.all()
    print(records)

    # Проверка конкретных записей
    assert any(
        record['chat_id'] == 1 and record['chat_key'] == 101 and record['chat_value'] == 'Updated Value 1' for record in
        records)
    assert any(
        record['chat_id'] == 2 and record['chat_key'] == 102 and record['chat_value'] == 'Привет привет привет 2' for
        record in
        records)
    assert not any(record['chat_id'] == 3 and record['chat_key'] == 103 for record in records)
    assert not any(record['chat_id'] == 4 and record['chat_key'] == 104 for record in records)
    assert any(record['chat_id'] == 5 and record['chat_key'] == 105 and record['chat_value'] == 'Value 5' for record in
               records)

    print("Все проверки пройдены успешно.")


def transform_json(input_file_path, output_file_path):
    # Load the original JSON file
    with open(input_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Initialize the new structure
    new_structure = {"_default": {}}

    # Iterate over the records in the original data
    for record in data["RecordSet"]:
        id_str = str(record["ID"])
        new_structure["_default"][id_str] = {
            "chat_id": record["CHAT_ID"],
            "chat_key": record["CHAT_KEY"],
            "chat_value": record["CHAT_VALUE"]
        }

    # Output the new structure to a JSON file
    with open(output_file_path, 'w', encoding='utf-8') as file:
        json.dump(new_structure, file, ensure_ascii=False, indent=4)

    print("Transformation complete. New file saved as '{}'.".format(output_file_path))

# Example usage


if __name__ == '__main__':
    pass
    # asyncio.run(test_unit())
    # transform_json('test3.json', 'transformed_data.json')
