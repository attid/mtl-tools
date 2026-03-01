import pytest

from other.monitoring_contracts import (
    is_helper_event,
    is_mmwb_pong,
    parse_helper_event,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#skynet #mmwb command=pong", True),
        ("#skynet #mmwb command=pong status=ok", True),
        ("#mmwb #skynet command=pong", False),
        ("#skynet #mmwb command=ping", False),
    ],
)
def test_is_mmwb_pong(text, expected):
    assert is_mmwb_pong(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#skynet #helper command=taken user_id=1 username=u agent_username=a url=https://t.me/c/1/2", True),
        ("#helper #skynet command=taken user_id=1 username=u agent_username=a url=https://t.me/c/1/2", False),
    ],
)
def test_is_helper_event(text, expected):
    assert is_helper_event(text) is expected


@pytest.mark.parametrize(
    ("text", "command", "url", "ack_url", "username"),
    [
        (
            "#skynet #helper command=taken user_id=123 username=client1 agent_username=agent1 url=https://t.me/c/2032873651/69621",
            "taken",
            "https://t.me/c/2032873651/69621",
            "https%3A%2F%2Ft.me%2Fc%2F2032873651%2F69621",
            "client1",
        ),
        (
            "#skynet #helper command=taken user_id=123 username=client1 agent_username=agent1 url=https%3A%2F%2Ft.me%2Fc%2F1466779498%2F25527",
            "taken",
            "https://t.me/c/1466779498/25527",
            "https%3A%2F%2Ft.me%2Fc%2F1466779498%2F25527",
            "client1",
        ),
        (
            "#skynet #helper command=closed user_id=123 agent_username=agent1 url=https://t.me/c/2032873651/69621 closed=true",
            "closed",
            "https://t.me/c/2032873651/69621",
            "https%3A%2F%2Ft.me%2Fc%2F2032873651%2F69621",
            None,
        ),
    ],
)
def test_parse_helper_event_valid(text, command, url, ack_url, username):
    event = parse_helper_event(text)
    assert event.command == command
    assert event.url == url
    assert event.ack_url == ack_url
    assert event.username == username


@pytest.mark.parametrize(
    "text",
    [
        "#skynet #helper command=unknown user_id=1 url=https://t.me/c/1/2",
        "#skynet #helper command=taken user_id=1 username=u agent_username=a",
        "#skynet #helper command=taken user_id=abc username=u agent_username=a url=https://t.me/c/1/2",
        "#skynet #helper command=taken user_id=1 agent_username=a url=https://t.me/c/1/2",
        "#skynet #helper command=closed user_id=1 agent_username=a url=https://t.me/c/1/2",
    ],
)
def test_parse_helper_event_invalid(text):
    with pytest.raises((ValueError, KeyError)):
        parse_helper_event(text)
