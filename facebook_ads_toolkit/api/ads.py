#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с объявлениями Facebook Ads.
Предоставляет функции для получения и управления объявлениями.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)

# Константы для повторных попыток
MAX_RETRIES = 3
RETRY_DELAY = 5
RATE_LIMIT_DELAY = 60

class AdManager:
    """Менеджер для работы с объявлениями Facebook Ads."""
    
    def __init__(self, ad_account_id: str, api_instance=None):
        """
        Инициализация менеджера объявлений.
        
        Args:
            ad_account_id: ID рекламного аккаунта
            api_instance: Экземпляр API Facebook
        """
        self.ad_account_id = ad_account_id if ad_account_id.startswith('act_') else f'act_{ad_account_id}'
        self.api_instance = api_instance
        self.ad_account = AdAccount(self.ad_account_id, api=self.api_instance)
        self._ad_cache = {}
    
    def _transform_ad_data(self, ad_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Преобразует данные объявления для совместимости.
        
        Args:
            ad_data: Исходные данные объявления
            
        Returns:
            Dict[str, Any]: Преобразованные данные
        """
        if 'adset' in ad_data:
            ad_data['ad_set_id'] = ad_data['adset']['id']
        return ad_data
    
    def get_ads(self, 
                fields: Optional[List[str]] = None,
                params: Optional[Dict[str, Any]] = None,
                use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Получает список объявлений с обработкой ошибок и кэшированием.
        
        Args:
            fields: Список полей для получения
            params: Параметры запроса
            use_cache: Использовать кэш
            
        Returns:
            List[Dict[str, Any]]: Список объявлений
        """
        if fields is None:
            fields = [
                'id', 'name', 'status',
                'adset', 'campaign_id',
                'creative', 'configured_status',
                'effective_status'
            ]
        
        if params is None:
            params = {
                'limit': 100,
                'effective_status': ['ACTIVE', 'PAUSED', 'ARCHIVED']
            }
        
        # Проверяем кэш
        cache_key = f"{json.dumps(fields)}_{json.dumps(params)}"
        if use_cache and cache_key in self._ad_cache:
            cache_time, cache_data = self._ad_cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < 300:
                return cache_data
        
        retries = 0
        while retries < MAX_RETRIES:
            try:
                logger.info(f"Запрашиваем объявления для аккаунта {self.ad_account_id}")
                ads = [
                    self._transform_ad_data(ad.export_all_data())
                    for ad in self.ad_account.get_ads(fields=fields, params=params)
                ]
                
                if use_cache:
                    self._ad_cache[cache_key] = (datetime.now(), ads)
                
                return ads
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    raise
        
        return []
    
    def get_ad_by_id(self, 
                     ad_id: str,
                     fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о конкретном объявлении.
        
        Args:
            ad_id: ID объявления
            fields: Список полей для получения
            
        Returns:
            Optional[Dict[str, Any]]: Данные объявления
        """
        if fields is None:
            fields = [
                'id', 'name', 'status',
                'adset', 'campaign_id',
                'creative', 'configured_status',
                'effective_status', 'tracking_specs',
                'recommendations', 'issues_info'
            ]
        
        retries = 0
        while retries < MAX_RETRIES:
            try:
                ad = Ad(ad_id, api=self.api_instance)
                data = ad.api_get(fields=fields).export_all_data()
                return self._transform_ad_data(data)
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    raise
        
        return None
    
    def update_ad(self, 
                  ad_id: str,
                  data: Dict[str, Any]) -> bool:
        """
        Обновляет объявление.
        
        Args:
            ad_id: ID объявления
            data: Данные для обновления
            
        Returns:
            bool: True если обновление успешно
        """
        retries = 0
        while retries < MAX_RETRIES:
            try:
                ad = Ad(ad_id, api=self.api_instance)
                result = ad.api_update(params=data)
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
        """Очищает кэш объявлений."""
        self._ad_cache.clear()
        logger.debug("Кэш объявлений очищен")


# Функции для обратной совместимости
def get_ads(ad_account_id: str,
            api_instance=None,
            fields: Optional[List[str]] = None,
            params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Получает список объявлений.
    
    Args:
        ad_account_id: ID рекламного аккаунта
        api_instance: Экземпляр API Facebook
        fields: Список полей для получения
        params: Параметры запроса
        
    Returns:
        List[Dict[str, Any]]: Список объявлений
    """
    manager = AdManager(ad_account_id, api_instance)
    return manager.get_ads(fields, params)
