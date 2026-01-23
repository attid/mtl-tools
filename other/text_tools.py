import re
from loguru import logger

def extract_url(msg: str, surl: str = 'eurmtl.me') -> str | None:
    try:
        if surl:
            pattern = rf"https?://{surl}[^\s]+"
        else:
            pattern = r"https?://[^\s]+"

        search_result = re.search(pattern, msg)

        if search_result:
            return search_result.group(0)
        else:
            return None
    except Exception as e:
        logger.error(f"Error extracting URL: {e}")
        return None
