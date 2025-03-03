#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для получения детальной информации о конкретной рекламной кампании Facebook.
Показывает статистику по кампании, группам объявлений и отдельным объявлениям.
"""

import os
import logging
import sys
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Импортируем необходимые модули
from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

def get_campaign_details(campaign_name=None, campaign_id=None, days=7):
    """
    Получает детальную информацию о рекламной кампании.
    
    Args:
        campaign_name (str): Название или часть названия кампании для поиска
        campaign_id (str): ID кампании для прямого доступа
        days (int): Количество дней для анализа
    
    Returns:
        dict: Данные о кампании, группах объявлений и объявлениях
    """
    # Получаем даты для запроса
    today = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    logger.info(f"Получение данных о кампании за период с {start_date} по {today}")
    
    # Инициализируем Facebook API
    logger.info("Инициализация Facebook API")
    auth = FacebookAuth()
    account, api = auth.initialize()
    
    if not account or not api:
        logger.error("Не удалось инициализировать Facebook API")
        raise Exception("Ошибка инициализации Facebook API")
    
    logger.info(f"Успешно авторизовались в аккаунте {account.get_id()}")
    
    # Получаем данные о кампании
    try:
        # Если указан ID кампании, получаем данные напрямую
        if campaign_id:
            logger.info(f"Получение данных для кампании с ID: {campaign_id}")
            
            try:
                # Получаем данные кампании
                campaign = Campaign(campaign_id).api_get(
                    fields=[
                        'id', 'name', 'status', 'objective', 'created_time', 
                        'start_time', 'stop_time', 'daily_budget', 'lifetime_budget'
                    ]
                )
            except Exception as e:
                logger.error(f"Ошибка при получении кампании с ID {campaign_id}: {str(e)}")
                return None
        else:
            # Параметры запроса для кампаний
            campaigns_params = {
                'limit': 100,
                'fields': [
                    'id', 'name', 'status', 'objective', 'created_time', 
                    'start_time', 'stop_time', 'daily_budget', 'lifetime_budget'
                ]
            }
            
            # Если указано название кампании, добавляем фильтр
            if campaign_name:
                campaigns_params['filtering'] = [
                    {
                        'field': 'name',
                        'operator': 'CONTAIN',
                        'value': campaign_name
                    }
                ]
            
            # Получаем список кампаний
            campaigns = account.get_campaigns(params=campaigns_params)
            
            if not campaigns:
                logger.warning(f"Кампании с названием '{campaign_name}' не найдены")
                return None
            
            # Если кампаний несколько, выводим список и просим выбрать
            if len(campaigns) > 1 and campaign_name:
                print(f"Найдено {len(campaigns)} кампаний, соответствующих запросу '{campaign_name}':")
                for i, campaign in enumerate(campaigns):
                    print(f"{i+1}. {campaign['name']} (ID: {campaign['id']})")
                
                # Возвращаем список кампаний для выбора
                return {
                    'campaigns': [
                        {
                            'id': campaign['id'],
                            'name': campaign['name']
                        } for campaign in campaigns
                    ]
                }
            
            # Выбираем первую кампанию из списка
            campaign = campaigns[0]
        
        campaign_id = campaign['id']
        logger.info(f"Получение данных для кампании: {campaign['name']} (ID: {campaign_id})")
        
        # Получаем статистику по кампании
        insights_params = {
            'time_range': {'since': start_date, 'until': today},
            'fields': [
                'impressions', 'clicks', 'spend', 'ctr', 'cpc', 'cpp',
                'reach', 'frequency', 'actions', 'action_values',
                'date_start', 'date_stop'
            ],
            'time_increment': 1  # Разбивка по дням
        }
        
        campaign_insights = Campaign(campaign_id).get_insights(params=insights_params)
        
        # Получаем группы объявлений для кампании
        adsets_params = {
            'fields': [
                'id', 'name', 'status', 'daily_budget', 'lifetime_budget',
                'targeting', 'bid_amount', 'billing_event', 'optimization_goal'
            ]
        }
        
        adsets = Campaign(campaign_id).get_ad_sets(params=adsets_params)
        
        # Получаем статистику по группам объявлений
        adsets_data = []
        for adset in adsets:
            adset_id = adset['id']
            
            # Получаем статистику по группе объявлений
            adset_insights = AdSet(adset_id).get_insights(params=insights_params)
            
            # Получаем объявления в группе
            ads_params = {
                'fields': [
                    'id', 'name', 'status', 'created_time', 
                    'updated_time', 'creative'
                ]
            }
            
            ads = AdSet(adset_id).get_ads(params=ads_params)
            
            # Получаем статистику по объявлениям
            ads_data = []
            for ad in ads:
                ad_id = ad['id']
                
                # Получаем статистику по объявлению
                ad_insights = Ad(ad_id).get_insights(params=insights_params)
                
                # Объединяем данные объявления и статистику
                ad_data = {
                    'id': ad['id'],
                    'name': ad['name'],
                    'status': ad['status'],
                    'insights': ad_insights
                }
                
                ads_data.append(ad_data)
            
            # Объединяем данные группы объявлений, статистику и объявления
            adset_data = {
                'id': adset['id'],
                'name': adset['name'],
                'status': adset['status'],
                'daily_budget': adset.get('daily_budget'),
                'lifetime_budget': adset.get('lifetime_budget'),
                'targeting': adset.get('targeting'),
                'insights': adset_insights,
                'ads': ads_data
            }
            
            adsets_data.append(adset_data)
        
        # Формируем итоговый отчет
        report = {
            'campaign': {
                'id': campaign['id'],
                'name': campaign['name'],
                'status': campaign['status'],
                'objective': campaign.get('objective'),
                'created_time': campaign.get('created_time'),
                'start_time': campaign.get('start_time'),
                'stop_time': campaign.get('stop_time'),
                'daily_budget': campaign.get('daily_budget'),
                'lifetime_budget': campaign.get('lifetime_budget')
            },
            'insights': campaign_insights,
            'adsets': adsets_data,
            'start_date': start_date,
            'end_date': today
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных о кампании: {str(e)}")
        raise

def format_campaign_report(report):
    """
    Форматирует отчет о кампании для вывода в консоль.
    
    Args:
        report (dict): Отчет с данными о кампании
        
    Returns:
        str: Отформатированный отчет
    """
    # Если получен список кампаний для выбора
    if 'campaigns' in report and not 'campaign' in report:
        return "Пожалуйста, укажите ID конкретной кампании с помощью аргумента --id"
    
    campaign = report['campaign']
    
    output = f"Детальный отчет по кампании: {campaign['name']}\n"
    output += "=" * 80 + "\n"
    
    # Основная информация о кампании
    output += "ИНФОРМАЦИЯ О КАМПАНИИ:\n"
    output += f"ID: {campaign['id']}\n"
    output += f"Статус: {campaign['status']}\n"
    output += f"Цель: {campaign.get('objective', 'Н/Д')}\n"
    
    if campaign.get('daily_budget'):
        output += f"Дневной бюджет: {float(campaign['daily_budget'])/100:.2f}\n"
    
    if campaign.get('lifetime_budget'):
        output += f"Общий бюджет: {float(campaign['lifetime_budget'])/100:.2f}\n"
    
    if campaign.get('start_time'):
        output += f"Дата запуска: {campaign['start_time']}\n"
    
    if campaign.get('stop_time'):
        output += f"Дата окончания: {campaign['stop_time']}\n"
    
    output += "\n"
    
    # Статистика по кампании
    output += "СТАТИСТИКА ПО ДНЯМ:\n"
    output += "-" * 80 + "\n"
    output += f"{'Дата':<12} {'Показы':<10} {'Клики':<8} {'CTR, %':<8} {'CPC':<8} {'Расход':<10} {'Охват':<10}\n"
    output += "-" * 80 + "\n"
    
    total_impressions = 0
    total_clicks = 0
    total_spend = 0
    total_reach = 0
    
    for insight in report['insights']:
        date = insight.get('date_start')
        impressions = int(insight.get('impressions', 0))
        clicks = int(insight.get('clicks', 0))
        ctr = float(insight.get('ctr', 0)) * 100
        cpc = float(insight.get('cpc', 0))
        spend = float(insight.get('spend', 0))
        reach = int(insight.get('reach', 0))
        
        total_impressions += impressions
        total_clicks += clicks
        total_spend += spend
        total_reach += reach
        
        output += f"{date:<12} {impressions:<10} {clicks:<8} {ctr:<8.2f} {cpc:<8.2f} {spend:<10.2f} {reach:<10}\n"
    
    # Итоги по кампании
    output += "-" * 80 + "\n"
    
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 and total_clicks > 0 else 0
    avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    
    output += f"{'ИТОГО':<12} {total_impressions:<10} {total_clicks:<8} {avg_ctr:<8.2f} {avg_cpc:<8.2f} {total_spend:<10.2f} {total_reach:<10}\n"
    output += "=" * 80 + "\n\n"
    
    # Информация по группам объявлений
    output += f"ГРУППЫ ОБЪЯВЛЕНИЙ ({len(report['adsets'])} шт.):\n"
    output += "-" * 80 + "\n"
    
    for i, adset in enumerate(report['adsets']):
        output += f"{i+1}. {adset['name']} (ID: {adset['id']})\n"
        output += f"   Статус: {adset['status']}\n"
        
        if adset.get('daily_budget'):
            output += f"   Дневной бюджет: {float(adset['daily_budget'])/100:.2f}\n"
        
        if adset.get('lifetime_budget'):
            output += f"   Общий бюджет: {float(adset['lifetime_budget'])/100:.2f}\n"
        
        # Статистика по группе объявлений
        adset_total_spend = sum(float(insight.get('spend', 0)) for insight in adset['insights'])
        adset_total_impressions = sum(int(insight.get('impressions', 0)) for insight in adset['insights'])
        adset_total_clicks = sum(int(insight.get('clicks', 0)) for insight in adset['insights'])
        
        output += f"   Показы: {adset_total_impressions}, Клики: {adset_total_clicks}, "
        if adset_total_impressions > 0 and adset_total_clicks > 0:
            output += f"CTR: {(adset_total_clicks / adset_total_impressions * 100):.2f}%, "
        else:
            output += f"CTR: 0.00%, "
        output += f"Расход: {adset_total_spend:.2f}\n"
        
        # Информация по объявлениям
        output += f"   Объявления ({len(adset['ads'])} шт.):\n"
        
        for j, ad in enumerate(adset['ads']):
            output += f"      {j+1}. {ad['name']} (ID: {ad['id']})\n"
            output += f"         Статус: {ad['status']}\n"
            
            # Статистика по объявлению
            ad_total_spend = sum(float(insight.get('spend', 0)) for insight in ad['insights'])
            ad_total_impressions = sum(int(insight.get('impressions', 0)) for insight in ad['insights'])
            ad_total_clicks = sum(int(insight.get('clicks', 0)) for insight in ad['insights'])
            
            output += f"         Показы: {ad_total_impressions}, Клики: {ad_total_clicks}, "
            if ad_total_impressions > 0 and ad_total_clicks > 0:
                output += f"CTR: {(ad_total_clicks / ad_total_impressions * 100):.2f}%, "
            else:
                output += f"CTR: 0.00%, "
            output += f"Расход: {ad_total_spend:.2f}\n"
        
        output += "\n"
    
    return output

def main():
    """
    Основная функция скрипта.
    """
    try:
        # Получаем аргументы командной строки
        import argparse
        parser = argparse.ArgumentParser(description='Получение детальной информации о рекламной кампании Facebook')
        parser.add_argument('--name', type=str, help='Название или часть названия кампании для поиска')
        parser.add_argument('--id', type=str, help='ID кампании')
        parser.add_argument('--days', type=int, default=7, help='Количество дней для анализа (по умолчанию 7)')
        args = parser.parse_args()
        
        # Проверяем, что указано хотя бы одно из: название или ID
        if not args.name and not args.id:
            print("Необходимо указать название (--name) или ID (--id) кампании")
            return
        
        # Получаем данные о кампании
        campaign_name = args.name
        campaign_id = args.id
        days = args.days
        
        report = get_campaign_details(campaign_name=campaign_name, campaign_id=campaign_id, days=days)
        
        if not report:
            print(f"Кампания не найдена. Проверьте правильность названия или ID.")
            return
        
        # Если получен список кампаний для выбора
        if 'campaigns' in report and not 'campaign' in report:
            print("Найдено несколько кампаний. Пожалуйста, уточните запрос или укажите ID конкретной кампании:")
            for campaign in report['campaigns']:
                print(f"ID: {campaign['id']}, Название: {campaign['name']}")
            return
        
        # Форматируем и выводим отчет
        formatted_report = format_campaign_report(report)
        print(formatted_report)
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении скрипта: {str(e)}")
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main()
