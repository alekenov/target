#!/usr/bin/env python
"""
Командный интерфейс для оптимизации рекламных кампаний Facebook.
"""

import argparse
import logging
import sys
import os
import json
from datetime import datetime

# Добавляем родительскую директорию в sys.path, чтобы можно было импортировать модули
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.optimization.campaign_optimizer import CampaignOptimizer
from facebook_ads_toolkit.utils.logging_utils import setup_logging

def main():
    """Основная функция для запуска оптимизации рекламных кампаний."""
    # Настраиваем парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Оптимизация рекламных кампаний Facebook.')
    
    parser.add_argument('--days', type=int, default=30,
                       help='Количество дней для анализа (по умолчанию: 30)')
    
    parser.add_argument('--output-dir', type=str, default='reports',
                       help='Директория для сохранения отчетов (по умолчанию: "reports")')
    
    parser.add_argument('--env-path', type=str,
                       help='Путь к файлу .env с параметрами авторизации')
    
    parser.add_argument('--debug', action='store_true', 
                       help='Включить режим отладки (увеличивает детализацию логов)')
    
    parser.add_argument('--recommendations-only', action='store_true',
                       help='Только формирование рекомендаций без внесения изменений')
    
    parser.add_argument('--thresholds', type=str,
                       help='Путь к JSON-файлу с пользовательскими порогами для оптимизации')
    
    parser.add_argument('--optimize-budgets', action='store_true',
                       help='Оптимизировать бюджеты кампаний')
    
    parser.add_argument('--optimize-bids', action='store_true',
                       help='Оптимизировать ставки в группах объявлений')
    
    parser.add_argument('--optimize-statuses', action='store_true',
                       help='Оптимизировать статусы объявлений (пауза/запуск)')
    
    # Разбираем аргументы
    args = parser.parse_args()
    
    # Настраиваем логирование
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(log_level=log_level, log_dir='logs')
    
    logger.info("Запуск оптимизации рекламных кампаний Facebook")
    
    try:
        # Инициализируем авторизацию
        auth = FacebookAuth(args.env_path)
        account, api = auth.initialize()
        
        if not account or not api:
            logger.error("Не удалось инициализировать авторизацию Facebook")
            return 1
        
        # Создаем оптимизатор кампаний
        optimizer = CampaignOptimizer(account, api)
        
        # Загружаем пользовательские пороги, если указаны
        if args.thresholds:
            try:
                with open(args.thresholds, 'r', encoding='utf-8') as f:
                    thresholds = json.load(f)
                optimizer.set_thresholds(thresholds)
                logger.info(f"Загружены пользовательские пороги из {args.thresholds}")
            except Exception as e:
                logger.error(f"Ошибка при загрузке порогов: {str(e)}")
        
        # Запускаем анализ
        logger.info(f"Анализ данных за последние {args.days} дней...")
        analysis_results = optimizer.analyze_account(days=args.days)
        
        # Определяем, какие типы оптимизации нужно выполнить
        optimization_types = []
        if args.optimize_budgets:
            optimization_types.append("бюджеты")
        if args.optimize_bids:
            optimization_types.append("ставки")
        if args.optimize_statuses:
            optimization_types.append("статусы")
        
        # Если ничего конкретно не выбрано, оптимизируем всё
        if not optimization_types:
            optimization_types = ["бюджеты", "ставки", "статусы"]
            logger.info("Параметры оптимизации не указаны, будет выполнена полная оптимизация")
        else:
            logger.info(f"Будут оптимизированы: {', '.join(optimization_types)}")
        
        # Формируем отчет (либо рекомендации, либо применяем изменения)
        if args.recommendations_only:
            logger.info("Формирование рекомендаций по оптимизации...")
            results = optimizer.get_optimization_recommendations(analysis_results)
            report_type = "recommendations"
        else:
            logger.info("Применение оптимизаций...")
            
            # Создаем патчи для мокинга методов API, которые не нужно выполнять
            if "бюджеты" not in optimization_types:
                original_budget_update = optimizer._optimize_budgets
                optimizer._optimize_budgets = lambda x: []
            
            if "ставки" not in optimization_types:
                original_bid_update = optimizer._optimize_bids
                optimizer._optimize_bids = lambda x: []
            
            if "статусы" not in optimization_types:
                original_status_update = optimizer._optimize_ad_statuses
                optimizer._optimize_ad_statuses = lambda x: []
            
            # Выполняем оптимизацию
            results = optimizer.optimize_campaigns(analysis_results)
            report_type = "optimizations"
            
            # Восстанавливаем исходные методы
            if "бюджеты" not in optimization_types:
                optimizer._optimize_budgets = original_budget_update
            
            if "ставки" not in optimization_types:
                optimizer._optimize_bids = original_bid_update
            
            if "статусы" not in optimization_types:
                optimizer._optimize_ad_statuses = original_status_update
        
        # Создаем директорию для отчетов, если её нет
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Формируем имя файла отчета
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(
            args.output_dir, 
            f"fb_ads_{report_type}_{timestamp}.json"
        )
        
        # Сохраняем результаты в файл
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Результаты сохранены в файл: {output_file}")
        
        # Выводим краткую статистику
        budget_changes = results.get('budget_changes', [])
        bid_changes = results.get('bid_changes', [])
        status_changes = results.get('status_changes', [])
        
        print("\n=== Статистика оптимизации ===")
        print(f"Изменения бюджетов: {len(budget_changes)}")
        print(f"Изменения ставок: {len(bid_changes)}")
        print(f"Изменения статусов объявлений: {len(status_changes)}")
        print(f"Файл отчета: {output_file}")
        
        return 0
        
    except Exception as e:
        logger.exception(f"Произошла ошибка при оптимизации: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 