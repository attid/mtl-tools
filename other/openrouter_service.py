import asyncio
from typing import Optional

from loguru import logger
from openai import AsyncOpenAI

from other.config_reader import config
from other.openrouter_reactions import build_messages, normalize_label

_client: Optional[AsyncOpenAI] = None

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "google/gemini-3-flash-preview"
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://montelibero.org",
    "X-Title": "Montelibero Bot",
}


def _get_client() -> AsyncOpenAI:
    global _client
    if not config.openrouter_key:
        return None
    if _client is None:
        _client = AsyncOpenAI(
            api_key=config.openrouter_key.get_secret_value(),
            base_url=OPENROUTER_BASE_URL,
        )
    return _client


async def classify_message(text: str, timeout_sec: float = 10.0) -> Optional[str]:
    client = _get_client()
    if client is None:
        return None
    messages = build_messages(text)
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=OPENROUTER_MODEL,
                extra_headers=OPENROUTER_HEADERS,
                messages=messages,
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
