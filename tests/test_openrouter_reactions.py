from other.openrouter_reactions import build_messages, label_to_emoji, normalize_label


def test_normalize_label_known_values():
    assert normalize_label("backseat") == "backseat"
    assert normalize_label("лучшееб") == "лучшееб"
    assert normalize_label("лидер.") == "лидер"
    assert normalize_label("None") is None
    assert normalize_label(None) is None


def test_label_to_emoji_mapping():
    assert label_to_emoji("backseat") == "🤬"
    assert label_to_emoji("красавчик") == "💪"
    assert label_to_emoji("unknown") is None
    assert label_to_emoji(None) is None


def test_build_messages_structure():
    messages = build_messages("test message")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "test message"
