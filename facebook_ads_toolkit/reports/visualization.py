"""
Модуль для визуализации данных в отчетах.
Поддерживает создание различных типов графиков и диаграмм для анализа рекламных данных.
"""

import os
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union

from ..utils.data_handlers import format_currency, format_number

logger = logging.getLogger(__name__)

class ChartGenerator:
    """Класс для создания визуализаций данных."""
    
    def __init__(self, output_dir: str = "reports"):
        """
        Инициализация генератора графиков.
        
        Args:
            output_dir: Директория для сохранения графиков
        """
        self.output_dir = output_dir
        
        # Создаем директорию для графиков, если она не существует
        os.makedirs(os.path.join(output_dir, "charts"), exist_ok=True)
        
        # Настраиваем стиль для графиков
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Настраиваем поддержку кириллицы
        plt.rcParams['font.family'] = 'DejaVu Sans'
    
    def _create_chart_dir(self, report_id: str) -> str:
        """
        Создание директории для графиков отчета.
        
        Args:
            report_id: Идентификатор отчета
            
        Returns:
            str: Путь к директории для графиков
        """
        chart_dir = os.path.join(self.output_dir, "charts", report_id)
        os.makedirs(chart_dir, exist_ok=True)
        return chart_dir
    
    def _money_formatter(self, x, pos):
        """Форматирование денежных значений для осей графика."""
        return format_currency(x)
    
    def _percent_formatter(self, x, pos):
        """Форматирование процентных значений для осей графика."""
        return f"{x:.1f}%"
    
    def generate_spend_chart(self, 
                          data: Dict[str, Any], 
                          report_id: str,
                          top_n: int = 5,
                          title: str = "Расходы по кампаниям") -> str:
        """
        Создание графика расходов по кампаниям.
        
        Args:
            data: Данные для визуализации
            report_id: Идентификатор отчета
            top_n: Количество кампаний для отображения
            title: Заголовок графика
            
        Returns:
            str: Путь к сохраненному графику
        """
        try:
            # Создаем директорию для графиков
            chart_dir = self._create_chart_dir(report_id)
            
            # Получаем данные о кампаниях
            campaign_performance = data.get("campaign_performance", {})
            top_campaigns_by_spend = campaign_performance.get("top_campaigns_by_spend", [])
            
            # Проверяем наличие данных
            if not top_campaigns_by_spend:
                logger.warning("Нет данных о расходах по кампаниям для создания графика")
                return ""
            
            # Ограничиваем количество кампаний для отображения
            campaigns = top_campaigns_by_spend[:top_n]
            
            # Подготавливаем данные для графика
            names = [campaign.get("name", f"Кампания {i+1}")[:20] for i, campaign in enumerate(campaigns)]
            spends = [campaign.get("spend", 0) for campaign in campaigns]
            
            # Создаем график
            plt.figure(figsize=(10, 6))
            bars = plt.bar(names, spends, color='#4267B2')
            
            # Настраиваем оси
            plt.ylabel('Расходы')
            plt.xlabel('Кампании')
            plt.title(title)
            
            # Форматируем значения на оси Y
            plt.gca().yaxis.set_major_formatter(FuncFormatter(self._money_formatter))
            
            # Поворачиваем подписи по оси X для лучшей читаемости
            plt.xticks(rotation=30, ha='right')
            
            # Добавляем подписи значений над столбцами
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        format_currency(height),
                        ha='center', va='bottom', rotation=0)
            
            plt.tight_layout()
            
            # Сохраняем график
            chart_path = os.path.join(chart_dir, f"spend_chart.png")
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            logger.info(f"График расходов по кампаниям успешно создан: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании графика расходов: {str(e)}")
            return ""
    
    def generate_ctr_chart(self, 
                        data: Dict[str, Any], 
                        report_id: str,
                        top_n: int = 5,
                        title: str = "CTR по кампаниям") -> str:
        """
        Создание графика CTR по кампаниям.
        
        Args:
            data: Данные для визуализации
            report_id: Идентификатор отчета
            top_n: Количество кампаний для отображения
            title: Заголовок графика
            
        Returns:
            str: Путь к сохраненному графику
        """
        try:
            # Создаем директорию для графиков
            chart_dir = self._create_chart_dir(report_id)
            
            # Получаем данные о кампаниях
            campaign_performance = data.get("campaign_performance", {})
            top_campaigns_by_ctr = campaign_performance.get("top_campaigns_by_ctr", [])
            
            # Проверяем наличие данных
            if not top_campaigns_by_ctr:
                logger.warning("Нет данных о CTR по кампаниям для создания графика")
                return ""
            
            # Ограничиваем количество кампаний для отображения
            campaigns = top_campaigns_by_ctr[:top_n]
            
            # Подготавливаем данные для графика
            names = [campaign.get("name", f"Кампания {i+1}")[:20] for i, campaign in enumerate(campaigns)]
            ctrs = [campaign.get("ctr", 0) for campaign in campaigns]
            
            # Создаем график
            plt.figure(figsize=(10, 6))
            bars = plt.bar(names, ctrs, color='#4267B2')
            
            # Настраиваем оси
            plt.ylabel('CTR, %')
            plt.xlabel('Кампании')
            plt.title(title)
            
            # Форматируем значения на оси Y
            plt.gca().yaxis.set_major_formatter(FuncFormatter(self._percent_formatter))
            
            # Поворачиваем подписи по оси X для лучшей читаемости
            plt.xticks(rotation=30, ha='right')
            
            # Добавляем подписи значений над столбцами
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f"{height:.2f}%",
                        ha='center', va='bottom', rotation=0)
            
            plt.tight_layout()
            
            # Сохраняем график
            chart_path = os.path.join(chart_dir, f"ctr_chart.png")
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            logger.info(f"График CTR по кампаниям успешно создан: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании графика CTR: {str(e)}")
            return ""
    
    def generate_metrics_trend_chart(self, 
                                  data: Dict[str, Any], 
                                  report_id: str,
                                  metric: str = "ctr",
                                  title: str = "Динамика CTR") -> str:
        """
        Создание графика динамики метрики по времени.
        
        Args:
            data: Данные для визуализации
            report_id: Идентификатор отчета
            metric: Метрика для отображения (ctr, cpc, spend)
            title: Заголовок графика
            
        Returns:
            str: Путь к сохраненному графику
        """
        try:
            # Создаем директорию для графиков
            chart_dir = self._create_chart_dir(report_id)
            
            # Получаем данные о трендах
            trends = data.get("trends", {})
            metric_data = trends.get(f"{metric}_trend", [])
            
            # Проверяем наличие данных
            if not metric_data:
                logger.warning(f"Нет данных о динамике {metric} для создания графика")
                return ""
            
            # Подготавливаем данные для графика
            dates = [datetime.fromisoformat(item.get("date")) for item in metric_data if "date" in item]
            values = [item.get("value", 0) for item in metric_data if "value" in item]
            
            # Проверяем соответствие данных
            if len(dates) != len(values) or not dates:
                logger.warning(f"Некорректные данные о динамике {metric} для создания графика")
                return ""
            
            # Создаем график
            plt.figure(figsize=(12, 6))
            plt.plot(dates, values, marker='o', linestyle='-', color='#4267B2', linewidth=2)
            
            # Настраиваем оси
            plt.ylabel(metric.upper())
            plt.xlabel('Дата')
            plt.title(title)
            
            # Форматируем значения на оси Y в зависимости от метрики
            if metric == "ctr":
                plt.gca().yaxis.set_major_formatter(FuncFormatter(self._percent_formatter))
            elif metric in ["cpc", "spend"]:
                plt.gca().yaxis.set_major_formatter(FuncFormatter(self._money_formatter))
            
            # Форматируем ось X для отображения дат
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            
            # Добавляем сетку
            plt.grid(True, alpha=0.3)
            
            # Добавляем подписи значений
            for i, (date, value) in enumerate(zip(dates, values)):
                if i % max(1, len(dates) // 10) == 0:  # Показываем каждую 10-ю точку или все, если их мало
                    if metric == "ctr":
                        label = f"{value:.2f}%"
                    elif metric in ["cpc", "spend"]:
                        label = format_currency(value)
                    else:
                        label = f"{value:.2f}"
                        
                    plt.annotate(label, (date, value), 
                                textcoords="offset points", 
                                xytext=(0, 10), 
                                ha='center')
            
            plt.tight_layout()
            
            # Сохраняем график
            chart_path = os.path.join(chart_dir, f"{metric}_trend_chart.png")
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            logger.info(f"График динамики {metric} успешно создан: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании графика динамики {metric}: {str(e)}")
            return ""
    
    def generate_ad_comparison_chart(self, 
                                  data: Dict[str, Any], 
                                  report_id: str,
                                  metric: str = "ctr",
                                  title: str = "Сравнение CTR объявлений") -> str:
        """
        Создание графика сравнения объявлений по выбранной метрике.
        
        Args:
            data: Данные для визуализации
            report_id: Идентификатор отчета
            metric: Метрика для сравнения (ctr, cpc, spend)
            title: Заголовок графика
            
        Returns:
            str: Путь к сохраненному графику
        """
        try:
            # Создаем директорию для графиков
            chart_dir = self._create_chart_dir(report_id)
            
            # Получаем данные об объявлениях
            ads = data.get("ads", [])
            
            # Проверяем наличие данных
            if not ads or len(ads) < 2:
                logger.warning("Недостаточно данных для сравнения объявлений")
                return ""
            
            # Подготавливаем данные для графика
            names = [ad.get("name", f"Объявление {i+1}")[:25] for i, ad in enumerate(ads)]
            values = [ad.get(metric, 0) for ad in ads]
            
            # Создаем график
            plt.figure(figsize=(10, 6))
            
            # Выбираем цвет в зависимости от метрики
            color = '#4267B2'  # Цвет Facebook по умолчанию
            if metric == 'ctr':
                color = '#36A2EB'  # Синий для CTR
            elif metric == 'cpc':
                color = '#FF6384'  # Красный для CPC
            elif metric == 'spend':
                color = '#4BC0C0'  # Зеленоватый для расходов
            
            bars = plt.bar(names, values, color=color)
            
            # Настраиваем оси
            metric_label = metric.upper()
            if metric == "ctr":
                metric_label = "CTR, %"
            elif metric == "cpc":
                metric_label = "Стоимость клика"
            elif metric == "spend":
                metric_label = "Расходы"
            
            plt.ylabel(metric_label)
            plt.xlabel('Объявления')
            plt.title(title)
            
            # Форматируем значения на оси Y в зависимости от метрики
            if metric == "ctr":
                plt.gca().yaxis.set_major_formatter(FuncFormatter(self._percent_formatter))
            elif metric in ["cpc", "spend"]:
                plt.gca().yaxis.set_major_formatter(FuncFormatter(self._money_formatter))
            
            # Поворачиваем подписи по оси X для лучшей читаемости
            plt.xticks(rotation=30, ha='right')
            
            # Добавляем подписи значений над столбцами
            for bar in bars:
                height = bar.get_height()
                if metric == "ctr":
                    label = f"{height:.2f}%"
                elif metric in ["cpc", "spend"]:
                    label = format_currency(height)
                else:
                    label = f"{height:.2f}"
                    
                plt.text(bar.get_x() + bar.get_width()/2., height + max(values) * 0.01,
                        label, ha='center', va='bottom', rotation=0)
            
            plt.tight_layout()
            
            # Сохраняем график
            chart_path = os.path.join(chart_dir, f"ad_comparison_{metric}_chart.png")
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            logger.info(f"График сравнения объявлений по {metric} успешно создан: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании графика сравнения объявлений: {str(e)}")
            return ""
    
    def generate_hourly_performance_chart(self, 
                                       data: Dict[str, Any], 
                                       report_id: str,
                                       ad_id: Optional[str] = None,
                                       metric: str = "ctr",
                                       title: str = "Эффективность по времени суток") -> str:
        """
        Создание графика эффективности по времени суток.
        
        Args:
            data: Данные для визуализации
            report_id: Идентификатор отчета
            ad_id: ID объявления (если None, усредняется по всем)
            metric: Метрика для анализа (ctr, cpc, spend)
            title: Заголовок графика
            
        Returns:
            str: Путь к сохраненному графику
        """
        try:
            # Создаем директорию для графиков
            chart_dir = self._create_chart_dir(report_id)
            
            # Получаем данные об объявлениях
            ads = data.get("ads", [])
            
            # Проверяем наличие данных
            if not ads:
                logger.warning("Нет данных об объявлениях для анализа по времени суток")
                return ""
            
            # Подготавливаем данные для графика
            hours = list(range(24))
            values_by_hour = {hour: [] for hour in hours}
            
            # Если указан конкретный ID объявления
            if ad_id:
                ad = next((a for a in ads if a.get("id") == ad_id), None)
                if not ad:
                    logger.warning(f"Объявление с ID {ad_id} не найдено")
                    return ""
                
                hourly_data = ad.get("hourly_performance", {})
                if not hourly_data:
                    logger.warning(f"Нет данных о производительности по часам для объявления {ad_id}")
                    return ""
                
                # Заполняем значения метрики по часам
                for hour in hours:
                    hour_str = str(hour)
                    if hour_str in hourly_data:
                        values_by_hour[hour] = [hourly_data[hour_str].get(metric, 0)]
            else:
                # Собираем данные со всех объявлений
                for ad in ads:
                    hourly_data = ad.get("hourly_performance", {})
                    if hourly_data:
                        for hour in hours:
                            hour_str = str(hour)
                            if hour_str in hourly_data:
                                values_by_hour[hour].append(hourly_data[hour_str].get(metric, 0))
            
            # Рассчитываем средние значения по часам
            avg_values = []
            for hour in hours:
                if values_by_hour[hour]:
                    avg_values.append(sum(values_by_hour[hour]) / len(values_by_hour[hour]))
                else:
                    avg_values.append(0)
            
            # Создаем график
            plt.figure(figsize=(12, 6))
            
            # Выбираем стиль в зависимости от метрики
            if metric == 'ctr':
                plt.plot(hours, avg_values, marker='o', linestyle='-', color='#36A2EB', linewidth=2)
                plt.fill_between(hours, avg_values, alpha=0.2, color='#36A2EB')
            elif metric == 'cpc':
                plt.plot(hours, avg_values, marker='s', linestyle='-', color='#FF6384', linewidth=2)
            elif metric == 'spend':
                plt.bar(hours, avg_values, color='#4BC0C0', alpha=0.7)
            else:
                plt.plot(hours, avg_values, marker='o', linestyle='-', color='#4267B2', linewidth=2)
            
            # Настраиваем оси
            metric_label = metric.upper()
            if metric == "ctr":
                metric_label = "CTR, %"
            elif metric == "cpc":
                metric_label = "Стоимость клика"
            elif metric == "spend":
                metric_label = "Расходы"
            
            plt.ylabel(metric_label)
            plt.xlabel('Час дня')
            plt.title(title)
            
            # Форматируем значения на оси Y в зависимости от метрики
            if metric == "ctr":
                plt.gca().yaxis.set_major_formatter(FuncFormatter(self._percent_formatter))
            elif metric in ["cpc", "spend"]:
                plt.gca().yaxis.set_major_formatter(FuncFormatter(self._money_formatter))
            
            # Настраиваем ось X для отображения часов
            plt.xticks(hours)
            plt.xlim(-0.5, 23.5)
            
            # Добавляем сетку
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Сохраняем график
            chart_path = os.path.join(chart_dir, f"hourly_{metric}_chart.png")
            if ad_id:
                chart_path = os.path.join(chart_dir, f"hourly_{metric}_ad_{ad_id}_chart.png")
            
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            logger.info(f"График эффективности по времени суток успешно создан: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании графика эффективности по времени суток: {str(e)}")
            return ""
    
    def generate_daily_performance_chart(self, 
                                      data: Dict[str, Any], 
                                      report_id: str,
                                      ad_id: Optional[str] = None,
                                      metric: str = "ctr",
                                      title: str = "Эффективность по дням недели") -> str:
        """
        Создание графика эффективности по дням недели.
        
        Args:
            data: Данные для визуализации
            report_id: Идентификатор отчета
            ad_id: ID объявления (если None, усредняется по всем)
            metric: Метрика для анализа (ctr, cpc, spend)
            title: Заголовок графика
            
        Returns:
            str: Путь к сохраненному графику
        """
        try:
            # Создаем директорию для графиков
            chart_dir = self._create_chart_dir(report_id)
            
            # Получаем данные об объявлениях
            ads = data.get("ads", [])
            
            # Проверяем наличие данных
            if not ads:
                logger.warning("Нет данных об объявлениях для анализа по дням недели")
                return ""
            
            # Определяем дни недели
            days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            day_idx = {i+1: day for i, day in enumerate(days)}
            
            # Подготавливаем данные для графика
            values_by_day = {day: [] for day in days}
            
            # Если указан конкретный ID объявления
            if ad_id:
                ad = next((a for a in ads if a.get("id") == ad_id), None)
                if not ad:
                    logger.warning(f"Объявление с ID {ad_id} не найдено")
                    return ""
                
                daily_data = ad.get("daily_performance", {})
                if not daily_data:
                    logger.warning(f"Нет данных о производительности по дням для объявления {ad_id}")
                    return ""
                
                # Заполняем значения метрики по дням
                for day_num, day_name in day_idx.items():
                    if str(day_num) in daily_data:
                        values_by_day[day_name] = [daily_data[str(day_num)].get(metric, 0)]
            else:
                # Собираем данные со всех объявлений
                for ad in ads:
                    daily_data = ad.get("daily_performance", {})
                    if daily_data:
                        for day_num, day_name in day_idx.items():
                            if str(day_num) in daily_data:
                                values_by_day[day_name].append(daily_data[str(day_num)].get(metric, 0))
            
            # Рассчитываем средние значения по дням
            avg_values = []
            for day in days:
                if values_by_day[day]:
                    avg_values.append(sum(values_by_day[day]) / len(values_by_day[day]))
                else:
                    avg_values.append(0)
            
            # Создаем график
            plt.figure(figsize=(10, 6))
            
            # Выбираем стиль графика в зависимости от метрики
            if metric == 'ctr':
                color = '#36A2EB'
            elif metric == 'cpc':
                color = '#FF6384'
            elif metric == 'spend':
                color = '#4BC0C0'
            else:
                color = '#4267B2'
            
            bars = plt.bar(days, avg_values, color=color)
            
            # Настраиваем оси
            metric_label = metric.upper()
            if metric == "ctr":
                metric_label = "CTR, %"
            elif metric == "cpc":
                metric_label = "Стоимость клика"
            elif metric == "spend":
                metric_label = "Расходы"
            
            plt.ylabel(metric_label)
            plt.xlabel('День недели')
            plt.title(title)
            
            # Форматируем значения на оси Y в зависимости от метрики
            if metric == "ctr":
                plt.gca().yaxis.set_major_formatter(FuncFormatter(self._percent_formatter))
            elif metric in ["cpc", "spend"]:
                plt.gca().yaxis.set_major_formatter(FuncFormatter(self._money_formatter))
            
            # Поворачиваем подписи по оси X для лучшей читаемости
            plt.xticks(rotation=15, ha='right')
            
            # Добавляем подписи значений над столбцами
            for bar in bars:
                height = bar.get_height()
                if metric == "ctr":
                    label = f"{height:.2f}%"
                elif metric in ["cpc", "spend"]:
                    label = format_currency(height)
                else:
                    label = f"{height:.2f}"
                    
                plt.text(bar.get_x() + bar.get_width()/2., height + max(avg_values) * 0.01,
                        label, ha='center', va='bottom', rotation=0)
            
            plt.tight_layout()
            
            # Сохраняем график
            chart_path = os.path.join(chart_dir, f"daily_{metric}_chart.png")
            if ad_id:
                chart_path = os.path.join(chart_dir, f"daily_{metric}_ad_{ad_id}_chart.png")
            
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            logger.info(f"График эффективности по дням недели успешно создан: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании графика эффективности по дням недели: {str(e)}")
            return ""
    
    def generate_all_charts(self, data: Dict[str, Any], report_id: str) -> Dict[str, str]:
        """
        Создание всех типов графиков для отчета.
        
        Args:
            data: Данные для визуализации
            report_id: Идентификатор отчета
            
        Returns:
            Dict[str, str]: Словарь с путями к созданным графикам
        """
        charts = {}
        
        # Создаем график расходов по кампаниям
        spend_chart = self.generate_spend_chart(data, report_id)
        if spend_chart:
            charts["spend_chart"] = spend_chart
        
        # Создаем график CTR по кампаниям
        ctr_chart = self.generate_ctr_chart(data, report_id)
        if ctr_chart:
            charts["ctr_chart"] = ctr_chart
        
        # Создаем графики трендов для разных метрик
        for metric in ["ctr", "cpc", "spend"]:
            trend_chart = self.generate_metrics_trend_chart(data, report_id, metric)
            if trend_chart:
                charts[f"{metric}_trend_chart"] = trend_chart
        
        # Если это отчет сравнения объявлений
        if "ads" in data and len(data.get("ads", [])) > 1:
            # Создаем графики сравнения объявлений по разным метрикам
            for metric in ["ctr", "cpc", "spend"]:
                comparison_chart = self.generate_ad_comparison_chart(data, report_id, metric)
                if comparison_chart:
                    charts[f"ad_comparison_{metric}_chart"] = comparison_chart
            
            # Создаем графики по времени суток
            hourly_ctr_chart = self.generate_hourly_performance_chart(data, report_id, metric="ctr")
            if hourly_ctr_chart:
                charts["hourly_ctr_chart"] = hourly_ctr_chart
            
            # Создаем графики по дням недели
            daily_ctr_chart = self.generate_daily_performance_chart(data, report_id, metric="ctr")
            if daily_ctr_chart:
                charts["daily_ctr_chart"] = daily_ctr_chart
        
        return charts 