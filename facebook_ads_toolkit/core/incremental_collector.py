#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Инкрементальный сборщик данных из Facebook Ads API с поддержкой контрольных точек
и надежным механизмом восстановления.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import time
from dataclasses import dataclass
from enum import Enum

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

logger = logging.getLogger(__name__)

class CollectionError(Exception):
    """Базовый класс для ошибок сбора данных."""
    pass

class APILimitError(CollectionError):
    """Ошибка превышения лимита API."""
    pass

class NetworkError(CollectionError):
    """Ошибка сети."""
    pass

class DataValidationError(CollectionError):
    """Ошибка валидации данных."""
    pass

class CollectionStatus(Enum):
    """Статусы процесса сбора данных."""
    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

@dataclass
class CollectionProgress:
    """Класс для хранения прогресса сбора данных."""
    total_items: int = 0
    processed_items: int = 0
    start_time: datetime = None
    last_checkpoint_time: datetime = None
    status: CollectionStatus = CollectionStatus.INITIALIZED
    error_count: int = 0
    last_processed_id: str = None

class IncrementalCollector:
    """Класс для инкрементального сбора данных с поддержкой контрольных точек."""
    
    CHECKPOINT_INTERVAL = 100  # Количество элементов между контрольными точками
    
    def __init__(self, account: AdAccount, db_manager):
        """
        Инициализация коллектора.
        
        Args:
            account: Объект рекламного аккаунта Facebook
            db_manager: Менеджер базы данных
        """
        self.account = account
        self.db_manager = db_manager
        self.retry_delay = 60
        self.max_retries = 3
        self.progress = CollectionProgress()
        
    def _save_checkpoint(self, collection_type: str, last_id: str, metadata: Dict) -> None:
        """
        Сохранение контрольной точки в базу данных.
        
        Args:
            collection_type: Тип собираемых данных (campaigns/ad_sets/ads)
            last_id: ID последнего обработанного элемента
            metadata: Дополнительные метаданные для сохранения
        """
        checkpoint_data = {
            'collection_type': collection_type,
            'last_processed_id': last_id,
            'processed_items': self.progress.processed_items,
            'total_items': self.progress.total_items,
            'status': self.progress.status.value,
            'metadata': json.dumps(metadata),
            'timestamp': datetime.now()
        }
        
        self.db_manager.save_checkpoint(checkpoint_data)
        self.progress.last_checkpoint_time = datetime.now()
        logger.info(f"Сохранена контрольная точка: {collection_type}, ID: {last_id}")

    def _load_last_checkpoint(self, collection_type: str) -> Optional[Dict]:
        """
        Загрузка последней контрольной точки из базы данных.
        
        Args:
            collection_type: Тип собираемых данных
            
        Returns:
            Dict: Данные последней контрольной точки или None
        """
        checkpoint = self.db_manager.get_last_checkpoint(collection_type)
        if checkpoint:
            self.progress.processed_items = checkpoint['processed_items']
            self.progress.total_items = checkpoint['total_items']
            self.progress.status = CollectionStatus(checkpoint['status'])
            self.progress.last_processed_id = checkpoint['last_processed_id']
            logger.info(f"Загружена контрольная точка: {collection_type}, ID: {checkpoint['last_processed_id']}")
        return checkpoint

    def _calculate_eta(self) -> str:
        """Расчет оставшегося времени на основе текущей скорости обработки."""
        if not self.progress.start_time or self.progress.processed_items == 0:
            return "неизвестно"
            
        elapsed_time = (datetime.now() - self.progress.start_time).total_seconds()
        items_per_second = self.progress.processed_items / elapsed_time
        remaining_items = self.progress.total_items - self.progress.processed_items
        
        if items_per_second > 0:
            remaining_seconds = remaining_items / items_per_second
            return str(timedelta(seconds=int(remaining_seconds)))
        return "неизвестно"

    def _make_api_call(self, func, *args, **kwargs) -> Optional[Any]:
        """
        Выполняет API-вызов с обработкой ошибок и повторными попытками.
        
        Args:
            func: Функция API для вызова
            *args: Позиционные аргументы для функции
            **kwargs: Именованные аргументы для функции
            
        Returns:
            Результат API-вызова
            
        Raises:
            APILimitError: При превышении лимита API
            NetworkError: При проблемах с сетью
            CollectionError: При других ошибках сбора
        """
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                time.sleep(1)  # Базовая задержка между запросами
                return result
            except Exception as e:
                if "User request limit reached" in str(e):
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Достигнут лимит запросов. Ожидание {self.retry_delay} секунд...")
                        time.sleep(self.retry_delay)
                        continue
                    raise APILimitError("Превышен лимит запросов к API")
                elif "Network" in str(e):
                    raise NetworkError(f"Ошибка сети: {str(e)}")
                else:
                    raise CollectionError(f"Ошибка при сборе данных: {str(e)}")

    def collect_incremental_data(self, force_full: bool = False, start_date: datetime = None) -> Dict[str, List[Dict]]:
        """
        Сбор обновленных данных с поддержкой контрольных точек и восстановления.
        
        Args:
            force_full: Если True, игнорирует последнюю синхронизацию
            start_date: Начальная дата для сбора данных
            
        Returns:
            Dict: Словарь с обновленными данными
        """
        self.progress.start_time = datetime.now()
        self.progress.status = CollectionStatus.IN_PROGRESS
        
        try:
            # Определяем время последней синхронизации
            if start_date:
                since_time = start_date
            elif not force_full:
                checkpoint = self._load_last_checkpoint('campaigns')
                if checkpoint and checkpoint['status'] == CollectionStatus.INTERRUPTED.value:
                    logger.info("Восстановление сбора с последней контрольной точки")
                    since_time = datetime.fromisoformat(json.loads(checkpoint['metadata'])['since_time'])
                else:
                    last_sync = self.db_manager.get_last_sync_state('campaigns')
                    since_time = last_sync['last_sync_time'] or datetime.now() - timedelta(days=7)
            else:
                since_time = datetime.now() - timedelta(days=30)
            
            logger.info(f"Начало сбора данных с {since_time}")
            
            # Собираем данные с контрольными точками
            updated_data = {
                'campaigns': [],
                'ad_sets': [],
                'ads': [],
                'insights': []
            }
            
            # Сбор кампаний
            campaigns = self._collect_with_checkpoints(
                'campaigns',
                lambda: self._get_updated_campaigns(since_time),
                {'since_time': since_time.isoformat()}
            )
            updated_data['campaigns'] = campaigns
            
            # Сбор групп объявлений
            for campaign in campaigns:
                ad_sets = self._collect_with_checkpoints(
                    'ad_sets',
                    lambda: self._get_updated_ad_sets(campaign['id'], since_time),
                    {'campaign_id': campaign['id'], 'since_time': since_time.isoformat()}
                )
                updated_data['ad_sets'].extend(ad_sets)
            
            # Сбор объявлений
            for ad_set in updated_data['ad_sets']:
                ads = self._collect_with_checkpoints(
                    'ads',
                    lambda: self._get_updated_ads(ad_set['id'], since_time),
                    {'ad_set_id': ad_set['id'], 'since_time': since_time.isoformat()}
                )
                updated_data['ads'].extend(ads)
            
            # Сбор статистики
            ad_ids = [ad['id'] for ad in updated_data['ads']]
            if ad_ids:
                insights = self._collect_with_checkpoints(
                    'insights',
                    lambda: self._get_insights(ad_ids, since_time),
                    {'ad_ids': ad_ids, 'since_time': since_time.isoformat()}
                )
                updated_data['insights'] = insights
            
            self.progress.status = CollectionStatus.COMPLETED
            logger.info("Сбор данных успешно завершен")
            
            # Обновляем состояние синхронизации
            now = datetime.now()
            self.db_manager.update_last_sync('campaigns', now)
            self.db_manager.update_last_sync('ad_sets', now)
            self.db_manager.update_last_sync('ads', now)
            self.db_manager.update_last_sync('ad_insights', now)
            
            return updated_data
            
        except Exception as e:
            self.progress.status = CollectionStatus.FAILED
            logger.error(f"Ошибка при сборе данных: {str(e)}")
            raise

    def _collect_with_checkpoints(self, collection_type: str, collector_func, metadata: Dict) -> List[Dict]:
        """
        Выполняет сбор данных с периодическим сохранением контрольных точек.
        
        Args:
            collection_type: Тип собираемых данных
            collector_func: Функция для сбора данных
            metadata: Метаданные для сохранения в контрольной точке
            
        Returns:
            List[Dict]: Собранные данные
        """
        checkpoint = self._load_last_checkpoint(collection_type)
        if checkpoint and checkpoint['status'] == CollectionStatus.COMPLETED.value:
            logger.info(f"Пропуск {collection_type}: уже собрано")
            return []
            
        try:
            items = collector_func()
            self.progress.total_items = len(items)
            
            for i, item in enumerate(items):
                if checkpoint and item['id'] <= checkpoint['last_processed_id']:
                    continue
                    
                self.progress.processed_items += 1
                
                if self.progress.processed_items % self.CHECKPOINT_INTERVAL == 0:
                    self._save_checkpoint(collection_type, item['id'], metadata)
                    eta = self._calculate_eta()
                    logger.info(
                        f"Прогресс {collection_type}: {self.progress.processed_items}/{self.progress.total_items} "
                        f"({(self.progress.processed_items/self.progress.total_items)*100:.1f}%). "
                        f"Осталось времени: {eta}"
                    )
            
            if items:
                self._save_checkpoint(collection_type, items[-1]['id'], metadata)
            
            return items
            
        except Exception as e:
            self.progress.error_count += 1
            logger.error(f"Ошибка при сборе {collection_type}: {str(e)}")
            raise

    def _get_updated_campaigns(self, since_time: datetime) -> List[Dict]:
        """Получение обновленных кампаний."""
        params = {
            'time_range': {
                'since': since_time.strftime('%Y-%m-%d'),
                'until': datetime.now().strftime('%Y-%m-%d')
            },
            'fields': [
                'id', 'name', 'status', 'objective',
                'daily_budget', 'lifetime_budget',
                'start_time', 'stop_time', 'updated_time'
            ],
            'limit': 1000  # Увеличиваем размер пакета
        }
        
        campaigns = self._make_api_call(self.account.get_campaigns, params=params)
        return [campaign.export_all_data() for campaign in campaigns] if campaigns else []

    def _get_updated_ad_sets(self, campaign_id: str, since_time: datetime) -> List[Dict]:
        """Получение обновленных групп объявлений."""
        campaign = Campaign(campaign_id)
        params = {
            'time_range': {
                'since': since_time.strftime('%Y-%m-%d'),
                'until': datetime.now().strftime('%Y-%m-%d')
            },
            'fields': [
                'id', 'campaign_id', 'name', 'status',
                'daily_budget', 'lifetime_budget',
                'targeting', 'updated_time'
            ],
            'limit': 1000
        }
        
        ad_sets = self._make_api_call(campaign.get_ad_sets, params=params)
        return [ad_set.export_all_data() for ad_set in ad_sets] if ad_sets else []

    def _get_updated_ads(self, ad_set_id: str, since_time: datetime) -> List[Dict]:
        """Получение обновленных объявлений."""
        ad_set = AdSet(ad_set_id)
        params = {
            'time_range': {
                'since': since_time.strftime('%Y-%m-%d'),
                'until': datetime.now().strftime('%Y-%m-%d')
            },
            'fields': [
                'id', 'ad_set_id', 'name', 'status',
                'creative', 'updated_time'
            ],
            'limit': 1000
        }
        
        ads = self._make_api_call(ad_set.get_ads, params=params)
        return [ad.export_all_data() for ad in ads] if ads else []

    def _get_insights(self, ad_ids: List[str], since_time: datetime) -> List[Dict]:
        """Получение статистики для объявлений."""
        params = {
            'time_range': {
                'since': since_time.strftime('%Y-%m-%d'),
                'until': datetime.now().strftime('%Y-%m-%d')
            },
            'fields': [
                'ad_id', 'date_start', 'impressions',
                'clicks', 'spend', 'ctr', 'cpc',
                'actions', 'cost_per_action_type'
            ],
            'time_increment': 1,
            'filtering': [{'field': 'ad.id', 'operator': 'IN', 'value': ad_ids}],
            'limit': 1000
        }
        
        insights = self._make_api_call(self.account.get_insights, params=params)
        return [insight.export_all_data() for insight in insights] if insights else []
