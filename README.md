# GooseBot 🪿

Короткие и уместные ответы, немного безумия, периодическое «Кря». Поддерживает DM и группы/каналы.

## Быстрый старт (Docker)
1) Скопируй `.env.example` → `.env` и заполни `BOT_TOKEN`, `PUBLIC_URL`, `OPENROUTER_KEY`.
2) `docker compose up --build -d`
3) `make set-webhook` (или `./scripts/set_webhook.sh` с экспортированными переменными)
4) Проверь `/serve` на твоём домене: должен вернуть `{ "ok": true, "ping": "🪿" }`

## Локальная разработка
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Настройка поведения
- Переменные `.env`: `QUACK_FREQ_DM`, `GROUP_REACT_PROB`, `GROUP_RANDOM_QUACK`, `COOLDOWN_SEC`, `DM_MAX_WORDS`, `GROUP_MAX_WORDS`.
- Фразы редактируются в `assets/one_liners.json`.

## Мемы
- Сейчас отправляется текстовый мем. Позже добавь `sendPhoto` с реальными `file_id`.

## Примечания безопасности
- Бот не даёт советы по преступлениям и не обсуждает 18+ темы.
