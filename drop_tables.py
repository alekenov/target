#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

def drop_tables():
    """Удаляет таблицы из базы данных."""
    try:
        # Подключение к базе данных
        connection = pymysql.connect(
            host=os.getenv('AURORA_HOST'),
            user=os.getenv('AURORA_MASTER_USERNAME'),
            password=os.getenv('AURORA_MASTER_PASSWORD'),
            database=os.getenv('AURORA_DATABASE_NAME'),
            port=int(os.getenv('AURORA_PORT', 3306)),
            cursorclass=DictCursor,
            connect_timeout=10
        )
        
        cursor = connection.cursor()
        
        # Удаляем таблицы в правильном порядке (из-за внешних ключей)
        tables = ['ad_insights', 'ads', 'ad_sets', 'campaigns', 'config']
        
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"Таблица {table} успешно удалена")
            except Exception as e:
                logger.error(f"Ошибка при удалении таблицы {table}: {str(e)}")
        
        connection.commit()
        logger.info("Все таблицы успешно удалены")
        
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {str(e)}")
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
    drop_tables()
