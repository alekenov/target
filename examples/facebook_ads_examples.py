#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Примеры использования функций для работы с Facebook Ads API.
"""

import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.api.facebook_ads_api import (
    get_all_ad_sets,
    get_all_ads,
    get_ads_insights_batch,
    get_ad_creatives_batch,
    get_account_summary
)
from facebook_ads_toolkit.db.batch_operations import (
    save_ads_batch,
    save_insights_batch,
    cleanup_old_insights
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция с примерами использования."""
    try:
        # Загрузка переменных окружения
        load_dotenv()
        account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')
        
        if not account_id:
            raise ValueError("Не указан ID рекламного аккаунта")
            
        # Инициализация Facebook API
        auth = FacebookAuth()
        if not auth.validate_access():
            raise ValueError("Ошибка доступа к Facebook API")
            
        # 1. Получение сводки по аккаунту
        logger.info("Получение сводки по аккаунту...")
        account_summary = get_account_summary(account_id)
        logger.info(f"Информация об аккаунте: {account_summary.get('account_info', {})}")
        
        # 2. Получение всех групп объявлений
        logger.info("Получение групп объявлений...")
        ad_sets = get_all_ad_sets(account_id, status_filter=['ACTIVE', 'PAUSED'])
        logger.info(f"Получено {len(ad_sets)} групп объявлений")
        
        # 3. Получение всех объявлений
        logger.info("Получение объявлений...")
        ads = get_all_ads(account_id, status_filter=['ACTIVE', 'PAUSED'])
        logger.info(f"Получено {len(ads)} объявлений")
        
        # 4. Сохранение объявлений в БД
        if ads:
            logger.info("Сохранение объявлений в базу данных...")
            if save_ads_batch(ads):
                logger.info("Объявления успешно сохранены")
            else:
                logger.error("Ошибка при сохранении объявлений")
                
        # 5. Получение креативов для объявлений
        if ads:
            ad_ids = [ad['id'] for ad in ads]
            logger.info("Получение креативов...")
            creatives = get_ad_creatives_batch(account_id, ad_ids)
            logger.info(f"Получено {len(creatives)} креативов")
            
        # 6. Получение статистики за последние 7 дней
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        logger.info("Получение статистики...")
        insights = get_ads_insights_batch(
            account_id,
            start_date=start_date,
            end_date=end_date,
            level='ad'
        )
        logger.info(f"Получено {len(insights)} записей статистики")
        
        # 7. Сохранение статистики в БД
        if insights:
            logger.info("Сохранение статистики в базу данных...")
            if save_insights_batch(insights):
                logger.info("Статистика успешно сохранена")
            else:
                logger.error("Ошибка при сохранении статистики")
                
        # 8. Очистка старых данных
        logger.info("Очистка устаревших данных...")
        if cleanup_old_insights(days=90):
            logger.info("Устаревшие данные успешно удалены")
        else:
            logger.error("Ошибка при удалении устаревших данных")
            
    except Exception as e:
        logger.error(f"Ошибка при выполнении примеров: {e}")
        raise

if __name__ == '__main__':
    main() 