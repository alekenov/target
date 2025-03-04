#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Генератор ежедневных отчетов.
"""

import logging
from datetime import datetime, timedelta

from facebook_ads_toolkit.reports.report_base import ReportBase

logger = logging.getLogger(__name__)

class DailyReport(ReportBase):
    """Класс для генерации ежедневных отчетов."""
    
    def generate(self) -> str:
        """
        Генерация ежедневного отчета.
        
        Returns:
            str: Текст отчета в формате Markdown
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        # Получаем статистику
        today_stats = self._get_total_stats(today, today)
        yesterday_stats = self._get_total_stats(yesterday, yesterday)
        week_stats = self._get_total_stats(week_ago, today)
        
        # Формируем отчет
        report = [
            "*📊 Ежедневный отчет по рекламе*",
            f"_Дата: {today.strftime('%d.%m.%Y')}_\n"
        ]
        
        # Основные метрики
        report.extend([
            "*Основные показатели:*",
            f"💰 Расходы: {self._format_currency(today_stats['total_spend'])} "
            f"{self._get_trend_indicator(today_stats['total_spend'], yesterday_stats['total_spend'])} "
            f"({self._format_change(today_stats['total_spend'], yesterday_stats['total_spend'])})",
            
            f"👥 Показы: {today_stats['total_impressions']:,} "
            f"{self._get_trend_indicator(today_stats['total_impressions'], yesterday_stats['total_impressions'])} "
            f"({self._format_change(today_stats['total_impressions'], yesterday_stats['total_impressions'])})",
            
            f"🖱 Клики: {today_stats['total_clicks']:,} "
            f"{self._get_trend_indicator(today_stats['total_clicks'], yesterday_stats['total_clicks'])} "
            f"({self._format_change(today_stats['total_clicks'], yesterday_stats['total_clicks'])})\n"
        ])
        
        # Эффективность
        report.extend([
            "*Эффективность:*",
            f"📈 CTR: {self._format_percentage(today_stats['avg_ctr'])} "
            f"{self._get_trend_indicator(today_stats['avg_ctr'], yesterday_stats['avg_ctr'])}",
            
            f"💵 CPC: {self._format_currency(today_stats['avg_cpc'])} "
            f"{self._get_trend_indicator(today_stats['avg_cpc'], yesterday_stats['avg_cpc'])}\n"
        ])
        
        # Конверсии
        if today_stats['total_conversions'] > 0:
            report.extend([
                "*Конверсии:*",
                f"🎯 Количество: {today_stats['total_conversions']:,} "
                f"{self._get_trend_indicator(today_stats['total_conversions'], yesterday_stats['total_conversions'])}",
                
                f"💸 Стоимость: {self._format_currency(today_stats['avg_cost_per_conversion'])} "
                f"{self._get_trend_indicator(today_stats['avg_cost_per_conversion'], yesterday_stats['avg_cost_per_conversion'])}\n"
            ])
        
        # Статистика по кампаниям
        campaigns = self._get_campaign_stats(today, today)
        if campaigns:
            report.append("*Статистика по кампаниям:*")
            for campaign in campaigns[:5]:  # Топ 5 кампаний
                report.append(
                    f"📱 {campaign['campaign_name']}\n"
                    f"   Расходы: {self._format_currency(campaign['spend'])}\n"
                    f"   Показы: {campaign['impressions']:,}\n"
                    f"   CTR: {self._format_percentage(campaign['ctr'])}"
                )
        
        return "\n".join(report)
