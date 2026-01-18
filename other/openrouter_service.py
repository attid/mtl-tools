import asyncio
from typing import Optional

from loguru import logger
from openrouter import OpenRouter

from other.config_reader import config
from other.openrouter_reactions import build_messages, normalize_label

OPENROUTER_MODEL = "google/gemini-3-flash-preview"
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://montelibero.org",
    "X-Title": "Montelibero Bot",
}


async def classify_message(text: str, timeout_sec: float = 10.0) -> Optional[str]:
    if not config.openrouter_key:
        return None
    messages = build_messages(text)
    try:
        async with OpenRouter(
            api_key=config.openrouter_key.get_secret_value()
        ) as client:
            response = await asyncio.wait_for(
                client.chat.send_async(
                    model=OPENROUTER_MODEL,
                    messages=messages,
                    extra_headers=OPENROUTER_HEADERS,
                ),
                timeout=timeout_sec,
            )
    except Exception as exc:
        logger.warning(f"OpenRouter request failed: {exc}")
        return None

    if not response.choices:
        return None
    content = response.choices[0].message.content if response.choices[0].message else None
    return normalize_label(content)
