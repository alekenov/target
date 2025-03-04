#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для пакетных операций с базой данных.
Содержит функции для массового сохранения данных из Facebook Ads.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
import json
from facebook_ads_toolkit.db.db_utils import DatabaseConnection, get_connection

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_ads_batch(ads_data: List[Dict[str, Any]]) -> bool:
    """
    Пакетное сохранение объявлений в базу данных.
    
    Args:
        ads_data (List[Dict[str, Any]]): Список данных объявлений из Facebook API
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    if not ads_data:
        return True
        
    try:
        conn, cursor = get_connection()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Подготовка данных для массовой вставки
        values = []
        update_values = []
        
        for ad in ads_data:
            values.append((
                ad['id'],
                ad.get('name'),
                ad.get('adset_id'),
                ad.get('status'),
                json.dumps(ad.get('creative', {})),
                current_time,
                current_time
            ))
            
            update_values.append((
                ad.get('name'),
                ad.get('adset_id'),
                ad.get('status'),
                json.dumps(ad.get('creative', {})),
                current_time,
                ad['id']
            ))
        
        # Массовая вставка с обработкой дубликатов
        cursor.executemany(
            """
            INSERT INTO ads (id, name, ad_set_id, status, creative, created_time, updated_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                ad_set_id = VALUES(ad_set_id),
                status = VALUES(status),
                creative = VALUES(creative),
                updated_time = VALUES(updated_time)
            """,
            values
        )
        
        conn.commit()
        logger.info(f"Успешно сохранено {len(ads_data)} объявлений")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при пакетном сохранении объявлений: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def save_insights_batch(insights_data: List[Dict[str, Any]]) -> bool:
    """
    Пакетное сохранение статистики в базу данных.
    
    Args:
        insights_data (List[Dict[str, Any]]): Список данных статистики из Facebook API
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    if not insights_data:
        return True
        
    try:
        conn, cursor = get_connection()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Подготовка данных для массовой вставки
        values = []
        
        for insight in insights_data:
            values.append((
                insight.get('ad_id'),
                insight.get('date_start'),
                int(insight.get('impressions', 0)),
                int(insight.get('clicks', 0)),
                float(insight.get('spend', 0)),
                float(insight.get('ctr', 0)),
                float(insight.get('cpc', 0)),
                int(insight.get('conversions', 0)),
                current_time
            ))
        
        # Массовая вставка с обработкой дубликатов
        cursor.executemany(
            """
            INSERT INTO ad_insights (
                ad_id, date, impressions, clicks, spend,
                ctr, cpc, conversions, created_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                impressions = VALUES(impressions),
                clicks = VALUES(clicks),
                spend = VALUES(spend),
                ctr = VALUES(ctr),
                cpc = VALUES(cpc),
                conversions = VALUES(conversions)
            """,
            values
        )
        
        conn.commit()
        logger.info(f"Успешно сохранено {len(insights_data)} записей статистики")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при пакетном сохранении статистики: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def cleanup_old_insights(days: int = 90) -> bool:
    """
    Удаляет старые записи статистики из базы данных.
    
    Args:
        days (int): Количество дней, после которых данные считаются устаревшими
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    try:
        conn, cursor = get_connection()
        
        # Удаляем записи старше указанного количества дней
        cursor.execute(
            """
            DELETE FROM ad_insights
            WHERE date < DATE_SUB(CURRENT_DATE, INTERVAL %s DAY)
            """,
            (days,)
        )
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Удалено {deleted_count} устаревших записей статистики")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при удалении устаревших данных: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close() 