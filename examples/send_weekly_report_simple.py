#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
from datetime import datetime, timedelta
import traceback

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.reports.report_generator import get_campaigns_list, get_campaign_insights
from facebook_ads_toolkit.integrations.telegram_integration import send_telegram_message

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def format_currency(value):
    """Форматирует числовое значение как валюту."""
    if value is None:
        return "0.00 ₽"
    return f"{float(value):.2f} ₽"

def format_percentage(value):
    """Форматирует числовое значение как процент."""
    if value is None:
        return "0.00%"
    return f"{float(value) * 100:.2f}%"

def get_weekly_report():
    """Формирует еженедельный отчет по рекламным кампаниям."""
    try:
        # Инициализация Facebook API
        logger.info("Инициализация Facebook API")
        auth = FacebookAuth()
        api = auth.get_api()
        account = auth.get_ad_account()
        logger.info(f"Facebook API инициализирован. Аккаунт: {account.get_id()}")

        # Получение данных о кампаниях
        logger.info("Получение данных о кампаниях")
        campaigns = get_campaigns_list(account, status=['ACTIVE'])
        
        if not campaigns:
            logger.warning("Нет данных о кампаниях для еженедельного отчета")
            return "⚠️ *Еженедельный отчет*\n\nНет активных рекламных кампаний для формирования отчета."
        
        logger.info(f"Получено {len(campaigns)} активных кампаний")
        
        # Определение дат для отчета (последние 7 дней)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        # Заголовок отчета
        report = f"📊 *Еженедельный отчет по рекламным кампаниям*\n"
        report += f"*Период:* {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"
        
        # Общая статистика
        total_spend = 0
        total_impressions = 0
        total_clicks = 0
        total_conversions = 0
        
        # Сбор данных по каждой кампании
        campaign_data = []
        
        for campaign in campaigns:
            try:
                # Получение инсайтов по кампании
                insights = get_campaign_insights(
                    account, 
                    campaign['id'], 
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
                
                if not insights:
                    continue
                
                # Извлечение метрик
                spend = insights.get('spend', 0)
                impressions = insights.get('impressions', 0)
                clicks = insights.get('clicks', 0)
                conversions = insights.get('actions', [])
                conversion_count = sum(action.get('value', 0) for action in conversions if action.get('action_type') == 'offsite_conversion')
                
                # Расчет производных метрик
                ctr = clicks / impressions if impressions > 0 else 0
                cpc = float(spend) / clicks if clicks > 0 else 0
                cpm = float(spend) / impressions * 1000 if impressions > 0 else 0
                
                # Добавление к общей статистике
                total_spend += float(spend)
                total_impressions += impressions
                total_clicks += clicks
                total_conversions += conversion_count
                
                # Сохранение данных кампании
                campaign_data.append({
                    'name': campaign['name'],
                    'spend': float(spend),
                    'impressions': impressions,
                    'clicks': clicks,
                    'conversions': conversion_count,
                    'ctr': ctr,
                    'cpc': cpc,
                    'cpm': cpm
                })
                
            except Exception as e:
                logger.error(f"Ошибка при получении данных для кампании {campaign['name']}: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Расчет общих показателей
        overall_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
        overall_cpc = total_spend / total_clicks if total_clicks > 0 else 0
        overall_cpm = total_spend / total_impressions * 1000 if total_impressions > 0 else 0
        
        # Добавление общей статистики в отчет
        report += f"*Общая статистика:*\n"
        report += f"💰 Расходы: {format_currency(total_spend)}\n"
        report += f"👁 Показы: {total_impressions:,}\n"
        report += f"🖱 Клики: {total_clicks:,}\n"
        report += f"🎯 Конверсии: {total_conversions:,}\n"
        report += f"📈 CTR: {format_percentage(overall_ctr)}\n"
        report += f"💸 CPC: {format_currency(overall_cpc)}\n"
        report += f"📊 CPM: {format_currency(overall_cpm)}\n\n"
        
        # Сортировка кампаний по расходам (от большего к меньшему)
        campaign_data.sort(key=lambda x: x['spend'], reverse=True)
        
        # Добавление топ-5 кампаний по расходам
        report += f"*Топ-5 кампаний по расходам:*\n"
        for i, campaign in enumerate(campaign_data[:5], 1):
            report += f"{i}. *{campaign['name']}*\n"
            report += f"   💰 Расходы: {format_currency(campaign['spend'])}\n"
            report += f"   👁 Показы: {campaign['impressions']:,}\n"
            report += f"   🖱 Клики: {campaign['clicks']:,}\n"
            report += f"   📈 CTR: {format_percentage(campaign['ctr'])}\n"
            report += f"   💸 CPC: {format_currency(campaign['cpc'])}\n\n"
        
        # Рекомендации на основе данных
        report += "*Рекомендации:*\n"
        
        # Кампании с высоким CPC
        high_cpc_campaigns = [c for c in campaign_data if c['cpc'] > overall_cpc * 1.5 and c['clicks'] > 10]
        if high_cpc_campaigns:
            report += "⚠️ Кампании с высоким CPC (требуют оптимизации):\n"
            for campaign in high_cpc_campaigns[:3]:  # Топ-3 с высоким CPC
                report += f"- {campaign['name']}: {format_currency(campaign['cpc'])}\n"
            report += "\n"
        
        # Кампании с низким CTR
        low_ctr_campaigns = [c for c in campaign_data if c['ctr'] < overall_ctr * 0.7 and c['impressions'] > 1000]
        if low_ctr_campaigns:
            report += "⚠️ Кампании с низким CTR (требуют улучшения креативов):\n"
            for campaign in low_ctr_campaigns[:3]:  # Топ-3 с низким CTR
                report += f"- {campaign['name']}: {format_percentage(campaign['ctr'])}\n"
            report += "\n"
        
        # Успешные кампании
        good_campaigns = [c for c in campaign_data if c['ctr'] > overall_ctr * 1.3 and c['cpc'] < overall_cpc * 0.8]
        if good_campaigns:
            report += "✅ Успешные кампании (рекомендуется увеличить бюджет):\n"
            for campaign in good_campaigns[:3]:  # Топ-3 успешных
                report += f"- {campaign['name']}: CTR {format_percentage(campaign['ctr'])}, CPC {format_currency(campaign['cpc'])}\n"
        
        return report
        
    except Exception as e:
        logger.error(f"Ошибка при формировании еженедельного отчета: {str(e)}")
        logger.error(traceback.format_exc())
        return f"⚠️ *Ошибка при формировании еженедельного отчета*\n\n{str(e)}"

def main():
    """Основная функция для отправки еженедельного отчета."""
    logger.info("Запуск скрипта отправки еженедельного отчета")
    
    try:
        # Формирование отчета
        report = get_weekly_report()
        
        # Отправка отчета в Telegram
        channel_id = os.getenv("TELEGRAM_LOG_CHANNEL_ID")
        if channel_id:
            logger.info(f"Отправка еженедельного отчета в Telegram канал {channel_id}")
            response = send_telegram_message(channel_id, report, parse_mode="Markdown")
            logger.info(f"Отчет отправлен. Ответ: {response.status_code} {response.reason}")
        else:
            logger.warning("ID канала Telegram не указан в переменных окружения")
            print(report)
    
    except Exception as e:
        logger.error(f"Ошибка при отправке еженедельного отчета: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 