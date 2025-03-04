#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для вывода информации о таблицах в базе данных.
"""

import logging
import pymysql
from dotenv import load_dotenv
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def show_table_structure():
    """Вывод структуры таблиц в базе данных."""
    load_dotenv()
    
    # Получение параметров подключения
    host = os.getenv('AURORA_HOST')
    port = int(os.getenv('AURORA_PORT', '3306'))
    user = os.getenv('AURORA_USERNAME')
    password = os.getenv('AURORA_PASSWORD')
    database = os.getenv('AURORA_DATABASE')
    
    logger.info(f"Подключение к базе данных {database} на хосте {host}:{port}")
    
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        logger.info("Успешное подключение к базе данных")
        
        with connection.cursor() as cursor:
            # Получение списка таблиц
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            table_names = [list(table.values())[0] for table in tables]
            logger.info(f"Таблицы в базе данных: {', '.join(table_names)}")
            
            # Для каждой таблицы вывести структуру
            for table_name in table_names:
                logger.info(f"\nСтруктура таблицы '{table_name}':")
                
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                
                for column in columns:
                    logger.info(f"  - {column['Field']}: {column['Type']} (Null: {column['Null']}, Key: {column['Key']}, Default: {column['Default']})")
                
                # Посмотрим несколько записей
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                
                if rows:
                    logger.info(f"  Примеры данных ({len(rows)} записей):")
                    for row in rows:
                        logger.info(f"    {row}")
                else:
                    logger.info("  Таблица пуста")
        
        connection.close()
        
    except Exception as e:
        logger.error(f"Ошибка при работе с базой данных: {str(e)}")

if __name__ == "__main__":
    show_table_structure()
