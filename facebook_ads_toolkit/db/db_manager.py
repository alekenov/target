#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Менеджер базы данных для работы с Aurora MySQL.
"""

import logging
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple

from facebook_ads_toolkit.config import (
    AURORA_HOST,
    AURORA_PORT,
    AURORA_DATABASE,
    AURORA_USERNAME,
    AURORA_PASSWORD
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер для работы с базой данных."""
    
    def __init__(self):
        """Инициализация менеджера базы данных."""
        self.connection_params = {
            'host': AURORA_HOST,
            'port': AURORA_PORT,
            'user': AURORA_USERNAME,
            'password': AURORA_PASSWORD,
            'db': AURORA_DATABASE,
            'charset': 'utf8mb4',
            'cursorclass': DictCursor
        }
        logger.info(f"Инициализирован пул соединений с базой данных на хосте {AURORA_HOST}")
    
    @contextmanager
    def connection(self):
        """Контекстный менеджер для работы с соединением."""
        conn = None
        try:
            conn = pymysql.connect(**self.connection_params)
            cursor = conn.cursor()
            yield conn, cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка при работе с базой данных: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для получения соединения с базой данных.
        Используется для прямого взаимодействия с соединением.
        
        Yields:
            pymysql.Connection: Соединение с базой данных
        """
        conn = None
        try:
            conn = pymysql.connect(**self.connection_params)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка при работе с базой данных: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_last_sync_state(self, entity_type: str) -> Dict:
        """
        Получение состояния последней синхронизации.
        
        Args:
            entity_type: Тип сущности (campaigns, ad_sets, ads, insights)
            
        Returns:
            Dict: Состояние синхронизации
        """
        query = """
            SELECT last_sync, status, error_message, updated_at
            FROM sync_state
            WHERE entity_type = %s
            ORDER BY updated_at DESC
            LIMIT 1
        """
        
        with self.connection() as (conn, cursor):
            cursor.execute(query, (entity_type,))
            result = cursor.fetchone()
            
        return result if result else {
            'last_sync': None,
            'status': None,
            'error_message': None,
            'updated_at': None
        }
    
    def update_last_sync(self, entity_type: str, sync_time: datetime,
                        status: str = 'success', error_message: str = None) -> None:
        """
        Обновление состояния синхронизации.
        
        Args:
            entity_type: Тип сущности
            sync_time: Время синхронизации
            status: Статус (success/error)
            error_message: Сообщение об ошибке
        """
        query = """
            INSERT INTO sync_state (entity_type, last_sync, status, error_message, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            last_sync = VALUES(last_sync),
            status = VALUES(status),
            error_message = VALUES(error_message),
            updated_at = VALUES(updated_at)
        """
        
        with self.connection() as (conn, cursor):
            cursor.execute(query, (entity_type, sync_time, status, error_message))
    
    def upsert_campaigns(self, campaigns: List[Dict]) -> None:
        """
        Обновление или вставка данных о кампаниях.
        
        Args:
            campaigns: Список кампаний
        """
        query = """
            INSERT INTO campaigns (
                id, name, status, objective, daily_budget,
                lifetime_budget, start_time, stop_time
            ) VALUES (
                %(id)s, %(name)s, %(status)s, %(objective)s,
                %(daily_budget)s, %(lifetime_budget)s,
                %(start_time)s, %(stop_time)s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                status = VALUES(status),
                objective = VALUES(objective),
                daily_budget = VALUES(daily_budget),
                lifetime_budget = VALUES(lifetime_budget),
                start_time = VALUES(start_time),
                stop_time = VALUES(stop_time)
        """
        
        with self.connection() as (conn, cursor):
            cursor.executemany(query, campaigns)
    
    def upsert_ad_sets(self, ad_sets: List[Dict]) -> None:
        """
        Обновление или вставка данных о группах объявлений.
        
        Args:
            ad_sets: Список групп объявлений
        """
        query = """
            INSERT INTO ad_sets (
                id, campaign_id, name, status, daily_budget,
                lifetime_budget, targeting
            ) VALUES (
                %(id)s, %(campaign_id)s, %(name)s, %(status)s,
                %(daily_budget)s, %(lifetime_budget)s, %(targeting)s
            ) ON DUPLICATE KEY UPDATE
                campaign_id = VALUES(campaign_id),
                name = VALUES(name),
                status = VALUES(status),
                daily_budget = VALUES(daily_budget),
                lifetime_budget = VALUES(lifetime_budget),
                targeting = VALUES(targeting)
        """
        
        with self.connection() as (conn, cursor):
            cursor.executemany(query, ad_sets)
    
    def upsert_ads(self, ads: List[Dict]) -> None:
        """
        Обновление или вставка данных об объявлениях.
        
        Args:
            ads: Список объявлений
        """
        query = """
            INSERT INTO ads (
                id, ad_set_id, name, status, creative
            ) VALUES (
                %(id)s, %(ad_set_id)s, %(name)s,
                %(status)s, %(creative)s
            ) ON DUPLICATE KEY UPDATE
                ad_set_id = VALUES(ad_set_id),
                name = VALUES(name),
                status = VALUES(status),
                creative = VALUES(creative)
        """
        
        with self.connection() as (conn, cursor):
            cursor.executemany(query, ads)
    
    def upsert_insights(self, insights: List[Dict]) -> None:
        """
        Обновление или вставка статистики.
        
        Args:
            insights: Список записей статистики
        """
        query = """
            INSERT INTO ad_insights (
                ad_id, date_start, impressions, clicks, spend,
                ctr, cpc, conversations, cost_per_conversation
            ) VALUES (
                %(ad_id)s, %(date_start)s, %(impressions)s,
                %(clicks)s, %(spend)s, %(ctr)s, %(cpc)s,
                %(conversations)s, %(cost_per_conversation)s
            ) ON DUPLICATE KEY UPDATE
                impressions = VALUES(impressions),
                clicks = VALUES(clicks),
                spend = VALUES(spend),
                ctr = VALUES(ctr),
                cpc = VALUES(cpc),
                conversations = VALUES(conversations),
                cost_per_conversation = VALUES(cost_per_conversation)
        """
        
        with self.connection() as (conn, cursor):
            cursor.executemany(query, insights)
    
    def standardize_collation(self) -> None:
        """Стандартизация collation для всех таблиц."""
        tables = [
            'campaigns', 'ad_sets', 'ads', 'ad_insights',
            'sync_state', 'reports'
        ]
        
        with self.connection() as (conn, cursor):
            for table in tables:
                cursor.execute(f"""
                    ALTER TABLE {table}
                    CONVERT TO CHARACTER SET utf8mb4
                    COLLATE utf8mb4_unicode_ci
                """)
                logger.info(f"Стандартизирована collation для таблицы {table}")
