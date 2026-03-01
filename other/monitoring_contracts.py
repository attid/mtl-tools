import re
from dataclasses import dataclass
from urllib.parse import quote, unquote


PONG_PATTERN = re.compile(r"#skynet\s+#mmwb\s+command=pong", re.IGNORECASE)
HELPER_PATTERN = re.compile(r"#skynet\s+#helper\b", re.IGNORECASE)


@dataclass(frozen=True)
class HelperEvent:
    command: str
    user_id: int
    agent_username: str
    url: str
    ack_url: str
    username: str | None = None


def parse_kv_payload(text: str) -> dict[str, str]:
    pairs = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)=([^\s]+)", text)
    return {k: v for k, v in pairs}


def is_mmwb_pong(text: str) -> bool:
    return bool(PONG_PATTERN.search(text))


def is_helper_event(text: str) -> bool:
    return bool(HELPER_PATTERN.search(text))


def parse_helper_event(text: str) -> HelperEvent:
    payload = parse_kv_payload(text)
    command = payload.get("command", "").lower()
    if command not in {"taken", "closed"}:
        raise ValueError("unknown command")

    url_raw = payload.get("url")
    if not url_raw:
        raise ValueError("missing url")
    url = unquote(url_raw)
    ack_url = quote(url, safe="")

    user_id = int(payload["user_id"])
    agent_username = payload["agent_username"]

    if command == "taken":
        username = payload["username"]
        return HelperEvent(
            command=command,
            user_id=user_id,
            username=username,
            agent_username=agent_username,
            url=url,
            ack_url=ack_url,
        )

    if payload.get("closed", "").lower() != "true":
        raise ValueError("closed flag must be true")

    return HelperEvent(
        command=command,
        user_id=user_id,
        username=None,
        agent_username=agent_username,
        url=url,
        ack_url=ack_url,
    )
