# Деплой FitTrain Bot на Replit

Этот архив подготовлен для деплоя Telegram-бота на Replit как постоянного фонового процесса.

## Что внутри архива

- `app/` - код Telegram-бота
- `run.py` - точка входа
- `requirements.txt` - Python-зависимости
- `.replit` - команда запуска для Replit
- `.env.example` - пример переменных окружения

В архив специально не добавлены:

- `.env` - там должен быть приватный токен бота
- `fittrain.db` - локальная база с данными
- `__pycache__/` и тестовые кеши
- `cms/` - CMS-панель деплоится отдельно, если она нужна

При первом запуске бот сам создаст SQLite-базу `fittrain.db` и начальные типы тренировок.

## Переменные окружения

Добавьте их в Replit Secrets:

```env
BOT_TOKEN=123456:ABCDEF...
DATABASE_URL=sqlite+aiosqlite:///fittrain.db
BOT_TIMEZONE=Europe/Moscow
ADMIN_IDS=123456789
CMS_API_URL=http://localhost:8000/api
CMS_FRONTEND_URL=http://localhost:3000
EVENING_CHECK_HOUR=20
FOLLOWUP_DELAY_MINUTES=30
```

Обязательная переменная: `BOT_TOKEN`.

Рекомендуемые:

- `DATABASE_URL=sqlite+aiosqlite:///fittrain.db`
- `BOT_TIMEZONE=Europe/Moscow`
- `ADMIN_IDS=<ваш Telegram ID>`

`CMS_API_URL` и `CMS_FRONTEND_URL` нужны только если вы отдельно поднимаете CMS.

## Команды

Команда запуска:

```bash
python run.py
```

Если зависимости не установились автоматически, выполните в Shell:

```bash
pip install -r requirements.txt
```

## Рекомендуемый тип деплоя

Выбирайте `Reserved VM` и режим `Background worker`.

Бот работает через Telegram long polling, поэтому ему не нужен публичный HTTP-порт. Для такого процесса Autoscale не подходит, потому что инстансы могут засыпать или масштабироваться до нуля.
