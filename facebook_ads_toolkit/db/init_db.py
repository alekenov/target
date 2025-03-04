#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для инициализации базы данных.
"""

import os
import logging
from dotenv import load_dotenv
import pymysql

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def init_database():
    """Инициализация базы данных и создание таблиц."""
    load_dotenv()
    
    # Параметры подключения
    connection_params = {
        'host': os.getenv('AURORA_HOST'),
        'port': int(os.getenv('AURORA_PORT', '3306')),
        'user': os.getenv('AURORA_USERNAME'),
        'password': os.getenv('AURORA_PASSWORD'),
        'db': os.getenv('AURORA_DATABASE'),
        'charset': 'utf8mb4'
    }
    
    # SQL для создания таблиц
    create_tables_sql = """
    -- Set default character set and collation
    SET NAMES utf8mb4;
    SET character_set_client = utf8mb4;

    -- Create campaigns table
    CREATE TABLE IF NOT EXISTS campaigns (
        id VARCHAR(255) PRIMARY KEY COLLATE utf8mb4_unicode_ci,
        name VARCHAR(255) COLLATE utf8mb4_unicode_ci,
        status VARCHAR(50) COLLATE utf8mb4_unicode_ci,
        objective VARCHAR(50) COLLATE utf8mb4_unicode_ci,
        daily_budget DECIMAL(15,2),
        lifetime_budget DECIMAL(15,2),
        start_time DATETIME,
        stop_time DATETIME,
        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        last_sync_time DATETIME
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

    -- Create ad_sets table
    CREATE TABLE IF NOT EXISTS ad_sets (
        id VARCHAR(255) PRIMARY KEY COLLATE utf8mb4_unicode_ci,
        campaign_id VARCHAR(255) COLLATE utf8mb4_unicode_ci,
        name VARCHAR(255) COLLATE utf8mb4_unicode_ci,
        status VARCHAR(50) COLLATE utf8mb4_unicode_ci,
        daily_budget DECIMAL(15,2),
        lifetime_budget DECIMAL(15,2),
        targeting JSON,
        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        last_sync_time DATETIME,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

    -- Create ads table
    CREATE TABLE IF NOT EXISTS ads (
        id VARCHAR(255) PRIMARY KEY COLLATE utf8mb4_unicode_ci,
        ad_set_id VARCHAR(255) COLLATE utf8mb4_unicode_ci,
        name VARCHAR(255) COLLATE utf8mb4_unicode_ci,
        status VARCHAR(50) COLLATE utf8mb4_unicode_ci,
        creative JSON,
        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        last_sync_time DATETIME,
        FOREIGN KEY (ad_set_id) REFERENCES ad_sets(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

    -- Create ad_insights table
    CREATE TABLE IF NOT EXISTS ad_insights (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        ad_id VARCHAR(255) COLLATE utf8mb4_unicode_ci,
        date_start DATE,
        impressions INT,
        clicks INT,
        spend DECIMAL(15,2),
        ctr DECIMAL(10,4),
        cpc DECIMAL(10,2),
        conversations INT,
        cost_per_conversation DECIMAL(10,2),
        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_sync_time DATETIME,
        FOREIGN KEY (ad_id) REFERENCES ads(id),
        UNIQUE KEY `ad_date_idx` (ad_id, date_start)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

    -- Create sync_state table
    CREATE TABLE IF NOT EXISTS sync_state (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        entity_type VARCHAR(50) COLLATE utf8mb4_unicode_ci,
        last_sync_time DATETIME,
        status VARCHAR(50) COLLATE utf8mb4_unicode_ci,
        error_message TEXT COLLATE utf8mb4_unicode_ci,
        updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY `entity_type_idx` (entity_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

    -- Insert initial sync states
    INSERT IGNORE INTO sync_state (entity_type, status, updated_time) VALUES
    ('campaigns', 'PENDING', NOW()),
    ('ad_sets', 'PENDING', NOW()),
    ('ads', 'PENDING', NOW()),
    ('insights', 'PENDING', NOW());
    """
    
    try:
        # Подключение к базе данных
        conn = pymysql.connect(**connection_params)
        cursor = conn.cursor()
        
        # Создание таблиц
        for statement in create_tables_sql.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        conn.commit()
        logger.info("База данных успешно инициализирована")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        raise
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_database()
