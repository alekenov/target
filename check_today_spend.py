#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для проверки трат на рекламу в Facebook.
Использует Facebook Marketing API для получения данных о расходах за текущий день 
или за указанный период.
"""

import os
import logging
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import argparse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Импортируем необходимые модули
from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_business.adobjects.adaccount import AdAccount

def get_ad_spend(days=0, use_today=True, specific_date=None):
    """
    Получает данные о тратах на рекламу Facebook за указанный период.
    
    Args:
        days (int): Количество дней для анализа (0 - только сегодня, 
                   >0 - за указанное количество дней до сегодня)
        use_today (bool): Использовать ли сегодняшнюю дату как конечную
        specific_date (str): Конкретная дата в формате YYYY-MM-DD для анализа
    
    Returns:
        dict: Данные о тратах по кампаниям
    """
    # Получаем даты для запроса
    today = datetime.now().strftime('%Y-%m-%d')
    
    if specific_date:
        # Если указана конкретная дата, используем её
        start_date = specific_date
        end_date = specific_date
        logger.info(f"Получение данных о тратах на рекламу за {specific_date}")
    elif days > 0:
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = today
        logger.info(f"Получение данных о тратах на рекламу за период с {start_date} по {end_date}")
    else:
        start_date = today
        end_date = today
        logger.info("Получение данных о тратах на рекламу за сегодня")
    
    # Инициализируем Facebook API
    logger.info("Инициализация Facebook API")
    auth = FacebookAuth()
    account, api = auth.initialize()
    
    if not account or not api:
        logger.error("Не удалось инициализировать Facebook API")
        raise Exception("Ошибка инициализации Facebook API")
    
    logger.info(f"Успешно авторизовались в аккаунте {account.get_id()}")
    
    # Получаем данные о тратах
    try:
        # Параметры запроса
        params = {
            'time_range': {'since': start_date, 'until': end_date},
            'level': 'account',  # Изменено с 'campaign' на 'account'
            'fields': [
                'spend',
                'impressions',
                'clicks',
                'ctr',
                'cpc',
                'reach',
                'date_start',
                'date_stop',
                'account_currency'
            ],
            'time_increment': 1  # Разбивка по дням
        }
        
        # Выполняем запрос к API
        insights = account.get_insights(params=params)
        
        # Преобразуем результаты в словарь
        daily_data = {}
        campaigns_data = []
        total_spend = 0
        currency = "USD"  # Значение по умолчанию
        
        for insight in insights:
            date = insight.get('date_start')
            spend = float(insight.get('spend', 0))
            currency = insight.get('account_currency', 'USD')
            
            # Добавляем данные в общий список
            campaign_data = {
                'date': date,
                'spend': spend,
                'impressions': int(insight.get('impressions', 0)),
                'clicks': int(insight.get('clicks', 0)),
                'ctr': float(insight.get('ctr', 0)) * 100 if insight.get('ctr') else 0,
                'cpc': float(insight.get('cpc', 0)),
                'reach': int(insight.get('reach', 0)),
                'currency': currency
            }
            
            campaigns_data.append(campaign_data)
            total_spend += spend
            
            # Группируем данные по дням
            if date not in daily_data:
                daily_data[date] = {
                    'total_spend': 0,
                    'campaigns': [],
                    'currency': currency
                }
            
            daily_data[date]['total_spend'] += spend
            daily_data[date]['campaigns'].append(campaign_data)
        
        # Если данных нет, попробуем запросить без time_increment
        if not campaigns_data and days == 0:
            logger.info("Данных с разбивкой по дням не найдено. Пробуем запрос без разбивки.")
            params.pop('time_increment', None)
            insights = account.get_insights(params=params)
            
            for insight in insights:
                spend = float(insight.get('spend', 0))
                currency = insight.get('account_currency', 'USD')
                
                # Добавляем данные в общий список
                campaign_data = {
                    'date': end_date,
                    'spend': spend,
                    'impressions': int(insight.get('impressions', 0)),
                    'clicks': int(insight.get('clicks', 0)),
                    'ctr': float(insight.get('ctr', 0)) * 100 if insight.get('ctr') else 0,
                    'cpc': float(insight.get('cpc', 0)),
                    'reach': int(insight.get('reach', 0)),
                    'currency': currency
                }
                
                campaigns_data.append(campaign_data)
                total_spend += spend
                
                # Группируем данные по дням
                if end_date not in daily_data:
                    daily_data[end_date] = {
                        'total_spend': 0,
                        'campaigns': [],
                        'currency': currency
                    }
                
                daily_data[end_date]['total_spend'] += spend
                daily_data[end_date]['campaigns'].append(campaign_data)
        
        # Если все еще нет данных за сегодня или запрошен период с сегодняшним днем,
        # попробуем получить данные за сегодня напрямую из аккаунта
        if ((not daily_data.get(end_date) and days >= 0) or (days == 0 and not campaigns_data)) and not specific_date:
            logger.info("Пробуем получить данные за сегодня через прямой запрос к аккаунту")
            
            # Получаем данные о тратах за сегодня через поле amount_spent
            account_fields = ['name', 'account_id', 'amount_spent', 'spend_cap', 'currency', 'account_status']
            account_info = account.api_get(fields=account_fields)
            
            amount_spent = float(account_info.get('amount_spent', 0))
            currency = account_info.get('currency', 'USD')
            
            logger.info(f"Получены данные о тратах напрямую из аккаунта: {amount_spent} {currency}")
            
            # Добавляем данные в общий список как обобщенную кампанию
            campaign_data = {
                'date': end_date,
                'spend': amount_spent,
                'impressions': 0,  # Нет данных
                'clicks': 0,       # Нет данных
                'ctr': 0,          # Нет данных
                'cpc': 0,          # Нет данных
                'reach': 0,        # Нет данных
                'currency': currency
            }
            
            campaigns_data.append(campaign_data)
            
            # Если запрошен только сегодняшний день, устанавливаем total_spend
            if days == 0:
                total_spend = amount_spent
            else:
                # Если запрошен период, добавляем траты за сегодня к общей сумме
                total_spend += amount_spent
            
            # Группируем данные по дням
            if end_date not in daily_data:
                daily_data[end_date] = {
                    'total_spend': 0,
                    'campaigns': [],
                    'currency': currency,
                    'note': 'Данные получены напрямую из аккаунта'
                }
            
            daily_data[end_date]['total_spend'] = amount_spent
            daily_data[end_date]['campaigns'].append(campaign_data)
        
        # Проверяем наличие данных за конкретную дату, если она указана
        if specific_date and not daily_data.get(specific_date):
            logger.info(f"Данных за {specific_date} не найдено в Insights API. Пробуем получить общие данные аккаунта.")
            
            # Получаем данные о тратах через поле amount_spent
            account_fields = ['name', 'account_id', 'amount_spent', 'spend_cap', 'currency', 'account_status']
            account_info = account.api_get(fields=account_fields)
            
            amount_spent = float(account_info.get('amount_spent', 0))
            currency = account_info.get('currency', 'USD')
            
            logger.info(f"Общие траты аккаунта: {amount_spent} {currency}")
            logger.warning(f"Facebook API не возвращает данные за {specific_date} через Insights API.")
            logger.warning("Это может происходить из-за задержки в обработке данных Facebook или из-за особенностей API.")
            logger.warning("Рекомендуется проверить траты напрямую в интерфейсе Facebook Ads Manager.")
            
            # Добавляем предупреждение в отчет
            if not daily_data:
                daily_data = {}
            
            daily_data[specific_date] = {
                'total_spend': 0,  # Мы не знаем точную сумму за этот день
                'campaigns': [],
                'currency': currency,
                'note': 'Данные недоступны через API. Проверьте Facebook Ads Manager.'
            }
            
            # Добавляем пустую запись для отображения в отчете
            campaign_data = {
                'date': specific_date,
                'spend': 0,  # Мы не знаем точную сумму
                'impressions': 0,
                'clicks': 0,
                'ctr': 0,
                'cpc': 0,
                'reach': 0,
                'currency': currency
            }
            
            campaigns_data.append(campaign_data)
            daily_data[specific_date]['campaigns'].append(campaign_data)
        
        # Формируем итоговый отчет
        report = {
            'start_date': start_date,
            'end_date': end_date,
            'campaigns': campaigns_data,
            'daily_data': daily_data,
            'total_spend': total_spend,
            'currency': currency,
            'campaign_count': len(set(c['date'] for c in campaigns_data))
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных о тратах: {str(e)}")
        raise

def format_spend_report(report):
    """
    Форматирует отчет о тратах для вывода в консоль.
    
    Args:
        report (dict): Отчет с данными о тратах
        
    Returns:
        str: Отформатированный отчет
    """
    start_date = report.get('start_date')
    end_date = report.get('end_date')
    campaigns = report.get('campaigns', [])
    daily_data = report.get('daily_data', {})
    total_spend = report.get('total_spend', 0)
    currency = report.get('currency', 'USD')
    
    # Формируем заголовок отчета
    if start_date == end_date:
        header = f"Отчет о тратах на рекламу Facebook за {start_date}"
    else:
        header = f"Отчет о тратах на рекламу Facebook за период {start_date} - {end_date}"
    
    # Формируем разделитель
    separator = "=" * 80
    
    # Формируем сводку по дням
    daily_summary = "СВОДКА ПО ДНЯМ:"
    daily_separator = "-" * 80
    
    daily_lines = []
    for date, data in sorted(daily_data.items()):
        spend = data.get('total_spend', 0)
        currency = data.get('currency', 'USD')
        campaign_count = len(data.get('campaigns', []))
        note = data.get('note', '')
        
        if note:
            daily_lines.append(f"{date}: {spend:.2f} {currency} ({campaign_count} записей) - {note}")
        else:
            daily_lines.append(f"{date}: {spend:.2f} {currency} ({campaign_count} записей)")
    
    # Формируем таблицу с данными
    table_header = f"{'Дата':<12} {'Показы':<10} {'Клики':<9} {'CTR, %':<9} {'CPC':<9} {'Расход':<9}"
    table_separator = "-" * 80
    
    table_lines = []
    for campaign in sorted(campaigns, key=lambda x: x.get('date', '')):
        date = campaign.get('date', '')
        impressions = campaign.get('impressions', 0)
        clicks = campaign.get('clicks', 0)
        ctr = campaign.get('ctr', 0)
        cpc = campaign.get('cpc', 0)
        spend = campaign.get('spend', 0)
        currency = campaign.get('currency', 'USD')
        
        table_lines.append(
            f"{date:<12} {impressions:<10} {clicks:<9} {ctr:<9.2f} {cpc:<9.2f} {spend:<9.2f} {currency}"
        )
    
    # Формируем итоговую строку
    total_line = f"ИТОГО {' ':<69} {total_spend:<9.2f} {currency}"
    
    # Формируем примечания
    notes = []
    for date, data in daily_data.items():
        if 'note' in data:
            notes.append(f"Примечание: {data['note']}")
    
    # Собираем все части отчета
    report_parts = [
        header,
        separator,
        daily_summary,
        daily_separator,
        "\n".join(daily_lines),
        separator,
        "",
        table_header,
        table_separator,
        "\n".join(table_lines),
        table_separator,
        total_line,
        f"Всего записей: {len(campaigns)}",
    ]
    
    # Добавляем примечания, если они есть
    if notes:
        report_parts.append("")
        report_parts.append("\n".join(notes))
    
    # Объединяем все части отчета
    return "\n".join(report_parts)

def main():
    """
    Основная функция скрипта.
    """
    # Загружаем переменные окружения
    load_dotenv()
    
    # Устанавливаем ID аккаунта напрямую
    os.environ['FB_ACCOUNT_ID'] = 'act_4795321857166878'
    
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description='Проверка трат на рекламу в Facebook')
    parser.add_argument('--days', type=int, default=0, help='Количество дней для анализа (0 - только сегодня)')
    parser.add_argument('--yesterday', action='store_true', help='Показать данные за вчера')
    parser.add_argument('--date', type=str, help='Конкретная дата для анализа в формате YYYY-MM-DD')
    
    args = parser.parse_args()
    
    # Определяем параметры запроса
    days = args.days
    use_yesterday = args.yesterday
    specific_date = args.date
    
    if use_yesterday:
        # Если запрошены данные за вчера
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        specific_date = yesterday
        days = 0
    
    # Получаем данные о тратах
    try:
        report = get_ad_spend(days=days, use_today=True, specific_date=specific_date)
        
        # Форматируем и выводим отчет
        formatted_report = format_spend_report(report)
        print(formatted_report)
        
        # Выводим общую сумму трат
        total_spend = report.get('total_spend', 0)
        currency = report.get('currency', 'USD')
        
        if days > 0:
            print(f"\nОбщая сумма трат за последние {days} дней: {total_spend:.2f} {currency}")
        elif use_yesterday:
            print(f"\nОбщая сумма трат за вчера: {total_spend:.2f} {currency}")
        elif specific_date:
            print(f"\nОбщая сумма трат за {specific_date}: {total_spend:.2f} {currency}")
        else:
            print(f"\nОбщая сумма трат за сегодня: {total_spend:.2f} {currency}")
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении скрипта: {str(e)}")
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main()
