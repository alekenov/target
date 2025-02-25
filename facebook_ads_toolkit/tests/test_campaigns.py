#!/usr/bin/env python
"""
Тестовый скрипт для проверки доступа к активным кампаниям Facebook.
"""

import sys
import os
import logging
from datetime import datetime

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для проверки доступа к API."""
    
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
        
        # Получаем только активные кампании
        logger.info("Получение активных кампаний...")
        campaigns = account.get_campaigns(
            params={
                'effective_status': ['ACTIVE'],
                'limit': 100,  # Ограничиваем количество для теста
                'fields': campaign_fields
            }
        )
        
        # Фильтруем только кампании 2025 года
        campaigns_2025 = []
        for campaign in campaigns:
            campaign_data = campaign.export_all_data()
            if 'created_time' in campaign_data:
                campaign_year = campaign_data['created_time'][:4]  # Берем первые 4 символа (год)
                if campaign_year == '2025':
                    campaigns_2025.append(campaign_data)
        
        # Выводим результаты
        logger.info(f"Найдено {len(campaigns_2025)} активных кампаний за 2025 год:")
        for i, campaign in enumerate(campaigns_2025, 1):
            logger.info(f"{i}. {campaign.get('name', 'Без имени')} (ID: {campaign.get('id')})")
            logger.info(f"   Статус: {campaign.get('status')}")
            logger.info(f"   Цель: {campaign.get('objective')}")
            logger.info(f"   Дата создания: {campaign.get('created_time')}")
            logger.info("-" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"Ошибка при работе с API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 