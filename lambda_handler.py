#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AWS Lambda обработчик для Facebook Ads Dashboard.
Интегрирует Flask-приложение с AWS Lambda через API Gateway.
"""

import os
import sys
import json
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем текущую директорию в PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Импортируем Flask-приложение
from simple_dashboard import app

def lambda_handler(event, context):
    """
    Обработчик AWS Lambda для интеграции с API Gateway.
    
    Args:
        event (dict): Событие API Gateway
        context (object): Контекст выполнения Lambda
        
    Returns:
        dict: Ответ для API Gateway
    """
    try:
        logger.info(f"Получено событие: {json.dumps(event)}")
        
        # Импортируем aws-wsgi для преобразования событий API Gateway в WSGI
        from awsgi import response
        
        # Возвращаем ответ Flask-приложения
        return response(app, event, context)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {type(e)} - {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Внутренняя ошибка сервера",
                "message": str(e)
            })
        }
