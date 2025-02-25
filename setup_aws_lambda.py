#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для настройки AWS Lambda через API.
Этот скрипт создает все необходимые ресурсы для запуска ежедневного отчета по рекламным кампаниям Facebook.
"""

import os
import sys
import boto3
import json
import time
import uuid
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Конфигурация AWS
AWS_REGION = 'us-east-1'  # Можно изменить на нужный регион
LAMBDA_FUNCTION_NAME = 'fb-ads-daily-report'
LAMBDA_ROLE_NAME = 'fb-ads-lambda-role'
S3_BUCKET_NAME = f'fb-ads-reports-{uuid.uuid4().hex[:8]}'  # Генерируем уникальное имя бакета
LAMBDA_PACKAGE_ZIP = 'lambda_package.zip'
EVENT_RULE_NAME = 'fb-ads-daily-report-schedule'

# Конфигурация Facebook и Telegram
# Эти значения нужно заменить на реальные
FACEBOOK_APP_ID = 'YOUR_FB_APP_ID'
FACEBOOK_APP_SECRET = 'YOUR_FB_APP_SECRET'
FACEBOOK_ACCESS_TOKEN = 'YOUR_FB_ACCESS_TOKEN'
FACEBOOK_AD_ACCOUNT_ID = 'YOUR_FB_AD_ACCOUNT_ID'
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'

def create_s3_bucket():
    """
    Создает S3 бакет для хранения отчетов и пакета Lambda.
    
    Returns:
        str: Имя созданного бакета
    """
    logger.info(f"Создание S3 бакета: {S3_BUCKET_NAME}")
    
    try:
        s3 = boto3.client('s3', region_name=AWS_REGION)
        
        # Создаем бакет
        if AWS_REGION == 'us-east-1':
            s3.create_bucket(Bucket=S3_BUCKET_NAME)
        else:
            s3.create_bucket(
                Bucket=S3_BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
        
        # Настраиваем жизненный цикл объектов (удаление через 30 дней)
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'DeleteOldReports',
                    'Status': 'Enabled',
                    'Prefix': 'reports/',
                    'Expiration': {'Days': 30}
                }
            ]
        }
        
        s3.put_bucket_lifecycle_configuration(
            Bucket=S3_BUCKET_NAME,
            LifecycleConfiguration=lifecycle_config
        )
        
        logger.info(f"S3 бакет {S3_BUCKET_NAME} успешно создан")
        return S3_BUCKET_NAME
    
    except Exception as e:
        logger.error(f"Ошибка при создании S3 бакета: {str(e)}")
        raise

def upload_lambda_package():
    """
    Загружает пакет Lambda в S3 бакет.
    
    Returns:
        bool: True, если загрузка успешна, иначе False
    """
    logger.info(f"Загрузка пакета Lambda в S3 бакет: {S3_BUCKET_NAME}")
    
    try:
        s3 = boto3.client('s3', region_name=AWS_REGION)
        
        # Проверяем, существует ли файл пакета
        if not os.path.exists(LAMBDA_PACKAGE_ZIP):
            logger.error(f"Файл пакета Lambda не найден: {LAMBDA_PACKAGE_ZIP}")
            return False
        
        # Загружаем пакет в S3
        with open(LAMBDA_PACKAGE_ZIP, 'rb') as file_data:
            s3.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=LAMBDA_PACKAGE_ZIP,
                Body=file_data
            )
        
        logger.info(f"Пакет Lambda успешно загружен в S3 бакет: s3://{S3_BUCKET_NAME}/{LAMBDA_PACKAGE_ZIP}")
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке пакета Lambda: {str(e)}")
        return False

def create_iam_role():
    """
    Создает IAM роль для Lambda функции.
    
    Returns:
        str: ARN созданной роли
    """
    logger.info(f"Создание IAM роли: {LAMBDA_ROLE_NAME}")
    
    try:
        iam = boto3.client('iam', region_name=AWS_REGION)
        
        # Создаем политику доверия для Lambda
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Создаем роль
        response = iam.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for Facebook Ads Daily Report Lambda function'
        )
        
        role_arn = response['Role']['Arn']
        
        # Добавляем базовую политику для выполнения Lambda
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        # Создаем политику для доступа к S3
        s3_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject"
                    ],
                    "Resource": f"arn:aws:s3:::{S3_BUCKET_NAME}/*"
                }
            ]
        }
        
        # Создаем и прикрепляем политику для S3
        policy_name = f"{LAMBDA_ROLE_NAME}-s3-policy"
        iam.put_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(s3_policy)
        )
        
        # Ждем, пока роль станет доступна
        logger.info("Ожидание активации IAM роли (10 секунд)...")
        time.sleep(10)
        
        logger.info(f"IAM роль {LAMBDA_ROLE_NAME} успешно создана: {role_arn}")
        return role_arn
    
    except Exception as e:
        logger.error(f"Ошибка при создании IAM роли: {str(e)}")
        raise

def create_lambda_function(role_arn):
    """
    Создает Lambda функцию.
    
    Args:
        role_arn (str): ARN IAM роли для Lambda
        
    Returns:
        str: ARN созданной Lambda функции
    """
    logger.info(f"Создание Lambda функции: {LAMBDA_FUNCTION_NAME}")
    
    try:
        lambda_client = boto3.client('lambda', region_name=AWS_REGION)
        
        # Настраиваем переменные окружения
        environment_variables = {
            'S3_BUCKET_NAME': S3_BUCKET_NAME,
            'FACEBOOK_APP_ID': FACEBOOK_APP_ID,
            'FACEBOOK_APP_SECRET': FACEBOOK_APP_SECRET,
            'FACEBOOK_ACCESS_TOKEN': FACEBOOK_ACCESS_TOKEN,
            'FACEBOOK_AD_ACCOUNT_ID': FACEBOOK_AD_ACCOUNT_ID,
            'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
            'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
        }
        
        # Создаем Lambda функцию
        response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime='python3.9',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={
                'S3Bucket': S3_BUCKET_NAME,
                'S3Key': LAMBDA_PACKAGE_ZIP
            },
            Description='Lambda function for Facebook Ads Daily Report',
            Timeout=300,
            MemorySize=512,
            Environment={
                'Variables': environment_variables
            },
            Publish=True
        )
        
        function_arn = response['FunctionArn']
        logger.info(f"Lambda функция {LAMBDA_FUNCTION_NAME} успешно создана: {function_arn}")
        return function_arn
    
    except Exception as e:
        logger.error(f"Ошибка при создании Lambda функции: {str(e)}")
        raise

def create_event_rule(lambda_arn):
    """
    Создает правило EventBridge для запуска Lambda функции по расписанию.
    
    Args:
        lambda_arn (str): ARN Lambda функции
        
    Returns:
        str: ARN созданного правила
    """
    logger.info(f"Создание правила EventBridge: {EVENT_RULE_NAME}")
    
    try:
        events = boto3.client('events', region_name=AWS_REGION)
        
        # Создаем правило с расписанием (ежедневно в 8:00 UTC)
        response = events.put_rule(
            Name=EVENT_RULE_NAME,
            ScheduleExpression='cron(0 8 * * ? *)',
            State='ENABLED',
            Description='Triggers Facebook Ads Daily Report Lambda function every day at 8:00 UTC'
        )
        
        rule_arn = response['RuleArn']
        
        # Добавляем Lambda функцию как цель правила
        events.put_targets(
            Rule=EVENT_RULE_NAME,
            Targets=[
                {
                    'Id': 'DailyReportLambdaTarget',
                    'Arn': lambda_arn
                }
            ]
        )
        
        # Добавляем разрешение для EventBridge вызывать Lambda функцию
        lambda_client = boto3.client('lambda', region_name=AWS_REGION)
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId=f"{EVENT_RULE_NAME}-invoke",
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=rule_arn
        )
        
        logger.info(f"Правило EventBridge {EVENT_RULE_NAME} успешно создано: {rule_arn}")
        return rule_arn
    
    except Exception as e:
        logger.error(f"Ошибка при создании правила EventBridge: {str(e)}")
        raise

def test_lambda_function():
    """
    Тестирует Lambda функцию, вызывая ее вручную.
    
    Returns:
        dict: Результат выполнения функции
    """
    logger.info(f"Тестирование Lambda функции: {LAMBDA_FUNCTION_NAME}")
    
    try:
        lambda_client = boto3.client('lambda', region_name=AWS_REGION)
        
        # Вызываем Lambda функцию
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload=json.dumps({})
        )
        
        # Получаем результат
        status_code = response['StatusCode']
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        if status_code == 200:
            logger.info(f"Lambda функция успешно выполнена: {payload}")
        else:
            logger.error(f"Ошибка при выполнении Lambda функции: {payload}")
        
        return payload
    
    except Exception as e:
        logger.error(f"Ошибка при тестировании Lambda функции: {str(e)}")
        return {'error': str(e)}

def main():
    """
    Основная функция скрипта.
    """
    try:
        # Проверяем, заполнены ли переменные конфигурации
        if (FACEBOOK_APP_ID.startswith('YOUR_') or
            FACEBOOK_APP_SECRET.startswith('YOUR_') or
            FACEBOOK_ACCESS_TOKEN.startswith('YOUR_') or
            FACEBOOK_AD_ACCOUNT_ID.startswith('YOUR_') or
            TELEGRAM_BOT_TOKEN.startswith('YOUR_') or
            TELEGRAM_CHAT_ID.startswith('YOUR_')):
            logger.error("Необходимо заполнить переменные конфигурации в скрипте")
            print("\nПожалуйста, откройте скрипт и замените следующие значения на реальные:")
            print("FACEBOOK_APP_ID = 'YOUR_FB_APP_ID'")
            print("FACEBOOK_APP_SECRET = 'YOUR_FB_APP_SECRET'")
            print("FACEBOOK_ACCESS_TOKEN = 'YOUR_FB_ACCESS_TOKEN'")
            print("FACEBOOK_AD_ACCOUNT_ID = 'YOUR_FB_AD_ACCOUNT_ID'")
            print("TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'")
            print("TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'")
            return
        
        # Проверяем, существует ли пакет Lambda
        if not os.path.exists(LAMBDA_PACKAGE_ZIP):
            logger.error(f"Файл пакета Lambda не найден: {LAMBDA_PACKAGE_ZIP}")
            print(f"\nПожалуйста, создайте пакет Lambda, выполнив скрипт prepare_lambda_package.sh:")
            print("./prepare_lambda_package.sh")
            return
        
        # Создаем S3 бакет
        bucket_name = create_s3_bucket()
        
        # Загружаем пакет Lambda в S3
        if not upload_lambda_package():
            logger.error("Не удалось загрузить пакет Lambda в S3")
            return
        
        # Создаем IAM роль
        role_arn = create_iam_role()
        
        # Создаем Lambda функцию
        lambda_arn = create_lambda_function(role_arn)
        
        # Создаем правило EventBridge
        rule_arn = create_event_rule(lambda_arn)
        
        # Выводим информацию о созданных ресурсах
        print("\n=== Ресурсы AWS успешно созданы ===")
        print(f"S3 бакет: {S3_BUCKET_NAME}")
        print(f"IAM роль: {LAMBDA_ROLE_NAME} ({role_arn})")
        print(f"Lambda функция: {LAMBDA_FUNCTION_NAME} ({lambda_arn})")
        print(f"EventBridge правило: {EVENT_RULE_NAME} ({rule_arn})")
        
        # Спрашиваем, нужно ли протестировать Lambda функцию
        test_lambda = input("\nХотите протестировать Lambda функцию? (y/n): ")
        if test_lambda.lower() == 'y':
            result = test_lambda_function()
            print(f"\nРезультат тестирования Lambda функции: {json.dumps(result, indent=2)}")
        
        print("\nНастройка AWS Lambda для ежедневного отчета по рекламным кампаниям Facebook завершена!")
        print("Отчеты будут генерироваться ежедневно в 8:00 UTC и отправляться в Telegram.")
        
    except Exception as e:
        logger.error(f"Ошибка при настройке AWS Lambda: {str(e)}")
        print(f"\nПроизошла ошибка: {str(e)}")
        print("Пожалуйста, проверьте логи для получения дополнительной информации.")

if __name__ == "__main__":
    main() 