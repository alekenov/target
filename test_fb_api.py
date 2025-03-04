#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Тестирование подключения к Facebook API.
"""

import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from facebook_business.adobjects.adaccount import AdAccount

from facebook_ads_toolkit.core.authenticator import FacebookAuth

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_fb_api():
    """Тестирование подключения к Facebook API и получения основных данных."""
    load_dotenv()

    try:
        # Инициализация Facebook API
        auth = FacebookAuth()
        account, api = auth.initialize()
        
        if not account or not api:
            logger.error("Ошибка инициализации Facebook API")
            return
        
        logger.info(f"Успешное подключение к Facebook API для аккаунта {account.get_id()}")
        
        # Получение активных кампаний
        campaigns = account.get_campaigns(
            fields=['name', 'status', 'objective', 'daily_budget', 'lifetime_budget', 'start_time', 'stop_time'],
            params={'effective_status': ['ACTIVE', 'PAUSED']}
        )
        
        logger.info(f"Получено кампаний: {len(campaigns)}")
        
        # Вывод информации о первых 5 кампаниях
        for i, campaign in enumerate(campaigns[:5]):
            logger.info(f"Кампания {i+1}: {campaign['name']} (статус: {campaign.get('status')})")
            
        # Получение групп объявлений для первой кампании
        if campaigns:
            ad_sets = campaigns[0].get_ad_sets(
                fields=['name', 'status', 'daily_budget', 'lifetime_budget', 'targeting']
            )
            
            logger.info(f"Получено групп объявлений для кампании '{campaigns[0]['name']}': {len(ad_sets)}")
            
            # Вывод информации о первых 3 группах объявлений
            for i, ad_set in enumerate(ad_sets[:3]):
                logger.info(f"Группа объявлений {i+1}: {ad_set['name']} (статус: {ad_set.get('status')})")
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании Facebook API: {str(e)}")

if __name__ == "__main__":
    test_fb_api()
