"""
Модуль генерации различных типов отчетов для Facebook Ads Toolkit.
Поддерживает создание и кастомизацию различных типов отчетов с экспортом в различные форматы.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import csv

from ..utils.data_handlers import format_currency, format_number
from ..analysis.ad_analyzer import AdAnalyzer
from ..analysis.data_fetchers import AdDataFetcher

logger = logging.getLogger(__name__)

class ReportTemplate(ABC):
    """Абстрактный базовый класс для всех шаблонов отчетов."""
    
    def __init__(self, title: str, description: str):
        """
        Инициализация шаблона отчета.
        
        Args:
            title: Заголовок отчета
            description: Описание отчета
        """
        self.title = title
        self.description = description
        self.created_at = datetime.now()
        self.sections = []
        
    @abstractmethod
    def generate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерация отчета на основе предоставленных данных.
        
        Args:
            data: Данные для генерации отчета
            
        Returns:
            Dict[str, Any]: Сгенерированный отчет
        """
        pass
    
    def add_section(self, section: 'ReportSection'):
        """
        Добавление секции в отчет.
        
        Args:
            section: Секция отчета
        """
        self.sections.append(section)


class ReportSection:
    """Класс для представления секции отчета."""
    
    def __init__(self, title: str, content_generator: Callable[[Dict[str, Any]], Any]):
        """
        Инициализация секции отчета.
        
        Args:
            title: Заголовок секции
            content_generator: Функция для генерации содержимого секции
        """
        self.title = title
        self.content_generator = content_generator
        
    def generate_content(self, data: Dict[str, Any]) -> Any:
        """
        Генерация содержимого секции.
        
        Args:
            data: Данные для генерации содержимого
            
        Returns:
            Any: Сгенерированное содержимое
        """
        return self.content_generator(data)


class ReportFormat(ABC):
    """Абстрактный базовый класс для всех форматов отчетов."""
    
    @abstractmethod
    def export(self, report_data: Dict[str, Any], file_path: str) -> str:
        """
        Экспорт отчета в файл.
        
        Args:
            report_data: Данные отчета
            file_path: Путь к файлу для сохранения
            
        Returns:
            str: Путь к созданному файлу
        """
        pass


class CampaignPerformanceReport(ReportTemplate):
    """Шаблон отчета о производительности рекламных кампаний."""
    
    def __init__(self):
        """Инициализация шаблона отчета о производительности кампаний."""
        super().__init__(
            "Отчет о производительности рекламных кампаний",
            "Подробный анализ эффективности рекламных кампаний, включая метрики, тенденции и рекомендации."
        )
        
        # Добавляем стандартные секции отчета
        self.add_section(ReportSection("Общая статистика", self._generate_overall_stats))
        self.add_section(ReportSection("Статистика по кампаниям", self._generate_campaign_stats))
        self.add_section(ReportSection("Динамика показателей", self._generate_metrics_trends))
        self.add_section(ReportSection("Рекомендации", self._generate_recommendations))
        
    def generate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерация отчета о производительности кампаний.
        
        Args:
            data: Данные для генерации отчета
            
        Returns:
            Dict[str, Any]: Сгенерированный отчет
        """
        report = {
            "title": self.title,
            "description": self.description,
            "generated_at": self.created_at.isoformat(),
            "time_range": data.get("time_range", {}),
            "sections": {}
        }
        
        # Генерируем содержимое каждой секции
        for section in self.sections:
            report["sections"][section.title] = section.generate_content(data)
        
        return report
    
    def _generate_overall_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация общей статистики."""
        metrics = data.get("metrics", {})
        
        return {
            "active_campaigns": metrics.get("active_campaigns", 0),
            "total_campaigns": metrics.get("total_campaigns", 0),
            "active_adsets": metrics.get("active_adsets", 0), 
            "total_adsets": metrics.get("total_adsets", 0),
            "active_ads": metrics.get("active_ads", 0),
            "total_ads": metrics.get("total_ads", 0),
            "total_spend": metrics.get("total_spend", 0),
            "total_impressions": metrics.get("total_impressions", 0),
            "total_clicks": metrics.get("total_clicks", 0),
            "avg_ctr": metrics.get("avg_ctr", 0),
            "avg_cpc": metrics.get("avg_cpc", 0)
        }
    
    def _generate_campaign_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация статистики по кампаниям."""
        campaign_performance = data.get("campaign_performance", {})
        
        return {
            "top_campaigns_by_ctr": campaign_performance.get("top_campaigns_by_ctr", []),
            "top_campaigns_by_spend": campaign_performance.get("top_campaigns_by_spend", []),
            "underperforming_campaigns": campaign_performance.get("underperforming_campaigns", [])
        }
    
    def _generate_metrics_trends(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация трендов метрик."""
        trends = data.get("trends", {})
        
        # Если трендов нет в данных, возвращаем пустой словарь
        if not trends:
            return {}
        
        return {
            "spend_trend": trends.get("spend_trend", []),
            "ctr_trend": trends.get("ctr_trend", []),
            "cpc_trend": trends.get("cpc_trend", [])
        }
    
    def _generate_recommendations(self, data: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций."""
        recommendations = []
        
        # Анализ данных для формирования рекомендаций
        campaign_performance = data.get("campaign_performance", {})
        ad_performance = data.get("ad_performance", {})
        
        # Рекомендации для лучших кампаний
        top_campaigns = campaign_performance.get("top_campaigns_by_ctr", [])
        if top_campaigns:
            best_campaign = top_campaigns[0]
            recommendations.append(
                f"Рассмотрите увеличение бюджета для кампании \"{best_campaign.get('name', '')}\", "
                f"так как она показывает наилучший CTR ({best_campaign.get('ctr', 0):.2f}%)."
            )
        
        # Рекомендации для худших объявлений
        underperforming_ads = ad_performance.get("underperforming_ads", [])
        if underperforming_ads:
            worst_ad = underperforming_ads[0]
            recommendations.append(
                f"Рассмотрите остановку или оптимизацию объявления \"{worst_ad.get('name', '')}\", "
                f"так как оно показывает низкий CTR ({worst_ad.get('ctr', 0):.2f}%) "
                f"при достаточном количестве показов ({worst_ad.get('impressions', 0):,})."
            )
        
        # Общие рекомендации
        recommendations.append("Регулярно проверяйте производительность рекламы и корректируйте стратегии.")
        recommendations.append("Тестируйте различные варианты креативов и таргетирования для улучшения результатов.")
        
        return recommendations


class AdComparisonReport(ReportTemplate):
    """Шаблон отчета для сравнения рекламных объявлений."""
    
    def __init__(self):
        """Инициализация шаблона отчета для сравнения объявлений."""
        super().__init__(
            "Сравнительный анализ рекламных объявлений",
            "Детальное сравнение эффективности различных рекламных объявлений."
        )
        
        # Добавляем секции для отчета
        self.add_section(ReportSection("Сравнение основных метрик", self._generate_metrics_comparison))
        self.add_section(ReportSection("Сравнение по времени суток", self._generate_time_of_day_comparison))
        self.add_section(ReportSection("Сравнение по дням недели", self._generate_day_of_week_comparison))
        self.add_section(ReportSection("Выводы", self._generate_conclusions))
    
    def generate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерация отчета для сравнения объявлений.
        
        Args:
            data: Данные для генерации отчета
            
        Returns:
            Dict[str, Any]: Сгенерированный отчет
        """
        report = {
            "title": self.title,
            "description": self.description,
            "generated_at": self.created_at.isoformat(),
            "time_range": data.get("time_range", {}),
            "ads_compared": [ad.get("name", "Неизвестное объявление") for ad in data.get("ads", [])],
            "sections": {}
        }
        
        # Генерируем содержимое каждой секции
        for section in self.sections:
            report["sections"][section.title] = section.generate_content(data)
        
        return report
    
    def _generate_metrics_comparison(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация сравнения основных метрик."""
        ads = data.get("ads", [])
        
        result = {}
        for ad in ads:
            ad_id = ad.get("id", "unknown")
            result[ad_id] = {
                "name": ad.get("name", "Неизвестное объявление"),
                "impressions": ad.get("impressions", 0),
                "clicks": ad.get("clicks", 0),
                "ctr": ad.get("ctr", 0),
                "cpc": ad.get("cpc", 0),
                "spend": ad.get("spend", 0)
            }
        
        return result
    
    def _generate_time_of_day_comparison(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация сравнения по времени суток."""
        ads = data.get("ads", [])
        
        result = {}
        for ad in ads:
            ad_id = ad.get("id", "unknown")
            hourly_data = ad.get("hourly_performance", {})
            
            if hourly_data:
                result[ad_id] = {
                    "name": ad.get("name", "Неизвестное объявление"),
                    "hourly_data": hourly_data
                }
        
        return result
    
    def _generate_day_of_week_comparison(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация сравнения по дням недели."""
        ads = data.get("ads", [])
        
        result = {}
        for ad in ads:
            ad_id = ad.get("id", "unknown")
            daily_data = ad.get("daily_performance", {})
            
            if daily_data:
                result[ad_id] = {
                    "name": ad.get("name", "Неизвестное объявление"),
                    "daily_data": daily_data
                }
        
        return result
    
    def _generate_conclusions(self, data: Dict[str, Any]) -> List[str]:
        """Генерация выводов на основе сравнения."""
        conclusions = []
        ads = data.get("ads", [])
        
        if len(ads) < 2:
            conclusions.append("Недостаточно данных для сравнения объявлений.")
            return conclusions
        
        # Определение лучшего объявления по CTR
        best_ctr_ad = max(ads, key=lambda ad: ad.get("ctr", 0))
        worst_ctr_ad = min(ads, key=lambda ad: ad.get("ctr", 0))
        
        if best_ctr_ad and worst_ctr_ad:
            conclusions.append(
                f"Объявление \"{best_ctr_ad.get('name', '')}\" показывает на "
                f"{(best_ctr_ad.get('ctr', 0) - worst_ctr_ad.get('ctr', 0)):.2f}% "
                f"лучший CTR, чем \"{worst_ctr_ad.get('name', '')}\"."
            )
        
        # Определение наиболее экономичного объявления по CPC
        best_cpc_ad = min(ads, key=lambda ad: ad.get("cpc", float('inf')) or float('inf'))
        worst_cpc_ad = max(ads, key=lambda ad: ad.get("cpc", 0))
        
        if best_cpc_ad and worst_cpc_ad and best_cpc_ad.get("cpc") and worst_cpc_ad.get("cpc"):
            conclusions.append(
                f"Объявление \"{best_cpc_ad.get('name', '')}\" имеет на "
                f"{format_currency(worst_cpc_ad.get('cpc', 0) - best_cpc_ad.get('cpc', 0))} "
                f"меньшую стоимость клика, чем \"{worst_cpc_ad.get('name', '')}\"."
            )
        
        # Общие выводы
        conclusions.append("Рекомендуется переназначить бюджет в пользу более эффективных объявлений.")
        conclusions.append("Рассмотрите возможность адаптации креативов менее эффективных объявлений по образцу более успешных.")
        
        return conclusions


class JsonReportFormat(ReportFormat):
    """Класс для экспорта отчетов в формате JSON."""
    
    def export(self, report_data: Dict[str, Any], file_path: str) -> str:
        """
        Экспорт отчета в формате JSON.
        
        Args:
            report_data: Данные отчета
            file_path: Путь к файлу для сохранения
            
        Returns:
            str: Путь к созданному файлу
        """
        try:
            # Убедимся, что директория существует
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Записываем данные в JSON-файл
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Отчет успешно экспортирован в JSON: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте отчета в JSON: {str(e)}")
            raise


class TextReportFormat(ReportFormat):
    """Класс для экспорта отчетов в текстовом формате."""
    
    def export(self, report_data: Dict[str, Any], file_path: str) -> str:
        """
        Экспорт отчета в текстовом формате.
        
        Args:
            report_data: Данные отчета
            file_path: Путь к файлу для сохранения
            
        Returns:
            str: Путь к созданному файлу
        """
        try:
            # Убедимся, что директория существует
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Формируем содержимое отчета
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write(f"{report_data.get('title', 'Отчет').upper():^70}\n")
                f.write("=" * 70 + "\n\n")
                
                # Добавляем описание
                f.write(f"{report_data.get('description', '')}\n\n")
                
                # Добавляем информацию о времени генерации и периоде анализа
                f.write(f"Дата генерации: {datetime.fromisoformat(report_data.get('generated_at')).strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                time_range = report_data.get('time_range', {})
                if time_range:
                    f.write(f"Период анализа: {time_range.get('since', 'н/д')} - {time_range.get('until', 'н/д')}\n")
                
                f.write("\n" + "=" * 70 + "\n\n")
                
                # Добавляем содержимое секций
                sections = report_data.get('sections', {})
                for section_title, section_content in sections.items():
                    f.write(f"=== {section_title.upper()} ===\n\n")
                    
                    # Обработка разных типов содержимого
                    if isinstance(section_content, dict):
                        for key, value in section_content.items():
                            if isinstance(value, dict):
                                f.write(f"{value.get('name', key)}:\n")
                                for k, v in value.items():
                                    if k != 'name':
                                        if isinstance(v, float):
                                            f.write(f"   {k}: {v:.2f}\n")
                                        else:
                                            f.write(f"   {k}: {v}\n")
                                f.write("\n")
                            else:
                                f.write(f"{key}: {value}\n")
                    elif isinstance(section_content, list):
                        for i, item in enumerate(section_content, 1):
                            if isinstance(item, str):
                                f.write(f"{i}. {item}\n")
                            elif isinstance(item, dict):
                                f.write(f"{i}. {item.get('name', 'Элемент ' + str(i))}\n")
                                for k, v in item.items():
                                    if k != 'name':
                                        if isinstance(v, float):
                                            f.write(f"   {k}: {v:.2f}\n")
                                        else:
                                            f.write(f"   {k}: {v}\n")
                            f.write("\n")
                    else:
                        f.write(f"{section_content}\n")
                    
                    f.write("\n" + "-" * 50 + "\n\n")
                
                f.write("=" * 70 + "\n")
                f.write("КОНЕЦ ОТЧЕТА".center(70) + "\n")
                f.write("=" * 70 + "\n")
            
            logger.info(f"Отчет успешно экспортирован в текстовом формате: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте отчета в текстовом формате: {str(e)}")
            raise


class CsvReportFormat(ReportFormat):
    """Класс для экспорта отчетов в формате CSV."""
    
    def export(self, report_data: Dict[str, Any], file_path: str) -> str:
        """
        Экспорт отчета в формате CSV.
        
        Args:
            report_data: Данные отчета
            file_path: Путь к файлу для сохранения
            
        Returns:
            str: Путь к созданному файлу
        """
        try:
            # Убедимся, что директория существует
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Подготавливаем данные для CSV
            csv_data = []
            headers = []
            
            # Определяем, какие данные экспортировать
            if "title" in report_data and report_data["title"] == "Отчет о производительности рекламных кампаний":
                # Для отчета о производительности кампаний
                if "sections" in report_data and "Статистика по кампаниям" in report_data["sections"]:
                    campaign_stats = report_data["sections"]["Статистика по кампаниям"]
                    top_campaigns = campaign_stats.get("top_campaigns_by_ctr", [])
                    
                    if top_campaigns:
                        # Определяем заголовки
                        headers = ["Кампания", "Расходы", "Показы", "Клики", "CTR", "CPC"]
                        
                        # Заполняем данные
                        for campaign in top_campaigns:
                            row = [
                                campaign.get("name", ""),
                                format_currency(campaign.get("spend", 0)),
                                format_number(campaign.get("impressions", 0)),
                                format_number(campaign.get("clicks", 0)),
                                f"{campaign.get('ctr', 0):.2f}%",
                                format_currency(campaign.get("cpc", 0))
                            ]
                            csv_data.append(row)
            
            elif "title" in report_data and report_data["title"] == "Сравнительный анализ рекламных объявлений":
                # Для отчета сравнения объявлений
                if "sections" in report_data and "Сравнение основных метрик" in report_data["sections"]:
                    metrics_comparison = report_data["sections"]["Сравнение основных метрик"]
                    
                    if metrics_comparison:
                        # Определяем заголовки
                        headers = ["Объявление", "Расходы", "Показы", "Клики", "CTR", "CPC"]
                        
                        # Заполняем данные
                        for ad_id, ad_data in metrics_comparison.items():
                            row = [
                                ad_data.get("name", ""),
                                format_currency(ad_data.get("spend", 0)),
                                format_number(ad_data.get("impressions", 0)),
                                format_number(ad_data.get("clicks", 0)),
                                f"{ad_data.get('ctr', 0):.2f}%",
                                format_currency(ad_data.get("cpc", 0))
                            ]
                            csv_data.append(row)
            
            # Записываем данные в CSV-файл
            if headers and csv_data:
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(csv_data)
                
                logger.info(f"Отчет успешно экспортирован в CSV: {file_path}")
                return file_path
            else:
                logger.warning(f"Нет данных для экспорта в CSV: {file_path}")
                return ""
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте отчета в CSV: {str(e)}")
            raise


class ReportManager:
    """Класс для управления отчетами и их экспортом."""
    
    def __init__(self, output_dir: str = "reports"):
        """
        Инициализация менеджера отчетов.
        
        Args:
            output_dir: Директория для сохранения отчетов
        """
        self.output_dir = output_dir
        
        # Создаем директорию для отчетов, если она не существует
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Регистрируем доступные шаблоны отчетов
        self.report_templates = {
            "campaign_performance": CampaignPerformanceReport(),
            "ad_comparison": AdComparisonReport()
        }
        
        # Регистрируем доступные форматы экспорта
        self.export_formats = {
            "json": JsonReportFormat(),
            "txt": TextReportFormat(),
            "csv": CsvReportFormat()
        }
    
    def generate_report(self, 
                       template_name: str, 
                       data: Dict[str, Any], 
                       export_formats: List[str] = ["json"],
                       custom_filename: Optional[str] = None) -> Dict[str, str]:
        """
        Генерация отчета и его экспорт в указанные форматы.
        
        Args:
            template_name: Имя шаблона отчета
            data: Данные для генерации отчета
            export_formats: Форматы для экспорта отчета
            custom_filename: Пользовательское имя файла
            
        Returns:
            Dict[str, str]: Словарь с путями к созданным файлам
        """
        # Проверяем существование шаблона
        if template_name not in self.report_templates:
            raise ValueError(f"Шаблон отчета '{template_name}' не найден")
        
        # Генерируем отчет
        report_template = self.report_templates[template_name]
        report_data = report_template.generate(data)
        
        # Формируем базовое имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if custom_filename:
            base_filename = f"{custom_filename}"
        else:
            base_filename = f"{template_name}_report_{timestamp}"
        
        # Экспортируем отчет в указанные форматы
        exported_files = {}
        for format_name in export_formats:
            if format_name not in self.export_formats:
                logger.warning(f"Формат экспорта '{format_name}' не поддерживается, пропускаем")
                continue
            
            file_path = os.path.join(self.output_dir, f"{base_filename}.{format_name}")
            export_format = self.export_formats[format_name]
            
            try:
                exported_file = export_format.export(report_data, file_path)
                exported_files[format_name] = exported_file
            except Exception as e:
                logger.error(f"Ошибка при экспорте отчета в формате {format_name}: {str(e)}")
        
        return exported_files 