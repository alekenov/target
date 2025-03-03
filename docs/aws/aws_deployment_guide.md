# Руководство по развертыванию отчетов Facebook Ads в AWS

Это руководство описывает процесс настройки автоматизированной системы для ежедневного сбора и отправки отчетов по рекламным кампаниям Facebook с использованием AWS Lambda и EventBridge.

## Предварительные требования

1. Аккаунт AWS с правами администратора
2. AWS CLI, установленный и настроенный на вашем компьютере
3. Приложение Facebook с доступом к Marketing API
4. Бот Telegram для отправки отчетов
5. Python 3.9 или выше

## Пошаговое руководство по развертыванию

### 1. Подготовка переменных окружения

Создайте файл `.env` в корне проекта со следующими переменными:

```
# Facebook API
FACEBOOK_APP_ID=ваш_app_id
FACEBOOK_APP_SECRET=ваш_app_secret
FACEBOOK_ACCESS_TOKEN=ваш_access_token
FACEBOOK_AD_ACCOUNT_ID=ваш_ad_account_id

# AWS
S3_BUCKET_NAME=fb-ads-reports-bucket

# Telegram
TELEGRAM_BOT_TOKEN=токен_бота_telegram
TELEGRAM_CHAT_ID=id_чата_telegram

# База данных Aurora
AURORA_HOST=ваш_хост_aurora
AURORA_MASTER_USERNAME=admin
AURORA_MASTER_PASSWORD=ваш_пароль
AURORA_DATABASE_NAME=facebook_ads_db
AURORA_PORT=3306
```

### 2. Создание S3 бакета

```bash
aws s3api create-bucket \
  --bucket fb-ads-reports-bucket \
  --region us-east-1
```

### 3. Создание базы данных Aurora MySQL

1. Создайте кластер Aurora MySQL через консоль AWS или CLI:

```bash
aws rds create-db-cluster \
  --db-cluster-identifier facebook-ads-aurora-cluster \
  --engine aurora-mysql \
  --engine-version 8.0.mysql_aurora.3.08.1 \
  --master-username admin \
  --master-user-password ваш_пароль \
  --db-subnet-group-name default \
  --vpc-security-group-ids sg-xxxxxxxx \
  --serverless-v2-scaling-configuration MinCapacity=1,MaxCapacity=8
```

2. Создайте экземпляр базы данных:

```bash
aws rds create-db-instance \
  --db-instance-identifier facebook-ads-aurora-cluster-instance-1 \
  --db-cluster-identifier facebook-ads-aurora-cluster \
  --engine aurora-mysql \
  --db-instance-class db.serverless
```

3. Дождитесь создания кластера и экземпляра (это может занять 5-10 минут).

4. Создайте базу данных и таблицы, подключившись к кластеру:

```sql
CREATE DATABASE facebook_ads_db;
USE facebook_ads_db;

CREATE TABLE campaigns (
  id VARCHAR(255) PRIMARY KEY,
  name VARCHAR(255),
  status VARCHAR(50),
  daily_budget DECIMAL(10,2),
  lifetime_budget DECIMAL(10,2),
  start_time DATETIME,
  stop_time DATETIME,
  created_time DATETIME,
  updated_time DATETIME
);

CREATE TABLE ad_sets (
  id VARCHAR(255) PRIMARY KEY,
  campaign_id VARCHAR(255),
  name VARCHAR(255),
  status VARCHAR(50),
  daily_budget DECIMAL(10,2),
  lifetime_budget DECIMAL(10,2),
  targeting JSON,
  created_time DATETIME,
  updated_time DATETIME,
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE ads (
  id VARCHAR(255) PRIMARY KEY,
  ad_set_id VARCHAR(255),
  name VARCHAR(255),
  status VARCHAR(50),
  creative JSON,
  created_time DATETIME,
  updated_time DATETIME,
  FOREIGN KEY (ad_set_id) REFERENCES ad_sets(id)
);

CREATE TABLE ad_insights (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ad_id VARCHAR(255),
  date DATE,
  impressions INT,
  clicks INT,
  spend DECIMAL(10,2),
  ctr DECIMAL(10,4),
  cpc DECIMAL(10,4),
  conversions INT,
  created_time DATETIME,
  FOREIGN KEY (ad_id) REFERENCES ads(id)
);

CREATE TABLE config (
  `key` VARCHAR(255) PRIMARY KEY,
  value JSON,
  description TEXT,
  updated_time DATETIME
);
```

### 4. Подготовка пакета Lambda

1. Запустите скрипт для создания ZIP-архива:

```bash
chmod +x prepare_lambda_package.sh
./prepare_lambda_package.sh
```

2. Загрузите созданный архив в S3:

```bash
aws s3 cp lambda_package.zip s3://fb-ads-reports-bucket/lambda_package.zip
```

### 5. Создание IAM роли для Lambda

1. Создайте файл `lambda-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

2. Создайте роль:

```bash
aws iam create-role \
  --role-name fb-ads-lambda-role \
  --assume-role-policy-document file://lambda-trust-policy.json
```

3. Прикрепите необходимые политики:

```bash
aws iam attach-role-policy \
  --role-name fb-ads-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name fb-ads-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

### 6. Создание Lambda функции

```bash
aws lambda create-function \
  --function-name fb-ads-daily-report \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT_ID:role/fb-ads-lambda-role \
  --handler lambda_function.lambda_handler \
  --timeout 300 \
  --memory-size 512 \
  --code S3Bucket=fb-ads-reports-bucket,S3Key=lambda_package.zip \
  --environment "Variables={S3_BUCKET_NAME=fb-ads-reports-bucket,FACEBOOK_APP_ID=ваш_app_id,FACEBOOK_APP_SECRET=ваш_app_secret,FACEBOOK_ACCESS_TOKEN=ваш_access_token,FACEBOOK_AD_ACCOUNT_ID=ваш_ad_account_id,TELEGRAM_BOT_TOKEN=токен_бота_telegram,TELEGRAM_CHAT_ID=id_чата_telegram,AURORA_HOST=ваш_хост_aurora,AURORA_MASTER_USERNAME=admin,AURORA_MASTER_PASSWORD=ваш_пароль,AURORA_DATABASE_NAME=facebook_ads_db,AURORA_PORT=3306}"
```

### 7. Настройка EventBridge для ежедневного запуска

1. Создайте файл `event-rule.json`:

```json
{
  "Name": "fb-ads-daily-report-schedule",
  "ScheduleExpression": "cron(0 8 * * ? *)",
  "State": "ENABLED"
}
```

2. Создайте правило:

```bash
aws events put-rule \
  --cli-input-json file://event-rule.json
```

3. Добавьте Lambda функцию как цель:

```bash
aws events put-targets \
  --rule fb-ads-daily-report-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT_ID:function:fb-ads-daily-report"
```

4. Разрешите EventBridge вызывать Lambda функцию:

```bash
aws lambda add-permission \
  --function-name fb-ads-daily-report \
  --statement-id fb-ads-daily-report-event \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:REGION:ACCOUNT_ID:rule/fb-ads-daily-report-schedule
```

### 8. Тестирование Lambda функции

Вы можете вручную запустить Lambda функцию для тестирования:

```bash
aws lambda invoke \
  --function-name fb-ads-daily-report \
  --payload '{}' \
  response.json
```

## Альтернативный способ: использование CloudFormation

Вместо ручной настройки каждого компонента, вы можете использовать предоставленный шаблон CloudFormation:

```bash
aws cloudformation create-stack \
  --stack-name facebook-ads-reporting \
  --template-body file://cloudformation-template.yaml \
  --parameters ParameterKey=S3BucketName,ParameterValue=fb-ads-reports-bucket \
               ParameterKey=FacebookAppId,ParameterValue=ваш_app_id \
               ParameterKey=FacebookAppSecret,ParameterValue=ваш_app_secret \
               ParameterKey=FacebookAccessToken,ParameterValue=ваш_access_token \
               ParameterKey=FacebookAdAccountId,ParameterValue=ваш_ad_account_id \
               ParameterKey=TelegramBotToken,ParameterValue=токен_бота_telegram \
               ParameterKey=TelegramChatId,ParameterValue=id_чата_telegram
```

## Мониторинг и отладка

### CloudWatch Logs

Логи Lambda функции доступны в CloudWatch:

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/fb-ads-daily-report \
  --start-time $(date -d "1 hour ago" +%s000) \
  --end-time $(date +%s000)
```

### Настройка оповещений

Создайте CloudWatch Alarm для мониторинга ошибок:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fb-ads-lambda-errors \
  --alarm-description "Alarm for Facebook Ads Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=FunctionName,Value=fb-ads-daily-report \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:REGION:ACCOUNT_ID:your-sns-topic
```

## Оптимизация затрат

1. **Настройка автопаузы Aurora**: Настройте автоматическую паузу кластера в периоды неактивности.
2. **Уменьшение максимальной ёмкости**: Если нагрузка небольшая, уменьшите максимальную ёмкость до 2-4 ACU.
3. **Мониторинг использования**: Регулярно проверяйте метрики использования в CloudWatch.
4. **Резервные экземпляры**: Для долгосрочных проектов рассмотрите возможность использования резервных экземпляров.

## Обновление Lambda функции

Когда вам нужно обновить код Lambda функции:

```bash
# Создайте новый пакет
./prepare_lambda_package.sh

# Загрузите его в S3
aws s3 cp lambda_package.zip s3://fb-ads-reports-bucket/lambda_package.zip

# Обновите функцию
aws lambda update-function-code \
  --function-name fb-ads-daily-report \
  --s3-bucket fb-ads-reports-bucket \
  --s3-key lambda_package.zip
```

## Безопасность

1. **Ограничение доступа к базе данных**: Настройте группы безопасности для ограничения доступа к базе данных.
2. **Ротация секретов**: Регулярно обновляйте токены доступа и пароли.
3. **Мониторинг безопасности**: Включите AWS CloudTrail для отслеживания действий в вашем аккаунте.
4. **Шифрование**: Убедитесь, что данные в S3 и Aurora зашифрованы.