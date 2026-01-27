
import aiohttp
from dataclasses import dataclass
from loguru import logger

from other.config_reader import config
from other.global_data import adv_text
from other.pyro_tools import MessageInfo


@dataclass
class MiniAppPage:
    url: str


def _text_to_html(text: str) -> str:
    """Convert plain text to HTML paragraphs.

    Double newlines become paragraph breaks.
    Single newlines become <br> within paragraphs.
    """
    paragraphs = text.split('\n\n')
    html_paragraphs = []
    for p in paragraphs:
        p = p.strip()
        if p:
            p_with_br = p.replace('\n', '<br>\n')
            html_paragraphs.append(f'<p>{p_with_br}</p>')
    return '\n'.join(html_paragraphs)


HTML_HEAD = """<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        html {{
            background-color: #f1f5f9;
            min-height: 100%;
            padding: 20px;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: #ffffff;
            color: #334155;
            font-size: 16px;
            line-height: 1.6;
            max-width: 760px;
            margin: 0 auto;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        b {{
            color: #0f172a;
            font-weight: 600;
        }}
        a {{
            color: #2563eb;
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.2s;
        }}
        a:hover {{
            border-bottom-color: #2563eb;
        }}
        blockquote {{
            border-left: 4px solid #cbd5e1;
            margin: 20px 0;
            padding: 10px 16px;
            color: #64748b;
            font-style: italic;
            background: #f8fafc;
            border-radius: 0 8px 8px 0;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            display: block;
            margin: 10px 0;
        }}
        p {{
            margin: 0 0 1em 0;
        }}
        p:last-child {{
            margin-bottom: 0;
        }}
        @media (max-width: 600px) {{
            html {{ padding: 0; }}
            body {{
                padding: 20px;
                border-radius: 0;
                box-shadow: none;
            }}
        }}
    </style>
</head>"""


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
        title = f"Message from {msg_info.user_from}"

        body_parts = [f'<p><b>Сообщение от {msg_info.user_from}:</b></p>']
        body_parts.append(_text_to_html(msg_info.message_text))

        if msg_info.reply_to_message:
            body_parts.append(f'<p>{adv_text}</p>')
            body_parts.append(f'<blockquote><b>Ответ на сообщение от {msg_info.reply_to_message.user_from}:</b><br>')
            body_parts.append(_text_to_html(msg_info.reply_to_message.message_text))
            body_parts.append('</blockquote>')

        body_html = '\n'.join(body_parts)

        full_html = f"""<!DOCTYPE html>
<html>
{HTML_HEAD.format(title=title)}
<body>
{body_html}
</body>
</html>"""
        return await self.create_stateless_page(full_html)

miniapps = MiniAppsAPI(config.miniapps_key)
