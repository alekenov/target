#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import pymysql
from pymysql.cursors import DictCursor
from tabulate import tabulate
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# В среде Lambda не используем dotenv, переменные окружения уже установлены
# Проверяем, находимся ли мы в среде Lambda
is_lambda = 'AWS_LAMBDA_FUNCTION_NAME' in os.environ

# Если не в Lambda и есть модуль dotenv, загружаем переменные окружения из .env
if not is_lambda:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Переменные окружения загружены из .env файла")
    except ImportError:
        logger.warning("Модуль dotenv не найден, используем переменные окружения системы")

def format_money(value):
    """Форматирует денежные значения."""
    if value is None:
        return "0.00"
    return f"{float(value):.2f}"

def get_db_connection():
    """
    Создает и возвращает соединение с базой данных.
    
    Returns:
        pymysql.Connection: Объект соединения с базой данных
    """
    try:
        connection = pymysql.connect(
            host=os.getenv('AURORA_HOST'),
            user=os.getenv('AURORA_MASTER_USERNAME'),
            password=os.getenv('AURORA_MASTER_PASSWORD'),
            database=os.getenv('AURORA_DATABASE_NAME'),
            port=int(os.getenv('AURORA_PORT', 3306)),
            connect_timeout=10,
            cursorclass=DictCursor,
            charset='utf8mb4',
            collation='utf8mb4_0900_ai_ci'
        )
        logger.info(f"Соединение с базой данных установлено: {os.getenv('AURORA_HOST')}:{os.getenv('AURORA_PORT')}")
        return connection
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}")
        raise

def show_insights_data():
    """
    Показывает данные о тратах из базы данных.
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Получаем данные о тратах
        cursor.execute("""
            SELECT 
                DATE_FORMAT(i.date_start, '%Y-%m-%d') as date,
                c.name as campaign_name,
                i.impressions,
                i.clicks,
                i.spend,
                ROUND(i.ctr, 2) as ctr,
                ROUND(i.cpc, 2) as cpc
            FROM ad_insights i
            LEFT JOIN campaigns c ON i.campaign_id = c.id
            ORDER BY i.date_start DESC, c.name
            LIMIT 100
        """)
        
        data = cursor.fetchall()
        
        if data:
            # Группируем данные по кампаниям
            campaigns = {}
            
            for row in data:
                campaign_name = row['campaign_name']
                if campaign_name not in campaigns:
                    campaigns[campaign_name] = {
                        'data': [],
                        'total_spend': 0,
                        'total_impressions': 0,
                        'total_clicks': 0
                    }
                
                # Добавляем данные в таблицу
                table_row = [
                    row['date'],
                    row['campaign_name'],
                    f"{row['impressions']:,}",
                    f"{row['clicks']:,}",
                    format_money(row['spend']),
                    f"{row['ctr']:.2f}",
                    format_money(row['cpc'])
                ]
                campaigns[campaign_name]['data'].append(table_row)
                
                # Суммируем общие показатели
                campaigns[campaign_name]['total_spend'] += float(row['spend']) if row['spend'] else 0
                campaigns[campaign_name]['total_impressions'] += int(row['impressions']) if row['impressions'] else 0
                campaigns[campaign_name]['total_clicks'] += int(row['clicks']) if row['clicks'] else 0
            
            # Выводим данные по каждой кампании
            headers = ['Дата', 'Кампания', 'Показы', 'Клики', 'Траты ($)', 'CTR (%)', 'CPC ($)']
            
            for campaign_name, data in campaigns.items():
                print(f"\n=== Кампания: {campaign_name} ===")
                print(tabulate(data['data'], headers=headers, tablefmt='grid'))
                
                # Выводим итоги
                total_spend = data['total_spend']
                total_impressions = data['total_impressions']
                total_clicks = data['total_clicks']
                
                print(f"\nИтого по кампании:")
                print(f"Всего записей: {len(data['data'])}")
                print(f"Общие траты: ${total_spend:.2f}")
                print(f"Всего показов: {total_impressions:,}")
                print(f"Всего кликов: {total_clicks:,}")
                
                if total_impressions > 0:
                    print(f"Средний CTR: {(total_clicks/total_impressions*100):.2f}%")
                if total_clicks > 0:
                    print(f"Средний CPC: ${(total_spend/total_clicks):.2f}")
            
        else:
            print("Данных о тратах пока нет в базе данных")
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных из базы: {type(e)} - {str(e)}")
        raise
    finally:
        if 'connection' in locals():
            connection.close()

def show_campaigns():
    """
    Показывает список кампаний из базы данных.
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Получаем список кампаний
        cursor.execute("""
            SELECT 
                id,
                name,
                status,
                daily_budget,
                lifetime_budget
            FROM campaigns
            ORDER BY name
        """)
        
        data = cursor.fetchall()
        
        if data:
            # Подготавливаем данные для таблицы
            table_data = []
            for row in data:
                daily_budget = format_money(row['daily_budget']) if row['daily_budget'] else '-'
                lifetime_budget = format_money(row['lifetime_budget']) if row['lifetime_budget'] else '-'
                
                status_text = row['status']
                if status_text == 'ACTIVE':
                    status_text = 'Активна'
                elif status_text == 'PAUSED':
                    status_text = 'Приостановлена'
                elif status_text == 'ARCHIVED':
                    status_text = 'Архивирована'
                
                table_row = [
                    row['id'],
                    row['name'],
                    status_text,
                    daily_budget,
                    lifetime_budget
                ]
                table_data.append(table_row)
            
            # Выводим таблицу
            headers = ['ID', 'Название', 'Статус', 'Дневной бюджет ($)', 'Общий бюджет ($)']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            print(f"\nВсего кампаний: {len(data)}")
            
        else:
            print("Кампаний пока нет в базе данных")
            
    except Exception as e:
        logger.error(f"Ошибка при получении списка кампаний: {type(e)} - {str(e)}")
        raise
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    # Загружаем переменные окружения
    if not is_lambda:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
    
    # Выводим данные
    print("=== Список кампаний ===")
    show_campaigns()
    
    print("\n=== Данные о тратах ===")
    show_insights_data()
