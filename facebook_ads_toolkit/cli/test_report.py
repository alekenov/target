#!/usr/bin/env python3
"""
Тестовый модуль для проверки функциональности отчетов.
Запускает процесс создания тестовых отчетов с демонстрационными данными.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..reports.report_generator import ReportManager
from ..reports.visualization import ChartGenerator
from ..utils.data_handlers import save_to_json, load_from_json, format_currency, format_number

logger = logging.getLogger(__name__)

def generate_demo_data() -> Dict[str, Any]:
    """
    Генерация демонстрационных данных для тестирования отчетов.
    
    Returns:
        Dict[str, Any]: Демонстрационные данные
    """
    # Период времени
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    time_range = {
        'since': start_date.strftime('%Y-%m-%d'),
        'until': end_date.strftime('%Y-%m-%d')
    }
    
    # Данные о кампаниях
    campaigns = [
        {
            'id': '1001',
            'name': 'Летняя распродажа',
            'status': 'ACTIVE',
            'insights': {
                'spend': 15000,
                'impressions': 250000,
                'clicks': 7500
            }
        },
        {
            'id': '1002',
            'name': 'Новая коллекция',
            'status': 'ACTIVE',
            'insights': {
                'spend': 12000,
                'impressions': 180000,
                'clicks': 5400
            }
        },
        {
            'id': '1003',
            'name': 'Промо-акция',
            'status': 'PAUSED',
            'insights': {
                'spend': 8000,
                'impressions': 120000,
                'clicks': 3000
            }
        },
        {
            'id': '1004',
            'name': 'Специальные предложения',
            'status': 'ACTIVE',
            'insights': {
                'spend': 20000,
                'impressions': 300000,
                'clicks': 9000
            }
        },
        {
            'id': '1005',
            'name': 'Бонусы постоянным клиентам',
            'status': 'ACTIVE',
            'insights': {
                'spend': 5000,
                'impressions': 80000,
                'clicks': 2000
            }
        }
    ]
    
    # Данные об объявлениях для сравнения
    ads = [
        {
            'id': '2001',
            'name': 'Объявление 1',
            'status': 'ACTIVE',
            'campaign_id': '1001',
            'insights': {
                'spend': 5000,
                'impressions': 100000,
                'clicks': 3000,
                'ctr': 3.0,
                'cpc': 1.67
            },
            'hourly_performance': [
                {'hour': 0, 'impressions': 1000, 'clicks': 20, 'ctr': 2.0},
                {'hour': 1, 'impressions': 800, 'clicks': 15, 'ctr': 1.88},
                {'hour': 2, 'impressions': 500, 'clicks': 8, 'ctr': 1.6},
                {'hour': 3, 'impressions': 300, 'clicks': 5, 'ctr': 1.67},
                {'hour': 4, 'impressions': 200, 'clicks': 3, 'ctr': 1.5},
                {'hour': 5, 'impressions': 400, 'clicks': 7, 'ctr': 1.75},
                {'hour': 6, 'impressions': 1000, 'clicks': 18, 'ctr': 1.8},
                {'hour': 7, 'impressions': 2000, 'clicks': 40, 'ctr': 2.0},
                {'hour': 8, 'impressions': 5000, 'clicks': 130, 'ctr': 2.6},
                {'hour': 9, 'impressions': 7000, 'clicks': 210, 'ctr': 3.0},
                {'hour': 10, 'impressions': 8000, 'clicks': 240, 'ctr': 3.0},
                {'hour': 11, 'impressions': 10000, 'clicks': 300, 'ctr': 3.0},
                {'hour': 12, 'impressions': 12000, 'clicks': 380, 'ctr': 3.17},
                {'hour': 13, 'impressions': 10000, 'clicks': 320, 'ctr': 3.2},
                {'hour': 14, 'impressions': 9000, 'clicks': 290, 'ctr': 3.22},
                {'hour': 15, 'impressions': 8000, 'clicks': 250, 'ctr': 3.13},
                {'hour': 16, 'impressions': 7000, 'clicks': 210, 'ctr': 3.0},
                {'hour': 17, 'impressions': 5000, 'clicks': 150, 'ctr': 3.0},
                {'hour': 18, 'impressions': 4000, 'clicks': 120, 'ctr': 3.0},
                {'hour': 19, 'impressions': 3000, 'clicks': 90, 'ctr': 3.0},
                {'hour': 20, 'impressions': 2000, 'clicks': 60, 'ctr': 3.0},
                {'hour': 21, 'impressions': 2000, 'clicks': 60, 'ctr': 3.0},
                {'hour': 22, 'impressions': 1500, 'clicks': 40, 'ctr': 2.67},
                {'hour': 23, 'impressions': 1300, 'clicks': 34, 'ctr': 2.62}
            ],
            'daily_performance': [
                {'day': 0, 'name': 'Понедельник', 'impressions': 15000, 'clicks': 450, 'ctr': 3.0},
                {'day': 1, 'name': 'Вторник', 'impressions': 14000, 'clicks': 420, 'ctr': 3.0},
                {'day': 2, 'name': 'Среда', 'impressions': 13000, 'clicks': 390, 'ctr': 3.0},
                {'day': 3, 'name': 'Четверг', 'impressions': 15000, 'clicks': 450, 'ctr': 3.0},
                {'day': 4, 'name': 'Пятница', 'impressions': 16000, 'clicks': 480, 'ctr': 3.0},
                {'day': 5, 'name': 'Суббота', 'impressions': 14000, 'clicks': 420, 'ctr': 3.0},
                {'day': 6, 'name': 'Воскресенье', 'impressions': 13000, 'clicks': 390, 'ctr': 3.0}
            ]
        },
        {
            'id': '2002',
            'name': 'Объявление 2',
            'status': 'ACTIVE',
            'campaign_id': '1001',
            'insights': {
                'spend': 5000,
                'impressions': 80000,
                'clicks': 3200,
                'ctr': 4.0,
                'cpc': 1.56
            },
            'hourly_performance': [
                {'hour': 0, 'impressions': 800, 'clicks': 24, 'ctr': 3.0},
                {'hour': 1, 'impressions': 600, 'clicks': 18, 'ctr': 3.0},
                {'hour': 2, 'impressions': 400, 'clicks': 12, 'ctr': 3.0},
                {'hour': 3, 'impressions': 200, 'clicks': 6, 'ctr': 3.0},
                {'hour': 4, 'impressions': 200, 'clicks': 6, 'ctr': 3.0},
                {'hour': 5, 'impressions': 300, 'clicks': 9, 'ctr': 3.0},
                {'hour': 6, 'impressions': 800, 'clicks': 24, 'ctr': 3.0},
                {'hour': 7, 'impressions': 1000, 'clicks': 30, 'ctr': 3.0},
                {'hour': 8, 'impressions': 4000, 'clicks': 160, 'ctr': 4.0},
                {'hour': 9, 'impressions': 6000, 'clicks': 240, 'ctr': 4.0},
                {'hour': 10, 'impressions': 7000, 'clicks': 280, 'ctr': 4.0},
                {'hour': 11, 'impressions': 8000, 'clicks': 320, 'ctr': 4.0},
                {'hour': 12, 'impressions': 10000, 'clicks': 400, 'ctr': 4.0},
                {'hour': 13, 'impressions': 8000, 'clicks': 320, 'ctr': 4.0},
                {'hour': 14, 'impressions': 7000, 'clicks': 280, 'ctr': 4.0},
                {'hour': 15, 'impressions': 6000, 'clicks': 240, 'ctr': 4.0},
                {'hour': 16, 'impressions': 5000, 'clicks': 200, 'ctr': 4.0},
                {'hour': 17, 'impressions': 4000, 'clicks': 160, 'ctr': 4.0},
                {'hour': 18, 'impressions': 3000, 'clicks': 120, 'ctr': 4.0},
                {'hour': 19, 'impressions': 2000, 'clicks': 80, 'ctr': 4.0},
                {'hour': 20, 'impressions': 2000, 'clicks': 80, 'ctr': 4.0},
                {'hour': 21, 'impressions': 1500, 'clicks': 60, 'ctr': 4.0},
                {'hour': 22, 'impressions': 1200, 'clicks': 48, 'ctr': 4.0},
                {'hour': 23, 'impressions': 1000, 'clicks': 40, 'ctr': 4.0}
            ],
            'daily_performance': [
                {'day': 0, 'name': 'Понедельник', 'impressions': 12000, 'clicks': 480, 'ctr': 4.0},
                {'day': 1, 'name': 'Вторник', 'impressions': 11000, 'clicks': 440, 'ctr': 4.0},
                {'day': 2, 'name': 'Среда', 'impressions': 10000, 'clicks': 400, 'ctr': 4.0},
                {'day': 3, 'name': 'Четверг', 'impressions': 12000, 'clicks': 480, 'ctr': 4.0},
                {'day': 4, 'name': 'Пятница', 'impressions': 13000, 'clicks': 520, 'ctr': 4.0},
                {'day': 5, 'name': 'Суббота', 'impressions': 11000, 'clicks': 440, 'ctr': 4.0},
                {'day': 6, 'name': 'Воскресенье', 'impressions': 11000, 'clicks': 440, 'ctr': 4.0}
            ]
        }
    ]
    
    # Тренды для показа динамики
    ctr_trend = [
        {'date': (start_date + timedelta(days=i)).strftime('%Y-%m-%d'), 'ctr': 2.5 + (i % 5) * 0.1} 
        for i in range(30)
    ]
    
    # Формируем результаты анализа
    analysis_results = {
        'time_range': time_range,
        'campaign_performance': {
            'total_campaigns': len(campaigns),
            'active_campaigns': sum(1 for c in campaigns if c.get('status') == 'ACTIVE'),
            'paused_campaigns': sum(1 for c in campaigns if c.get('status') == 'PAUSED'),
            'total_spend': sum(c.get('insights', {}).get('spend', 0) for c in campaigns),
            'total_impressions': sum(c.get('insights', {}).get('impressions', 0) for c in campaigns),
            'total_clicks': sum(c.get('insights', {}).get('clicks', 0) for c in campaigns),
            'avg_ctr': sum(c.get('insights', {}).get('clicks', 0) for c in campaigns) / 
                      sum(c.get('insights', {}).get('impressions', 0) for c in campaigns) * 100 if 
                      sum(c.get('insights', {}).get('impressions', 0) for c in campaigns) > 0 else 0,
            'top_campaigns_by_spend': sorted(campaigns, 
                                       key=lambda x: x.get('insights', {}).get('spend', 0), 
                                       reverse=True),
            'top_campaigns_by_ctr': sorted(campaigns, 
                                      key=lambda x: x.get('insights', {}).get('clicks', 0) / 
                                                  x.get('insights', {}).get('impressions', 1) * 100, 
                                      reverse=True),
            'ctr_trend': ctr_trend
        },
        'ads': ads
    }
    
    return analysis_results

def generate_test_reports():
    """
    Генерация тестовых отчетов.
    """
    try:
        print("Генерация тестовых отчетов для Facebook Ads Toolkit...")
        
        # Создаем демонстрационные данные
        demo_data = generate_demo_data()
        
        # Сохраняем демо-данные для отладки
        os.makedirs("reports", exist_ok=True)
        save_to_json(demo_data, "reports/demo_data.json")
        
        print(f"Демонстрационные данные созданы и сохранены в reports/demo_data.json")
        
        # Создаем менеджер отчетов
        report_manager = ReportManager(output_dir="reports")
        
        # Генерируем отчет о производительности
        print("Генерация отчета о производительности кампаний...")
        performance_files = report_manager.generate_report(
            template_name="campaign_performance", 
            data=demo_data,
            export_formats=["json", "txt", "csv"],
            custom_filename="demo_performance_report"
        )
        
        print("Отчет о производительности кампаний создан:")
        for format_name, file_path in performance_files.items():
            print(f" - {format_name}: {file_path}")
        
        # Генерируем отчет сравнения
        print("\nГенерация отчета сравнения объявлений...")
        comparison_files = report_manager.generate_report(
            template_name="ad_comparison", 
            data=demo_data,
            export_formats=["json", "txt"],
            custom_filename="demo_comparison_report"
        )
        
        print("Отчет сравнения объявлений создан:")
        for format_name, file_path in comparison_files.items():
            print(f" - {format_name}: {file_path}")
        
        # Создаем графики
        print("\nСоздание графиков...")
        chart_generator = ChartGenerator(output_dir="reports")
        
        # Генерируем все графики
        charts = chart_generator.generate_all_charts(demo_data, "demo_report")
        
        print("Созданы графики:")
        for chart_name, chart_path in charts.items():
            print(f" - {chart_name}: {chart_path}")
        
        print("\nТестовые отчеты успешно созданы!")
            
    except Exception as e:
        logger.error(f"Ошибка при генерации тестовых отчетов: {str(e)}")
        print(f"Ошибка: {str(e)}")
        raise

def main():
    """
    Основная функция.
    """
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Генерация тестовых отчетов
    generate_test_reports()

if __name__ == "__main__":
    main() 