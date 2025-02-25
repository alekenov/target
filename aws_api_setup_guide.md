# Настройка AWS Lambda через API

Это руководство описывает процесс настройки AWS Lambda для ежедневного отчета по рекламным кампаниям Facebook с использованием Python и boto3 API.

## Преимущества этого подхода

1. **Автоматизация** - весь процесс настройки автоматизирован с помощью скрипта Python
2. **Уникальные имена ресурсов** - скрипт генерирует уникальные имена для S3 бакетов, избегая конфликтов
3. **Полный контроль** - вы можете легко изменить любые параметры в скрипте
4. **Воспроизводимость** - вы можете запустить скрипт несколько раз для создания нескольких окружений

## Предварительные требования

1. **Python 3.9 или выше**
2. **Библиотека boto3**:
   ```bash
   pip install boto3
   ```
3. **Настроенные AWS учетные данные**:
   - Создайте файл `~/.aws/credentials` с вашими учетными данными:
     ```
     [default]
     aws_access_key_id = YOUR_ACCESS_KEY
     aws_secret_access_key = YOUR_SECRET_KEY
     ```
   - Или настройте переменные окружения:
     ```bash
     export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
     export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
     ```

## Шаг 1: Подготовка пакета Lambda

1. Убедитесь, что у вас установлен Python 3.9 или выше
2. Сделайте скрипт `prepare_lambda_package.sh` исполняемым:
   ```bash
   chmod +x prepare_lambda_package.sh
   ```
3. Запустите скрипт для создания пакета Lambda:
   ```bash
   ./prepare_lambda_package.sh
   ```
4. После выполнения скрипта будет создан файл `lambda_package.zip`

## Шаг 2: Настройка параметров в скрипте

Откройте файл `setup_aws_lambda.py` и замените следующие значения на ваши реальные данные:

```python
# Конфигурация AWS
AWS_REGION = 'us-east-1'  # Можно изменить на нужный регион

# Конфигурация Facebook и Telegram
FACEBOOK_APP_ID = 'YOUR_FB_APP_ID'
FACEBOOK_APP_SECRET = 'YOUR_FB_APP_SECRET'
FACEBOOK_ACCESS_TOKEN = 'YOUR_FB_ACCESS_TOKEN'
FACEBOOK_AD_ACCOUNT_ID = 'YOUR_FB_AD_ACCOUNT_ID'
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'
```

## Шаг 3: Запуск скрипта настройки

1. Запустите скрипт настройки:
   ```bash
   python setup_aws_lambda.py
   ```

2. Скрипт выполнит следующие действия:
   - Создаст S3 бакет с уникальным именем
   - Загрузит пакет Lambda в S3 бакет
   - Создаст IAM роль с необходимыми разрешениями
   - Создаст Lambda функцию
   - Настроит правило EventBridge для запуска функции ежедневно
   - Предложит протестировать функцию

3. После успешного выполнения скрипт выведет информацию о созданных ресурсах:
   ```
   === Ресурсы AWS успешно созданы ===
   S3 бакет: fb-ads-reports-XXXXXXXX
   IAM роль: fb-ads-lambda-role (arn:aws:iam::XXXXXXXXXXXX:role/fb-ads-lambda-role)
   Lambda функция: fb-ads-daily-report (arn:aws:lambda:us-east-1:XXXXXXXXXXXX:function:fb-ads-daily-report)
   EventBridge правило: fb-ads-daily-report-schedule (arn:aws:events:us-east-1:XXXXXXXXXXXX:rule/fb-ads-daily-report-schedule)
   ```

## Шаг 4: Проверка настройки

1. Войдите в консоль AWS и проверьте созданные ресурсы:
   - S3 бакет: `fb-ads-reports-XXXXXXXX`
   - IAM роль: `fb-ads-lambda-role`
   - Lambda функция: `fb-ads-daily-report`
   - EventBridge правило: `fb-ads-daily-report-schedule`

2. Вы можете вручную запустить Lambda функцию из консоли AWS:
   - Перейдите в сервис Lambda
   - Выберите функцию `fb-ads-daily-report`
   - Нажмите "Test" (Тестировать)
   - Создайте новое тестовое событие с пустым JSON `{}`
   - Нажмите "Test" (Тестировать)

## Шаг 5: Мониторинг и обслуживание

1. **Просмотр логов**:
   - Перейдите в сервис CloudWatch
   - Выберите "Log groups" (Группы логов)
   - Найдите группу `/aws/lambda/fb-ads-daily-report`

2. **Обновление кода**:
   - Внесите изменения в файл `lambda_function.py`
   - Запустите скрипт `prepare_lambda_package.sh` для создания нового пакета
   - Обновите Lambda функцию с помощью AWS CLI:
     ```bash
     aws lambda update-function-code \
       --function-name fb-ads-daily-report \
       --zip-file fileb://lambda_package.zip
     ```

## Шаг 6: Удаление ресурсов

Если вам нужно удалить все созданные ресурсы, вы можете использовать следующие команды:

```bash
# Удаление правила EventBridge
aws events remove-targets --rule fb-ads-daily-report-schedule --ids DailyReportLambdaTarget
aws events delete-rule --name fb-ads-daily-report-schedule

# Удаление Lambda функции
aws lambda delete-function --function-name fb-ads-daily-report

# Удаление IAM роли
aws iam delete-role-policy --role-name fb-ads-lambda-role --policy-name fb-ads-lambda-role-s3-policy
aws iam detach-role-policy --role-name fb-ads-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name fb-ads-lambda-role

# Очистка и удаление S3 бакета
aws s3 rm s3://fb-ads-reports-XXXXXXXX --recursive
aws s3 rb s3://fb-ads-reports-XXXXXXXX
```

Замените `fb-ads-reports-XXXXXXXX` на фактическое имя вашего S3 бакета.

## Устранение неполадок

### Проблема: Ошибка доступа при создании ресурсов

1. Убедитесь, что ваши AWS учетные данные настроены правильно
2. Проверьте, что у вас есть необходимые разрешения для создания ресурсов
3. Проверьте логи для получения дополнительной информации об ошибке

### Проблема: Lambda функция завершается с ошибкой

1. Проверьте логи CloudWatch для получения информации об ошибке
2. Убедитесь, что все переменные окружения настроены правильно
3. Проверьте, что токен Facebook действителен и имеет необходимые разрешения

### Проблема: Отчеты не отправляются в Telegram

1. Проверьте, что токен бота Telegram и ID чата указаны правильно
2. Убедитесь, что бот добавлен в чат и имеет права на отправку сообщений
3. Проверьте логи Lambda функции на наличие ошибок при отправке сообщений 