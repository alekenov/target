# Руководство по развертыванию отчетов Facebook Ads в AWS

Это руководство описывает процесс настройки автоматизированной системы для ежедневного сбора и отправки отчетов по рекламным кампаниям Facebook с использованием AWS Lambda и EventBridge.

## Предварительные требования

1. Аккаунт AWS с правами администратора
2. AWS CLI, установленный и настроенный на вашем компьютере
3. Приложение Facebook с доступом к Marketing API
4. Бот Telegram для отправки отчетов

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

## Шаг 2: Создание S3 бакета

1. Создайте S3 бакет для хранения пакета Lambda и отчетов:
   ```bash
   aws s3 mb s3://fb-ads-reports-bucket --region us-east-1
   ```
   Замените `fb-ads-reports-bucket` на уникальное имя бакета и `us-east-1` на нужный регион.

2. Загрузите пакет Lambda в S3 бакет:
   ```bash
   aws s3 cp lambda_package.zip s3://fb-ads-reports-bucket/
   ```

## Шаг 3: Развертывание CloudFormation стека

1. Разверните CloudFormation стек с помощью шаблона:
   ```bash
   aws cloudformation create-stack \
     --stack-name fb-ads-daily-report \
     --template-body file://cloudformation-template.yaml \
     --parameters \
       ParameterKey=S3BucketName,ParameterValue=fb-ads-reports-bucket \
       ParameterKey=FacebookAppId,ParameterValue=YOUR_FB_APP_ID \
       ParameterKey=FacebookAppSecret,ParameterValue=YOUR_FB_APP_SECRET \
       ParameterKey=FacebookAccessToken,ParameterValue=YOUR_FB_ACCESS_TOKEN \
       ParameterKey=FacebookAdAccountId,ParameterValue=YOUR_FB_AD_ACCOUNT_ID \
       ParameterKey=TelegramBotToken,ParameterValue=YOUR_TELEGRAM_BOT_TOKEN \
       ParameterKey=TelegramChatId,ParameterValue=YOUR_TELEGRAM_CHAT_ID \
     --capabilities CAPABILITY_IAM \
     --region us-east-1
   ```
   
   Замените все значения `YOUR_*` на ваши реальные данные.

2. Дождитесь завершения создания стека:
   ```bash
   aws cloudformation wait stack-create-complete --stack-name fb-ads-daily-report
   ```

## Шаг 4: Проверка развертывания

1. Проверьте, что Lambda функция создана:
   ```bash
   aws lambda get-function --function-name fb-ads-daily-report
   ```

2. Запустите Lambda функцию вручную для проверки:
   ```bash
   aws lambda invoke \
     --function-name fb-ads-daily-report \
     --payload '{}' \
     response.json
   ```

3. Проверьте файл `response.json` на наличие ошибок и проверьте, что отчет был отправлен в Telegram.

## Шаг 5: Мониторинг и обслуживание

1. Настройте мониторинг Lambda функции в CloudWatch:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name fb-ads-daily-report-errors \
     --alarm-description "Alarm for FB Ads Daily Report Lambda errors" \
     --metric-name Errors \
     --namespace AWS/Lambda \
     --statistic Sum \
     --period 300 \
     --threshold 1 \
     --comparison-operator GreaterThanOrEqualToThreshold \
     --dimensions Name=FunctionName,Value=fb-ads-daily-report \
     --evaluation-periods 1 \
     --alarm-actions YOUR_SNS_TOPIC_ARN
   ```
   
   Замените `YOUR_SNS_TOPIC_ARN` на ARN вашей SNS темы для уведомлений.

2. Для просмотра логов Lambda функции:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/fb-ads-daily-report
   ```

## Шаг 6: Обновление Lambda функции

Если вам нужно обновить код Lambda функции:

1. Внесите изменения в `lambda_function.py`
2. Запустите скрипт `prepare_lambda_package.sh` для создания нового пакета
3. Загрузите новый пакет в S3:
   ```bash
   aws s3 cp lambda_package.zip s3://fb-ads-reports-bucket/
   ```
4. Обновите Lambda функцию:
   ```bash
   aws lambda update-function-code \
     --function-name fb-ads-daily-report \
     --s3-bucket fb-ads-reports-bucket \
     --s3-key lambda_package.zip
   ```

## Шаг 7: Удаление ресурсов

Если вам нужно удалить все созданные ресурсы:

1. Удалите CloudFormation стек:
   ```bash
   aws cloudformation delete-stack --stack-name fb-ads-daily-report
   ```

2. Дождитесь завершения удаления стека:
   ```bash
   aws cloudformation wait stack-delete-complete --stack-name fb-ads-daily-report
   ```

3. Очистите S3 бакет:
   ```bash
   aws s3 rm s3://fb-ads-reports-bucket --recursive
   aws s3 rb s3://fb-ads-reports-bucket
   ```

## Устранение неполадок

### Проблема: Lambda функция завершается с ошибкой

1. Проверьте логи CloudWatch:
   ```bash
   aws logs filter-log-events --log-group-name /aws/lambda/fb-ads-daily-report
   ```

2. Убедитесь, что все переменные окружения настроены правильно:
   ```bash
   aws lambda get-function-configuration --function-name fb-ads-daily-report
   ```

3. Проверьте, что токен Facebook действителен и имеет необходимые разрешения.

### Проблема: Отчеты не отправляются в Telegram

1. Проверьте, что токен бота Telegram и ID чата указаны правильно.
2. Убедитесь, что бот добавлен в чат и имеет права на отправку сообщений.
3. Проверьте логи Lambda функции на наличие ошибок при отправке сообщений.

### Проблема: Lambda функция не запускается по расписанию

1. Проверьте настройки EventBridge правила:
   ```bash
   aws events describe-rule --name fb-ads-daily-report-schedule
   ```

2. Убедитесь, что правило включено (State: ENABLED).
3. Проверьте, что у EventBridge есть разрешение на вызов Lambda функции. 