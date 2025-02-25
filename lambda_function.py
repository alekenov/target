#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AWS Lambda функция для получения ежедневного отчета о рекламных кампаниях Facebook.
Отчет включает информацию о расходах и показах по каждой кампании за день.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import json
import boto3
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Импортируем необходимые модули
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
    
    # Создаем объект для получения данных
    data_fetcher = AdDataFetcher(account)
    
    # Получаем данные о кампаниях
    campaigns_data = data_fetcher.get_campaigns_stats(
        fields=[
            'impressions', 'clicks', 'spend', 'ctr', 'cpc', 'cpp',
            'reach', 'frequency', 'actions', 'action_values'
        ],
        params={
            'time_range': {
                'since': yesterday,
                'until': today
            },
            'time_increment': 1
        }
    )
    
    # Формируем отчет
    report = {
        'date': yesterday,
        'campaigns': campaigns_data,
        'total': {
            'impressions': sum(c.get('impressions', 0) for c in campaigns_data),
            'clicks': sum(c.get('clicks', 0) for c in campaigns_data),
            'spend': sum(float(c.get('spend', 0)) for c in campaigns_data),
            'reach': sum(c.get('reach', 0) for c in campaigns_data)
        }
    }
    
    # Добавляем расчетные метрики
    if report['total']['impressions'] > 0:
        report['total']['ctr'] = (report['total']['clicks'] / report['total']['impressions']) * 100
    else:
        report['total']['ctr'] = 0
        
    if report['total']['clicks'] > 0:
        report['total']['cpc'] = report['total']['spend'] / report['total']['clicks']
    else:
        report['total']['cpc'] = 0
        
    if report['total']['reach'] > 0:
        report['total']['frequency'] = report['total']['impressions'] / report['total']['reach']
    else:
        report['total']['frequency'] = 0
    
    return report

def format_report(report):
    """
    Форматирует отчет для вывода в консоль.
    
    Args:
        report (dict): Отчет с данными о кампаниях
        
    Returns:
        str: Отформатированный отчет
    """
    output = f"Отчет по рекламным кампаниям за {report['date']}\n"
    output += "=" * 80 + "\n"
    
    # Заголовок таблицы
    output += f"{'ID кампании':<20} {'Показы':<10} {'Клики':<10} {'CTR':<10} {'CPC':<10} {'Расход':<10}\n"
    output += "-" * 80 + "\n"
    
    # Данные по кампаниям
    for campaign in report['campaigns']:
        campaign_id = campaign.get('campaign_id', 'Н/Д')
        impressions = campaign.get('impressions', 0)
        clicks = campaign.get('clicks', 0)
        ctr = campaign.get('ctr', 0)
        cpc = campaign.get('cpc', 0)
        spend = campaign.get('spend', 0)
        
        output += f"{campaign_id:<20} {impressions:<10} {clicks:<10} {ctr:<10.2f} {cpc:<10.2f} {spend:<10.2f}\n"
    
    # Итоговые данные
    output += "-" * 80 + "\n"
    output += f"{'ИТОГО':<20} {report['total']['impressions']:<10} {report['total']['clicks']:<10} "
    output += f"{report['total']['ctr']:<10.2f} {report['total']['cpc']:<10.2f} {report['total']['spend']:<10.2f}\n"
    
    return output

def save_report_to_s3(report):
    """
    Сохраняет отчет в S3 бакет.
    
    Args:
        report (dict): Отчет с данными о кампаниях
        
    Returns:
        str: Путь к сохраненному файлу
    """
    # Получаем имя S3 бакета из переменных окружения
    s3_bucket = os.environ.get('S3_BUCKET_NAME')
    if not s3_bucket:
        logger.error("Не указано имя S3 бакета в переменных окружения")
        return None
    
    # Формируем имя файла
    date_str = report['date']
    filename = f"fb_ads_report_{date_str}.json"
    s3_key = f"reports/{filename}"
    
    # Сохраняем отчет в S3
    try:
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=json.dumps(report, indent=2),
            ContentType='application/json'
        )
        logger.info(f"Отчет сохранен в S3: s3://{s3_bucket}/{s3_key}")
        return f"s3://{s3_bucket}/{s3_key}"
    except Exception as e:
        logger.error(f"Ошибка при сохранении отчета в S3: {str(e)}")
        return None

def format_telegram_report(report):
    """
    Форматирует отчет для отправки в Telegram.
    
    Args:
        report (dict): Отчет с данными о кампаниях
        
    Returns:
        str: Отформатированный отчет для Telegram
    """
    date_str = report['date']
    
    # Формируем заголовок
    message = f"📊 *Отчет по рекламным кампаниям Facebook за {date_str}*\n\n"
    
    # Добавляем общую статистику
    message += "*Общая статистика:*\n"
    message += f"👁 Показы: {report['total']['impressions']}\n"
    message += f"👆 Клики: {report['total']['clicks']}\n"
    message += f"💰 Расход: ${report['total']['spend']:.2f}\n"
    message += f"🎯 CTR: {report['total']['ctr']:.2f}%\n"
    message += f"💵 CPC: ${report['total']['cpc']:.2f}\n"
    message += f"👥 Охват: {report['total']['reach']}\n"
    message += f"🔄 Частота: {report['total']['frequency']:.2f}\n\n"
    
    # Добавляем данные по кампаниям
    message += "*Статистика по кампаниям:*\n"
    for campaign in report['campaigns']:
        campaign_name = campaign.get('campaign_name', 'Без названия')
        campaign_id = campaign.get('campaign_id', 'Н/Д')
        impressions = campaign.get('impressions', 0)
        clicks = campaign.get('clicks', 0)
        ctr = campaign.get('ctr', 0)
        spend = campaign.get('spend', 0)
        
        message += f"*{campaign_name}* (ID: {campaign_id})\n"
        message += f"👁 Показы: {impressions}\n"
        message += f"👆 Клики: {clicks}\n"
        message += f"💰 Расход: ${float(spend):.2f}\n"
        message += f"🎯 CTR: {ctr:.2f}%\n\n"
    
    return message

def send_telegram_message(message):
    """
    Отправляет сообщение в Telegram.
    
    Args:
        message (str): Текст сообщения
        
    Returns:
        bool: True, если сообщение успешно отправлено, иначе False
    """
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.error("Не указаны токен бота или ID чата Telegram в переменных окружения")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Ошибка при отправке сообщения в Telegram: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {str(e)}")
        return False

def lambda_handler(event, context):
    """
    Обработчик AWS Lambda.
    
    Args:
        event (dict): Событие, которое вызвало функцию
        context (object): Контекст выполнения функции
        
    Returns:
        dict: Результат выполнения функции
    """
    try:
        # Получаем отчет
        report = get_daily_ad_report()
        
        # Форматируем отчет
        formatted_report = format_report(report)
        logger.info(formatted_report)
        
        # Сохраняем отчет в S3
        report_file = save_report_to_s3(report)
        
        # Форматируем отчет для Telegram
        telegram_report = format_telegram_report(report)
        
        # Отправляем отчет в Telegram
        sent = send_telegram_message(telegram_report)
        if sent:
            logger.info("Отчет успешно отправлен в Telegram")
        else:
            logger.error("Не удалось отправить отчет в Telegram")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Отчет успешно сгенерирован и отправлен',
                'report_file': report_file
            })
        }
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении Lambda функции: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Ошибка: {str(e)}'
            })
        } 