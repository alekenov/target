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
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем текущую директорию в PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def lambda_handler(event, context):
    """
    Обработчик AWS Lambda для интеграции с API Gateway и обновления данных.
    
    Args:
        event (dict): Событие API Gateway или EventBridge
        context (object): Контекст выполнения Lambda
        
    Returns:
        dict: Ответ для API Gateway или EventBridge
    """
    try:
        logger.info(f"Получено событие: {json.dumps(event)}")
        
        # Проверяем, является ли это запросом на обновление данных
        if 'path' in event and event['path'] == '/update_data':
            logger.info("Запущено обновление данных о рекламных кампаниях")
            from show_data import update_facebook_ads_data
            
            # Обновляем данные о рекламных кампаниях
            result = update_facebook_ads_data()
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "Данные успешно обновлены",
                    "timestamp": datetime.now().isoformat(),
                    "result": result
                })
            }
        
        # Если это обычный запрос на отображение дашборда
        logger.info("Запрос на отображение дашборда")
        
        # Импортируем aws-wsgi для преобразования событий API Gateway в WSGI
        from awsgi import response
        
        # Импортируем Flask-приложение
        from simple_dashboard import app
        
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

if __name__ == "__main__":
    # Для локального тестирования
    test_event = {
        "path": "/",
        "httpMethod": "GET",
        "headers": {
            "Host": "localhost:5005"
        }
    }
    
    print(lambda_handler(test_event, None))
