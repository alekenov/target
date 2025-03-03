# Facebook Ads Hourly Report Lambda

## Описание
Lambda функция для автоматического сбора данных о рекламных кампаниях Facebook и отправки hourly отчетов в Telegram.

## Архитектура
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 300 seconds
- **Trigger**: EventBridge (CloudWatch Events) - каждый час
- **Handler**: lambda_function.lambda_handler

## Зависимости
- facebook-business==17.0.0 - Facebook Marketing API SDK
- python-telegram-bot==21.11.1 - Telegram Bot API
- asyncio - для асинхронных операций

## Переменные окружения
```
FB_APP_ID - ID приложения Facebook
FB_ACCESS_TOKEN - Токен доступа Facebook
FB_ACCOUNT_ID - ID рекламного аккаунта Facebook
TELEGRAM_BOT_TOKEN - Токен Telegram бота
TELEGRAM_CHAT_ID - ID чата для отправки отчетов
```

## Основные компоненты

### 1. Facebook API Интеграция
- Авторизация через access token
- Получение данных о кампаниях и их эффективности
- Обработка ошибок API и повторные попытки

### 2. Формирование отчета
- Сбор метрик за последний час
- Расчет ключевых показателей
- Форматирование данных для отправки

### 3. Telegram интеграция
- Асинхронная отправка сообщений
- Форматирование текста отчета
- Обработка ошибок отправки

## Развертывание

### Подготовка пакета
```bash
./prepare_minimal_lambda.sh
```

### Обновление кода функции
```bash
aws lambda update-function-code \
  --function-name fb-ads-hourly-report \
  --s3-bucket fb-ads-reports-7775438a \
  --s3-key minimal_lambda_package.zip
```

### Настройка расписания
```bash
# Создание правила EventBridge
aws events put-rule \
  --name fb-ads-daily-report \
  --schedule-expression "cron(0 * * * ? *)" \
  --description "Запуск отчета по Facebook Ads каждый час"

# Добавление разрешений для Lambda
aws lambda add-permission \
  --function-name fb-ads-hourly-report \
  --statement-id fb-ads-daily-report \
  --action 'lambda:InvokeFunction' \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:783764574393:rule/fb-ads-daily-report

# Настройка цели для правила
aws events put-targets \
  --rule fb-ads-daily-report \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:783764574393:function:fb-ads-hourly-report"
```

## Мониторинг

### CloudWatch Logs
- Логи доступны в группе `/aws/lambda/fb-ads-hourly-report`
- Каждый запуск создает новый поток логов
- Логи содержат информацию о выполнении и ошибках

### Проверка статуса
```bash
# Ручной запуск функции
aws lambda invoke \
  --function-name fb-ads-hourly-report \
  --payload '{}' \
  response.json

# Просмотр логов
aws logs get-log-events \
  --log-group-name /aws/lambda/fb-ads-hourly-report \
  --log-stream-name "YYYY/MM/DD/[$LATEST]XXXXX"
```

## Обработка ошибок
1. **Facebook API**
   - Автоматические повторные попытки при ошибках сети
   - Логирование неудачных запросов
   - Обработка ограничений API

2. **Telegram**
   - Асинхронная отправка с таймаутом
   - Повторные попытки при ошибках сети
   - Логирование статуса отправки

## Безопасность
- Все чувствительные данные хранятся в переменных окружения Lambda
- Минимальные IAM разрешения для функции
- Безопасное хранение токенов и ключей

## Обслуживание
1. **Обновление токенов**
   - Регулярная проверка срока действия FB_ACCESS_TOKEN
   - Обновление через переменные окружения Lambda

2. **Мониторинг использования**
   - Отслеживание расхода памяти
   - Контроль времени выполнения
   - Проверка количества ошибок

3. **Оптимизация**
   - Регулярный анализ логов
   - Настройка таймаутов
   - Оптимизация размера пакета

## Устранение неполадок
1. **Отчет не отправляется**
   - Проверить логи CloudWatch
   - Убедиться в валидности токенов
   - Проверить права доступа

2. **Ошибки Facebook API**
   - Проверить лимиты API
   - Обновить токен доступа
   - Проверить права приложения

3. **Проблемы с Telegram**
   - Проверить права бота
   - Убедиться в корректности CHAT_ID
   - Проверить статус Telegram API
