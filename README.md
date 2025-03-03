# Facebook Ads Monitoring Tool

Инструмент для мониторинга трат и производительности рекламных кампаний Facebook с возможностью отправки отчетов в Telegram и сохранения метрик в AWS Aurora MySQL.

## Основные компоненты

- `simple_lambda_function.py` - AWS Lambda функция для ежедневных отчетов о тратах Facebook в Telegram
- `check_today_spend.py` - Скрипт для проверки трат за сегодня, вчера или указанный период
- `fb_spend_monitor.py` - Скрипт для мониторинга активных кампаний и отправки уведомлений в Telegram

## Требования

- Python 3.9+
- Facebook Marketing API (facebook-business==17.0.0)
- python-telegram-bot[job-queue]==20.7
- python-dotenv==1.0.0
- pymysql==1.1.0

## Настройка

1. Убедитесь, что файл `.env` содержит все необходимые переменные окружения:

```bash
# Facebook API
FB_APP_ID=ваш_app_id
FB_APP_SECRET=ваш_app_secret
FB_ACCESS_TOKEN=ваш_access_token
FB_ACCOUNT_ID=act_ваш_account_id

# База данных AWS Aurora
DB_HOST=ваш_хост_базы_данных
DB_PORT=3306
DB_NAME=ваше_имя_базы
DB_USER=ваш_пользователь
DB_PASSWORD=ваш_пароль

# Telegram
TELEGRAM_BOT_TOKEN=ваш_telegram_bot_token
TELEGRAM_CHAT_ID=ваш_telegram_chat_id
```

2. Установите необходимые зависимости:

```bash
pip install -r requirements.txt
```

## Использование

### Проверка текущих трат

```bash
# Проверка трат за сегодня
python check_today_spend.py

# Проверка трат за вчера
python check_today_spend.py --yesterday

# Проверка трат за конкретную дату
python check_today_spend.py --date 2025-03-01

# Проверка трат за последние N дней
python check_today_spend.py --days 7
```

### Мониторинг активных кампаний

```bash
python fb_spend_monitor.py
```

### AWS Lambda функция

Lambda функция `simple_lambda_function.py` предназначена для запуска в AWS Lambda с настроенным триггером EventBridge, чтобы автоматически отправлять отчеты в заданное время.

## Формат отчета

```
📊 *Отчет о тратах на рекламу Facebook*
📅 Дата: 2025-03-01
🆔 Аккаунт: act_4795321857166878

*1. Широкая / эквадорские розы / 01,03*
💰 Расход: 12.93 USD
👁 Показы: 1,901
🖱 Клики: 63
📈 CTR: 3.31%
💵 CPC: 0.21 USD
💬 Переписки: 9
📊 Цена за переписку: 1.44 USD

...

*ИТОГО:*
💰 Общий расход: 47.82 USD
💬 Всего переписок: 68
📊 Средняя цена за переписку: 0.70 USD
📋 Всего активных кампаний: 4
```

## Примечания

- Инструмент использует Facebook Marketing API для получения данных о кампаниях
- Для работы инструмента необходимы права доступа к рекламному аккаунту Facebook
- Данные могут быть сохранены в базу данных AWS Aurora MySQL для дальнейшего анализа
- Для получения доступа к Facebook Marketing API необходимо создать приложение в [Facebook Developers](https://developers.facebook.com/)
