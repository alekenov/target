# Настройка Telegram бота для отправки отчетов

Это руководство поможет вам создать и настроить Telegram бота для отправки отчетов по рекламным кампаниям Facebook.

## 1. Создание бота через BotFather

1. Откройте Telegram и найдите [@BotFather](https://t.me/botfather)
2. Отправьте команду `/newbot`
3. Введите имя бота (например, "Facebook Ads Reports")
4. Введите уникальное имя пользователя для бота (должно заканчиваться на "bot", например "fb_ads_reports_bot")
5. BotFather предоставит вам токен бота. Сохраните его в надежном месте - это значение будет использоваться в переменной окружения `TELEGRAM_BOT_TOKEN`

## 2. Настройка бота

### Установка описания и команд

1. Отправьте команду `/setdescription` в чат с BotFather
2. Выберите вашего бота
3. Введите описание, например: "Бот для получения ежедневных отчетов по рекламным кампаниям Facebook"

4. Отправьте команду `/setcommands` в чат с BotFather
5. Выберите вашего бота
6. Введите список команд в формате:
```
report - Получить последний отчет
status - Проверить статус системы
help - Показать справку
```

### Настройка изображения профиля (опционально)

1. Отправьте команду `/setuserpic` в чат с BotFather
2. Выберите вашего бота
3. Отправьте изображение, которое будет использоваться как аватар бота

## 3. Получение ID чата

Существует несколько способов получить ID чата:

### Способ 1: Использование userinfobot

1. Найдите [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте любое сообщение этому боту
3. Бот ответит с вашим ID пользователя, который можно использовать как ID чата для личных сообщений

### Способ 2: Использование API Telegram

1. Добавьте вашего бота в чат (личный или групповой)
2. Отправьте любое сообщение в этот чат
3. Откройте в браузере URL:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```
(замените `<YOUR_BOT_TOKEN>` на токен вашего бота)

4. В ответе найдите поле `chat.id` - это и есть ID чата
5. Для групповых чатов ID будет отрицательным числом, для личных - положительным

## 4. Тестирование бота

Проверьте, что бот работает, отправив тестовое сообщение:

```
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" -d "chat_id=<YOUR_CHAT_ID>&text=Тестовое сообщение"
```

Замените:
- `<YOUR_BOT_TOKEN>` на токен вашего бота
- `<YOUR_CHAT_ID>` на ID чата

Если все настроено правильно, бот отправит сообщение "Тестовое сообщение" в указанный чат.

## 5. Интеграция с Lambda функцией

1. Добавьте переменные окружения в вашу Lambda функцию:
```
TELEGRAM_BOT_TOKEN=<YOUR_BOT_TOKEN>
TELEGRAM_CHAT_ID=<YOUR_CHAT_ID>
```

2. Используйте следующий код Python для отправки сообщений через бота:

```python
import requests

def send_telegram_message(message, chat_id=None, bot_token=None):
    """
    Отправляет сообщение через Telegram бота.
    
    Args:
        message (str): Текст сообщения
        chat_id (str, optional): ID чата. По умолчанию берется из переменных окружения.
        bot_token (str, optional): Токен бота. По умолчанию берется из переменных окружения.
    
    Returns:
        bool: True если сообщение успешно отправлено, иначе False
    """
    import os
    
    # Получаем значения из переменных окружения, если не указаны явно
    bot_token = bot_token or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = chat_id or os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("Ошибка: не указаны TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"  # Поддерживает HTML-форматирование
    }
    
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")
        return False
```

## 6. Отправка форматированных сообщений

Telegram поддерживает HTML-форматирование в сообщениях. Вы можете использовать следующие теги:

- `<b>Жирный текст</b>`
- `<i>Курсив</i>`
- `<u>Подчеркнутый</u>`
- `<s>Зачеркнутый</s>`
- `<code>Моноширинный шрифт</code>`
- `<pre>Блок кода</pre>`
- `<a href="URL">Ссылка</a>`

Пример форматированного отчета:

```python
def send_campaign_report(campaigns_data):
    """
    Отправляет отформатированный отчет по кампаниям в Telegram.
    
    Args:
        campaigns_data (list): Список словарей с данными кампаний
    """
    report = "<b>📊 Отчет по рекламным кампаниям</b>\n\n"
    
    for campaign in campaigns_data:
        status_emoji = "✅" if campaign["status"] == "ACTIVE" else "❌"
        
        report += f"{status_emoji} <b>{campaign['name']}</b>\n"
        report += f"Расходы: <b>{campaign['spend']} {campaign['currency']}</b>\n"
        report += f"Результаты: <b>{campaign['results']}</b>\n"
        report += f"Цена за результат: <b>{campaign['cost_per_result']} {campaign['currency']}</b>\n\n"
    
    report += "<i>Отчет сгенерирован автоматически</i>"
    
    send_telegram_message(report)
```

## 7. Отправка файлов

Для отправки файлов (например, CSV или PDF отчетов) используйте метод `sendDocument`:

```python
def send_telegram_document(file_path, caption=None, chat_id=None, bot_token=None):
    """
    Отправляет файл через Telegram бота.
    
    Args:
        file_path (str): Путь к файлу
        caption (str, optional): Подпись к файлу
        chat_id (str, optional): ID чата
        bot_token (str, optional): Токен бота
    
    Returns:
        bool: True если файл успешно отправлен, иначе False
    """
    import os
    
    bot_token = bot_token or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = chat_id or os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("Ошибка: не указаны TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    
    payload = {
        "chat_id": chat_id
    }
    
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "HTML"
    
    files = {
        "document": open(file_path, "rb")
    }
    
    try:
        response = requests.post(url, data=payload, files=files)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Ошибка при отправке файла в Telegram: {e}")
        return False
```

## 8. Обработка команд (для интерактивных ботов)

Если вы хотите, чтобы бот реагировал на команды пользователей, вам потребуется настроить webhook или использовать long polling:

```python
def handle_telegram_updates(event, context):
    """
    Обрабатывает входящие сообщения от Telegram.
    Эта функция может быть вызвана через API Gateway.
    
    Args:
        event: Событие Lambda
        context: Контекст Lambda
    """
    try:
        body = json.loads(event['body'])
        message = body.get('message', {})
        
        # Получаем текст сообщения и ID чата
        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id')
        
        if not text or not chat_id:
            return {'statusCode': 200}
        
        # Обрабатываем команды
        if text == '/report':
            # Генерируем и отправляем отчет
            send_campaign_report(get_campaigns_data())
        elif text == '/status':
            # Отправляем статус системы
            send_telegram_message("Система работает нормально", chat_id=chat_id)
        elif text == '/help':
            # Отправляем справку
            help_text = (
                "<b>Доступные команды:</b>\n"
                "/report - Получить последний отчет\n"
                "/status - Проверить статус системы\n"
                "/help - Показать эту справку"
            )
            send_telegram_message(help_text, chat_id=chat_id)
        
        return {'statusCode': 200}
    except Exception as e:
        print(f"Ошибка при обработке сообщения Telegram: {e}")
        return {'statusCode': 500}
```

## 9. Настройка webhook (опционально)

Для обработки команд в реальном времени настройте webhook:

1. Создайте API Gateway в AWS
2. Настройте интеграцию с Lambda функцией
3. Получите URL вашего API Gateway
4. Настройте webhook:

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_API_GATEWAY_URL>
```

## 10. Безопасность

- Храните токен бота в безопасном месте (AWS Secrets Manager, Parameter Store)
- Не публикуйте токен бота в публичных репозиториях
- Используйте HTTPS для webhook
- Проверяйте подлинность входящих запросов от Telegram

## Полезные ресурсы

- [Официальная документация Telegram Bot API](https://core.telegram.org/bots/api)
- [BotFather](https://t.me/botfather) - создание и управление ботами
- [Форматирование сообщений в Telegram](https://core.telegram.org/bots/api#formatting-options)
- [Примеры ботов на Python](https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples)
