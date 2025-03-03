# Руководство по настройке AWS Lambda для Facebook Ads Reporting

Это руководство поможет вам настроить AWS Lambda функцию для автоматического получения и отправки отчетов по рекламным кампаниям Facebook.

## 1. Подготовка пакета для загрузки в Lambda

### Требования

- Python 3.9+
- AWS CLI (установленный и настроенный)
- Доступ к AWS с правами на создание Lambda функций, S3 бакетов и EventBridge правил

### Шаги по подготовке пакета

1. Клонируйте репозиторий проекта:

```bash
git clone <URL_репозитория>
cd <директория_проекта>
```

2. Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate  # Для Linux/Mac
# или
.venv\Scripts\activate     # Для Windows

pip install -r requirements.txt
```

3. Используйте скрипт `prepare_lambda_package.sh` для создания ZIP-пакета:

```bash
chmod +x prepare_lambda_package.sh
./prepare_lambda_package.sh
```

Скрипт создаст файл `lambda_package.zip`, который содержит все необходимые файлы для загрузки в AWS Lambda.

## 2. Создание S3 бакета для хранения отчетов

1. Перейдите в [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Нажмите "Create bucket"
3. Введите имя бакета (например, `fb-ads-reports-bucket`)
4. Выберите регион (рекомендуется выбрать тот же регион, где будет размещена Lambda функция)
5. Оставьте остальные настройки по умолчанию и нажмите "Create bucket"

## 3. Создание IAM роли для Lambda функции

1. Перейдите в [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Выберите "Roles" в левом меню и нажмите "Create role"
3. Выберите "AWS service" и "Lambda" в качестве сервиса
4. Нажмите "Next: Permissions"
5. Добавьте следующие политики:
   - `AWSLambdaBasicExecutionRole` (для логирования)
   - `AmazonS3FullAccess` (для доступа к S3)
   - `AmazonRDSDataFullAccess` (для доступа к Aurora)
6. Нажмите "Next: Tags", добавьте теги при необходимости
7. Нажмите "Next: Review"
8. Введите имя роли (например, `facebook-ads-lambda-role`) и описание
9. Нажмите "Create role"

## 4. Создание Lambda функции

1. Перейдите в [AWS Lambda Console](https://console.aws.amazon.com/lambda/)
2. Нажмите "Create function"
3. Выберите "Author from scratch"
4. Введите имя функции (например, `facebook-ads-reporting`)
5. Выберите среду выполнения "Python 3.9"
6. В разделе "Permissions" выберите "Use an existing role" и выберите созданную ранее роль
7. Нажмите "Create function"

### Загрузка пакета

1. В разделе "Code source" нажмите "Upload from" и выберите ".zip file"
2. Загрузите созданный ранее файл `lambda_package.zip`
3. Нажмите "Save"

### Настройка переменных окружения

1. Перейдите в раздел "Configuration"
2. Выберите вкладку "Environment variables"
3. Нажмите "Edit" и добавьте следующие переменные:

```
FACEBOOK_APP_ID=ваш_app_id
FACEBOOK_APP_SECRET=ваш_app_secret
FACEBOOK_ACCESS_TOKEN=ваш_access_token
FACEBOOK_AD_ACCOUNT_ID=ваш_ad_account_id
S3_BUCKET_NAME=fb-ads-reports-bucket
TELEGRAM_BOT_TOKEN=токен_бота_telegram
TELEGRAM_CHAT_ID=id_чата_telegram
AURORA_HOST=ваш_хост_aurora
AURORA_MASTER_USERNAME=admin
AURORA_MASTER_PASSWORD=ваш_пароль
AURORA_DATABASE_NAME=facebook_ads_db
AURORA_PORT=3306
```

4. Нажмите "Save"

### Настройка таймаута и памяти

1. В разделе "Configuration" выберите вкладку "General configuration"
2. Нажмите "Edit" и установите:
   - Timeout: 3 минуты (или больше, в зависимости от объема данных)
   - Memory: 256 MB (или больше, в зависимости от объема данных)
3. Нажмите "Save"

## 5. Настройка EventBridge для запуска по расписанию

1. Перейдите в [AWS EventBridge Console](https://console.aws.amazon.com/events/)
2. Выберите "Rules" в левом меню и нажмите "Create rule"
3. Введите имя правила (например, `facebook-ads-daily-report`)
4. Выберите "Schedule" в качестве типа правила
5. Настройте расписание:
   - Fixed rate: 1 day (для ежедневного запуска)
   - Или используйте Cron expression для более гибкой настройки (например, `0 8 * * ? *` для запуска каждый день в 8:00 UTC)
6. Нажмите "Next"
7. В разделе "Select targets" выберите "Lambda function"
8. Выберите созданную ранее Lambda функцию
9. Нажмите "Next"
10. Добавьте теги при необходимости и нажмите "Next"
11. Проверьте настройки и нажмите "Create rule"

## 6. Тестирование Lambda функции

1. Вернитесь в [AWS Lambda Console](https://console.aws.amazon.com/lambda/)
2. Выберите вашу функцию
3. Нажмите "Test"
4. Создайте новое тестовое событие с пустым JSON объектом `{}`
5. Введите имя события (например, `TestEvent`)
6. Нажмите "Save" и затем "Test"
7. Проверьте результаты выполнения и логи

## 7. Мониторинг и логирование

### CloudWatch Logs

1. В консоли Lambda функции перейдите в раздел "Monitor"
2. Нажмите "View logs in CloudWatch"
3. Здесь вы можете просматривать логи выполнения функции

### Настройка оповещений

1. В [AWS CloudWatch Console](https://console.aws.amazon.com/cloudwatch/) выберите "Alarms" в левом меню
2. Нажмите "Create alarm"
3. Нажмите "Select metric"
4. Выберите "Lambda" > "By Function Name"
5. Найдите вашу функцию и выберите метрику "Errors"
6. Настройте условие срабатывания (например, "Greater than 0")
7. Настройте действие при срабатывании (например, отправка уведомления по email)
8. Завершите создание оповещения

## 8. Оптимизация и масштабирование

### Оптимизация памяти

Lambda функции автоматически масштабируются по количеству одновременных запусков, но вы можете оптимизировать использование памяти:

1. В консоли Lambda функции перейдите в раздел "Configuration" > "General configuration"
2. Экспериментируйте с различными значениями памяти (от 128 MB до 10240 MB)
3. Больше памяти также означает больше вычислительной мощности, что может ускорить выполнение функции

### Использование AWS Lambda Insights

1. В консоли Lambda функции перейдите в раздел "Configuration" > "Monitoring and operations tools"
2. Включите "Enhanced monitoring" и "Lambda Insights"
3. Это даст вам более детальную информацию о производительности функции

## 9. Безопасность

### Управление секретами

Для более безопасного хранения секретов рекомендуется использовать AWS Secrets Manager:

1. Перейдите в [AWS Secrets Manager Console](https://console.aws.amazon.com/secretsmanager/)
2. Нажмите "Store a new secret"
3. Выберите "Other type of secrets"
4. Добавьте все секретные переменные (токены, пароли)
5. Введите имя секрета (например, `facebook-ads-secrets`)
6. Завершите создание секрета
7. Обновите код Lambda функции для получения секретов из Secrets Manager вместо переменных окружения

### Ограничение доступа к S3

Настройте более строгие разрешения для S3 бакета:

1. В консоли S3 выберите ваш бакет
2. Перейдите в раздел "Permissions"
3. Настройте политику бакета, чтобы разрешить доступ только вашей Lambda функции

## 10. Устранение неполадок

### Распространенные проблемы и решения

1. **Ошибка "Function timed out"**
   - Увеличьте значение таймаута в настройках функции
   - Оптимизируйте код для более быстрого выполнения

2. **Ошибка "Memory limit exceeded"**
   - Увеличьте объем памяти в настройках функции

3. **Ошибки подключения к базе данных**
   - Проверьте, что Lambda функция имеет доступ к VPC, где размещена база данных
   - Проверьте группы безопасности и сетевые настройки

4. **Ошибки Facebook API**
   - Проверьте срок действия токена доступа
   - Убедитесь, что у приложения есть необходимые разрешения

### Отладка

1. Добавьте больше операторов логирования в код
2. Используйте X-Ray для трассировки выполнения функции:
   - В консоли Lambda функции перейдите в раздел "Configuration" > "Monitoring and operations tools"
   - Включите "AWS X-Ray active tracing"

## Полезные ресурсы

- [Документация AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Документация AWS S3](https://docs.aws.amazon.com/s3/)
- [Документация AWS EventBridge](https://docs.aws.amazon.com/eventbridge/)
- [Документация AWS CloudWatch](https://docs.aws.amazon.com/cloudwatch/)
- [Документация Facebook Marketing API](https://developers.facebook.com/docs/marketing-apis/)
