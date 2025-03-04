#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Генератор часовых отчетов.
"""

import logging
from datetime import datetime, timedelta

from facebook_ads_toolkit.reports.report_base import ReportBase

logger = logging.getLogger(__name__)

class HourlyReport(ReportBase):
    """Класс для генерации часовых отчетов."""
    
    def generate(self) -> str:
        """
        Генерация часового отчета.
        
        Returns:
            str: Текст отчета в формате Markdown
        """
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        previous_hour = now - timedelta(hours=1)
        
        # Получаем статистику
        current_stats = self._get_total_stats(now, now)
        previous_stats = self._get_total_stats(previous_hour, previous_hour)
        
        # Формируем отчет
        report = [
            "*⚡ Часовой отчет по рекламе*",
            f"_Время: {now.strftime('%H:%M %d.%m.%Y')}_\n"
        ]
        
        # Основные метрики
        report.extend([
            "*Текущий час:*",
            f"💰 Расходы: {self._format_currency(current_stats['total_spend'])} "
            f"{self._get_trend_indicator(current_stats['total_spend'], previous_stats['total_spend'])} "
            f"({self._format_change(current_stats['total_spend'], previous_stats['total_spend'])})",
            
            f"👥 Показы: {current_stats['total_impressions']:,} "
            f"{self._get_trend_indicator(current_stats['total_impressions'], previous_stats['total_impressions'])} "
            f"({self._format_change(current_stats['total_impressions'], previous_stats['total_impressions'])})",
            
            f"🖱 Клики: {current_stats['total_clicks']:,} "
            f"{self._get_trend_indicator(current_stats['total_clicks'], previous_stats['total_clicks'])} "
            f"({self._format_change(current_stats['total_clicks'], previous_stats['total_clicks'])})\n"
        ])
        
        # Эффективность
        report.extend([
            "*Эффективность:*",
            f"📈 CTR: {self._format_percentage(current_stats['avg_ctr'])} "
            f"{self._get_trend_indicator(current_stats['avg_ctr'], previous_stats['avg_ctr'])}",
            
            f"💵 CPC: {self._format_currency(current_stats['avg_cpc'])} "
            f"{self._get_trend_indicator(current_stats['avg_cpc'], previous_stats['avg_cpc'])}\n"
        ])
        
        # Конверсии
        if current_stats['total_conversions'] > 0:
            report.extend([
                "*Конверсии:*",
                f"🎯 Количество: {current_stats['total_conversions']:,} "
                f"{self._get_trend_indicator(current_stats['total_conversions'], previous_stats['total_conversions'])}",
                
                f"💸 Стоимость: {self._format_currency(current_stats['avg_cost_per_conversion'])} "
                f"{self._get_trend_indicator(current_stats['avg_cost_per_conversion'], previous_stats['avg_cost_per_conversion'])}\n"
            ])
        
        # Активные кампании
        campaigns = self._get_campaign_stats(now, now)
        if campaigns:
            report.append("*Активные кампании:*")
            for campaign in campaigns[:3]:  # Топ 3 кампании
                report.append(
                    f"📱 {campaign['campaign_name']}\n"
                    f"   Расходы: {self._format_currency(campaign['spend'])}\n"
                    f"   CTR: {self._format_percentage(campaign['ctr'])}"
                )
        
        return "\n".join(report)
