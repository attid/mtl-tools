# unban-button-ack: сохранять кнопку unban как след действия

## Контекст
- После нажатия `unban` callback inline-клавиатура исчезает.
- Требуемое поведение: кнопка должна заменяться на кнопку-подтверждение с username пользователя, который выполнил unban, и `callback_data="👀"`.

## План изменений
1. [x] Добавить регрессионный тест на `unban` callback с проверкой `editMessageReplyMarkup`.
2. [x] Обновить `routers/moderation.py`, чтобы вместо удаления клавиатуры она заменялась на кнопку с username.
3. [x] Обновить/добавить тесты.
4. [x] Docs не требуются: меняется только UI-поведение callback-кнопки.
5. [x] Проверка: `uv run pytest tests/routers/test_moderation.py -q`.

## Риски и открытые вопросы
- Нужно сохранить текущее действие `unban` без регрессии в бизнес-логике.
- Текст кнопки должен корректно деградировать, если username отсутствует.

## Верификация
- Нажать `unban` callback в тесте.
- Проверить `unbanChatMember`, `answerCallbackQuery` и `editMessageReplyMarkup`.
- Проверить, что в markup есть текст с username и `callback_data="👀"`.
