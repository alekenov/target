#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from dotenv import load_dotenv
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

def format_money(value):
    """Форматирует денежные значения."""
    if value is None:
        return "0.00"
    return f"{float(value):.2f}"

def get_db_connection():
    return pymysql.connect(
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
                a.name as ad_name,
                i.impressions,
                i.clicks,
                i.spend,
                ROUND(i.ctr, 2) as ctr,
                ROUND(i.cpc, 2) as cpc,
                i.conversations,
                i.cost_per_conversation,
                i.link_clicks,
                i.cost_per_link_click,
                c.objective
            FROM ad_insights i FORCE INDEX (PRIMARY)
            LEFT JOIN ads a FORCE INDEX (PRIMARY) ON CAST(i.ad_id AS CHAR) = CAST(a.id AS CHAR)
            LEFT JOIN ad_sets s FORCE INDEX (PRIMARY) ON CAST(a.ad_set_id AS CHAR) = CAST(s.id AS CHAR)
            LEFT JOIN campaigns c FORCE INDEX (PRIMARY) ON CAST(s.campaign_id AS CHAR) = CAST(c.id AS CHAR)
            ORDER BY i.date_start DESC, c.name, a.name
        """)
        
        data = cursor.fetchall()
        
        if data:
            # Группируем данные по целям кампаний
            campaigns_by_objective = {}
            
            for row in data:
                objective = row['objective']
                if objective not in campaigns_by_objective:
                    campaigns_by_objective[objective] = {
                        'data': [],
                        'total_spend': 0,
                        'total_impressions': 0,
                        'total_clicks': 0,
                        'total_conversations': 0,
                        'total_link_clicks': 0
                    }
                
                # Определяем метрику в зависимости от цели
                table_row = [
                    row['date'],
                    row['campaign_name'],
                    row['ad_name'],
                    f"{row['impressions']:,}",
                    f"{row['clicks']:,}",
                    format_money(row['spend']),
                    f"{row['ctr']:.2f}",
                    format_money(row['cpc']),
                    f"{row['conversations']:,}",
                    f"{row['link_clicks']:,}"
                ]
                campaigns_by_objective[objective]['data'].append(table_row)
                
                # Суммируем общие показатели
                campaigns_by_objective[objective]['total_spend'] += row['spend'] or 0
                campaigns_by_objective[objective]['total_impressions'] += row['impressions'] or 0
                campaigns_by_objective[objective]['total_clicks'] += row['clicks'] or 0
                campaigns_by_objective[objective]['total_conversations'] += row['conversations'] or 0
                campaigns_by_objective[objective]['total_link_clicks'] += row['link_clicks'] or 0
            
            # Выводим данные по каждой цели
            headers = ['Дата', 'Кампания', 'Объявление', 'Показы', 'Клики', 'Траты ($)', 'CTR (%)', 'CPC ($)', 'Переписки', 'Переходы']
            
            for objective, data in campaigns_by_objective.items():
                if objective == 'MESSAGES':
                    print("\n=== Кампании для переписок ===")
                elif objective == 'LINK_CLICKS':
                    print("\n=== Кампании для переходов ===")
                else:
                    print(f"\n=== Кампании с целью {objective} ===")
                
                print(tabulate(data['data'], headers=headers, tablefmt='grid'))
                
                # Выводим итоги
                total_spend = data['total_spend']
                total_impressions = data['total_impressions']
                total_clicks = data['total_clicks']
                total_conversations = data['total_conversations']
                total_link_clicks = data['total_link_clicks']
                
                print(f"\nИтого по цели:")
                print(f"Всего записей: {len(data['data'])}")
                print(f"Общие траты: ${total_spend:.2f}")
                print(f"Всего показов: {total_impressions:,}")
                print(f"Всего кликов: {total_clicks:,}")
                print(f"Всего переписок: {total_conversations:,}")
                print(f"Всего переходов: {total_link_clicks:,}")
                
                if total_impressions > 0:
                    print(f"Средний CTR: {(total_clicks/total_impressions*100):.2f}%")
                if total_clicks > 0:
                    print(f"Средний CPC: ${(total_spend/total_clicks):.2f}")
                if total_conversations > 0:
                    print(f"Средняя стоимость переписки: ${(total_spend/total_conversations):.2f}")
                if total_link_clicks > 0:
                    print(f"Средняя стоимость перехода: ${(total_spend/total_link_clicks):.2f}")
            
        else:
            print("Данных о тратах пока нет в базе данных")
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных из базы: {type(e)} - {str(e)}")
        raise
    finally:
        if 'connection' in locals():
            connection.close()

def show_summary_by_objective(data):
    """
    Показывает сводку по целям рекламных кампаний.
    """
    # Группируем данные по целям
    objectives = {}
    
    for row in data:
        objective = row['objective']
        if objective not in objectives:
            objectives[objective] = {
                'count': 0,
                'spend': 0,
                'impressions': 0,
                'clicks': 0,
                'conversations': 0,
                'cost_per_conversation': 0,
                'link_clicks': 0,
                'cost_per_link_click': 0
            }
        
        objectives[objective]['count'] += 1
        objectives[objective]['spend'] += float(row['spend'])
        objectives[objective]['impressions'] += int(row['impressions'])
        objectives[objective]['clicks'] += int(row['clicks'])
        objectives[objective]['conversations'] += int(row['conversations'])
        objectives[objective]['link_clicks'] += int(row['link_clicks'])
    
    # Выводим статистику по каждой цели
    for objective, stats in objectives.items():
        print(f"\nИтого по цели: {objective}")
        print(f"Всего записей: {stats['count']}")
        print(f"Общие траты: ${stats['spend']:.2f}")
        print(f"Всего показов: {stats['impressions']:,}")
        print(f"Всего кликов: {stats['clicks']:,}")
        print(f"Всего переписок: {stats['conversations']:,}")
        print(f"Всего переходов: {stats['link_clicks']:,}")
        
        # Считаем средние значения
        if stats['clicks'] > 0:
            avg_ctr = (stats['clicks'] / stats['impressions']) * 100
            avg_cpc = stats['spend'] / stats['clicks']
            print(f"Средний CTR: {avg_ctr:.2f}%")
            print(f"Средний CPC: ${avg_cpc:.2f}")
        
        if stats['conversations'] > 0:
            avg_cost_per_conversation = stats['spend'] / stats['conversations']
            print(f"Средняя стоимость переписки: ${avg_cost_per_conversation:.2f}")
            
        if stats['link_clicks'] > 0:
            avg_cost_per_link_click = stats['spend'] / stats['link_clicks']
            print(f"Средняя стоимость перехода: ${avg_cost_per_link_click:.2f}")

if __name__ == "__main__":
    # Загружаем переменные окружения
    load_dotenv()
    show_insights_data()
