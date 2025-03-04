#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для получения данных о тратах из Facebook API и сохранения их в базу данных.
Запускается через cron или ручной вызов. Сохраняет данные за указанный период.
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
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError
import pymysql
from pymysql.cursors import DictCursor

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
            account = AdAccount(self.account_id if self.account_id.startswith('act_') else f'act_{self.account_id}')
            
            logger.info(f"Успешно инициализировано соединение с Facebook API для аккаунта {self.account_id}")
            return account, api
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации Facebook API: {str(e)}")
            return None, None

class DatabaseConnection:
    """Context manager для работы с базой данных."""
    
    def __init__(self, dict_cursor=True):
        self.dict_cursor = dict_cursor
        self.connection = None
        self.cursor = None
    
    def __enter__(self):
        """Создание соединения с базой данных."""
        try:
            self.connection = pymysql.connect(
                host=os.getenv('AURORA_HOST', os.getenv('DB_HOST')),
                user=os.getenv('AURORA_MASTER_USERNAME', os.getenv('DB_USER', 'admin')),
                password=os.getenv('AURORA_MASTER_PASSWORD', os.getenv('DB_PASSWORD')),
                database=os.getenv('AURORA_DATABASE_NAME', os.getenv('DB_NAME', 'facebook_ads_db')),
                port=int(os.getenv('AURORA_PORT', os.getenv('DB_PORT', 3306))),
                cursorclass=DictCursor if self.dict_cursor else pymysql.cursors.Cursor,
                connect_timeout=10
            )
            self.cursor = self.connection.cursor()
            logger.info("Успешное подключение к базе данных")
            return self.cursor
        except Exception as e:
            logger.error(f"Ошибка при подключении к базе данных: {str(e)}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие соединения с базой данных."""
        if exc_type:
            logger.error(f"Ошибка базы данных: {exc_type} - {exc_val}")
            if self.connection:
                self.connection.rollback()
        else:
            if self.connection:
                self.connection.commit()
        
        if self.cursor:
            self.cursor.close()
        
        if self.connection:
            self.connection.close()
            logger.info("Соединение с базой данных закрыто")

def get_facebook_ad_spend(account, start_date, end_date):
    """
    Получает данные о тратах из Facebook API.
    
    Args:
        account: Объект AdAccount из Facebook API
        start_date (str): Начальная дата в формате YYYY-MM-DD
        end_date (str): Конечная дата в формате YYYY-MM-DD
        
    Returns:
        list: Список с данными о тратах
    """
    try:
        logger.info(f"Получение данных о тратах за период с {start_date} по {end_date}")
        
        # Создаем один коннект для всех операций
        with DatabaseConnection() as cursor:
            # 1. Получаем все кампании
            logger.info("Получение данных о кампаниях...")
            campaigns = account.get_campaigns(fields=[
                'id',
                'name',
                'status',
                'objective',
                'daily_budget',
                'lifetime_budget'
            ])
            
            # Подготавливаем данные для batch-вставки
            campaign_values = []
            campaign_info = {}
            
            for campaign in campaigns:
                campaign_info[campaign['id']] = {
                    'name': campaign['name'],
                    'status': campaign['status'],
                    'objective': campaign['objective']
                }
                campaign_values.append((
                    campaign['id'],
                    campaign['name'],
                    campaign['status'],
                    campaign['objective']
                ))
            
            # Batch-вставка кампаний
            if campaign_values:
                cursor.executemany("""
                    INSERT INTO campaigns (id, name, status, objective)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    status = VALUES(status),
                    objective = VALUES(objective)
                """, campaign_values)
            
            # 2. Получаем все группы объявлений для всех кампаний сразу
            logger.info("Получение данных о группах объявлений...")
            ad_sets = account.get_ad_sets(fields=[
                'id',
                'name',
                'campaign_id',
                'status',
                'targeting'
            ])
            
            # Подготавливаем данные для batch-вставки
            ad_set_values = []
            ad_set_map = {}
            
            for ad_set in ad_sets:
                targeting = ad_set.get('targeting', {})
                if hasattr(targeting, 'export_data'):
                    targeting = targeting.export_data()
                
                ad_set_map[ad_set['id']] = ad_set
                ad_set_values.append((
                    ad_set['id'],
                    ad_set['campaign_id'],
                    ad_set['name'],
                    ad_set['status'],
                    json.dumps(targeting)
                ))
            
            # Batch-вставка групп объявлений
            if ad_set_values:
                cursor.executemany("""
                    INSERT INTO ad_sets (id, campaign_id, name, status, targeting)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    status = VALUES(status),
                    targeting = VALUES(targeting)
                """, ad_set_values)
            
            # 3. Получаем все объявления сразу
            logger.info("Получение данных об объявлениях...")
            ads = account.get_ads(fields=[
                'id',
                'name',
                'status',
                'creative',
                'adset_id'
            ])
            
            # Подготавливаем данные для batch-вставки
            ad_values = []
            
            for ad in ads:
                creative = ad.get('creative', {})
                if hasattr(creative, 'export_data'):
                    creative = creative.export_data()
                
                ad_values.append((
                    ad['id'],
                    ad['adset_id'],
                    ad['name'],
                    ad['status'],
                    json.dumps(creative)
                ))
            
            # Batch-вставка объявлений
            if ad_values:
                cursor.executemany("""
                    INSERT INTO ads (id, ad_set_id, name, status, creative)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    status = VALUES(status),
                    creative = VALUES(creative)
                """, ad_values)
            
            # 4. Получаем статистику для всех объявлений сразу
            logger.info("Получение статистики...")
            params = {
                'time_range': {'since': start_date, 'until': end_date},
                'level': 'ad',
                'fields': [
                    'ad_id',
                    'ad_name',
                    'campaign_id',
                    'campaign_name',
                    'adset_id',
                    'adset_name',
                    'spend',
                    'impressions',
                    'clicks',
                    'ctr',
                    'cpc',
                    'reach',
                    'date_start',
                    'date_stop',
                    'actions',
                    'cost_per_action_type'
                ],
                'time_increment': 1
            }
            
            insights = account.get_insights(params=params)
            spend_data = []
            
            for insight in insights:
                campaign_id = insight.get('campaign_id')
                campaign = campaign_info.get(campaign_id, {})
                
                # Получаем данные о переписках/конверсиях
                conversations = 0
                cost_per_conversation = 0
                link_clicks = 0
                cost_per_link_click = 0
                
                actions = insight.get('actions', [])
                if hasattr(actions, 'export_data'):
                    actions = actions.export_data()
                    
                for action in actions:
                    action_type = action.get('action_type', '')
                    if action_type == 'onsite_conversion.messaging_conversation_started_7d':
                        conversations += int(action.get('value', 0))
                    elif action_type == 'link_click':
                        link_clicks += int(action.get('value', 0))
                
                cost_per_action = insight.get('cost_per_action_type', [])
                if hasattr(cost_per_action, 'export_data'):
                    cost_per_action = cost_per_action.export_data()
                    
                for cost in cost_per_action:
                    action_type = cost.get('action_type', '')
                    if action_type == 'onsite_conversion.messaging_conversation_started_7d':
                        cost_per_conversation = float(cost.get('value', 0))
                    elif action_type == 'link_click':
                        cost_per_link_click = float(cost.get('value', 0))
                
                spend_item = {
                    'date': insight.get('date_start'),
                    'campaign_id': campaign_id,
                    'campaign_name': campaign.get('name', insight.get('campaign_name')),
                    'ad_id': insight.get('ad_id'),
                    'ad_name': insight.get('ad_name'),
                    'adset_id': insight.get('adset_id'),
                    'adset_name': insight.get('adset_name'),
                    'status': campaign.get('status', 'UNKNOWN'),
                    'objective': campaign.get('objective', 'UNKNOWN'),
                    'spend': float(insight.get('spend', 0)),
                    'impressions': int(insight.get('impressions', 0)),
                    'clicks': int(insight.get('clicks', 0)),
                    'ctr': float(insight.get('ctr', 0)) * 100,
                    'cpc': float(insight.get('cpc', 0)) if insight.get('cpc') else 0,
                    'conversations': conversations,
                    'cost_per_conversation': cost_per_conversation,
                    'link_clicks': link_clicks,
                    'cost_per_link_click': cost_per_link_click
                }
                
                spend_data.append(spend_item)
            
            logger.info(f"Получено {len(spend_data)} записей о тратах")
            return spend_data
            
    except FacebookRequestError as e:
        logger.error(f"Ошибка Facebook API: {e.api_error_code()} - {e.api_error_message()}")
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении данных о тратах: {str(e)}")
        raise

def save_spend_data_to_db(spend_data):
    """
    Сохраняет данные о тратах в базу данных.
    
    Args:
        spend_data (list): Список словарей с данными о тратах
    """
    try:
        if not spend_data:
            logger.warning("Нет данных для сохранения")
            return
            
        with DatabaseConnection() as cursor:
            # Подготавливаем данные для batch-вставки
            values = []
            for data in spend_data:
                values.append((
                    data['ad_id'],
                    data['date'],
                    data['impressions'],
                    data['clicks'],
                    data['spend'],
                    data['ctr'],
                    data['cpc'],
                    data['conversations'],
                    data['cost_per_conversation'],
                    data['link_clicks'],
                    data['cost_per_link_click']
                ))
            
            # Batch-вставка статистики
            cursor.executemany("""
                INSERT INTO ad_insights (
                    ad_id, date_start, impressions, clicks, 
                    spend, ctr, cpc, conversations,
                    cost_per_conversation, link_clicks,
                    cost_per_link_click
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                impressions = VALUES(impressions),
                clicks = VALUES(clicks),
                spend = VALUES(spend),
                ctr = VALUES(ctr),
                cpc = VALUES(cpc),
                conversations = VALUES(conversations),
                cost_per_conversation = VALUES(cost_per_conversation),
                link_clicks = VALUES(link_clicks),
                cost_per_link_click = VALUES(cost_per_link_click)
            """, values)
            
            logger.info(f"Сохранено {len(values)} записей о тратах")
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в базу: {str(e)}")
        raise

def main():
    """
    Основная функция скрипта.
    """
    # Загружаем переменные окружения
    load_dotenv()
    
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description='Получение и сохранение данных о тратах Facebook в базу данных')
    parser.add_argument('--days', type=int, default=1, help='Количество дней для анализа (по умолчанию 1)')
    parser.add_argument('--start-date', type=str, help='Начальная дата в формате YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, help='Конечная дата в формате YYYY-MM-DD')
    args = parser.parse_args()
    
    # Определяем даты запроса
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    else:
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    
    logger.info(f"Запуск сбора данных о тратах Facebook за период с {start_date} по {end_date}")
    
    try:
        # Инициализируем Facebook API
        auth = FacebookAuth()
        account, api = auth.initialize()
        
        if not account or not api:
            logger.error("Не удалось инициализировать Facebook API")
            return
        
        # Получаем данные о тратах
        spend_data = get_facebook_ad_spend(account, start_date, end_date)
        
        # Сохраняем данные в базу данных
        save_spend_data_to_db(spend_data)
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении скрипта: {str(e)}")

if __name__ == "__main__":
    main()