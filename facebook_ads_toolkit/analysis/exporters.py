"""
Модуль для экспорта результатов анализа рекламы в различные форматы.
"""

import json
import csv
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.data_handlers import format_currency

logger = logging.getLogger(__name__)

class AnalysisExporter:
    """Класс для экспорта результатов анализа рекламы."""
    
    def __init__(self, analysis_results: Dict[str, Any], output_dir: str = "reports"):
        """
        Инициализация экспортера результатов анализа.
        
        Args:
            analysis_results: Результаты анализа рекламы
            output_dir: Директория для сохранения отчетов
        """
        self.analysis_results = analysis_results
        self.output_dir = output_dir
        
        # Создаем директорию для отчетов, если она не существует
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def export_to_json(self, filename: Optional[str] = None) -> str:
        """
        Экспорт результатов анализа в JSON.
        
        Args:
            filename: Имя файла (без расширения)
            
        Returns:
            str: Путь к созданному файлу
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ad_analysis_{timestamp}"
        
        file_path = os.path.join(self.output_dir, f"{filename}.json")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Результаты анализа успешно экспортированы в JSON: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте результатов в JSON: {str(e)}")
            raise
    
    def export_campaign_summary_to_csv(self, filename: Optional[str] = None) -> str:
        """
        Экспорт сводки по кампаниям в CSV.
        
        Args:
            filename: Имя файла (без расширения)
            
        Returns:
            str: Путь к созданному файлу
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"campaign_summary_{timestamp}"
        
        file_path = os.path.join(self.output_dir, f"{filename}.csv")
        
        try:
            # Получаем данные о кампаниях
            if 'campaign_performance' not in self.analysis_results:
                logger.warning("В результатах анализа нет данных о производительности кампаний")
                return ""
            
            campaigns = self.analysis_results['campaign_performance'].get('all_campaigns', [])
            
            if not campaigns:
                logger.warning("Нет данных о кампаниях для экспорта")
                return ""
            
            # Определяем заголовки CSV
            fieldnames = [
                'id', 'name', 'status', 'objective', 'spend', 'impressions', 'clicks', 
                'ctr', 'cpc', 'reach', 'frequency', 'adsets_count', 'ads_count'
            ]
            
            # Создаем CSV-файл
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Записываем заголовок
                writer.writeheader()
                
                # Записываем данные
                for campaign in campaigns:
                    row = {
                        'id': campaign.get('id', ''),
                        'name': campaign.get('name', ''),
                        'status': campaign.get('status', ''),
                        'objective': campaign.get('objective', ''),
                        'spend': round(campaign.get('spend', 0), 2),
                        'impressions': campaign.get('impressions', 0),
                        'clicks': campaign.get('clicks', 0),
                        'ctr': round(campaign.get('ctr', 0), 2),
                        'cpc': round(campaign.get('cpc', 0), 2),
                        'reach': campaign.get('reach', 0),
                        'frequency': round(campaign.get('frequency', 0), 2),
                        'adsets_count': campaign.get('adsets_count', 0),
                        'ads_count': campaign.get('ads_count', 0)
                    }
                    writer.writerow(row)
            
            logger.info(f"Сводка по кампаниям успешно экспортирована в CSV: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте сводки по кампаниям в CSV: {str(e)}")
            raise
    
    def export_ad_performance_to_csv(self, filename: Optional[str] = None) -> str:
        """
        Экспорт данных о производительности объявлений в CSV.
        
        Args:
            filename: Имя файла (без расширения)
            
        Returns:
            str: Путь к созданному файлу
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ad_performance_{timestamp}"
        
        file_path = os.path.join(self.output_dir, f"{filename}.csv")
        
        try:
            # Получаем данные об объявлениях
            if 'ad_performance' not in self.analysis_results:
                logger.warning("В результатах анализа нет данных о производительности объявлений")
                return ""
            
            ads = self.analysis_results['ad_performance'].get('all_ads', [])
            
            if not ads:
                logger.warning("Нет данных об объявлениях для экспорта")
                return ""
            
            # Определяем заголовки CSV
            fieldnames = [
                'id', 'name', 'campaign_id', 'adset_id', 'status', 'effective_status',
                'spend', 'impressions', 'clicks', 'ctr', 'cpc'
            ]
            
            # Создаем CSV-файл
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Записываем заголовок
                writer.writeheader()
                
                # Записываем данные
                for ad in ads:
                    row = {
                        'id': ad.get('id', ''),
                        'name': ad.get('name', ''),
                        'campaign_id': ad.get('campaign_id', ''),
                        'adset_id': ad.get('adset_id', ''),
                        'status': ad.get('status', ''),
                        'effective_status': ad.get('effective_status', ''),
                        'spend': round(ad.get('spend', 0), 2),
                        'impressions': ad.get('impressions', 0),
                        'clicks': ad.get('clicks', 0),
                        'ctr': round(ad.get('ctr', 0), 2),
                        'cpc': round(ad.get('cpc', 0), 2)
                    }
                    writer.writerow(row)
            
            logger.info(f"Данные о производительности объявлений успешно экспортированы в CSV: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте данных об объявлениях в CSV: {str(e)}")
            raise
    
    def generate_performance_report(self) -> str:
        """
        Генерация текстового отчета о производительности рекламы.
        
        Returns:
            str: Путь к созданному отчету
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = os.path.join(self.output_dir, f"performance_report_{timestamp}.txt")
        
        try:
            # Получаем данные из результатов анализа
            metrics = self.analysis_results.get('metrics', {})
            campaign_performance = self.analysis_results.get('campaign_performance', {})
            ad_performance = self.analysis_results.get('ad_performance', {})
            
            # Формируем отчет
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("==============================================\n")
                f.write("       ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ РЕКЛАМЫ    \n")
                f.write("==============================================\n\n")
                
                # Добавляем дату и временной диапазон
                time_range = self.analysis_results.get('time_range', {})
                f.write(f"Дата отчета: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if time_range:
                    f.write(f"Период анализа: {time_range.get('since', 'н/д')} - {time_range.get('until', 'н/д')}\n")
                f.write("\n")
                
                # Добавляем общую статистику
                f.write("=== ОБЩАЯ СТАТИСТИКА ===\n\n")
                f.write(f"Всего активных кампаний: {metrics.get('active_campaigns', 0)}/{metrics.get('total_campaigns', 0)}\n")
                f.write(f"Всего активных групп объявлений: {metrics.get('active_adsets', 0)}/{metrics.get('total_adsets', 0)}\n")
                f.write(f"Всего активных объявлений: {metrics.get('active_ads', 0)}/{metrics.get('total_ads', 0)}\n\n")
                
                f.write(f"Общие расходы: {format_currency(metrics.get('total_spend', 0))}\n")
                f.write(f"Общие показы: {metrics.get('total_impressions', 0):,}\n")
                f.write(f"Общие клики: {metrics.get('total_clicks', 0):,}\n")
                f.write(f"Средний CTR: {metrics.get('avg_ctr', 0):.2f}%\n")
                f.write(f"Средний CPC: {format_currency(metrics.get('avg_cpc', 0))}\n\n")
                
                # Добавляем статистику по лучшим кампаниям
                f.write("=== ЛУЧШИЕ КАМПАНИИ ПО CTR ===\n\n")
                top_campaigns = campaign_performance.get('top_campaigns_by_ctr', [])
                for i, campaign in enumerate(top_campaigns[:5], 1):
                    f.write(f"{i}. {campaign.get('name', 'Неизвестная кампания')}\n")
                    f.write(f"   Расходы: {format_currency(campaign.get('spend', 0))}\n")
                    f.write(f"   Показы: {campaign.get('impressions', 0):,}\n")
                    f.write(f"   Клики: {campaign.get('clicks', 0):,}\n")
                    f.write(f"   CTR: {campaign.get('ctr', 0):.2f}%\n")
                    f.write(f"   CPC: {format_currency(campaign.get('cpc', 0))}\n\n")
                
                # Добавляем статистику по лучшим объявлениям
                f.write("=== ЛУЧШИЕ ОБЪЯВЛЕНИЯ ПО CTR ===\n\n")
                top_ads = ad_performance.get('top_ads_by_ctr', [])
                for i, ad in enumerate(top_ads[:5], 1):
                    f.write(f"{i}. {ad.get('name', 'Неизвестное объявление')}\n")
                    f.write(f"   Расходы: {format_currency(ad.get('spend', 0))}\n")
                    f.write(f"   Показы: {ad.get('impressions', 0):,}\n")
                    f.write(f"   Клики: {ad.get('clicks', 0):,}\n")
                    f.write(f"   CTR: {ad.get('ctr', 0):.2f}%\n")
                    f.write(f"   CPC: {format_currency(ad.get('cpc', 0))}\n\n")
                
                # Добавляем рекомендации
                f.write("=== РЕКОМЕНДАЦИИ ===\n\n")
                
                # Анализ наиболее эффективных кампаний
                if top_campaigns:
                    best_campaign = top_campaigns[0]
                    f.write(f"1. Рассмотрите увеличение бюджета для кампании \"{best_campaign.get('name', '')}\", "
                            f"так как она показывает наилучший CTR ({best_campaign.get('ctr', 0):.2f}%).\n\n")
                
                # Анализ неэффективных объявлений
                underperforming_ads = ad_performance.get('underperforming_ads', [])
                if underperforming_ads:
                    worst_ad = underperforming_ads[0]
                    f.write(f"2. Рассмотрите остановку или оптимизацию объявления \"{worst_ad.get('name', '')}\", "
                            f"так как оно показывает низкий CTR ({worst_ad.get('ctr', 0):.2f}%) "
                            f"при достаточном количестве показов ({worst_ad.get('impressions', 0):,}).\n\n")
                
                # Общие рекомендации
                f.write("3. Регулярно проверяйте производительность рекламы и корректируйте стратегии.\n\n")
                f.write("4. Тестируйте различные варианты креативов и таргетирования для улучшения результатов.\n\n")
                
                f.write("==============================================\n")
                f.write("               КОНЕЦ ОТЧЕТА                  \n")
                f.write("==============================================\n")
            
            logger.info(f"Отчет о производительности успешно сгенерирован: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета о производительности: {str(e)}")
            raise
    
    def export_all(self) -> Dict[str, str]:
        """
        Экспорт всех доступных форматов отчетов.
        
        Returns:
            Dict[str, str]: Словарь с путями к созданным файлам
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        result = {}
        
        try:
            # Экспорт в JSON
            json_path = self.export_to_json(f"ad_analysis_{timestamp}")
            result['json'] = json_path
            
            # Экспорт сводки по кампаниям в CSV
            campaign_csv_path = self.export_campaign_summary_to_csv(f"campaign_summary_{timestamp}")
            result['campaign_csv'] = campaign_csv_path
            
            # Экспорт данных об объявлениях в CSV
            ad_csv_path = self.export_ad_performance_to_csv(f"ad_performance_{timestamp}")
            result['ad_csv'] = ad_csv_path
            
            # Генерация текстового отчета
            report_path = self.generate_performance_report()
            result['text_report'] = report_path
            
            logger.info(f"Все отчеты успешно экспортированы в директорию: {self.output_dir}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте всех отчетов: {str(e)}")
            raise 