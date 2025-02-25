#!/usr/bin/env python
"""
Командный интерфейс для анализа рекламы Facebook.
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timedelta

# Добавляем родительскую директорию в sys.path, чтобы можно было импортировать модули
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.analysis.data_fetchers import AdDataFetcher
from facebook_ads_toolkit.analysis.ad_analyzer import AdAnalyzer
from facebook_ads_toolkit.analysis.exporters import AnalysisExporter
from facebook_ads_toolkit.utils.logging_utils import setup_logging

def main():
    """Основная функция для запуска анализа рекламы."""
    # Настраиваем парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Анализ рекламы Facebook.')
    
    parser.add_argument('--days', type=int, default=14,
                       help='Количество дней для анализа (по умолчанию: 14)')
    
    parser.add_argument('--start-date', type=str,
                       help='Начальная дата анализа (YYYY-MM-DD)')
    
    parser.add_argument('--end-date', type=str,
                       help='Конечная дата анализа (YYYY-MM-DD)')
    
    parser.add_argument('--output-dir', type=str, default='reports',
                       help='Директория для сохранения отчетов (по умолчанию: "reports")')
    
    parser.add_argument('--env-path', type=str,
                       help='Путь к файлу .env с параметрами авторизации')
    
    parser.add_argument('--debug', action='store_true', 
                       help='Включить режим отладки (увеличивает детализацию логов)')
    
    parser.add_argument('--export-format', type=str, choices=['json', 'csv', 'txt', 'all'],
                       default='all', help='Формат экспорта результатов (по умолчанию: all)')
    
    parser.add_argument('--parallel', action='store_true',
                       help='Использовать параллельную обработку для ускорения анализа')
    
    parser.add_argument('--workers', type=int, default=2,
                       help='Количество рабочих потоков для параллельной обработки (по умолчанию: 2)')
    
    parser.add_argument('--year-filter', type=str, default='2025',
                       help='Фильтрация кампаний по году (по умолчанию: 2025, используйте "all" для всех лет)')
    
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Размер пакета для обработки (по умолчанию: 10)')
    
    parser.add_argument('--pause', type=float, default=3.0,
                       help='Пауза между запросами в секундах (по умолчанию: 3.0)')
    
    parser.add_argument('--limit-campaigns', type=int, default=50,
                       help='Максимальное количество кампаний для анализа (по умолчанию: 50)')
    
    parser.add_argument('--no-cache', action='store_true',
                       help='Отключить кэширование запросов к API')
    
    parser.add_argument('--cache-ttl', type=int, default=3600,
                       help='Время жизни кэша в секундах (по умолчанию: 3600, т.е. 1 час)')
    
    parser.add_argument('--clear-cache', action='store_true',
                       help='Очистить существующий кэш перед запуском')
    
    # Разбираем аргументы
    args = parser.parse_args()
    
    # Настраиваем логирование
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(log_level=log_level, log_dir='logs')
    
    logger.info("Запуск анализа рекламы Facebook")
    
    try:
        # Инициализируем авторизацию
        auth = FacebookAuth(args.env_path)
        account, api = auth.initialize()
        
        if not account or not api:
            logger.error("Не удалось инициализировать авторизацию Facebook")
            return 1
        
        # Определяем временной диапазон
        time_range = None
        if args.start_date and args.end_date:
            time_range = {'since': args.start_date, 'until': args.end_date}
            logger.info(f"Установлен временной диапазон: {args.start_date} - {args.end_date}")
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=args.days)
            time_range = {
                'since': start_date.strftime('%Y-%m-%d'),
                'until': end_date.strftime('%Y-%m-%d')
            }
            logger.info(f"Установлен временной диапазон: последние {args.days} дней")
        
        # Получаем данные
        fetcher = AdDataFetcher(account, api, use_cache=not args.no_cache, cache_expiration=args.cache_ttl)
        
        # Очищаем кэш, если нужно
        if args.clear_cache and not args.no_cache:
            from facebook_ads_toolkit.utils.cache_handler import CacheHandler
            cache_handler = CacheHandler()
            deleted = cache_handler.clear_all_cache()
            logger.info(f"Очищено {deleted} файлов кэша")
        
        if time_range:
            fetcher.set_time_range(time_range['since'], time_range['until'])
        
        logger.info("Получение данных о рекламе...")
        
        # Настраиваем год для фильтрации
        year_filter = args.year_filter
        if year_filter.lower() == 'all':
            year_filter = None
            logger.info("Анализ кампаний за все годы")
        else:
            logger.info(f"Анализ кампаний только за {year_filter} год")
        
        # Выбираем метод получения данных (параллельный или пакетный)
        if args.parallel:
            logger.info(f"Используется параллельная обработка с {args.workers} потоками")
            # Исправляем лямбда-выражение, чтобы оно корректно принимало параметр year_filter
            original_get_campaigns = fetcher.get_active_campaigns
            
            # Создаем новую функцию, сохраняющую параметр year_filter
            def get_campaigns_with_year_filter(limit=1000, year_filter=None):
                return original_get_campaigns(limit=limit, year_filter=year_filter or args.year_filter)
            
            # Переопределяем метод
            fetcher.get_active_campaigns = get_campaigns_with_year_filter
            
            ad_data = fetcher.fetch_all_parallel(max_workers=args.workers)
        else:
            logger.info(f"Используется последовательная пакетная обработка (размер пакета: {args.batch_size}, пауза: {args.pause}с)")
            ad_data = fetcher.fetch_all_batch(batch_size=args.batch_size, pause_between_batches=args.pause)
        
        # Анализируем данные
        analyzer = AdAnalyzer(ad_data)
        results = analyzer.analyze()
        
        # Выводим сводку
        analyzer.print_summary()
        
        # Экспортируем результаты
        exporter = AnalysisExporter(results, output_dir=args.output_dir)
        
        if args.export_format == 'json':
            exporter.export_to_json()
        elif args.export_format == 'csv':
            exporter.export_campaign_summary_to_csv()
            exporter.export_ad_performance_to_csv()
        elif args.export_format == 'txt':
            exporter.generate_performance_report()
        else:  # 'all'
            export_paths = exporter.export_all()
            logger.info(f"Экспортированы отчеты: {', '.join(export_paths.values())}")
        
        logger.info("Анализ рекламы успешно завершен")
        return 0
        
    except Exception as e:
        logger.exception(f"Произошла ошибка при анализе рекламы: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 