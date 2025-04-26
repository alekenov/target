# Инструкция по развертыванию Facebook Ads Dashboard в AWS Lambda

## Подготовка к развертыванию

1. Убедитесь, что у вас есть ZIP-архив `dashboard_lambda_package.zip`, созданный с помощью скрипта `prepare_lambda_package.sh`
2. Проверьте, что размер архива не превышает лимиты AWS Lambda (50 МБ для прямой загрузки)

## Создание Lambda-функции

1. Войдите в консоль AWS и перейдите в сервис Lambda
2. Нажмите "Create function" (Создать функцию)
3. Выберите "Author from scratch" (Создать с нуля)
4. Заполните основные настройки:
   - Function name: `facebook-ads-dashboard`
   - Runtime: Python 3.9
   - Architecture: x86_64
   - Permissions: Create a new role with basic Lambda permissions

5. Нажмите "Create function" (Создать функцию)

## Загрузка кода

1. В разделе "Code source" (Исходный код) нажмите "Upload from" (Загрузить из) и выберите ".zip file" (.zip файл)
2. Загрузите файл `dashboard_lambda_package.zip`
3. В поле "Handler" (Обработчик) укажите: `lambda_handler.lambda_handler`

## Настройка переменных окружения

В разделе "Configuration" (Конфигурация) -> "Environment variables" (Переменные окружения) добавьте следующие переменные:

```
AURORA_HOST=<адрес_базы_данных>
AURORA_PORT=3306
AURORA_DATABASE_NAME=<имя_базы_данных>
AURORA_MASTER_USERNAME=<имя_пользователя>
AURORA_MASTER_PASSWORD=<пароль>
FACEBOOK_APP_ID=<идентификатор_приложения>
FACEBOOK_APP_SECRET=<секрет_приложения>
FACEBOOK_ACCESS_TOKEN=<токен_доступа>
FACEBOOK_AD_ACCOUNT_ID=<идентификатор_рекламного_аккаунта>
```

## Настройка функции URL

1. В разделе "Configuration" (Конфигурация) -> "Function URL" (URL функции) нажмите "Create function URL" (Создать URL функции)
2. Выберите "Auth type: NONE" (Тип аутентификации: Нет)
3. Включите "Configure cross-origin resource sharing (CORS)" (Настроить совместное использование ресурсов между источниками)
4. Нажмите "Save" (Сохранить)

## Настройка таймаута и памяти

1. В разделе "Configuration" (Конфигурация) -> "General configuration" (Общая конфигурация) нажмите "Edit" (Редактировать)
2. Установите:
   - Memory (Память): 256 МБ
   - Timeout (Таймаут): 30 секунд
3. Нажмите "Save" (Сохранить)

## Тестирование функции

1. После создания функции URL, откройте его в браузере
2. Вы должны увидеть дашборд Facebook Ads

## Настройка регулярного обновления данных

Для автоматического обновления данных о рекламных кампаниях можно настроить EventBridge:

1. Перейдите в сервис EventBridge
2. Создайте новое правило:
   - Name: `facebook-ads-data-update`
   - Schedule: Cron expression `0 8 * * ? *` (ежедневно в 8:00 UTC)
   - Target: Lambda function `facebook-ads-dashboard`
   - Input: Constant (JSON text) `{"path": "/update_data", "httpMethod": "GET"}`
3. Нажмите "Create" (Создать)

## Мониторинг и логирование

Для мониторинга работы Lambda-функции:

1. Перейдите в раздел "Monitor" (Мониторинг) вашей Lambda-функции
2. Проверьте логи в CloudWatch Logs
3. Настройте оповещения в CloudWatch Alarms для отслеживания ошибок

## Безопасность

1. Рассмотрите возможность добавления базовой аутентификации к URL функции
2. Используйте AWS Secrets Manager для хранения чувствительных данных
3. Настройте IAM-роль Lambda с минимально необходимыми разрешениями
