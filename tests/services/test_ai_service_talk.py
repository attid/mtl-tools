import pytest
from unittest.mock import AsyncMock

import other.open_ai_tools as open_ai_tools
from services.external_services import AIService


@pytest.mark.asyncio
async def test_ai_service_talk_maps_gpt4_to_gpt_maxi(monkeypatch):
    mock_talk = AsyncMock(return_value="ok")
    monkeypatch.setattr(open_ai_tools, "talk", mock_talk)

    service = AIService()
    result = await service.talk(123, "Привет как дела", gpt4=True, googleit=True)

    assert result == "ok"
    mock_talk.assert_awaited_once()
    call = mock_talk.await_args
    assert call.args == (123, "Привет как дела")
    assert call.kwargs["gpt_maxi"] is True
    assert call.kwargs["googleit"] is True
    assert "gpt4" not in call.kwargs
