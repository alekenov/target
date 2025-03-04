#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с группами объявлений Facebook Ads.
Предоставляет функции для получения и управления группами объявлений.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)

# Константы для повторных попыток
MAX_RETRIES = 3
RETRY_DELAY = 5
RATE_LIMIT_DELAY = 60

class AdSetManager:
    """Менеджер для работы с группами объявлений Facebook Ads."""
    
    def __init__(self, ad_account_id: str, api_instance=None):
        """
        Инициализация менеджера групп объявлений.
        
        Args:
            ad_account_id: ID рекламного аккаунта
            api_instance: Экземпляр API Facebook
        """
        self.ad_account_id = ad_account_id if ad_account_id.startswith('act_') else f'act_{ad_account_id}'
        self.api_instance = api_instance
        self.ad_account = AdAccount(self.ad_account_id, api=self.api_instance)
        self._adset_cache = {}
    
    def get_ad_sets(self, 
                    fields: Optional[List[str]] = None,
                    params: Optional[Dict[str, Any]] = None,
                    use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Получает список групп объявлений с обработкой ошибок и кэшированием.
        
        Args:
            fields: Список полей для получения
            params: Параметры запроса
            use_cache: Использовать кэш
            
        Returns:
            List[Dict[str, Any]]: Список групп объявлений
        """
        if fields is None:
            fields = [
                'id', 'name', 'status', 'campaign_id',
                'daily_budget', 'lifetime_budget',
                'targeting', 'bid_amount',
                'billing_event', 'optimization_goal'
            ]
        
        if params is None:
            params = {
                'limit': 100,
                'effective_status': ['ACTIVE', 'PAUSED', 'ARCHIVED']
            }
        
        # Проверяем кэш
        cache_key = f"{json.dumps(fields)}_{json.dumps(params)}"
        if use_cache and cache_key in self._adset_cache:
            cache_time, cache_data = self._adset_cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < 300:
                return cache_data
        
        retries = 0
        while retries < MAX_RETRIES:
            try:
                logger.info(f"Запрашиваем группы объявлений для аккаунта {self.ad_account_id}")
                ad_sets = [
                    ad_set.export_all_data()
                    for ad_set in self.ad_account.get_ad_sets(fields=fields, params=params)
                ]
                
                if use_cache:
                    self._adset_cache[cache_key] = (datetime.now(), ad_sets)
                
                return ad_sets
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    raise
        
        return []
    
    def get_ad_set_by_id(self, 
                         ad_set_id: str,
                         fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о конкретной группе объявлений.
        
        Args:
            ad_set_id: ID группы объявлений
            fields: Список полей для получения
            
        Returns:
            Optional[Dict[str, Any]]: Данные группы объявлений
        """
        if fields is None:
            fields = [
                'id', 'name', 'status', 'campaign_id',
                'daily_budget', 'lifetime_budget',
                'targeting', 'bid_amount',
                'billing_event', 'optimization_goal',
                'attribution_spec', 'bid_strategy',
                'budget_remaining', 'configured_status',
                'effective_status', 'issues_info'
            ]
        
        retries = 0
        while retries < MAX_RETRIES:
            try:
                ad_set = AdSet(ad_set_id, api=self.api_instance)
                return ad_set.api_get(fields=fields).export_all_data()
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    raise
        
        return None
    
    def update_ad_set(self, 
                      ad_set_id: str,
                      data: Dict[str, Any]) -> bool:
        """
        Обновляет группу объявлений.
        
        Args:
            ad_set_id: ID группы объявлений
            data: Данные для обновления
            
        Returns:
            bool: True если обновление успешно
        """
        retries = 0
        while retries < MAX_RETRIES:
            try:
                ad_set = AdSet(ad_set_id, api=self.api_instance)
                result = ad_set.api_update(params=data)
                return result.success()
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    return False
        
        return False
    
    def clear_cache(self) -> None:
        """Очищает кэш групп объявлений."""
        self._adset_cache.clear()
        logger.debug("Кэш групп объявлений очищен")


# Функции для обратной совместимости
def get_ad_sets(ad_account_id: str,
                api_instance=None,
                fields: Optional[List[str]] = None,
                params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Получает список групп объявлений.
    
    Args:
        ad_account_id: ID рекламного аккаунта
        api_instance: Экземпляр API Facebook
        fields: Список полей для получения
        params: Параметры запроса
        
    Returns:
        List[Dict[str, Any]]: Список групп объявлений
    """
    manager = AdSetManager(ad_account_id, api_instance)
    return manager.get_ad_sets(fields, params)
