#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Базовый класс для генерации отчетов.
"""

import logging
from datetime import datetime, timedelta

from facebook_ads_toolkit.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ReportBase:
    """Базовый класс для всех отчетов."""
    
    def __init__(self):
        """Инициализация базового отчета."""
        self.db_manager = DatabaseManager()
        
    def _format_currency(self, value: float) -> str:
        """Форматирование денежных значений."""
        return f"{value:.2f} ₽"
        
    def _format_percentage(self, value: float) -> str:
        """Форматирование процентов."""
        return f"{value:.2f}%"
        
    def _get_trend_indicator(self, current: float, previous: float) -> str:
        """
        Получение индикатора тренда.
        
        Args:
            current: Текущее значение
            previous: Предыдущее значение
            
        Returns:
            str: Индикатор тренда (▲, ▼ или →)
        """
        if previous == 0:
            return "→"
        change = ((current - previous) / previous) * 100
        if abs(change) < 1:  # Изменение менее 1%
            return "→"
        return "▲" if change > 0 else "▼"
        
    def _format_change(self, current: float, previous: float) -> str:
        """
        Форматирование изменения значения.
        
        Args:
            current: Текущее значение
            previous: Предыдущее значение
            
        Returns:
            str: Отформатированное изменение со знаком
        """
        if previous == 0:
            return "+∞%" if current > 0 else "0%"
        change = ((current - previous) / previous) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.1f}%"
        
    def _get_campaign_stats(self, start_date: datetime, end_date: datetime) -> dict:
        """
        Получение статистики по кампаниям за период.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            dict: Статистика по кампаниям
        """
        query = """
            SELECT 
                c.name as campaign_name,
                SUM(i.impressions) as impressions,
                SUM(i.clicks) as clicks,
                SUM(i.spend) as spend,
                AVG(i.ctr) as ctr,
                AVG(i.cpc) as cpc,
                SUM(i.conversations) as conversations,
                AVG(i.cost_per_conversation) as cost_per_conversion
            FROM campaigns c
            JOIN ad_sets ads ON c.id = ads.campaign_id
            JOIN ads a ON ads.id = a.ad_set_id
            JOIN ad_insights i ON a.id = i.ad_id
            WHERE i.date_start BETWEEN %s AND %s
            GROUP BY c.id, c.name
            ORDER BY spend DESC
        """
        
        with self.db_manager.connection() as (conn, cursor):
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            
        return results
        
    def _get_total_stats(self, start_date: datetime, end_date: datetime) -> dict:
        """
        Получение общей статистики за период.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            dict: Общая статистика
        """
        query = """
            SELECT 
                SUM(impressions) as total_impressions,
                SUM(clicks) as total_clicks,
                SUM(spend) as total_spend,
                AVG(ctr) as avg_ctr,
                AVG(cpc) as avg_cpc,
                SUM(conversations) as total_conversions,
                AVG(cost_per_conversation) as avg_cost_per_conversion
            FROM ad_insights
            WHERE date_start BETWEEN %s AND %s
        """
        
        with self.db_manager.connection() as (conn, cursor):
            cursor.execute(query, (start_date, end_date))
            result = cursor.fetchone()
            
        return result
        
    def generate(self) -> str:
        """
        Генерация отчета. Должна быть переопределена в дочерних классах.
        
        Returns:
            str: Текст отчета
        """
        raise NotImplementedError("Метод generate() должен быть переопределен")
