#!/usr/bin/env python
"""
Тестовый скрипт для проверки оптимизированного получения данных о рекламе Facebook.
"""

import sys
import os
import logging
import time
from datetime import datetime, timedelta

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_ads_toolkit.analysis.data_fetchers import AdDataFetcher
from facebook_ads_toolkit.utils.cache_handler import CacheHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для тестирования оптимизаций."""
    
    # Используем новый токен доступа
    access_token = "EAAW4km4ocGkBO6v9qhh0gZAnCBxEvQRqNZCZCw1csy8BdJb4HUZBXM0cZBZClJGA8HLiJZAdK24mMXa6PQZBL5LITH3fLyXgreebyE2KHVjUp6JstedJlkZC1zZBifsTsDB4eYSQRxIDCJBSieNTYhJNojWTqoBuVzXYSQ2mGoUTeLiA0NFpcf7BylWNA98xLrPzWV"
    account_id = "act_259290474190473"  # ID рекламного аккаунта
    
    try:
        # Очистка кэша перед тестом (при необходимости)
        # cache_handler = CacheHandler()
        # cache_handler.clear_all_cache()
        
        # Инициализируем API с новым токеном
        logger.info("Инициализация API с новым токеном...")
        FacebookAdsApi.init(access_token=access_token)
        
        # Получаем аккаунт
        account = AdAccount(account_id)
        logger.info(f"Успешное подключение к рекламному аккаунту: {account_id}")
        
        # Создаем объект для получения данных с включенным кэшированием
        fetcher = AdDataFetcher(account, use_cache=True, cache_expiration=3600)
        
        # Устанавливаем временной диапазон для последних 7 дней
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        fetcher.set_time_range(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        logger.info(f"Установлен временной диапазон: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        
        # Тест 1: Получение активных кампаний с кэшированием
        logger.info("1. Запуск получения активных кампаний")
        start_time = time.time()
        campaigns = fetcher.get_active_campaigns(year_filter='2025')
        elapsed = time.time() - start_time
        logger.info(f"Получено {len(campaigns)} кампаний за {elapsed:.2f} секунд")
        
        # Второй запрос должен использовать кэш
        logger.info("2. Повторный запрос (должен использовать кэш)")
        start_time = time.time()
        campaigns_cached = fetcher.get_active_campaigns(year_filter='2025')
        elapsed = time.time() - start_time
        logger.info(f"Получено {len(campaigns_cached)} кампаний из кэша за {elapsed:.2f} секунд")
        
        # Тест 2: Получение данных в батч-режиме с ограничениями
        logger.info("3. Пакетная обработка с малым размером пакета и большими паузами")
        start_time = time.time()
        data = fetcher.fetch_all_batch(batch_size=5, pause_between_batches=5.0)
        elapsed = time.time() - start_time
        logger.info(f"Пакетная обработка завершена за {elapsed:.2f} секунд")
        logger.info(f"Получено: {len(data['campaigns'])} кампаний, {len(data['adsets'])} групп, {len(data['ads'])} объявлений")
        
        # Тест 3: Параллельная обработка с ограничением потоков
        logger.info("4. Параллельная обработка с 1 потоком (практически последовательная)")
        start_time = time.time()
        data = fetcher.fetch_all_parallel(max_workers=1)
        elapsed = time.time() - start_time
        logger.info(f"Параллельная обработка завершена за {elapsed:.2f} секунд")
        logger.info(f"Получено: {len(data['campaigns'])} кампаний, {len(data['adsets'])} групп, {len(data['ads'])} объявлений")
        
        logger.info("Тестирование оптимизаций завершено успешно")
        return 0
    
    except Exception as e:
        logger.error(f"Ошибка при работе с API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 