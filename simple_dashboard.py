#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Упрощенный веб-дашборд для отображения данных о рекламных кампаниях Facebook.
Использует данные, полученные из файла show_data.py.
"""

import os
import logging
import json
from datetime import datetime, timedelta
import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, render_template, request, jsonify
import sys

# Импортируем функции из show_data.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from show_data import get_db_connection, format_money

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


app = Flask(__name__)

def get_insights_data(days=7):
    """
    Получает данные о тратах из базы данных за указанное количество дней.
    
    Args:
        days (int): Количество дней для выборки данных
        
    Returns:
        list: Список словарей с данными о тратах
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Вычисляем дату начала периода
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Форматируем даты для SQL запроса
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"Получение данных о тратах за период с {start_date_str} по {end_date_str}")
        
        # SQL запрос для получения данных о тратах
        query = """
            SELECT 
                DATE_FORMAT(i.date_start, '%%Y-%%m-%%d') as date,
                c.name as campaign_name,
                i.impressions,
                i.clicks,
                i.spend
            FROM ad_insights i
            LEFT JOIN campaigns c ON i.campaign_id = c.id
            WHERE i.date_start >= %s AND i.date_start <= %s
            ORDER BY i.date_start DESC, c.name
        """
        
        cursor.execute(query, (start_date_str, end_date_str))
        results = cursor.fetchall()
        
        # Если результаты пустые, пробуем запрос без фильтрации по дате
        if not results:
            logger.warning("Данные не найдены. Пробуем запрос без фильтрации по дате.")
            query = """
                SELECT 
                    DATE_FORMAT(i.date_start, '%%Y-%%m-%%d') as date,
                    c.name as campaign_name,
                    i.impressions,
                    i.clicks,
                    i.spend
                FROM ad_insights i
                LEFT JOIN campaigns c ON i.campaign_id = c.id
                ORDER BY i.date_start DESC, c.name
                LIMIT 100
            """
            cursor.execute(query)
            results = cursor.fetchall()
        
        logger.info(f"Получено {len(results)} записей о тратах")
        
        # Обработка результатов
        insights = []
        for row in results:
            insights.append({
                'date': row['date'],
                'campaign_name': row['campaign_name'],
                'impressions': int(row['impressions']) if row['impressions'] else 0,
                'clicks': int(row['clicks']) if row['clicks'] else 0,
                'spend': float(row['spend']) if row['spend'] else 0,
                'ctr': (float(row['clicks']) / float(row['impressions']) * 100) if row['impressions'] and float(row['impressions']) > 0 else 0,
                'cpc': (float(row['spend']) / float(row['clicks'])) if row['clicks'] and float(row['clicks']) > 0 else 0
            })
        
        connection.close()
        return insights
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных о тратах: {e}")
        return []

def get_campaigns():
    """
    Получает список всех кампаний из базы данных.
    
    Returns:
        list: Список словарей с данными о кампаниях
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # SQL запрос для получения списка кампаний
        query = """
            SELECT 
                id,
                name,
                status,
                daily_budget,
                lifetime_budget
            FROM campaigns
            ORDER BY name
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        logger.info(f"Получено {len(results)} кампаний")
        
        # Обработка результатов
        campaigns = []
        for row in results:
            campaigns.append({
                'id': row['id'],
                'name': row['name'],
                'status': row['status'],
                'daily_budget': float(row['daily_budget']) if row['daily_budget'] else 0,
                'lifetime_budget': float(row['lifetime_budget']) if row['lifetime_budget'] else 0
            })
        
        connection.close()
        return campaigns
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка кампаний: {e}")
        return []

@app.route('/')
def index():
    """Главная страница дашборда."""
    return render_template('simple_index.html')

@app.route('/api/campaigns')
def api_campaigns():
    """API для получения списка кампаний."""
    campaigns = get_campaigns()
    return jsonify(campaigns)

@app.route('/api/insights')
def api_insights():
    """API для получения данных о тратах."""
    days = request.args.get('days', default=7, type=int)
    insights = get_insights_data(days)
    return jsonify(insights)

@app.route('/api/summary')
def api_summary():
    """API для получения сводных данных."""
    days = request.args.get('days', default=7, type=int)
    insights = get_insights_data(days)
    
    if not insights:
        return jsonify({
            'total_spend': 0,
            'total_impressions': 0,
            'total_clicks': 0,
            'avg_ctr': 0,
            'avg_cpc': 0
        })
    
    # Вычисляем сводные данные
    total_spend = sum(item['spend'] for item in insights)
    total_impressions = sum(item['impressions'] for item in insights)
    total_clicks = sum(item['clicks'] for item in insights)
    
    # Вычисляем средние значения
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    
    return jsonify({
        'total_spend': round(total_spend, 2),
        'total_impressions': total_impressions,
        'total_clicks': total_clicks,
        'avg_ctr': round(avg_ctr, 2),
        'avg_cpc': round(avg_cpc, 2)
    })

@app.route('/api/daily_spend')
def api_daily_spend():
    """API для получения данных о ежедневных тратах."""
    days = request.args.get('days', default=7, type=int)
    insights = get_insights_data(days)
    
    if not insights:
        return jsonify([])
    
    # Группируем данные по дате
    daily_data = {}
    for item in insights:
        date = item['date']
        if date not in daily_data:
            daily_data[date] = {
                'date': date,
                'spend': 0,
                'impressions': 0,
                'clicks': 0
            }
        
        daily_data[date]['spend'] += item['spend']
        daily_data[date]['impressions'] += item['impressions']
        daily_data[date]['clicks'] += item['clicks']
    
    # Преобразуем словарь в список и сортируем по дате
    daily_spend = list(daily_data.values())
    daily_spend.sort(key=lambda x: x['date'])
    
    return jsonify(daily_spend)

@app.route('/api/campaign_performance')
def api_campaign_performance():
    """API для получения данных о производительности кампаний."""
    days = request.args.get('days', default=7, type=int)
    insights = get_insights_data(days)
    
    if not insights:
        return jsonify([])
    
    # Группируем данные по кампаниям
    campaign_data = {}
    for item in insights:
        campaign = item['campaign_name']
        if campaign not in campaign_data:
            campaign_data[campaign] = {
                'campaign': campaign,
                'spend': 0,
                'impressions': 0,
                'clicks': 0
            }
        
        campaign_data[campaign]['spend'] += item['spend']
        campaign_data[campaign]['impressions'] += item['impressions']
        campaign_data[campaign]['clicks'] += item['clicks']
    
    # Вычисляем CTR и CPC для каждой кампании
    for campaign in campaign_data:
        data = campaign_data[campaign]
        data['ctr'] = (data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0
        data['cpc'] = (data['spend'] / data['clicks']) if data['clicks'] > 0 else 0
    
    # Преобразуем словарь в список и сортируем по расходам
    campaign_performance = list(campaign_data.values())
    campaign_performance.sort(key=lambda x: x['spend'], reverse=True)
    
    return jsonify(campaign_performance)

if __name__ == '__main__':
    # Создаем директорию для шаблонов, если она не существует
    os.makedirs('templates', exist_ok=True)
    
    # Запускаем приложение
    app.run(debug=True, host='0.0.0.0', port=5005)
