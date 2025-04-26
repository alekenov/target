# Пошаговая инструкция по развертыванию Facebook Ads Dashboard на AWS Lambda

## Подготовка пакета Lambda

1. **Подготовьте код и зависимости**

   Убедитесь, что у вас есть все необходимые файлы:
   - `simple_dashboard.py` - Основной файл дашборда
   - `show_data.py` - Файл с функциями для работы с данными
   - `lambda_handler.py` - Обработчик Lambda
   - `templates/` - Директория с HTML-шаблонами
   - `requirements.txt` - Файл с зависимостями

2. **Создайте пакет Lambda**

   Запустите скрипт для создания пакета:
   ```bash
   chmod +x prepare_lambda_package.sh
   ./prepare_lambda_package.sh
   ```

   Скрипт создаст файл `dashboard_lambda_package.zip`, который содержит весь код и зависимости.

## Загрузка пакета в S3

1. **Создайте S3 бакет** (если у вас его еще нет)

   ```bash
   aws s3 mb s3://your-lambda-packages-bucket --region your-region
   ```

2. **Загрузите ZIP-архив в S3**

   ```bash
   aws s3 cp dashboard_lambda_package.zip s3://your-lambda-packages-bucket/
   ```

## Развертывание с помощью CloudFormation

1. **Подготовьте параметры**

   Создайте файл `parameters.json` с параметрами для CloudFormation:

   ```json
   [
     {
       "ParameterKey": "LambdaS3Bucket",
       "ParameterValue": "your-lambda-packages-bucket"
     },
     {
       "ParameterKey": "LambdaS3Key",
       "ParameterValue": "dashboard_lambda_package.zip"
     },
     {
       "ParameterKey": "AuroraHost",
       "ParameterValue": "your-aurora-host.cluster-xxx.your-region.rds.amazonaws.com"
     },
     {
       "ParameterKey": "AuroraPort",
       "ParameterValue": "3306"
     },
     {
       "ParameterKey": "AuroraUsername",
       "ParameterValue": "your-username"
     },
     {
       "ParameterKey": "AuroraPassword",
       "ParameterValue": "your-password"
     },
     {
       "ParameterKey": "AuroraDatabase",
       "ParameterValue": "your-database"
     },
     {
       "ParameterKey": "FacebookAppId",
       "ParameterValue": "your-facebook-app-id"
     },
     {
       "ParameterKey": "FacebookAppSecret",
       "ParameterValue": "your-facebook-app-secret"
     },
     {
       "ParameterKey": "FacebookAccessToken",
       "ParameterValue": "your-facebook-access-token"
     },
     {
       "ParameterKey": "FacebookAdAccountId",
       "ParameterValue": "your-facebook-ad-account-id"
     },
     {
       "ParameterKey": "VpcId",
       "ParameterValue": "vpc-xxxxxxxx"
     },
     {
       "ParameterKey": "SubnetIds",
       "ParameterValue": "subnet-xxxxxxxx,subnet-yyyyyyyy"
     },
     {
       "ParameterKey": "SecurityGroupIds",
       "ParameterValue": "sg-xxxxxxxx"
     }
   ]
   ```

2. **Разверните CloudFormation стек**

   ```bash
   aws cloudformation create-stack \
     --stack-name facebook-ads-dashboard \
     --template-body file://dashboard-cloudformation.yaml \
     --parameters file://parameters.json \
     --capabilities CAPABILITY_IAM \
     --region your-region
   ```

3. **Дождитесь завершения развертывания**

   ```bash
   aws cloudformation wait stack-create-complete \
     --stack-name facebook-ads-dashboard \
     --region your-region
   ```

4. **Получите URL API Gateway**

   ```bash
   aws cloudformation describe-stacks \
     --stack-name facebook-ads-dashboard \
     --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
     --output text \
     --region your-region
   ```

## Настройка CloudFront (опционально)

Для улучшения производительности и добавления HTTPS:

1. **Создайте дистрибутив CloudFront через AWS Console**:
   - Origin Domain Name: URL вашего API Gateway (без https://)
   - Origin Path: /prod
   - Viewer Protocol Policy: Redirect HTTP to HTTPS
   - Allowed HTTP Methods: GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
   - Cache Policy: CachingDisabled
   - Origin Request Policy: AllViewer

2. **Получите домен CloudFront**:
   - После создания дистрибутива скопируйте "Distribution Domain Name"
   - Например: d1234abcdef.cloudfront.net

## Настройка Route 53 (опционально)

Если у вас есть домен в Route 53:

1. **Создайте запись**:
   - Record name: dashboard
   - Record type: A
   - Route traffic to: Alias to CloudFront distribution
   - Выберите ваш дистрибутив CloudFront

## Обновление кода

Для обновления кода дашборда:

1. **Внесите изменения в код**
2. **Создайте новый ZIP-архив**:
   ```bash
   ./prepare_lambda_package.sh
   ```
3. **Загрузите архив в S3**:
   ```bash
   aws s3 cp dashboard_lambda_package.zip s3://your-lambda-packages-bucket/
   ```
4. **Обновите Lambda функцию**:
   ```bash
   aws lambda update-function-code \
     --function-name facebook-ads-dashboard \
     --s3-bucket your-lambda-packages-bucket \
     --s3-key dashboard_lambda_package.zip \
     --region your-region
   ```

## Мониторинг и логи

1. **Просмотр логов**:
   - Откройте AWS Console и перейдите в раздел Lambda
   - Выберите вашу функцию facebook-ads-dashboard
   - Перейдите на вкладку "Monitor"
   - Нажмите "View logs in CloudWatch"

2. **Настройка оповещений**:
   - В CloudWatch создайте Alarm для мониторинга ошибок и производительности
   - Настройте оповещения по email или SMS

## Безопасность

1. **Ограничение доступа**:
   - Добавьте базовую аутентификацию в API Gateway
   - Настройте WAF для защиты от атак

2. **Защита учетных данных**:
   - Используйте AWS Secrets Manager для хранения учетных данных
   - Обновите CloudFormation шаблон для использования Secrets Manager

## Оптимизация затрат

1. **Настройка автоматического масштабирования**:
   - Установите подходящие значения для параметров Timeout и Memory
   - Используйте Provisioned Concurrency для предотвращения холодных стартов

2. **Мониторинг расходов**:
   - Настройте AWS Budgets для отслеживания расходов
   - Установите оповещения о превышении бюджета
