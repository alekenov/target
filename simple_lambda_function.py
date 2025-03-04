#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Упрощенная AWS Lambda функция для получения ежедневной статистики и трат из Facebook аккаунта
и отправки отчета в Telegram.
"""

import os
import logging
from datetime import datetime
import asyncio
import traceback
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Импортируем необходимые модули
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError
from telegram import Bot

from facebook_ads_toolkit.reports.formatters.telegram_formatter import TelegramFormatter
from facebook_ads_toolkit.reports.daily_report import DailyReport
from facebook_ads_toolkit.reports.hourly_report import HourlyReport

class FacebookAuth:
    """Класс для авторизации в Facebook Marketing API."""
    
    def __init__(self):
        """Инициализация класса авторизации."""
        self.app_id = os.getenv('FB_APP_ID')
        self.app_secret = os.getenv('FB_APP_SECRET', '')
        self.access_token = os.getenv('FB_ACCESS_TOKEN')
        self.account_id = os.getenv('FB_ACCOUNT_ID')
        
        if not self.app_id or not self.access_token or not self.account_id:
            logger.error("Не указаны FB_APP_ID, FB_ACCESS_TOKEN или FB_ACCOUNT_ID")
            raise ValueError("Не указаны обязательные переменные окружения")
    
    def initialize(self):
        """
        Инициализирует соединение с Facebook API.
        
        Returns:
            tuple: (AdAccount, FacebookAdsApi) - объект аккаунта и API
        """
        try:
            # Инициализация API
            api = FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self.access_token
            )
            
            # Получение объекта аккаунта
            account = AdAccount(f'act_{self.account_id}')
            
            logger.info(f"Успешно инициализировано соединение с Facebook API для аккаунта {self.account_id}")
            return account, api
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации Facebook API: {str(e)}")
            return None, None

def get_report_data():
    """Получает данные для отчета."""
    now = datetime.now()
    
    # Создаем отчеты
    daily_report = DailyReport()
    hourly_report = HourlyReport()
    
    # Получаем данные отчетов
    daily_data = daily_report.generate_report(now)
    hourly_data = hourly_report.generate_report(now)
    
    return {
        'daily': daily_data,
        'hourly': hourly_data
    }

def format_telegram_reports(report_data):
    """Форматирует отчеты для Telegram."""
    formatter = TelegramFormatter()
    
    # Форматируем каждый тип отчета
    daily_messages = formatter.format_report(report_data['daily'], 'daily')
    hourly_messages = formatter.format_report(report_data['hourly'], 'hourly')
    
    return daily_messages + hourly_messages

async def send_to_telegram(messages):
    """Отправляет сообщения в Telegram."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        raise ValueError("Не указан TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
    
    bot = Bot(token=bot_token)
    
    try:
        for message in messages:
            # Отправляем сообщение с поддержкой Markdown
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            # Небольшая задержка между сообщениями
            await asyncio.sleep(0.5)
            
    except Exception as e:
        logger.error(f"Ошибка при отправке в Telegram: {str(e)}")
        raise

async def main_async():
    """Асинхронная функция для получения и отправки отчетов."""
    try:
        # Получаем данные отчетов
        report_data = get_report_data()
        
        # Форматируем отчеты для Telegram
        messages = format_telegram_reports(report_data)
        
        # Отправляем отчеты
        await send_to_telegram(messages)
        
        logger.info("Отчеты успешно отправлены в Telegram")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def lambda_handler(event, context):
    """
    Обработчик AWS Lambda.
    
    Args:
        event (dict): Событие Lambda
        context (object): Контекст выполнения Lambda
        
    Returns:
        dict: Результат выполнения
    """
    try:
        asyncio.run(main_async())
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Отчеты успешно отправлены'})
        }
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Ошибка Lambda: {error_message}")
        logger.error(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        }

if __name__ == "__main__":
    asyncio.run(main_async())
