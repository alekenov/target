#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для сбора данных из Facebook Marketing API.
"""

import os
import json
import logging
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)

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

class FacebookDataCollector:
    """Класс для сбора данных из Facebook Marketing API."""
    
    def __init__(self, account):
        """
        Инициализация коллектора данных.
        
        Args:
            account: Объект AdAccount из Facebook API
        """
        self.account = account
    
    def collect_campaigns(self):
        """Сбор данных о кампаниях."""
        logger.info("Получение данных о кампаниях...")
        campaigns = self.account.get_campaigns(fields=[
            'id',
            'name',
            'status',
            'objective',
            'daily_budget',
            'lifetime_budget'
        ])
        
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
        
        return campaign_values, campaign_info
    
    def collect_ad_sets(self):
        """Сбор данных о группах объявлений."""
        logger.info("Получение данных о группах объявлений...")
        ad_sets = self.account.get_ad_sets(fields=[
            'id',
            'name',
            'campaign_id',
            'status',
            'targeting'
        ])
        
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
        
        return ad_set_values, ad_set_map
    
    def collect_insights(self, start_date, end_date):
        """
        Сбор данных о показателях эффективности.
        
        Args:
            start_date (str): Начальная дата в формате YYYY-MM-DD
            end_date (str): Конечная дата в формате YYYY-MM-DD
        """
        logger.info(f"Получение данных о показателях за период {start_date} - {end_date}")
        
        insights = self.account.get_insights(
            fields=[
                'campaign_id',
                'campaign_name',
                'adset_id',
                'adset_name',
                'spend',
                'impressions',
                'clicks',
                'reach',
                'date_start'
            ],
            params={
                'level': 'adset',
                'time_range': {
                    'since': start_date,
                    'until': end_date
                },
                'time_increment': 1
            }
        )
        
        return list(insights)
