#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Инкрементальный сборщик данных из Facebook Ads API.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

logger = logging.getLogger(__name__)

class IncrementalCollector:
    """Класс для инкрементального сбора данных."""
    
    def __init__(self, account: AdAccount, db_manager):
        """
        Инициализация коллектора.
        
        Args:
            account: Объект рекламного аккаунта Facebook
            db_manager: Менеджер базы данных
        """
        self.account = account
        self.db_manager = db_manager
        self.retry_delay = 60  # Задержка между повторными попытками в секундах
        self.max_retries = 3   # Максимальное количество попыток
        
    def _make_api_call(self, func, *args, **kwargs) -> Optional[Any]:
        """
        Выполняет API-вызов с обработкой ошибок и повторными попытками.
        
        Args:
            func: Функция API для вызова
            *args: Позиционные аргументы для функции
            **kwargs: Именованные аргументы для функции
            
        Returns:
            Результат API-вызова или None в случае ошибки
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
                raise
    
    def collect_incremental_data(self, force_full: bool = False, start_date: datetime = None) -> Dict[str, List[Dict]]:
        """
        Сбор обновленных данных.
        
        Args:
            force_full: Если True, игнорирует последнюю синхронизацию
            start_date: Начальная дата для сбора данных. Если не указана, используется последняя синхронизация
            
        Returns:
            Dict: Словарь с обновленными данными
        """
        # Определяем время последней синхронизации
        if start_date:
            since_time = start_date
        elif not force_full:
            last_sync = self.db_manager.get_last_sync_state('campaigns')
            since_time = last_sync['last_sync_time'] or datetime.now() - timedelta(days=7)
        else:
            since_time = datetime.now() - timedelta(days=30)
            
        logger.info(f"Fetching campaigns updated since {since_time}")
        
        # Собираем данные
        updated_data = {
            'campaigns': self._get_updated_campaigns(since_time),
            'ad_sets': [],
            'ads': [],
            'insights': []
        }
        
        # Для каждой кампании получаем связанные данные
        for campaign in updated_data['campaigns']:
            updated_data['ad_sets'].extend(
                self._get_updated_ad_sets(campaign['id'], since_time)
            )
        
        # Для каждой группы объявлений получаем объявления
        for ad_set in updated_data['ad_sets']:
            updated_data['ads'].extend(
                self._get_updated_ads(ad_set['id'], since_time)
            )
        
        # Получаем статистику для всех объявлений
        ad_ids = [ad['id'] for ad in updated_data['ads']]
        if ad_ids:
            updated_data['insights'] = self._get_insights(ad_ids, since_time)
        
        # Обновляем состояние синхронизации
        now = datetime.now()
        self.db_manager.update_last_sync('campaigns', now)
        self.db_manager.update_last_sync('ad_sets', now)
        self.db_manager.update_last_sync('ads', now)
        self.db_manager.update_last_sync('ad_insights', now)
        
        return updated_data
    
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
            'summary': True
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
            ]
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
            ]
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
            'filtering': [{'field': 'ad.id', 'operator': 'IN', 'value': ad_ids}]
        }
        
        insights = self._make_api_call(self.account.get_insights, params=params)
        return [insight.export_all_data() for insight in insights] if insights else []
