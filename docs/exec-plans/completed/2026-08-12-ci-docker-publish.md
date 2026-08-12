# CI-DOCKER-01: Сборка и публикация Docker в GitHub Actions

## Контекст
- Docker-образ сейчас публикуется вручную командой `just push-gitdocker`.
- Старая команда отправляет образ в `ghcr.io/montelibero/skynet`, хотя пакет
  должен принадлежать текущей репе `attid/skynet_bot`.
- Публикация должна происходить автоматически только после успешного CI.

## План изменений
1. [x] Подтвердить отсутствие Docker-job и наличие старых push-рецептов.
2. [x] Добавить Docker build для pull request без публикации и без package write.
3. [x] Добавить публикацию `latest` и короткого SHA после push в `main`.
4. [x] Удалить ручные `push-gitdocker*` из `justfile`.
5. [x] Обновить `AGENTS.md` под автоматическую публикацию.
6. [x] Проверить workflow, Justfile, Docker build и проектные quality gates.

## Риски и открытые вопросы
- Первый push создаст новый GHCR package; его видимость и доступ production
  окружения должны соответствовать настройкам репозитория.
- Production должен использовать `ghcr.io/attid/skynet_bot:latest`, а не старый
  пакет `ghcr.io/montelibero/skynet:latest`.

## Верификация
- Pull request собирает образ, но шаги login/push не выполняются.
- Push в `main` публикует два тега в GHCR текущей репы.
- Docker job запускается только после `secrets`, `lint` и `test`.
- Локальная сборка Docker и проектные проверки завершаются успешно.
