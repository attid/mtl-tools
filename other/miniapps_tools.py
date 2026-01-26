
import aiohttp
from dataclasses import dataclass
from loguru import logger

from other.config_reader import config
from other.global_data import adv_text
from other.pyro_tools import MessageInfo


@dataclass
class MiniAppPage:
    url: str


class MiniAppsAPI:
    BASE_URL = "https://mtlminiapps.us"

    def __init__(self, key: str | None):
        self.key = key

    async def create_stateless_page(self, html_content: str) -> MiniAppPage:
        if not self.key:
             logger.warning("MiniApps key is not set. Page creation might fail.")
        
        url = f"{self.BASE_URL}/api/generate"
        
        data = {
            "key": self.key,
            "html": html_content,
            "compress": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    json_data = await response.json()
                    # Response: {"url": "full_url"}
                    return MiniAppPage(url=json_data['url'])
                else:
                    text = await response.text()
                    raise Exception(f"Error creating page: {response.status} {text}")

    async def create_uuid_page(self, msg_info: MessageInfo) -> MiniAppPage:
        # Note: Ideally this method name should be updated since we are not using UUIDs anymore,
        # but keeping it for compatibility with existing calls.
        html_text = f'Сообщение от {msg_info.user_from} <br>'
        html_text += msg_info.message_text
        if msg_info.reply_to_message:
            html_text += f'<br><br>{adv_text}<br><br>'
            html_text += f'Ответ на сообщение от {msg_info.reply_to_message.user_from}: <br>'
            html_text += f'{msg_info.reply_to_message.message_text}'
            
        full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Message from {msg_info.user_from}</title>
<style>
body {{ font-family: sans-serif; padding: 20px; line-height: 1.6; max-width: 800px; margin: 0 auto; }}
img {{ max-width: 100%; height: auto; }}
blockquote {{ border-left: 2px solid #ccc; margin-left: 0; padding-left: 10px; color: #555; }}
</style>
</head>
<body>
{html_text}
</body>
</html>
"""
        return await self.create_stateless_page(full_html)

miniapps = MiniAppsAPI(config.miniapps_key)
