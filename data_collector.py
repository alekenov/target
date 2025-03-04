#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Основной скрипт для сбора данных о рекламных кампаниях Facebook.
Использует модули из facebook_ads_toolkit для работы с API и базой данных.
"""

import os
import logging
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv

from facebook_business.adobjects.adaccount import AdAccount

from facebook_ads_toolkit.core.authenticator import FacebookAuth
from facebook_ads_toolkit.core.incremental_collector import IncrementalCollector
from facebook_ads_toolkit.db.db_manager import DatabaseManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class DataCollector:
    """Класс для сбора и сохранения данных из Facebook Ads."""
    
    def __init__(self, ad_account_id: str):
        """
        Инициализация коллектора данных.
        
        Args:
            ad_account_id: ID рекламного аккаунта
        """
        # Инициализация Facebook API
        auth = FacebookAuth()
        self.account, self.api = auth.initialize()
        if not self.account or not self.api:
            raise ValueError("Ошибка инициализации Facebook API")
            
        # Убираем префикс 'act_' если он есть
        ad_account_id = ad_account_id.replace('act_', '')
            
        # Инициализация менеджеров
        self.db_manager = DatabaseManager()
        self.incremental_collector = IncrementalCollector(
            AdAccount(f'act_{ad_account_id}'),
            self.db_manager
        )
        
        logger.info(f"Инициализирован коллектор данных для аккаунта {ad_account_id}")
    
    def collect_and_save_data(self, force_full_sync: bool = False, start_date: datetime = None) -> None:
        """
        Собирает и сохраняет данные инкрементально.
        
        Args:
            force_full_sync: Если True, игнорирует последнюю синхронизацию и собирает все данные
            start_date: Начальная дата для сбора исторических данных
        """
        try:
            # Получаем обновленные данные
            updated_data = self.incremental_collector.collect_incremental_data(start_date=start_date)
            
            # Сохраняем кампании
            if updated_data['campaigns']:
                self.db_manager.upsert_campaigns(updated_data['campaigns'])
                logger.info(f"Обновлено {len(updated_data['campaigns'])} кампаний")
            
            # Сохраняем группы объявлений
            if updated_data['ad_sets']:
                self.db_manager.upsert_ad_sets(updated_data['ad_sets'])
                logger.info(f"Обновлено {len(updated_data['ad_sets'])} групп объявлений")
            
            # Сохраняем объявления
            if updated_data['ads']:
                self.db_manager.upsert_ads(updated_data['ads'])
                logger.info(f"Обновлено {len(updated_data['ads'])} объявлений")
            
            # Сохраняем статистику
            if updated_data['insights']:
                self.db_manager.upsert_insights(updated_data['insights'])
                logger.info(f"Обновлено {len(updated_data['insights'])} записей статистики")
            
            logger.info("Инкрементальное обновление данных успешно завершено")
            
        except Exception as e:
            logger.error(f"Ошибка при сборе данных: {str(e)}")
            # Обновляем статус синхронизации с ошибкой
            now = datetime.now()
            for entity_type in ['campaigns', 'ad_sets', 'ads', 'ad_insights']:
                self.db_manager.update_last_sync(
                    entity_type,
                    now,
                    status='error',
                    error_message=str(e)
                )
            raise

def main():
    """Основная функция скрипта."""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Сбор данных из Facebook Ads')
    parser.add_argument('--account', type=str,
                       default=os.getenv('FB_ACCOUNT_ID'),
                       help='ID рекламного аккаунта')
    parser.add_argument('--force-full', action='store_true',
                       help='Принудительно собрать все данные, игнорируя инкрементальный режим')
    parser.add_argument('--days', type=int,
                       help='Количество дней для сбора исторических данных')
    
    args = parser.parse_args()
    
    if not args.account:
        logger.error("Не указан ID рекламного аккаунта")
        return
    
    try:
        collector = DataCollector(args.account)
        if args.days:
            # Если указано количество дней, собираем данные за период
            start_date = datetime.now() - timedelta(days=args.days)
            collector.collect_and_save_data(force_full_sync=True, start_date=start_date)
            logger.info(f"Собраны данные за последние {args.days} дней")
        else:
            # Иначе работаем в инкрементальном режиме
            collector.collect_and_save_data(force_full_sync=args.force_full)
        logger.info("Сбор данных успешно завершен")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении скрипта: {str(e)}")


if __name__ == "__main__":
    main()
