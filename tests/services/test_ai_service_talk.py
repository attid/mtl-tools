import pytest

import other.open_ai_tools as open_ai_tools
from services.external_services import AIService
from tests.fakes import FakeAsyncMethod


@pytest.mark.asyncio
async def test_ai_service_talk_maps_gpt4_to_gpt_maxi(monkeypatch):
    mock_talk = FakeAsyncMethod(return_value="ok")
    monkeypatch.setattr(open_ai_tools, "talk", mock_talk)

    service = AIService()
    result = await service.talk(123, "Привет как дела", gpt4=True, googleit=True)

    assert result == "ok"
    mock_talk.assert_awaited_once()
    args, kwargs = mock_talk.call_args
    assert args == (123, "Привет как дела")
    assert kwargs["gpt_maxi"] is True
    assert kwargs["googleit"] is True
    assert "gpt4" not in kwargs
