#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для инициализации базы данных Aurora MySQL.
Создает необходимые таблицы, если они не существуют.
"""

import os
import logging
from dotenv import load_dotenv
import pymysql
from pymysql.cursors import DictCursor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def init_database():
    """Инициализация базы данных и создание таблиц."""
    try:
        # Подключение к базе данных
        connection = pymysql.connect(
            host=os.getenv('AURORA_HOST'),
            user=os.getenv('AURORA_MASTER_USERNAME'),
            password=os.getenv('AURORA_MASTER_PASSWORD'),
            port=int(os.getenv('AURORA_PORT', 3306)),
            cursorclass=DictCursor,
            connect_timeout=10
        )
        
        cursor = connection.cursor()
        
        # Создаем базу данных, если она не существует
        db_name = os.getenv('AURORA_DATABASE_NAME', 'facebook_ads_db')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")
        
        logger.info(f"База данных {db_name} создана или уже существует")
        
        # Создаем таблицы
        # 1. Таблица campaigns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50),
                objective VARCHAR(50),
                daily_budget DECIMAL(10,2),
                lifetime_budget DECIMAL(10,2),
                start_time DATETIME,
                stop_time DATETIME,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        logger.info("Таблица campaigns создана или уже существует")
        
        # 2. Таблица ad_sets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ad_sets (
                id VARCHAR(255) PRIMARY KEY,
                campaign_id VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50),
                daily_budget DECIMAL(10,2),
                lifetime_budget DECIMAL(10,2),
                targeting JSON,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        """)
        logger.info("Таблица ad_sets создана или уже существует")
        
        # 3. Таблица ads
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id VARCHAR(255) PRIMARY KEY,
                ad_set_id VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50),
                creative JSON,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ad_set_id) REFERENCES ad_sets(id)
            )
        """)
        logger.info("Таблица ads создана или уже существует")
        
        # 4. Таблица ad_insights
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ad_insights (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ad_id VARCHAR(255) NOT NULL,
                date_start DATE NOT NULL,
                impressions INT NOT NULL DEFAULT 0,
                clicks INT NOT NULL DEFAULT 0,
                spend DECIMAL(10,2) NOT NULL DEFAULT 0,
                ctr DECIMAL(5,2) NOT NULL DEFAULT 0,
                cpc DECIMAL(10,2) NOT NULL DEFAULT 0,
                conversations INT NOT NULL DEFAULT 0,
                cost_per_conversation DECIMAL(10,2) NOT NULL DEFAULT 0,
                link_clicks INT NOT NULL DEFAULT 0,
                cost_per_link_click DECIMAL(10,2) NOT NULL DEFAULT 0,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_ad_date (ad_id, date_start)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        logger.info("Таблица ad_insights создана или уже существует")
        
        # 5. Таблица config
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                `key` VARCHAR(255) NOT NULL UNIQUE,
                value TEXT,
                description TEXT,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        logger.info("Таблица config создана или уже существует")
        
        connection.commit()
        logger.info("Все таблицы успешно созданы")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
            logger.info("Соединение с базой данных закрыто")

if __name__ == "__main__":
    # Загружаем переменные окружения
    load_dotenv()
    init_database()
