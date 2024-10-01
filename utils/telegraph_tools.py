import uuid
from dataclasses import dataclass

import aiohttp

from utils.config_reader import config
from utils.converter import convert_html_to_telegraph_format
from utils.global_data import adv_text
from utils.pyro_tools import MessageInfo


@dataclass
class TelegraphArticle:
    path: str
    url: str
    title: str
    description: str
    views: int
    can_edit: bool


def parse_telegraph_response(response: dict) -> TelegraphArticle:
    article = TelegraphArticle(
        path=response['path'],
        url=response['url'],
        title=response['title'],
        description=response['description'],
        views=response['views'],
        can_edit=response['can_edit']
    )
    return article


class TelegraphAPI:
    BASE_URL = "https://api.telegra.ph"

    def __init__(self, access_token):
        self.access_token = access_token

    async def create_page(self, title, content, author_name=None, author_url=None,
                          return_content=False) -> TelegraphArticle:
        """
        Создает новую страницу (статью) в Telegraph.

        :param title: Заголовок страницы
        :param content: HTML-контент страницы или список элементов в формате Telegraph
        :param author_name: Имя автора (опционально)
        :param author_url: URL автора (опционально)
        :param return_content: Если True, возвращает содержимое страницы в ответе
        :return: Словарь с информацией о созданной странице
        """
        url = f"{self.BASE_URL}/createPage"

        if isinstance(content, str):
            content = convert_html_to_telegraph_format(content)

        data = {
            "access_token": self.access_token,
            "title": title,
            "content": content,
            "return_content": return_content
        }

        if author_name:
            data["author_name"] = author_name
        if author_url:
            data["author_url"] = author_url

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    json_data = await response.json()
                    if json_data['ok']:
                        # if return_content:
                        #     return parse_telegraph_response(json_data['result']).
                        return parse_telegraph_response(json_data['result'])
                else:
                    raise Exception(f"Ошибка при создании страницы: {response.status}")

    async def create_uuid_page(self, msg_info: MessageInfo):
        html_text = f'Сообщение от {msg_info.user_from} <br>'
        html_text += msg_info.message_text
        if msg_info.reply_to_message:
            html_text += f'<br><br>{adv_text}<br><br>'
            html_text += f'Ответ на сообщение от {msg_info.reply_to_message.user_from}: <br>'
            html_text += f'{msg_info.reply_to_message.message_text}'
        return await self.create_page(
            uuid.uuid4().hex,
            html_text
        )


telegraph = TelegraphAPI(config.telegraph_token)


# Пример использования:
async def main():
    msg_info = None

    print(await telegraph.create_uuid_page(msg_info))

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
