#!/usr/bin/env python
"""
Тестовый скрипт для проверки доступа к активным кампаниям Facebook с кэшированием.
"""

import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_ads_toolkit.utils.cache_handler import CacheHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_campaigns_with_cache(account: AdAccount, year_filter: str = '2025') -> List[Dict[str, Any]]:
    """
    Получение рекламных кампаний с использованием кэширования.
    
    Args:
        account: Рекламный аккаунт
        year_filter: Год для фильтрации кампаний
        
    Returns:
        List[Dict[str, Any]]: Список кампаний
    """
    # Инициализируем обработчик кэша с временем жизни 1 час
    cache_handler = CacheHandler(expiration_time=3600)
    
    # Определяем поля для получения данных о кампаниях
    campaign_fields = [
        'id',
        'name',
        'objective',
        'status',
        'daily_budget',
        'lifetime_budget',
        'created_time',
        'updated_time',
        'start_time',
    ]
    
    # Параметры запроса
    params = {
        'effective_status': ['ACTIVE'],
        'limit': 100,
        'fields': campaign_fields,
        'year_filter': year_filter
    }
    
    # Пытаемся получить данные из кэша
    cache_data = cache_handler.get_from_cache('campaigns', params)
    
    if cache_data:
        logger.info("Данные загружены из кэша")
        return cache_data
    
    # Если данных в кэше нет, делаем запрос к API
    logger.info("Получение данных из API...")
    campaigns = account.get_campaigns(
        params={
            'effective_status': ['ACTIVE'],
            'limit': params['limit'],
            'fields': params['fields']
        }
    )
    
    # Фильтруем кампании по году
    campaigns_filtered = []
    for campaign in campaigns:
        campaign_data = campaign.export_all_data()
        if 'created_time' in campaign_data:
            campaign_year = campaign_data['created_time'][:4]
            if year_filter is None or campaign_year == year_filter:
                campaigns_filtered.append(campaign_data)
    
    # Сохраняем результаты в кэш
    cache_handler.save_to_cache('campaigns', params, campaigns_filtered)
    logger.info("Данные сохранены в кэш")
    
    return campaigns_filtered

def main():
    """Основная функция для проверки доступа к API с кэшированием."""
    
    # Используем новый токен доступа
    access_token = "EAAW4km4ocGkBO6v9qhh0gZAnCBxEvQRqNZCZCw1csy8BdJb4HUZBXM0cZBZClJGA8HLiJZAdK24mMXa6PQZBL5LITH3fLyXgreebyE2KHVjUp6JstedJlkZC1zZBifsTsDB4eYSQRxIDCJBSieNTYhJNojWTqoBuVzXYSQ2mGoUTeLiA0NFpcf7BylWNA98xLrPzWV"
    account_id = "act_259290474190473"  # ID рекламного аккаунта
    
    try:
        # Инициализируем API с новым токеном
        logger.info("Инициализация API с новым токеном...")
        FacebookAdsApi.init(access_token=access_token)
        
        # Получаем аккаунт
        account = AdAccount(account_id)
        logger.info(f"Успешное подключение к рекламному аккаунту: {account_id}")
        
        # Получаем кампании с использованием кэширования
        campaigns = get_campaigns_with_cache(account, year_filter='2025')
        
        # Выводим результаты
        logger.info(f"Найдено {len(campaigns)} активных кампаний за 2025 год:")
        for i, campaign in enumerate(campaigns, 1):
            logger.info(f"{i}. {campaign.get('name', 'Без имени')} (ID: {campaign.get('id')})")
            logger.info(f"   Статус: {campaign.get('status')}")
            logger.info(f"   Цель: {campaign.get('objective')}")
            logger.info(f"   Дата создания: {campaign.get('created_time')}")
            logger.info("-" * 80)
        
        # Демонстрируем, что повторный запуск использует кэш
        logger.info("\nВторой запуск должен использовать кэш:")
        campaigns_cached = get_campaigns_with_cache(account, year_filter='2025')
        logger.info(f"Во втором запуске найдено {len(campaigns_cached)} кампаний")
        
        return 0
    
    except Exception as e:
        logger.error(f"Ошибка при работе с API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 