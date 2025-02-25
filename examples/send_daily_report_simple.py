#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для отправки ежедневного отчета в Telegram канал.
Использует реальные данные из Facebook API.
"""

import os
import logging
import asyncio
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv

from telegram import Bot

from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.reports.report_generator import get_campaigns_list, get_campaign_data

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_LOG_CHANNEL_ID = os.getenv('TELEGRAM_LOG_CHANNEL_ID')

async def send_message_to_channel(message):
    """
    Отправка сообщения в Telegram канал.
    
    Args:
        message (str): Текст сообщения для отправки.
    """
    try:
        logger.info(f"Отправка сообщения в канал {TELEGRAM_LOG_CHANNEL_ID}")
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=TELEGRAM_LOG_CHANNEL_ID,
            text=message,
            parse_mode='Markdown'
        )
        logger.info("Сообщение успешно отправлено")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        logger.error(traceback.format_exc())
        return False

def get_real_data():
    """
    Получение реальных данных о рекламных кампаниях из Facebook API.
    
    Returns:
        dict: Словарь с данными о кампаниях или None в случае ошибки.
    """
    try:
        logger.info("Инициализация Facebook API")
        auth = FacebookAuth()
        auth.initialize()
        logger.info(f"Facebook API инициализирован. Аккаунт: {auth.get_ad_account_id()}")
        
        # Получаем данные о кампаниях за последние 24 часа
        logger.info("Получение данных о кампаниях")
        yesterday = datetime.now() - timedelta(days=1)
        
        # Получаем список активных кампаний
        campaigns = get_campaigns_list(status='ACTIVE')
        
        if not campaigns:
            logger.warning("Не удалось получить список кампаний")
            return None
        
        logger.info(f"Получено {len(campaigns)} активных кампаний")
        
        # Получаем детальные данные по каждой кампании
        campaigns_with_metrics = get_campaign_data(
            campaign_id=None,
            days=1,
            status='ACTIVE',
            date_preset='yesterday',
            fields=['impressions', 'clicks', 'spend', 'conversions']
        )
        
        if not campaigns_with_metrics:
            logger.warning("Не удалось получить метрики кампаний")
            return None
        
        # Рассчитываем общие метрики
        total_impressions = sum(c.get('metrics', {}).get('impressions', 0) for c in campaigns_with_metrics)
        total_clicks = sum(c.get('metrics', {}).get('clicks', 0) for c in campaigns_with_metrics)
        total_spend = sum(c.get('metrics', {}).get('spend', 0) for c in campaigns_with_metrics)
        total_conversions = sum(c.get('metrics', {}).get('conversions', 0) for c in campaigns_with_metrics)
        
        # Рассчитываем производные метрики
        total_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        total_cpc = total_spend / total_clicks if total_clicks > 0 else 0
        total_cost_per_conversion = total_spend / total_conversions if total_conversions > 0 else 0
        
        # Добавляем CTR для каждой кампании для сортировки
        for campaign in campaigns_with_metrics:
            metrics = campaign.get('metrics', {})
            impressions = metrics.get('impressions', 0)
            clicks = metrics.get('clicks', 0)
            campaign['ctr'] = (clicks / impressions * 100) if impressions > 0 else 0
        
        return {
            'campaigns': campaigns_with_metrics,
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_spend': total_spend,
            'total_conversions': total_conversions,
            'total_ctr': total_ctr,
            'total_cpc': total_cpc,
            'total_cost_per_conversion': total_cost_per_conversion
        }
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных из Facebook API: {e}")
        logger.error(traceback.format_exc())
        return None

def format_daily_report(data):
    """
    Форматирование ежедневного отчета.
    
    Args:
        data (dict): Данные для отчета.
        
    Returns:
        str: Отформатированный текст отчета.
    """
    # Если данные не получены, возвращаем сообщение об ошибке
    if not data:
        today = datetime.now().strftime('%d.%m.%Y')
        return (
            f"📊 *Ежедневный отчет по рекламным кампаниям Facebook*\n"
            f"📅 Дата: {today}\n\n"
            f"⚠️ *Внимание:* Не удалось получить данные от Facebook API.\n\n"
            f"Возможные причины:\n"
            f"• Недействительный или просроченный токен доступа\n"
            f"• Отсутствие доступа к рекламному аккаунту\n"
            f"• Проблемы с подключением к Facebook API\n\n"
            f"Пожалуйста, проверьте настройки доступа и попробуйте снова."
        )
    
    # Даты для отчета
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    date_range = f"{yesterday.strftime('%d.%m.%Y')} - {today.strftime('%d.%m.%Y')}"
    
    # Заголовок отчета
    report = (
        f"📊 *Ежедневный отчет по рекламным кампаниям Facebook*\n"
        f"📅 Период: {date_range}\n\n"
        f"*Общие показатели:*\n"
        f"💰 Расход: {data['total_spend']:.2f} руб.\n"
        f"👁 Показы: {data['total_impressions']:,}\n"
        f"🖱 Клики: {data['total_clicks']:,}\n"
        f"📈 CTR: {data['total_ctr']:.2f}%\n"
        f"💵 CPC: {data['total_cpc']:.2f} руб.\n"
        f"🎯 Конверсии: {data['total_conversions']:,}\n"
        f"💸 Стоимость конверсии: {data['total_cost_per_conversion']:.2f} руб.\n\n"
    )
    
    # Топ кампаний
    report += "*Топ кампаний по эффективности:*\n"
    # Сортируем кампании по CTR
    sorted_campaigns = sorted(data['campaigns'], key=lambda x: x.get('ctr', 0), reverse=True)
    for i, campaign in enumerate(sorted_campaigns[:3], 1):
        metrics = campaign.get('metrics', {})
        status_emoji = "🟢" if campaign.get('status') == 'ACTIVE' else "🔴"
        report += (
            f"{i}. {status_emoji} *{campaign.get('name', 'Без имени')}*\n"
            f"   Показы: {metrics.get('impressions', 0):,} | "
            f"Клики: {metrics.get('clicks', 0):,} | "
            f"CTR: {campaign.get('ctr', 0):.2f}%\n"
            f"   Расход: {metrics.get('spend', 0):.2f} руб. | "
            f"Конверсии: {metrics.get('conversions', 0)}\n\n"
        )
    
    # Рекомендации
    report += "*Рекомендации:*\n"
    if data['total_ctr'] < 1.0:
        report += "• Низкий CTR. Рекомендуется пересмотреть креативы и таргетинг.\n"
    if data['total_cpc'] > 50:
        report += "• Высокий CPC. Рекомендуется оптимизировать ставки и таргетинг.\n"
    if data['total_cost_per_conversion'] > 500:
        report += "• Высокая стоимость конверсии. Рекомендуется оптимизировать таргетинг и бюджет.\n"
    
    # Если нет рекомендаций, добавляем стандартную
    if "Рекомендации:\n" == report.split("*Рекомендации:*\n")[1]:
        report += "• Показатели в пределах нормы. Рекомендуется продолжать текущую стратегию.\n"
    
    return report

async def main():
    """
    Основная функция для запуска отправки отчета.
    """
    logger.info("Запуск скрипта отправки ежедневного отчета")
    
    # Проверяем наличие необходимых переменных окружения
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_LOG_CHANNEL_ID:
        logger.error("Отсутствуют необходимые переменные окружения: TELEGRAM_BOT_TOKEN или TELEGRAM_LOG_CHANNEL_ID")
        return
    
    # Получаем реальные данные из Facebook API
    data = get_real_data()
    
    # Форматируем отчет
    report = format_daily_report(data)
    
    # Отправляем отчет
    await send_message_to_channel(report)

if __name__ == "__main__":
    asyncio.run(main()) 