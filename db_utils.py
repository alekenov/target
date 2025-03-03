#!/usr/bin/env python3
"""
Database Utility Module for Aurora Serverless

This module provides utility functions for interacting with the Aurora Serverless database.
It handles connection management and common database operations for the Facebook Ads Tool.
"""

import os
import logging
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Aurora Serverless Configuration
AURORA_HOSTNAME = os.getenv('AURORA_HOST')
AURORA_USERNAME = os.getenv('AURORA_MASTER_USERNAME', 'admin')
AURORA_PASSWORD = os.getenv('AURORA_MASTER_PASSWORD')
AURORA_DB_NAME = os.getenv('AURORA_DATABASE_NAME', 'facebook_ads_db')
AURORA_PORT = int(os.getenv('AURORA_PORT', '3306'))

# Глобальное соединение для повторного использования
_global_connection = None

def get_connection(dict_cursor=True):
    """
    Получить соединение с базой данных, повторно используя существующее, если оно доступно.
    
    Args:
        dict_cursor (bool): Использовать ли словарный курсор
        
    Returns:
        Tuple[pymysql.Connection, pymysql.cursors.Cursor]: Соединение и курсор
    """
    global _global_connection
    
    if not AURORA_HOSTNAME:
        raise ValueError("AURORA_HOST is not set. Please create the Aurora Serverless cluster first.")
    
    if not AURORA_PASSWORD:
        raise ValueError("AURORA_MASTER_PASSWORD is not set. Please set it in your .env file.")
    
    try:
        # Проверяем, активно ли существующее соединение
        if _global_connection is not None:
            try:
                _global_connection.ping(reconnect=True)
                cursor = _global_connection.cursor(DictCursor if dict_cursor else pymysql.cursors.Cursor)
                return _global_connection, cursor
            except Exception:
                # Если соединение не активно, закрываем его и создаем новое
                try:
                    _global_connection.close()
                except Exception:
                    pass
                _global_connection = None
        
        # Создаем новое соединение
        logger.info(f"Connecting to database: {AURORA_HOSTNAME}:{AURORA_PORT}, user: {AURORA_USERNAME}, database: {AURORA_DB_NAME}")
        _global_connection = pymysql.connect(
            host=AURORA_HOSTNAME,
            user=AURORA_USERNAME,
            password=AURORA_PASSWORD,
            database=AURORA_DB_NAME,
            port=AURORA_PORT,
            cursorclass=DictCursor if dict_cursor else pymysql.cursors.Cursor,
            connect_timeout=10
        )
        cursor = _global_connection.cursor()
        logger.info("Database connection established successfully")
        return _global_connection, cursor
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        raise

def close_connection():
    """Закрыть глобальное соединение с базой данных."""
    global _global_connection
    
    if _global_connection is not None:
        try:
            _global_connection.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
        finally:
            _global_connection = None

class DatabaseConnection:
    """Context manager for database connections."""
    
    def __init__(self, dict_cursor=True, reuse_connection=False):
        """Initialize the database connection context manager.
        
        Args:
            dict_cursor (bool): Whether to use a dictionary cursor
            reuse_connection (bool): Whether to reuse an existing connection
        """
        self.dict_cursor = dict_cursor
        self.reuse_connection = reuse_connection
        self.connection = None
        self.cursor = None
        self.should_close = not reuse_connection
    
    def __enter__(self):
        """Enter the context manager, establishing a database connection."""
        if self.reuse_connection:
            self.connection, self.cursor = get_connection(self.dict_cursor)
        else:
            if not AURORA_HOSTNAME:
                raise ValueError("AURORA_HOST is not set. Please create the Aurora Serverless cluster first.")
            
            if not AURORA_PASSWORD:
                raise ValueError("AURORA_MASTER_PASSWORD is not set. Please set it in your .env file.")
            
            logger.info(f"Connecting to database: {AURORA_HOSTNAME}:{AURORA_PORT}, user: {AURORA_USERNAME}, database: {AURORA_DB_NAME}")
            
            try:
                self.connection = pymysql.connect(
                    host=AURORA_HOSTNAME,
                    user=AURORA_USERNAME,
                    password=AURORA_PASSWORD,
                    database=AURORA_DB_NAME,
                    port=AURORA_PORT,
                    cursorclass=DictCursor if self.dict_cursor else pymysql.cursors.Cursor,
                    connect_timeout=10
                )
                self.cursor = self.connection.cursor()
                logger.info("Database connection established successfully")
            except Exception as e:
                logger.error(f"Error connecting to the database: {e}")
                raise
        
        return self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager, closing the database connection."""
        if exc_type:
            logger.error(f"Database error: {exc_type} - {exc_val}")
            if self.connection:
                self.connection.rollback()
        else:
            if self.connection:
                self.connection.commit()
        
        if self.cursor:
            self.cursor.close()
        
        if self.connection and self.should_close:
            self.connection.close()

# Campaign operations
def save_campaign(campaign_data: Dict[str, Any], cursor=None) -> bool:
    """
    Save a campaign to the database.
    
    Args:
        campaign_data (Dict[str, Any]): Campaign data from Facebook API
        cursor: Optional database cursor for batch operations
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        should_close = cursor is None
        conn = None
        
        if cursor is None:
            conn, cursor = get_connection()
        
        # Check if the campaign already exists
        cursor.execute(
            "SELECT id FROM campaigns WHERE id = %s",
            (campaign_data['id'],)
        )
        exists = cursor.fetchone()
        
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if exists:
            # Update existing campaign
            cursor.execute(
                """
                UPDATE campaigns
                SET name = %s, status = %s, daily_budget = %s, lifetime_budget = %s,
                start_time = %s, stop_time = %s, updated_time = %s
                WHERE id = %s
                """,
                (
                    campaign_data.get('name'),
                    campaign_data.get('status'),
                    campaign_data.get('daily_budget', 0),
                    campaign_data.get('lifetime_budget', 0),
                    campaign_data.get('start_time'),
                    campaign_data.get('stop_time'),
                    current_time,
                    campaign_data['id']
                )
            )
            logger.info(f"Updated campaign {campaign_data['id']} in database")
        else:
            # Insert new campaign
            cursor.execute(
                """
                INSERT INTO campaigns (
                    id, name, status, daily_budget, lifetime_budget,
                    start_time, stop_time, created_time, updated_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    campaign_data['id'],
                    campaign_data.get('name'),
                    campaign_data.get('status'),
                    campaign_data.get('daily_budget', 0),
                    campaign_data.get('lifetime_budget', 0),
                    campaign_data.get('start_time'),
                    campaign_data.get('stop_time'),
                    current_time,
                    current_time
                )
            )
            logger.info(f"Inserted campaign {campaign_data['id']} into database")
        
        if conn and should_close:
            conn.commit()
            
        return True
    except Exception as e:
        logger.error(f"Error saving campaign to database: {e}")
        if conn and should_close:
            conn.rollback()
        return False

def save_campaigns_batch(campaigns_data: List[Dict[str, Any]]) -> bool:
    """
    Сохранить пакет кампаний в базу данных, используя одно соединение.
    
    Args:
        campaigns_data (List[Dict[str, Any]]): Список данных кампаний из Facebook API
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    if not campaigns_data:
        return True
    
    try:
        conn, cursor = get_connection()
        
        for campaign_data in campaigns_data:
            save_campaign(campaign_data, cursor)
        
        conn.commit()
        logger.info(f"Saved batch of {len(campaigns_data)} campaigns to database")
        return True
    except Exception as e:
        logger.error(f"Error saving campaigns batch to database: {e}")
        if conn:
            conn.rollback()
        return False

def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a campaign from the database.
    
    Args:
        campaign_id (str): Campaign ID
        
    Returns:
        Optional[Dict[str, Any]]: Campaign data or None if not found
    """
    try:
        with DatabaseConnection() as cursor:
            cursor.execute(
                "SELECT * FROM campaigns WHERE id = %s",
                (campaign_id,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting campaign from database: {e}")
        return None

def get_all_campaigns() -> List[Dict[str, Any]]:
    """
    Get all campaigns from the database.
    
    Returns:
        List[Dict[str, Any]]: List of campaign data
    """
    try:
        with DatabaseConnection() as cursor:
            cursor.execute("SELECT * FROM campaigns")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting all campaigns from database: {e}")
        return []

# Ad Set operations
def save_ad_set(ad_set_data: Dict[str, Any], cursor=None) -> bool:
    """
    Save an ad set to the database.
    
    Args:
        ad_set_data (Dict[str, Any]): Ad set data from Facebook API
        cursor: Optional database cursor for batch operations
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        should_close = cursor is None
        conn = None
        
        if cursor is None:
            conn, cursor = get_connection()
        
        # Check if the ad set already exists
        cursor.execute(
            "SELECT id FROM ad_sets WHERE id = %s",
            (ad_set_data['id'],)
        )
        exists = cursor.fetchone()
        
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if exists:
            # Update existing ad set
            cursor.execute(
                """
                UPDATE ad_sets
                SET name = %s, campaign_id = %s, status = %s, daily_budget = %s,
                lifetime_budget = %s, targeting = %s, start_time = %s, end_time = %s,
                updated_time = %s
                WHERE id = %s
                """,
                (
                    ad_set_data.get('name'),
                    ad_set_data.get('campaign_id'),
                    ad_set_data.get('status'),
                    ad_set_data.get('daily_budget', 0),
                    ad_set_data.get('lifetime_budget', 0),
                    json.dumps(ad_set_data.get('targeting', {})),
                    ad_set_data.get('start_time'),
                    ad_set_data.get('end_time'),
                    current_time,
                    ad_set_data['id']
                )
            )
            logger.info(f"Updated ad set {ad_set_data['id']} in database")
        else:
            # Insert new ad set
            cursor.execute(
                """
                INSERT INTO ad_sets (
                    id, name, campaign_id, status, daily_budget, lifetime_budget,
                    targeting, start_time, end_time, created_time, updated_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ad_set_data['id'],
                    ad_set_data.get('name'),
                    ad_set_data.get('campaign_id'),
                    ad_set_data.get('status'),
                    ad_set_data.get('daily_budget', 0),
                    ad_set_data.get('lifetime_budget', 0),
                    json.dumps(ad_set_data.get('targeting', {})),
                    ad_set_data.get('start_time'),
                    ad_set_data.get('end_time'),
                    current_time,
                    current_time
                )
            )
            logger.info(f"Inserted ad set {ad_set_data['id']} into database")
        
        if conn and should_close:
            conn.commit()
            
        return True
    except Exception as e:
        logger.error(f"Error saving ad set to database: {e}")
        if conn and should_close:
            conn.rollback()
        return False

def save_ad_sets_batch(ad_sets_data: List[Dict[str, Any]]) -> bool:
    """
    Сохранить пакет групп объявлений в базу данных, используя одно соединение.
    
    Args:
        ad_sets_data (List[Dict[str, Any]]): Список данных групп объявлений из Facebook API
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    if not ad_sets_data:
        return True
    
    try:
        conn, cursor = get_connection()
        
        for ad_set_data in ad_sets_data:
            save_ad_set(ad_set_data, cursor)
        
        conn.commit()
        logger.info(f"Saved batch of {len(ad_sets_data)} ad sets to database")
        return True
    except Exception as e:
        logger.error(f"Error saving ad sets batch to database: {e}")
        if conn:
            conn.rollback()
        return False

def get_ad_set(ad_set_id: str) -> Optional[Dict[str, Any]]:
    """
    Get an ad set from the database.
    
    Args:
        ad_set_id (str): Ad set ID
        
    Returns:
        Optional[Dict[str, Any]]: Ad set data or None if not found
    """
    try:
        with DatabaseConnection() as cursor:
            cursor.execute(
                "SELECT * FROM ad_sets WHERE id = %s",
                (ad_set_id,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting ad set from database: {e}")
        return None

def get_all_ad_sets() -> List[Dict[str, Any]]:
    """
    Get all ad sets from the database.
    
    Returns:
        List[Dict[str, Any]]: List of ad set data
    """
    try:
        with DatabaseConnection() as cursor:
            cursor.execute("SELECT * FROM ad_sets")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting all ad sets from database: {e}")
        return []

# Ad operations
def save_ad(ad_data: Dict[str, Any], cursor=None) -> bool:
    """
    Save an ad to the database.
    
    Args:
        ad_data (Dict[str, Any]): Ad data from Facebook API
        cursor: Optional database cursor for batch operations
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        should_close = cursor is None
        conn = None
        
        if cursor is None:
            conn, cursor = get_connection()
        
        # Check if the ad already exists
        cursor.execute(
            "SELECT id FROM ads WHERE id = %s",
            (ad_data['id'],)
        )
        exists = cursor.fetchone()
        
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if exists:
            # Update existing ad
            cursor.execute(
                """
                UPDATE ads
                SET name = %s, ad_set_id = %s, status = %s, creative = %s,
                updated_time = %s
                WHERE id = %s
                """,
                (
                    ad_data.get('name'),
                    ad_data.get('adset_id'),
                    ad_data.get('status'),
                    json.dumps(ad_data.get('creative', {})),
                    current_time,
                    ad_data['id']
                )
            )
            logger.info(f"Updated ad {ad_data['id']} in database")
        else:
            # Insert new ad
            cursor.execute(
                """
                INSERT INTO ads (
                    id, name, ad_set_id, status, creative, created_time, updated_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ad_data['id'],
                    ad_data.get('name'),
                    ad_data.get('adset_id'),
                    ad_data.get('status'),
                    json.dumps(ad_data.get('creative', {})),
                    current_time,
                    current_time
                )
            )
            logger.info(f"Inserted ad {ad_data['id']} into database")
        
        if conn and should_close:
            conn.commit()
            
        return True
    except Exception as e:
        logger.error(f"Error saving ad to database: {e}")
        if conn and should_close:
            conn.rollback()
        return False

def save_ads_batch(ads_data: List[Dict[str, Any]]) -> bool:
    """
    Сохранить пакет объявлений в базу данных, используя одно соединение.
    
    Args:
        ads_data (List[Dict[str, Any]]): Список данных объявлений из Facebook API
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    if not ads_data:
        return True
    
    try:
        conn, cursor = get_connection()
        
        for ad_data in ads_data:
            save_ad(ad_data, cursor)
        
        conn.commit()
        logger.info(f"Saved batch of {len(ads_data)} ads to database")
        return True
    except Exception as e:
        logger.error(f"Error saving ads batch to database: {e}")
        if conn:
            conn.rollback()
        return False

def get_ad(ad_id: str) -> Optional[Dict[str, Any]]:
    """
    Get an ad from the database.
    
    Args:
        ad_id (str): Ad ID
        
    Returns:
        Optional[Dict[str, Any]]: Ad data or None if not found
    """
    try:
        with DatabaseConnection() as cursor:
            cursor.execute(
                "SELECT * FROM ads WHERE id = %s",
                (ad_id,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting ad from database: {e}")
        return None

def get_all_ads() -> List[Dict[str, Any]]:
    """
    Get all ads from the database.
    
    Returns:
        List[Dict[str, Any]]: List of ad data
    """
    try:
        with DatabaseConnection() as cursor:
            cursor.execute("SELECT * FROM ads")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting all ads from database: {e}")
        return []

# Ad Insights operations
def save_ad_insights(insights_data: Dict[str, Any]) -> bool:
    """
    Save ad insights to the database.
    
    Args:
        insights_data (Dict[str, Any]): Insights data from Facebook API
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with DatabaseConnection() as cursor:
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                """
                INSERT INTO ad_insights (
                    ad_id, ad_set_id, campaign_id, date_start, date_stop,
                    impressions, clicks, spend, reach, frequency,
                    cpc, cpm, ctr, unique_clicks, unique_ctr, created_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    insights_data.get('ad_id'),
                    insights_data.get('adset_id'),
                    insights_data.get('campaign_id'),
                    insights_data.get('date_start'),
                    insights_data.get('date_stop'),
                    insights_data.get('impressions'),
                    insights_data.get('clicks'),
                    insights_data.get('spend'),
                    insights_data.get('reach'),
                    insights_data.get('frequency'),
                    insights_data.get('cpc'),
                    insights_data.get('cpm'),
                    insights_data.get('ctr'),
                    insights_data.get('unique_clicks'),
                    insights_data.get('unique_ctr'),
                    current_time
                )
            )
            logger.info(f"Inserted insights for campaign {insights_data.get('campaign_id')} into database")
                
        return True
    except Exception as e:
        logger.error(f"Error saving ad insights to database: {e}")
        return False

# Configuration operations
def save_config(key: str, value: Any) -> bool:
    """
    Save a configuration key-value pair to the database.
    
    Args:
        key (str): Configuration key
        value (Any): Configuration value (will be converted to JSON)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with DatabaseConnection() as cursor:
            # Check if the key already exists
            cursor.execute(
                "SELECT config_key FROM config WHERE config_key = %s",
                (key,)
            )
            exists = cursor.fetchone()
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Convert value to JSON string if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            if exists:
                # Update existing config
                cursor.execute(
                    """
                    UPDATE config
                    SET config_value = %s, updated_time = %s
                    WHERE config_key = %s
                    """,
                    (value, current_time, key)
                )
                logger.info(f"Updated config {key} in database")
            else:
                # Insert new config
                cursor.execute(
                    """
                    INSERT INTO config (
                        config_key, config_value, created_time, updated_time
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (key, value, current_time, current_time)
                )
                logger.info(f"Inserted config {key} into database")
                
        return True
    except Exception as e:
        logger.error(f"Error saving config to database: {e}")
        return False

def get_config(key: str) -> Optional[Any]:
    """
    Get a configuration value from the database.
    
    Args:
        key (str): Configuration key
        
    Returns:
        Optional[Any]: Configuration value or None if not found
    """
    try:
        with DatabaseConnection() as cursor:
            cursor.execute(
                "SELECT config_value FROM config WHERE config_key = %s",
                (key,)
            )
            result = cursor.fetchone()
            
            if result:
                value = result['config_value']
                try:
                    # Try to parse as JSON
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Return as is if not valid JSON
                    return value
            
            return None
    except Exception as e:
        logger.error(f"Error getting config from database: {e}")
        return None

# Test function
def test_connection() -> bool:
    """
    Test the database connection.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Testing database connection to {AURORA_HOSTNAME}:{AURORA_PORT} as {AURORA_USERNAME}")
    
    try:
        with DatabaseConnection() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            logger.info(f"Database connection successful. MySQL version: {version['VERSION()']}")
            
            # Получение списка таблиц
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [list(table.values())[0] for table in tables]
            logger.info(f"Database tables: {', '.join(table_names) if table_names else 'No tables found'}")
            
            return True
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        logger.error(f"Database connection test failed: {e}")
        return False

if __name__ == "__main__":
    # Test the database connection
    if test_connection():
        print("Database connection test successful")
    else:
        print("Database connection test failed")
