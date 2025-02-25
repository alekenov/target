#!/usr/bin/env python
"""
Скрипт для отслеживания изменений в рекламном кабинете Facebook.
Позволяет получать и анализировать историю изменений за указанный период.
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.analysis.activity_tracker import ActivityTracker

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_results(results, output_dir='reports', filename=None):
    """
    Сохранение результатов в файл.
    
    Args:
        results: Результаты для сохранения
        output_dir: Директория для сохранения
        filename: Имя файла (если None, генерируется автоматически)
    
    Returns:
        str: Путь к сохраненному файлу
    """
    os.makedirs(output_dir, exist_ok=True)
    
    if filename is None:
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"changes_report_{date_str}.json"
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Результаты сохранены в файл: {filepath}")
    return filepath

def print_summary(stats):
    """
    Вывод сводки по изменениям.
    
    Args:
        stats: Статистика изменений
    """
    print("\n" + "=" * 80)
    print("СВОДКА ПО ИЗМЕНЕНИЯМ В РЕКЛАМНОМ КАБИНЕТЕ")
    print("=" * 80)
    
    print(f"\nВсего активностей: {stats['total_activities']}")
    print(f"Изменений в кампаниях: {stats['total_campaign_changes']}")
    print(f"Изменений в группах объявлений: {stats['total_adset_changes']}")
    print(f"Изменений в объявлениях: {stats['total_ad_changes']}")
    
    print("\nАКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ:")
    for user, count in stats['users_activity'].items():
        print(f"- {user}: {count} действий")
    
    if stats['campaigns_modified']:
        print("\nИЗМЕНЕННЫЕ КАМПАНИИ (топ 5):")
        for i, campaign in enumerate(stats['campaigns_modified'][:5], 1):
            print(f"{i}. {campaign['name']} (ID: {campaign['id']})")
            print(f"   Количество изменений: {campaign['changes_count']}")
            print(f"   Последнее изменение: {campaign['last_change']}")
    
    if stats['adsets_modified']:
        print("\nИЗМЕНЕННЫЕ ГРУППЫ ОБЪЯВЛЕНИЙ (топ 5):")
        for i, adset in enumerate(stats['adsets_modified'][:5], 1):
            print(f"{i}. {adset['name']} (ID: {adset['id']})")
            print(f"   Количество изменений: {adset['changes_count']}")
            print(f"   Последнее изменение: {adset['last_change']}")
    
    if stats['ads_modified']:
        print("\nИЗМЕНЕННЫЕ ОБЪЯВЛЕНИЯ (топ 5):")
        for i, ad in enumerate(stats['ads_modified'][:5], 1):
            print(f"{i}. {ad['name']} (ID: {ad['id']})")
            print(f"   Количество изменений: {ad['changes_count']}")
            print(f"   Последнее изменение: {ad['last_change']}")
    
    print("=" * 80 + "\n")

def main():
    """Основная функция для запуска отслеживания изменений."""
    parser = argparse.ArgumentParser(description="Отслеживание изменений в рекламном кабинете Facebook")
    
    parser.add_argument("--days", type=int, default=14,
                        help="Количество дней для анализа (по умолчанию 14)")
    
    parser.add_argument("--output-dir", type=str, default="reports",
                        help="Директория для сохранения отчетов (по умолчанию 'reports')")
    
    parser.add_argument("--use-cache", action="store_true",
                        help="Использовать кэширование")
    
    parser.add_argument("--clear-cache", action="store_true",
                        help="Очистить кэш перед запуском")
    
    parser.add_argument("--debug", action="store_true",
                        help="Включить расширенное логирование")
    
    parser.add_argument("--access-token", type=str,
                        default="EAAW4km4ocGkBO6v9qhh0gZAnCBxEvQRqNZCZCw1csy8BdJb4HUZBXM0cZBZClJGA8HLiJZAdK24mMXa6PQZBL5LITH3fLyXgreebyE2KHVjUp6JstedJlkZC1zZBifsTsDB4eYSQRxIDCJBSieNTYhJNojWTqoBuVzXYSQ2mGoUTeLiA0NFpcf7BylWNA98xLrPzWV",
                        help="Токен доступа к API Facebook")
    
    parser.add_argument("--account-id", type=str,
                        default="act_259290474190473",
                        help="ID рекламного аккаунта")
    
    parser.add_argument("--campaign-id", type=str,
                        help="ID конкретной кампании для анализа (опционально)")
    
    parser.add_argument("--adset-id", type=str,
                        help="ID конкретной группы объявлений для анализа (опционально)")
    
    parser.add_argument("--ad-id", type=str,
                        help="ID конкретного объявления для анализа (опционально)")
    
    parser.add_argument("--full-report", action="store_true",
                        help="Получить полный отчет по всем изменениям")
    
    args = parser.parse_args()
    
    # Настройка уровня логирования
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Включен режим отладки")
    
    # Инициализация кэша
    if args.use_cache:
        logger.info("Кэширование включено")
        
        if args.clear_cache:
            from facebook_ads_toolkit.utils.cache_handler import CacheHandler
            cache_handler = CacheHandler()
            cache_handler.clear_cache()
            logger.info("Кэш очищен")
    
    try:
        # Инициализация API
        FacebookAdsApi.init(access_token=args.access_token)
        account = AdAccount(args.account_id)
        
        # Создаем трекер активности
        tracker = ActivityTracker(account, use_cache=args.use_cache)
        
        if args.campaign_id:
            # Анализ одной указанной кампании
            logger.info(f"Получение изменений для кампании: {args.campaign_id}")
            changes = tracker.get_campaign_changes(args.campaign_id, days=args.days)
            
            # Сохраняем результаты
            filename = f"campaign_changes_{args.campaign_id}_{datetime.now().strftime('%Y%m%d')}.json"
            save_results(changes, args.output_dir, filename)
            
            # Выводим информацию
            print(f"\nПолучено {len(changes.get('changes', []))} изменений для кампании {args.campaign_id}")
            
        elif args.adset_id:
            # Анализ одной указанной группы объявлений
            logger.info(f"Получение изменений для группы объявлений: {args.adset_id}")
            changes = tracker.get_adset_changes(args.adset_id, days=args.days)
            
            # Сохраняем результаты
            filename = f"adset_changes_{args.adset_id}_{datetime.now().strftime('%Y%m%d')}.json"
            save_results(changes, args.output_dir, filename)
            
            # Выводим информацию
            print(f"\nПолучено {len(changes.get('changes', []))} изменений для группы объявлений {args.adset_id}")
            
        elif args.ad_id:
            # Анализ одного указанного объявления
            logger.info(f"Получение изменений для объявления: {args.ad_id}")
            changes = tracker.get_ad_changes(args.ad_id, days=args.days)
            
            # Сохраняем результаты
            filename = f"ad_changes_{args.ad_id}_{datetime.now().strftime('%Y%m%d')}.json"
            save_results(changes, args.output_dir, filename)
            
            # Выводим информацию
            print(f"\nПолучено {len(changes.get('changes', []))} изменений для объявления {args.ad_id}")
            
        elif args.full_report:
            # Получаем все изменения
            logger.info(f"Получение всех изменений за последние {args.days} дней...")
            all_changes = tracker.get_all_changes(days=args.days)
            
            # Сохраняем полный отчет
            filename = f"full_changes_report_{datetime.now().strftime('%Y%m%d')}.json"
            save_results(all_changes, args.output_dir, filename)
            
            # Выводим информацию
            print("\nПолный отчет по изменениям сохранен")
            
        else:
            # Получаем активность по аккаунту
            logger.info(f"Получение активности по аккаунту за последние {args.days} дней...")
            activity = tracker.get_account_activity(days=args.days)
            
            # Анализируем изменения
            changes = {
                'account_activity': activity,
                'campaign_changes': [],
                'adset_changes': [],
                'ad_changes': []
            }
            
            stats = tracker.analyze_changes(changes)
            
            # Сохраняем результаты
            filename = f"account_activity_{datetime.now().strftime('%Y%m%d')}.json"
            save_results(stats, args.output_dir, filename)
            
            # Выводим сводку
            print_summary(stats)
        
        return 0
    
    except Exception as e:
        logger.error(f"Ошибка при отслеживании изменений: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 