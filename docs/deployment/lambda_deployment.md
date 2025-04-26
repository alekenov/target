# Развертывание Facebook Ads Dashboard на AWS Lambda

## Преимущества использования AWS Lambda

- Бессерверная архитектура - не нужно управлять серверами
- Автоматическое масштабирование
- Оплата только за фактическое использование
- Интеграция с существующей инфраструктурой AWS

## Подготовка дашборда для Lambda

1. Создайте файл `lambda_handler.py` для интеграции Flask с AWS Lambda:

```python
import os
import sys
from simple_dashboard import app

# Добавляем директорию с кодом в PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def lambda_handler(event, context):
    """
    Обработчик AWS Lambda для интеграции с API Gateway
    """
    from awsgi import response
    
    return response(app, event, context)
```

2. Создайте файл `requirements.txt` с зависимостями:

```
flask==2.0.1
pymysql==1.0.2
pandas==1.3.3
python-dotenv==0.19.0
aws-wsgi==0.2.7
```

3. Подготовьте пакет для загрузки в Lambda:

```bash
# Создайте виртуальное окружение и установите зависимости
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Создайте директорию для пакета
mkdir -p package

# Скопируйте код в директорию пакета
cp -r simple_dashboard.py templates/ show_data.py lambda_handler.py package/

# Скопируйте зависимости
cp -r venv/lib/python3.8/site-packages/* package/

# Создайте ZIP-архив
cd package
zip -r ../lambda_package.zip .
cd ..
```

## Настройка AWS Lambda

1. Создайте функцию Lambda:
   - Откройте AWS Console и перейдите в раздел Lambda
   - Нажмите "Create function"
   - Выберите "Author from scratch"
   - Укажите имя функции: "facebook-ads-dashboard"
   - Runtime: Python 3.8
   - Architecture: x86_64
   - Нажмите "Create function"

2. Загрузите ZIP-архив:
   - В разделе "Code source" выберите "Upload from" > ".zip file"
   - Загрузите файл `lambda_package.zip`
   - Нажмите "Save"

3. Настройте обработчик:
   - В разделе "Runtime settings" нажмите "Edit"
   - Укажите Handler: `lambda_handler.lambda_handler`
   - Нажмите "Save"

4. Настройте переменные окружения:
   - В разделе "Configuration" выберите "Environment variables"
   - Нажмите "Edit"
   - Добавьте все необходимые переменные окружения:
     - FACEBOOK_APP_ID
     - FACEBOOK_APP_SECRET
     - FACEBOOK_ACCESS_TOKEN
     - FACEBOOK_AD_ACCOUNT_ID
     - AURORA_HOST
     - AURORA_MASTER_USERNAME
     - AURORA_MASTER_PASSWORD
     - AURORA_DATABASE_NAME
     - AURORA_PORT
   - Нажмите "Save"

5. Настройте таймаут и память:
   - В разделе "Configuration" выберите "General configuration"
   - Нажмите "Edit"
   - Установите Timeout: 30 seconds
   - Установите Memory: 256 MB
   - Нажмите "Save"

6. Настройте VPC (для доступа к Aurora MySQL):
   - В разделе "Configuration" выберите "VPC"
   - Нажмите "Edit"
   - Выберите VPC, в которой находится ваша база данных Aurora
   - Выберите подсети и группы безопасности
   - Нажмите "Save"

## Настройка API Gateway

1. Создайте API Gateway:
   - Откройте AWS Console и перейдите в раздел API Gateway
   - Нажмите "Create API"
   - Выберите "REST API" и нажмите "Build"
   - Укажите имя API: "facebook-ads-dashboard-api"
   - Нажмите "Create API"

2. Создайте ресурс и метод:
   - Нажмите "Create Resource"
   - Выберите "Proxy resource" и установите флажок
   - Resource Path: `{proxy+}`
   - Нажмите "Create Resource"
   - Выберите "ANY" метод
   - Integration type: Lambda Function
   - Lambda Function: facebook-ads-dashboard
   - Нажмите "Save"

3. Настройте корневой ресурс:
   - Выберите корневой ресурс "/"
   - Нажмите "Create Method"
   - Выберите "ANY"
   - Integration type: Lambda Function
   - Lambda Function: facebook-ads-dashboard
   - Нажмите "Save"

4. Разверните API:
   - Нажмите "Deploy API"
   - Deployment stage: [New Stage]
   - Stage name: prod
   - Нажмите "Deploy"

5. Получите URL вашего API:
   - В разделе "Stages" выберите "prod"
   - Скопируйте "Invoke URL"

## Настройка CloudFront (опционально)

Для улучшения производительности и добавления HTTPS:

1. Создайте дистрибутив CloudFront:
   - Откройте AWS Console и перейдите в раздел CloudFront
   - Нажмите "Create Distribution"
   - Origin Domain Name: URL вашего API Gateway
   - Origin Path: /prod
   - Viewer Protocol Policy: Redirect HTTP to HTTPS
   - Allowed HTTP Methods: GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
   - Cache Policy: CachingDisabled
   - Origin Request Policy: AllViewer
   - Нажмите "Create Distribution"

2. Получите домен CloudFront:
   - После создания дистрибутива скопируйте "Distribution Domain Name"
   - Например: d1234abcdef.cloudfront.net

## Настройка Route 53 (опционально)

Если у вас есть домен в Route 53:

1. Создайте запись:
   - Откройте AWS Console и перейдите в раздел Route 53
   - Выберите вашу Hosted Zone
   - Нажмите "Create Record"
   - Record name: dashboard
   - Record type: A
   - Route traffic to: Alias to CloudFront distribution
   - Выберите ваш дистрибутив CloudFront
   - Нажмите "Create records"

## Доступ к дашборду

Теперь ваш дашборд доступен по URL:

- Через API Gateway: https://your-api-id.execute-api.your-region.amazonaws.com/prod/
- Через CloudFront: https://d1234abcdef.cloudfront.net/
- Через Route 53: https://dashboard.your-domain.com/

## Обновление дашборда

Для обновления кода дашборда:

1. Внесите изменения в код
2. Создайте новый ZIP-архив
3. Загрузите архив в Lambda
4. Дождитесь обновления функции

## Мониторинг и логи

1. Просмотр логов:
   - Откройте AWS Console и перейдите в раздел Lambda
   - Выберите вашу функцию
   - Перейдите на вкладку "Monitor"
   - Нажмите "View logs in CloudWatch"

2. Настройка оповещений:
   - В CloudWatch создайте Alarm для мониторинга ошибок и производительности
   - Настройте оповещения по email или SMS
