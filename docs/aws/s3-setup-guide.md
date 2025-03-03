# Руководство по настройке S3 для хранения отчетов Facebook Ads

Это руководство поможет вам настроить AWS S3 бакет для хранения отчетов по рекламным кампаниям Facebook.

## 1. Создание S3 бакета

### Шаги по созданию бакета

1. Перейдите в [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Нажмите "Create bucket"
3. Введите имя бакета (например, `fb-ads-reports-bucket`)
   - Имя бакета должно быть глобально уникальным
   - Используйте только строчные буквы, цифры и дефисы
4. Выберите регион (рекомендуется выбрать тот же регион, где размещена Lambda функция)
5. В разделе "Object Ownership" выберите "ACLs disabled"
6. В разделе "Block Public Access settings for this bucket" оставьте все опции включенными для безопасности
7. В разделе "Bucket Versioning" выберите "Enable" для сохранения истории изменений файлов
8. В разделе "Default encryption" выберите "Enable" и используйте "Amazon S3 managed keys (SSE-S3)"
9. Нажмите "Create bucket"

## 2. Настройка жизненного цикла объектов

Для автоматического управления хранением отчетов:

1. Перейдите в [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Выберите созданный бакет
3. Перейдите на вкладку "Management"
4. В разделе "Lifecycle rules" нажмите "Create lifecycle rule"
5. Введите имя правила (например, "Reports-Lifecycle")
6. В разделе "Rule scope" выберите "Apply to all objects in the bucket" или укажите префикс (например, "reports/")
7. В разделе "Lifecycle rule actions" выберите:
   - "Move current versions of objects between storage classes"
   - "Expire current versions of objects"
8. Настройте переходы между классами хранения:
   - Через 30 дней переместить в "Standard-IA"
   - Через 90 дней переместить в "Glacier"
9. Настройте срок хранения:
   - Удалять объекты через 365 дней (или другой срок по вашему выбору)
10. Нажмите "Create rule"

## 3. Настройка IAM политики для доступа к бакету

### Создание политики для Lambda функции

1. Перейдите в [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Выберите "Policies" в левом меню и нажмите "Create policy"
3. Перейдите на вкладку "JSON" и вставьте следующую политику:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::fb-ads-reports-bucket",
                "arn:aws:s3:::fb-ads-reports-bucket/*"
            ]
        }
    ]
}
```

4. Замените `fb-ads-reports-bucket` на имя вашего бакета
5. Нажмите "Next: Tags", добавьте теги при необходимости
6. Нажмите "Next: Review"
7. Введите имя политики (например, `S3FacebookAdsReportsAccess`) и описание
8. Нажмите "Create policy"

### Присоединение политики к роли Lambda

1. Перейдите в [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Выберите "Roles" в левом меню
3. Найдите и выберите роль, используемую вашей Lambda функцией
4. Нажмите "Attach policies"
5. Найдите созданную политику и выберите ее
6. Нажмите "Attach policy"

## 4. Структура хранения отчетов в S3

Рекомендуется организовать хранение отчетов в S3 с использованием следующей структуры:

```
fb-ads-reports-bucket/
├── daily/
│   ├── YYYY-MM-DD/
│   │   ├── campaign_report.csv
│   │   ├── campaign_report.json
│   │   ├── adset_report.csv
│   │   └── ad_report.csv
│   └── ...
├── weekly/
│   ├── YYYY-MM-DD_YYYY-MM-DD/
│   │   ├── weekly_report.csv
│   │   └── weekly_report.json
│   └── ...
├── monthly/
│   ├── YYYY-MM/
│   │   ├── monthly_report.csv
│   │   └── monthly_report.json
│   └── ...
└── custom/
    └── ...
```

## 5. Загрузка файлов в S3 из Lambda функции

### Пример кода для загрузки отчета в S3

```python
import boto3
import os
from datetime import datetime

def upload_report_to_s3(report_data, report_type='daily', file_format='csv'):
    """
    Загружает отчет в S3 бакет.
    
    Args:
        report_data (str): Содержимое отчета
        report_type (str): Тип отчета (daily, weekly, monthly, custom)
        file_format (str): Формат файла (csv, json)
    
    Returns:
        str: URL загруженного файла
    """
    # Получаем имя бакета из переменных окружения
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME не задан в переменных окружения")
    
    # Создаем клиент S3
    s3_client = boto3.client('s3')
    
    # Формируем путь к файлу
    today = datetime.now()
    
    if report_type == 'daily':
        folder = f"daily/{today.strftime('%Y-%m-%d')}"
    elif report_type == 'weekly':
        # Вычисляем начало и конец недели
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        folder = f"weekly/{start_of_week.strftime('%Y-%m-%d')}_{end_of_week.strftime('%Y-%m-%d')}"
    elif report_type == 'monthly':
        folder = f"monthly/{today.strftime('%Y-%m')}"
    else:
        folder = f"custom/{today.strftime('%Y-%m-%d')}"
    
    # Формируем имя файла
    filename = f"campaign_report.{file_format}"
    
    # Полный путь к файлу в S3
    s3_key = f"{folder}/{filename}"
    
    try:
        # Загружаем файл в S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=report_data,
            ContentType=f"text/{file_format}" if file_format == 'csv' else 'application/json'
        )
        
        # Формируем URL файла
        region = boto3.session.Session().region_name
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        
        print(f"Отчет успешно загружен в S3: {s3_url}")
        return s3_url
    
    except Exception as e:
        print(f"Ошибка при загрузке отчета в S3: {str(e)}")
        raise
```

### Пример использования функции загрузки

```python
# Пример создания CSV отчета
import pandas as pd
from io import StringIO

def generate_and_upload_campaign_report(campaigns_data):
    """
    Генерирует и загружает отчет по кампаниям в S3.
    
    Args:
        campaigns_data (list): Список словарей с данными кампаний
    
    Returns:
        str: URL загруженного файла
    """
    # Создаем DataFrame из данных
    df = pd.DataFrame(campaigns_data)
    
    # Преобразуем DataFrame в CSV
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    
    # Загружаем CSV в S3
    s3_url = upload_report_to_s3(csv_buffer.getvalue(), report_type='daily', file_format='csv')
    
    return s3_url
```

## 6. Получение файлов из S3

### Пример кода для получения отчета из S3

```python
import boto3
import os

def get_report_from_s3(report_date, report_type='daily', file_format='csv', filename='campaign_report'):
    """
    Получает отчет из S3 бакета.
    
    Args:
        report_date (str): Дата отчета в формате YYYY-MM-DD
        report_type (str): Тип отчета (daily, weekly, monthly, custom)
        file_format (str): Формат файла (csv, json)
        filename (str): Имя файла без расширения
    
    Returns:
        str: Содержимое отчета
    """
    # Получаем имя бакета из переменных окружения
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME не задан в переменных окружения")
    
    # Создаем клиент S3
    s3_client = boto3.client('s3')
    
    # Формируем путь к файлу
    if report_type == 'daily':
        folder = f"daily/{report_date}"
    elif report_type == 'weekly':
        folder = f"weekly/{report_date}"  # Предполагается, что report_date содержит диапазон дат
    elif report_type == 'monthly':
        folder = f"monthly/{report_date}"  # Предполагается, что report_date в формате YYYY-MM
    else:
        folder = f"custom/{report_date}"
    
    # Полный путь к файлу в S3
    s3_key = f"{folder}/{filename}.{file_format}"
    
    try:
        # Получаем файл из S3
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        
        # Читаем содержимое файла
        report_content = response['Body'].read().decode('utf-8')
        
        return report_content
    
    except Exception as e:
        print(f"Ошибка при получении отчета из S3: {str(e)}")
        raise
```

## 7. Генерация пресетов URL для доступа к отчетам

### Создание временных URL для доступа к отчетам

```python
import boto3
import os
from datetime import datetime, timedelta

def generate_presigned_url(s3_key, expiration=3600):
    """
    Генерирует временный URL для доступа к файлу в S3.
    
    Args:
        s3_key (str): Путь к файлу в S3
        expiration (int): Срок действия URL в секундах (по умолчанию 1 час)
    
    Returns:
        str: Временный URL для доступа к файлу
    """
    # Получаем имя бакета из переменных окружения
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME не задан в переменных окружения")
    
    # Создаем клиент S3
    s3_client = boto3.client('s3')
    
    try:
        # Генерируем временный URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        
        return presigned_url
    
    except Exception as e:
        print(f"Ошибка при генерации временного URL: {str(e)}")
        raise
```

## 8. Мониторинг использования S3

### Настройка уведомлений о событиях S3

1. Перейдите в [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Выберите ваш бакет
3. Перейдите на вкладку "Properties"
4. В разделе "Event notifications" нажмите "Create event notification"
5. Введите имя уведомления (например, "ReportUploaded")
6. В разделе "Event types" выберите "All object create events"
7. В разделе "Destination" выберите "Lambda function"
8. Выберите вашу Lambda функцию или создайте новую
9. Нажмите "Save changes"

### Настройка метрик CloudWatch

1. Перейдите в [AWS CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
2. Выберите "Metrics" в левом меню
3. Выберите "S3" в списке сервисов
4. Выберите "Storage Metrics" или "Request Metrics"
5. Найдите метрики для вашего бакета
6. Создайте панель мониторинга с нужными метриками

## 9. Оптимизация затрат

### Использование классов хранения

Для оптимизации затрат на хранение отчетов можно использовать разные классы хранения:

1. **Standard**: Для новых отчетов, к которым требуется частый доступ
2. **Standard-IA**: Для отчетов, к которым доступ требуется реже (например, старше 30 дней)
3. **Glacier**: Для архивных отчетов (например, старше 90 дней)

Настройте правила жизненного цикла (см. раздел 2) для автоматического перемещения объектов между классами хранения.

### Настройка бюджета

1. Перейдите в [AWS Billing Console](https://console.aws.amazon.com/billing/)
2. Выберите "Budgets" в левом меню
3. Нажмите "Create budget"
4. Выберите "Cost budget"
5. Настройте бюджет для отслеживания затрат на S3
6. Настройте оповещения при превышении бюджета

## 10. Безопасность

### Шифрование данных

1. Перейдите в [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Выберите ваш бакет
3. Перейдите на вкладку "Properties"
4. В разделе "Default encryption" нажмите "Edit"
5. Выберите "Enable" и используйте "Amazon S3 managed keys (SSE-S3)" или "AWS Key Management Service key (SSE-KMS)"
6. Нажмите "Save changes"

### Настройка политики бакета для ограничения доступа

1. Перейдите в [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Выберите ваш бакет
3. Перейдите на вкладку "Permissions"
4. В разделе "Bucket policy" нажмите "Edit"
5. Вставьте следующую политику:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::fb-ads-reports-bucket",
                "arn:aws:s3:::fb-ads-reports-bucket/*"
            ],
            "Condition": {
                "Bool": {
                    "aws:SecureTransport": "false"
                }
            }
        },
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::ACCOUNT_ID:role/facebook-ads-lambda-role"
            },
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::fb-ads-reports-bucket",
                "arn:aws:s3:::fb-ads-reports-bucket/*"
            ]
        }
    ]
}
```

6. Замените `fb-ads-reports-bucket` на имя вашего бакета
7. Замените `ACCOUNT_ID` на ID вашего AWS аккаунта
8. Замените `facebook-ads-lambda-role` на имя роли вашей Lambda функции
9. Нажмите "Save changes"

## Полезные ресурсы

- [Документация AWS S3](https://docs.aws.amazon.com/s3/)
- [Руководство по безопасности S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [Руководство по оптимизации затрат S3](https://aws.amazon.com/blogs/storage/s3-cost-optimization-for-predictable-and-dynamic-access-patterns/)
- [Руководство по жизненному циклу объектов S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
