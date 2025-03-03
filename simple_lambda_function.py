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

def get_campaign_stats():
    """Получает статистику по всем кампаниям."""
    today = datetime.now().strftime('%Y-%m-%d')
    
    auth = FacebookAuth()
    account, api = auth.initialize()
    
    if not account or not api:
        raise Exception("Ошибка инициализации Facebook API")
    
    params = {
        'time_range': {'since': today, 'until': today},
        'level': 'campaign',
        'fields': [
            'campaign_name',
            'objective',
            'spend',
            'impressions',
            'clicks',
            'ctr',
            'cpc',
            'actions',
            'cost_per_action_type',
            'website_ctr',
            'website_purchase_roas'
        ]
    }
    
    insights = account.get_insights(params=params)
    campaigns_data = list(insights)
    
    return campaigns_data

def format_telegram_report():
    """Форматирует отчет для Telegram."""
    today = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M:%S')
    campaigns = get_campaign_stats()
    
    # Подготовка данных для отчета
    total_spend = 0
    total_conversations = 0
    total_website_clicks = 0
    active_campaigns = 0
    
    report_text = f"""📊 *Отчет о тратах на рекламу Facebook*
📅 Дата: {today}
⏰ Время: {current_time}
🆔 Аккаунт: act\_4795321857166878

"""
    
    # Форматируем данные по каждой кампании
    for i, campaign in enumerate(campaigns, 1):
        name = campaign.get('campaign_name', 'Неизвестно').replace('.', '\\.').replace('-', '\\-')
        objective = campaign.get('objective', '').lower()
        spend = float(campaign.get('spend', 0))
        impressions = int(campaign.get('impressions', 0))
        clicks = int(campaign.get('clicks', 0))
        ctr = float(campaign.get('ctr', 0))  # CTR уже в процентах от Facebook
        cpc = float(campaign.get('cpc', 0))
        
        # Получаем данные о переписках
        conversations = 0
        cost_per_conversation = 0
        website_clicks = 0
        cost_per_website_click = 0
        
        actions = campaign.get('actions', [])
        for action in actions:
            action_type = action.get('action_type', '')
            if action_type == 'onsite_conversion.messaging_conversation_started_7d':
                conversations += int(action.get('value', 0))
            elif action_type == 'link_click':
                website_clicks += int(action.get('value', 0))
        
        cost_per_action = campaign.get('cost_per_action_type', [])
        for cost in cost_per_action:
            action_type = cost.get('action_type', '')
            if action_type == 'onsite_conversion.messaging_conversation_started_7d':
                cost_per_conversation = float(cost.get('value', 0))
            elif action_type == 'link_click':
                cost_per_website_click = float(cost.get('value', 0))
        
        if spend > 0:
            active_campaigns += 1
            total_spend += spend
            total_conversations += conversations
            total_website_clicks += website_clicks
            
            report_text += f"""*{i}\\. {name}*
💰 Расход: {spend:.2f} USD
👁 Показы: {impressions:,}
🖱 Клики: {clicks:,}
📈 CTR: {ctr:.2f}%
💵 CPC: {cpc:.2f} USD
"""
            
            # Добавляем специфичную статистику в зависимости от цели
            if 'messages' in objective or name.lower().startswith('широкая'):
                report_text += f"""💬 Переписки: {conversations}
📊 Цена за переписку: {cost_per_conversation:.2f} USD

"""
            else:  # для целей на сайт
                report_text += f"""🌐 Клики на сайт: {website_clicks}
📊 Цена за клик на сайт: {cost_per_website_click:.2f} USD

"""
    
    # Добавляем итоговую статистику
    avg_cost_per_conversation = total_spend / total_conversations if total_conversations > 0 else 0
    avg_cost_per_website_click = total_spend / total_website_clicks if total_website_clicks > 0 else 0
    
    report_text += f"""*ИТОГО:*
💰 Общий расход: {total_spend:.2f} USD
"""

    if total_conversations > 0:
        report_text += f"""💬 Всего переписок: {total_conversations}
📊 Средняя цена за переписку: {avg_cost_per_conversation:.2f} USD
"""

    if total_website_clicks > 0:
        report_text += f"""🌐 Всего кликов на сайт: {total_website_clicks}
📊 Средняя цена за клик на сайт: {avg_cost_per_website_click:.2f} USD
"""

    report_text += f"""📋 Всего активных кампаний: {active_campaigns}"""
    
    return report_text

async def send_to_telegram(message):
    """
    Отправляет сообщение в Telegram канал.
    
    Args:
        message (str): Текст сообщения
        
    Returns:
        bool: True, если сообщение успешно отправлено, иначе False
    """
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            logger.error("Не указаны TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
            return False
        
        bot = Bot(token=bot_token)
        
        # Пробуем отправить с форматированием
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='MarkdownV2'
            )
            logger.info(f"Сообщение успешно отправлено в Telegram (chat_id: {chat_id})")
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения в Telegram: {str(e)}")
            # Пробуем отправить без форматирования
            await bot.send_message(
                chat_id=chat_id,
                text=message.replace('*', '').replace('_', ''),
                parse_mode=None
            )
            logger.info(f"Сообщение отправлено без форматирования в чат {chat_id}")
            return True
            
    except Exception as e:
        logger.error(f"Критическая ошибка при отправке сообщения в Telegram: {str(e)}")
        return False

async def main_async():
    """
    Асинхронная функция для получения и отправки отчета о тратах.
    """
    try:
        # Форматируем отчет
        message = format_telegram_report()
        
        # Отправляем отчет в Telegram
        success = await send_to_telegram(message)
        
        if success:
            logger.info("Отчет успешно отправлен в Telegram")
        else:
            logger.error("Не удалось отправить отчет в Telegram")
    except Exception as e:
        logger.error(f"Ошибка при выполнении скрипта: {str(e)}")
        logger.error(traceback.format_exc())

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
        # Запускаем асинхронную функцию
        asyncio.run(main_async())
        
        return {
            'statusCode': 200,
            'body': 'Отчет успешно отправлен в Telegram'
        }
        
    except Exception as e:
        error_msg = f"Ошибка: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        return {
            'statusCode': 500,
            'body': error_msg
        }

if __name__ == "__main__":
    asyncio.run(main_async())
