#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для получения ежедневного отчета о рекламных кампаниях Facebook.
Отчет включает информацию о расходах и показах по каждой кампании за день.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from facebook_ads_toolkit.auth.facebook_auth import init_facebook_api, get_api, get_ad_account
from facebook_ads_toolkit.reports.ad_data_fetcher import AdDataFetcher
from facebook_business.adobjects.adaccount import AdAccount

def get_daily_ad_report():
    """
    Получает отчет о расходах и показах рекламных кампаний за день.
    
    Returns:
        dict: Отчет с данными о кампаниях
    """
    logger.info("Получение ежедневного отчета о рекламных кампаниях")
    
    # Получаем текущую дату и дату вчерашнего дня
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Инициализируем Facebook API
    logger.info("Инициализация Facebook API")
    account, api = init_facebook_api()
    if not account or not api:
        logger.error("Не удалось инициализировать Facebook API")
        raise Exception("Ошибка инициализации Facebook API")
    
    logger.info(f"Facebook API инициализирован. Аккаунт: {account.get_id()}")
    
    # Получаем объект аккаунта
    account_obj = get_ad_account()
    
    # Создаем объект для получения данных
    data_fetcher = AdDataFetcher(account_obj)
    
    # Получаем список активных кампаний
    logger.info("Получение списка активных кампаний")
    campaigns_params = {
        'fields': ['id', 'name', 'status', 'effective_status', 'daily_budget', 'lifetime_budget'],
        'filtering': [
            {
                'field': 'effective_status',
                'operator': 'IN',
                'value': ['ACTIVE', 'PAUSED']
            }
        ]
    }
    
    campaigns = data_fetcher.fetch_campaigns(params=campaigns_params)
    logger.info(f"Получено {len(campaigns)} кампаний")
    
    # Получаем данные о показах и расходах за день
    logger.info(f"Получение данных о показах и расходах за период {yesterday} - {today}")
    
    campaign_insights = []
    for campaign in campaigns:
        campaign_id = campaign['id']
        logger.info(f"Получение данных для кампании {campaign['name']} (ID: {campaign_id})")
        
        try:
            # Получаем инсайты для кампании
            insights = data_fetcher.get_campaign_insights(
                campaign_id=campaign_id,
                start_date=yesterday,
                end_date=today
            )
            
            # Добавляем имя кампании к инсайтам
            insights['campaign_name'] = campaign['name']
            insights['campaign_id'] = campaign_id
            insights['status'] = campaign['effective_status']
            
            # Добавляем бюджет
            if 'daily_budget' in campaign and campaign['daily_budget']:
                insights['budget'] = f"{float(campaign['daily_budget'])/100:.2f} USD/день"
            elif 'lifetime_budget' in campaign and campaign['lifetime_budget']:
                insights['budget'] = f"{float(campaign['lifetime_budget'])/100:.2f} USD (на весь период)"
            else:
                insights['budget'] = "Не указан"
            
            # Получаем объявления для этой кампании
            if insights and 'spend' in insights and float(insights.get('spend', 0)) > 0:
                # Получаем группы объявлений для этой кампании
                adsets_params = {
                    'fields': ['id', 'name', 'status', 'effective_status'],
                    'filtering': [
                        {
                            'field': 'campaign.id',
                            'operator': 'EQUAL',
                            'value': campaign_id
                        }
                    ]
                }
                adsets = data_fetcher.fetch_adsets(params=adsets_params)
                
                # Получаем объявления для каждой группы объявлений
                ads_list = []
                for adset in adsets:
                    adset_id = adset['id']
                    ads_params = {
                        'fields': ['id', 'name', 'status', 'effective_status'],
                        'filtering': [
                            {
                                'field': 'adset.id',
                                'operator': 'EQUAL',
                                'value': adset_id
                            }
                        ]
                    }
                    ads = data_fetcher.fetch_ads(params=ads_params)
                    
                    # Получаем инсайты для каждого объявления
                    for ad in ads:
                        ad_id = ad['id']
                        try:
                            ad_insights = data_fetcher.fetch_insights(
                                entity_ids=[ad_id],
                                entity_type='ad',
                                start_date=yesterday,
                                end_date=today
                            )
                            
                            if ad_insights and len(ad_insights) > 0:
                                ad_data = {
                                    'id': ad_id,
                                    'name': ad['name'],
                                    'status': ad['effective_status'],
                                    'adset_id': adset_id,
                                    'adset_name': adset['name']
                                }
                                
                                # Добавляем метрики из инсайтов
                                for key in ['impressions', 'clicks', 'spend', 'ctr', 'cpc']:
                                    if key in ad_insights[0]:
                                        ad_data[key] = ad_insights[0][key]
                                
                                # Добавляем объявление только если у него есть расходы
                                if 'spend' in ad_data and float(ad_data.get('spend', 0)) > 0:
                                    ads_list.append(ad_data)
                        except Exception as e:
                            logger.error(f"Ошибка при получении инсайтов для объявления {ad_id}: {str(e)}")
                
                # Добавляем объявления к инсайтам кампании
                insights['ads'] = ads_list
                
                # Добавляем кампанию в список только если у нее есть расходы
                campaign_insights.append(insights)
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных для кампании {campaign_id}: {str(e)}")
    
    # Формируем отчет
    report = {
        'date': today,
        'account_id': account_obj.get_id_assured(),
        'total_campaigns': len(campaigns),
        'campaigns_with_data': len(campaign_insights),
        'campaigns': campaign_insights
    }
    
    # Рассчитываем общие показатели
    total_spend = sum(float(c.get('spend', 0)) for c in campaign_insights if 'spend' in c)
    total_impressions = sum(int(c.get('impressions', 0)) for c in campaign_insights if 'impressions' in c)
    
    report['total_spend'] = f"{total_spend:.2f} USD"
    report['total_impressions'] = total_impressions
    
    return report

def format_report(report, max_campaigns=10):
    """
    Форматирует отчет для вывода в консоль.
    
    Args:
        report (dict): Отчет с данными о кампаниях
        max_campaigns (int): Максимальное количество кампаний для вывода
        
    Returns:
        str: Отформатированный отчет
    """
    output = f"📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ ПО РЕКЛАМНЫМ КАМПАНИЯМ FACEBOOK\n"
    output += f"Дата: {report['date']}\n"
    output += f"Аккаунт: {report['account_id']}\n\n"
    
    output += f"ОБЩИЕ ПОКАЗАТЕЛИ:\n"
    output += f"Всего кампаний: {report['total_campaigns']}\n"
    output += f"Кампаний с расходами: {report['campaigns_with_data']}\n"
    output += f"Общие расходы: {report['total_spend']}\n"
    output += f"Общие показы: {report['total_impressions']}\n\n"
    
    # Находим кампании с данными о расходах
    campaigns_with_data = [c for c in report['campaigns'] if 'spend' in c and float(c.get('spend', 0)) > 0]
    
    output += f"КАМПАНИИ С РАСХОДАМИ ({len(campaigns_with_data)} из {report['total_campaigns']}):\n\n"
    
    # Сортируем кампании по расходам (от большего к меньшему)
    sorted_campaigns = sorted(
        campaigns_with_data, 
        key=lambda x: float(x.get('spend', 0)) if 'spend' in x else 0, 
        reverse=True
    )
    
    # Ограничиваем количество кампаний для вывода
    campaigns_to_show = sorted_campaigns[:max_campaigns]
    
    for i, campaign in enumerate(campaigns_to_show, 1):
        output += f"{i}. {campaign['campaign_name']} (ID: {campaign['campaign_id']})\n"
        output += f"   Статус: {campaign['status']}\n"
        output += f"   Бюджет: {campaign['budget']}\n"
        
        # Добавляем данные о расходах и показах, если они есть
        if 'spend' in campaign:
            output += f"   Расходы: {campaign['spend']} USD\n"
        else:
            output += f"   Расходы: Нет данных\n"
            
        if 'impressions' in campaign:
            output += f"   Показы: {campaign['impressions']}\n"
        else:
            output += f"   Показы: Нет данных\n"
            
        # Добавляем дополнительные метрики, если они есть
        if 'clicks' in campaign:
            output += f"   Клики: {campaign['clicks']}\n"
            
        if 'ctr' in campaign:
            output += f"   CTR: {campaign['ctr']}%\n"
            
        if 'cpc' in campaign:
            output += f"   CPC: {campaign['cpc']} USD\n"
        
        # Добавляем информацию об объявлениях
        if 'ads' in campaign and campaign['ads']:
            output += f"\n   📱 ОБЪЯВЛЕНИЯ ({len(campaign['ads'])}):\n"
            
            # Сортируем объявления по расходам
            sorted_ads = sorted(
                campaign['ads'],
                key=lambda x: float(x.get('spend', 0)) if 'spend' in x else 0,
                reverse=True
            )
            
            # Показываем максимум 5 объявлений для каждой кампании
            max_ads = 5
            ads_to_show = sorted_ads[:max_ads]
            
            for j, ad in enumerate(ads_to_show, 1):
                output += f"      {j}. {ad['name']} (ID: {ad['id']})\n"
                output += f"         Группа объявлений: {ad['adset_name']}\n"
                output += f"         Статус: {ad['status']}\n"
                
                if 'spend' in ad:
                    output += f"         Расходы: {ad['spend']} USD\n"
                
                if 'impressions' in ad:
                    output += f"         Показы: {ad['impressions']}\n"
                
                if 'clicks' in ad:
                    output += f"         Клики: {ad['clicks']}\n"
                
                if 'ctr' in ad:
                    output += f"         CTR: {ad['ctr']}%\n"
                
                if 'cpc' in ad:
                    output += f"         CPC: {ad['cpc']} USD\n"
                
                output += "\n"
            
            if len(sorted_ads) > max_ads:
                output += f"      ... и еще {len(sorted_ads) - max_ads} объявлений\n"
            
        output += "\n"
    
    if len(sorted_campaigns) > max_campaigns:
        output += f"... и еще {len(sorted_campaigns) - max_campaigns} кампаний с расходами\n\n"
    
    output += f"Полный отчет сохранен в файл: reports/fb_ads_report_{report['date']}.json\n"
    
    return output

def format_telegram_report(report, max_campaigns=5):
    """
    Форматирует отчет для отправки в Telegram.
    
    Args:
        report (dict): Отчет с данными о кампаниях
        max_campaigns (int): Максимальное количество кампаний для вывода
        
    Returns:
        str: Отформатированный отчет для Telegram
    """
    # Используем HTML-форматирование для Telegram
    output = f"<b>📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ ПО РЕКЛАМНЫМ КАМПАНИЯМ FACEBOOK</b>\n"
    output += f"<b>Дата:</b> {report['date']}\n"
    output += f"<b>Аккаунт:</b> {report['account_id']}\n\n"
    
    output += f"<b>ОБЩИЕ ПОКАЗАТЕЛИ:</b>\n"
    output += f"• Всего кампаний: <b>{report['total_campaigns']}</b>\n"
    output += f"• Кампаний с расходами: <b>{report['campaigns_with_data']}</b>\n"
    output += f"• Общие расходы: <b>{report['total_spend']}</b>\n"
    output += f"• Общие показы: <b>{report['total_impressions']}</b>\n\n"
    
    # Находим кампании с данными о расходах
    campaigns_with_data = [c for c in report['campaigns'] if 'spend' in c and float(c.get('spend', 0)) > 0]
    
    output += f"<b>ТОП КАМПАНИЙ ПО РАСХОДАМ:</b>\n\n"
    
    # Сортируем кампании по расходам (от большего к меньшему)
    sorted_campaigns = sorted(
        campaigns_with_data, 
        key=lambda x: float(x.get('spend', 0)) if 'spend' in x else 0, 
        reverse=True
    )
    
    # Ограничиваем количество кампаний для вывода
    campaigns_to_show = sorted_campaigns[:max_campaigns]
    
    for i, campaign in enumerate(campaigns_to_show, 1):
        output += f"{i}. <b>{campaign['campaign_name']}</b>\n"
        
        # Добавляем данные о расходах и показах, если они есть
        if 'spend' in campaign:
            output += f"   💰 Расходы: <b>{campaign['spend']} USD</b>\n"
        
        if 'impressions' in campaign:
            output += f"   👁 Показы: <b>{campaign['impressions']}</b>\n"
            
        # Добавляем дополнительные метрики, если они есть
        if 'clicks' in campaign and 'ctr' in campaign:
            output += f"   🖱 Клики: <b>{campaign['clicks']}</b> (CTR: <b>{campaign['ctr']}%</b>)\n"
            
        if 'cpc' in campaign:
            output += f"   💵 CPC: <b>{campaign['cpc']} USD</b>\n"
        
        # Добавляем информацию о топ-3 объявлениях
        if 'ads' in campaign and campaign['ads']:
            # Сортируем объявления по расходам
            sorted_ads = sorted(
                campaign['ads'],
                key=lambda x: float(x.get('spend', 0)) if 'spend' in x else 0,
                reverse=True
            )
            
            # Показываем максимум 3 объявления для каждой кампании в Telegram
            max_ads = 3
            ads_to_show = sorted_ads[:max_ads]
            
            output += f"\n   <b>📱 Топ объявления:</b>\n"
            
            for j, ad in enumerate(ads_to_show, 1):
                output += f"   {j}. <i>{ad['name']}</i>\n"
                
                if 'spend' in ad:
                    output += f"      💰 Расходы: <b>{ad['spend']} USD</b>\n"
                
                if 'impressions' in ad and 'clicks' in ad:
                    output += f"      👁 Показы: <b>{ad['impressions']}</b> | 🖱 Клики: <b>{ad['clicks']}</b>\n"
                
                if 'ctr' in ad and 'cpc' in ad:
                    output += f"      📊 CTR: <b>{ad['ctr']}%</b> | 💵 CPC: <b>{ad['cpc']} USD</b>\n"
            
            if len(sorted_ads) > max_ads:
                output += f"   ... и еще {len(sorted_ads) - max_ads} объявлений\n"
            
        output += "\n"
    
    return output

def save_report_to_file(report, filename=None):
    """
    Сохраняет отчет в JSON-файл.
    
    Args:
        report (dict): Отчет с данными о кампаниях
        filename (str, optional): Имя файла для сохранения
        
    Returns:
        str: Путь к сохраненному файлу
    """
    if filename is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"fb_ads_report_{date_str}.json"
    
    # Создаем директорию reports, если она не существует
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
    
    logger.info(f"Отчет сохранен в файл: {filepath}")
    return filepath

def send_telegram_message(message, chat_id=None, bot_token=None):
    """
    Отправляет сообщение в Telegram канал или чат.
    
    Args:
        message (str): Текст сообщения
        chat_id (str, optional): ID чата или канала
        bot_token (str, optional): Токен Telegram бота
        
    Returns:
        bool: True, если сообщение успешно отправлено, иначе False
    """
    # Получаем токен бота и ID чата из переменных окружения, если не указаны
    if not bot_token:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not chat_id:
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.error("Не указаны TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data)
        response_json = response.json()
        
        if response.status_code == 200 and response_json.get('ok'):
            logger.info(f"Сообщение успешно отправлено в Telegram (chat_id: {chat_id})")
            return True
        else:
            logger.error(f"Ошибка при отправке сообщения в Telegram: {response_json}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {str(e)}")
        return False

def main():
    """
    Основная функция скрипта.
    """
    # Загружаем переменные окружения
    load_dotenv()
    
    try:
        # Получаем отчет
        report = get_daily_ad_report()
        
        # Форматируем и выводим отчет в консоль
        formatted_report = format_report(report)
        print(formatted_report)
        
        # Сохраняем отчет в файл
        report_file = save_report_to_file(report)
        
        # Форматируем отчет для Telegram
        telegram_report = format_telegram_report(report)
        
        # Отправляем отчет в Telegram
        sent = send_telegram_message(telegram_report)
        if sent:
            logger.info("Отчет успешно отправлен в Telegram")
        else:
            logger.error("Не удалось отправить отчет в Telegram")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении скрипта: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 