#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Тестирование подключения к Aurora MySQL.
"""

import logging
import time
import pymysql
from dotenv import load_dotenv
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_db_connection():
    """Тестирование подключения к базе данных."""
    load_dotenv()
    
    # Получение параметров подключения
    host = os.getenv('AURORA_HOST')
    port = int(os.getenv('AURORA_PORT', '3306'))
    user = os.getenv('AURORA_USERNAME')
    password = os.getenv('AURORA_PASSWORD')
    database = os.getenv('AURORA_DATABASE')
    
    logger.info(f"Попытка подключения к базе данных MySQL на хосте {host}:{port}")
    logger.info(f"Пользователь: {user}, База данных: {database}")
    
    # Пробуем подключиться с несколькими попытками
    max_retries = 3
    retry_delay = 2  # секунды
    
    for attempt in range(1, max_retries + 1):
        try:
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=10
            )
            
            logger.info("Успешное подключение к базе данных")
            
            # Проверяем доступность таблиц
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                table_names = [table[0] for table in tables]
                logger.info(f"Доступные таблицы: {', '.join(table_names) if table_names else 'Таблицы отсутствуют'}")
                
                # Пробуем выполнить простой запрос
                if 'campaigns' in table_names:
                    cursor.execute("SELECT COUNT(*) FROM campaigns")
                    count = cursor.fetchone()[0]
                    logger.info(f"Количество кампаний в базе данных: {count}")
            
            connection.close()
            return True
            
        except pymysql.MySQLError as e:
            error_code = e.args[0]
            error_message = e.args[1] if len(e.args) > 1 else str(e)
            
            logger.error(f"Ошибка подключения к базе данных (попытка {attempt}/{max_retries}): "
                         f"Код {error_code} - {error_message}")
            
            if attempt < max_retries:
                logger.info(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Увеличиваем время ожидания перед следующей попыткой
            else:
                logger.error("Все попытки подключения к базе данных исчерпаны")
                
                # Проверяем доступность хоста
                import subprocess
                logger.info(f"Проверка доступности хоста {host}...")
                try:
                    result = subprocess.run(['ping', '-c', '3', host], 
                                         capture_output=True, text=True)
                    logger.info(f"Результат ping:\n{result.stdout}")
                except Exception as ping_error:
                    logger.error(f"Ошибка при выполнении команды ping: {str(ping_error)}")
                
    return False

if __name__ == "__main__":
    test_db_connection()
