#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для инициализации базы данных и импорта данных из Facebook API.
"""

import logging
import os
import sys
import pymysql
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Подключаем модули
from facebook_ads_toolkit.core.authenticator import FacebookAuth
from facebook_ads_toolkit.db.db_manager import DatabaseManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def init_db():
    """Инициализация базы данных."""
    load_dotenv()
    
    try:
        # Подключение к MySQL
        db_manager = DatabaseManager()
        
        # Чтение SQL схемы
        schema_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'facebook_ads_toolkit',
            'db',
            'schema.sql'
        )
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        logger.info("Создание/обновление таблиц в базе данных...")
        
        # Выполнение SQL запросов из файла схемы
        with db_manager.get_connection() as connection:
            # Разбиваем SQL файл на отдельные команды
            sql_commands = schema_sql.split(';')
            
            with connection.cursor() as cursor:
                for command in sql_commands:
                    command = command.strip()
                    if command:
                        logger.info(f"Выполнение SQL: {command[:100]}...")
                        cursor.execute(command)
            
            connection.commit()
            
        logger.info("Таблицы успешно созданы.")
        return True
        
    except pymysql.MySQLError as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {str(e)}")
        return False

def import_campaigns():
    """Импорт кампаний из Facebook API."""
    try:
        # Инициализация Facebook API
        auth = FacebookAuth()
        account, api = auth.initialize()
        
        if not account or not api:
            logger.error("Ошибка при инициализации Facebook API")
            return False
        
        # Подключение к базе данных
        db_manager = DatabaseManager()
        
        # Получение активных кампаний
        logger.info("Получение кампаний из Facebook API...")
        campaigns = account.get_campaigns(
            fields=[
                'id', 'name', 'status', 'objective', 
                'daily_budget', 'lifetime_budget', 
                'start_time', 'stop_time', 
                'created_time', 'updated_time'
            ],
            params={'date_preset': 'last_90d'}
        )
        
        logger.info(f"Получено кампаний: {len(campaigns)}")
        
        # Импорт кампаний в базу данных
        logger.info("Импорт кампаний в базу данных...")
        
        with db_manager.get_connection() as connection:
            with connection.cursor() as cursor:
                for campaign in campaigns:
                    # Формирование данных для вставки
                    campaign_data = {
                        'id': campaign['id'],
                        'name': campaign['name'],
                        'status': campaign['status'],
                        'daily_budget': float(campaign.get('daily_budget', 0)) / 100 if campaign.get('daily_budget') else None,
                        'lifetime_budget': float(campaign.get('lifetime_budget', 0)) / 100 if campaign.get('lifetime_budget') else None,
                        'start_time': campaign.get('start_time'),
                        'stop_time': campaign.get('stop_time'),
                        'created_time': campaign.get('created_time'),
                        'updated_time': campaign.get('updated_time'),
                        'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # SQL запрос для вставки/обновления
                    sql = """
                    INSERT INTO campaigns (
                        id, name, status, daily_budget, lifetime_budget,
                        start_time, stop_time, created_time, updated_time, last_sync
                    ) VALUES (
                        %(id)s, %(name)s, %(status)s, %(daily_budget)s, %(lifetime_budget)s,
                        %(start_time)s, %(stop_time)s, %(created_time)s, %(updated_time)s, %(last_sync)s
                    ) ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        status = VALUES(status),
                        daily_budget = VALUES(daily_budget),
                        lifetime_budget = VALUES(lifetime_budget),
                        start_time = VALUES(start_time),
                        stop_time = VALUES(stop_time),
                        updated_time = VALUES(updated_time),
                        last_sync = VALUES(last_sync)
                    """
                    
                    cursor.execute(sql, campaign_data)
                    
                    logger.info(f"Импортирована кампания: {campaign['name']} (ID: {campaign['id']})")
                
                connection.commit()
        
        logger.info("Импорт кампаний успешно завершен")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при импорте кампаний: {str(e)}")
        return False

def main():
    """Основная функция."""
    logger.info("Начало инициализации и импорта данных")
    
    # Шаг 1: Инициализация базы данных
    if not init_db():
        logger.error("Не удалось инициализировать базу данных")
        return
    
    # Шаг 2: Импорт кампаний
    if not import_campaigns():
        logger.error("Не удалось импортировать кампании")
        return
    
    logger.info("Процесс инициализации и импорта данных успешно завершен")

if __name__ == "__main__":
    main()
