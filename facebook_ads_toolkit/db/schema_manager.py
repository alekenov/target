#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для управления схемой базы данных.
Предоставляет функции для создания, обновления и оптимизации таблиц.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from facebook_ads_toolkit.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class SchemaManager:
    """
    Менеджер схемы базы данных для создания и оптимизации таблиц.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Инициализация менеджера схемы.
        
        Args:
            db_manager: Менеджер базы данных (если None, будет создан новый)
        """
        self.db_manager = db_manager or DatabaseManager()
    
    def create_database(self, db_name: str) -> bool:
        """
        Создает базу данных, если она не существует.
        
        Args:
            db_name: Имя базы данных
            
        Returns:
            bool: True, если операция выполнена успешно
        """
        try:
            self.db_manager.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            self.db_manager.execute(f"USE {db_name}")
            logger.info(f"База данных {db_name} создана или уже существует")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании базы данных: {str(e)}")
            return False
    
    def create_tables(self) -> bool:
        """
        Создает все необходимые таблицы, если они не существуют.
        
        Returns:
            bool: True, если все таблицы созданы успешно
        """
        try:
            # Создаем таблицы в правильном порядке (с учетом зависимостей)
            self._create_campaigns_table()
            self._create_ad_sets_table()
            self._create_ads_table()
            self._create_ad_insights_table()
            self._create_config_table()
            
            logger.info("Все таблицы успешно созданы")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {str(e)}")
            return False

    def get_table_status(self) -> List[Dict[str, Any]]:
        """
        Получает статус всех таблиц в базе данных.
        
        Returns:
            List[Dict[str, Any]]: Список словарей с информацией о таблицах
        """
        try:
            with self.db_manager.connection() as (conn, cursor):
                cursor.execute("""
                    SELECT 
                        TABLE_NAME,
                        TABLE_ROWS,
                        DATA_LENGTH,
                        INDEX_LENGTH,
                        UPDATE_TIME
                    FROM 
                        information_schema.TABLES 
                    WHERE 
                        TABLE_SCHEMA = DATABASE()
                """)
                tables = cursor.fetchall()
                
                result = []
                for table in tables:
                    result.append({
                        'table_name': table['TABLE_NAME'],
                        'table_rows': table['TABLE_ROWS'] or 0,
                        'data_size': table['DATA_LENGTH'] or 0,
                        'index_size': table['INDEX_LENGTH'] or 0,
                        'last_update': table['UPDATE_TIME']
                    })
                return result
        except Exception as e:
            logger.error(f"Ошибка при получении статуса таблиц: {str(e)}")
            return []
    
    def optimize_tables(self) -> bool:
        """
        Оптимизирует таблицы для повышения производительности.
        Добавляет индексы и выполняет другие оптимизации.
        
        Returns:
            bool: True, если все оптимизации выполнены успешно
        """
        try:
            # Добавляем индексы для оптимизации запросов
            self._add_indexes()
            
            # Оптимизируем таблицы
            tables = ['campaigns', 'ad_sets', 'ads', 'ad_insights', 'config']
            for table in tables:
                self.db_manager.execute(f"OPTIMIZE TABLE {table}")
            
            logger.info("Все таблицы успешно оптимизированы")
            return True
        except Exception as e:
            logger.error(f"Ошибка при оптимизации таблиц: {str(e)}")
            return False
    
    def _create_campaigns_table(self) -> None:
        """Создает таблицу campaigns."""
        self.db_manager.execute("""
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
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_campaign_status (status),
                INDEX idx_campaign_objective (objective),
                INDEX idx_campaign_created (created_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("Таблица campaigns создана или уже существует")
    
    def _create_ad_sets_table(self) -> None:
        """Создает таблицу ad_sets."""
        self.db_manager.execute("""
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
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
                INDEX idx_adset_campaign (campaign_id),
                INDEX idx_adset_status (status),
                INDEX idx_adset_created (created_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("Таблица ad_sets создана или уже существует")
    
    def _create_ads_table(self) -> None:
        """Создает таблицу ads."""
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id VARCHAR(255) PRIMARY KEY,
                ad_set_id VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50),
                creative JSON,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ad_set_id) REFERENCES ad_sets(id),
                INDEX idx_ad_adset (ad_set_id),
                INDEX idx_ad_status (status),
                INDEX idx_ad_created (created_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("Таблица ads создана или уже существует")
    
    def _create_ad_insights_table(self) -> None:
        """Создает таблицу ad_insights."""
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS ad_insights (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ad_id VARCHAR(255) NOT NULL,
                date_start DATE NOT NULL,
                hour_start DATETIME,
                hour_end DATETIME,
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
                UNIQUE KEY unique_ad_date (ad_id, date_start),
                INDEX idx_insights_ad (ad_id),
                INDEX idx_insights_date (date_start),
                INDEX idx_insights_hour_start (hour_start),
                INDEX idx_insights_hour_end (hour_end),
                INDEX idx_insights_spend (spend),
                INDEX idx_insights_created (created_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("Таблица ad_insights создана или уже существует")
    
    def _create_config_table(self) -> None:
        """Создает таблицу config."""
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                `key` VARCHAR(255) NOT NULL UNIQUE,
                value TEXT,
                description TEXT,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_config_key (`key`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("Таблица config создана или уже существует")
    
    def _add_indexes(self) -> None:
        """Добавляет индексы для оптимизации запросов."""
        pass  # Индексы уже добавлены при создании таблиц

def init_database(db_name: str = None) -> bool:
    """
    Инициализирует базу данных и создает необходимые таблицы.
    
    Args:
        db_name: Имя базы данных (если None, используется значение из переменных окружения)
        
    Returns:
        bool: True, если инициализация выполнена успешно
    """
    try:
        schema_manager = SchemaManager()
        if db_name:
            schema_manager.create_database(db_name)
        return schema_manager.create_tables()
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        return False
