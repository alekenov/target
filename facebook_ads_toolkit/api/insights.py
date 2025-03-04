#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы со статистикой Facebook Ads.
Предоставляет функции для получения статистики по кампаниям, группам и объявлениям.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import json
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)

# Константы для повторных попыток
MAX_RETRIES = 3
RETRY_DELAY = 5
RATE_LIMIT_DELAY = 60

class InsightsManager:
    """Менеджер для работы со статистикой Facebook Ads."""
    
    def __init__(self, ad_account_id: str, api_instance=None):
        """
        Инициализация менеджера статистики.
        
        Args:
            ad_account_id: ID рекламного аккаунта
            api_instance: Экземпляр API Facebook
        """
        self.ad_account_id = ad_account_id if ad_account_id.startswith('act_') else f'act_{ad_account_id}'
        self.api_instance = api_instance
        self.ad_account = AdAccount(self.ad_account_id, api=self.api_instance)
        self._insights_cache = {}
    
    def get_insights(self,
                    level: str = 'ad',
                    fields: Optional[List[str]] = None,
                    params: Optional[Dict[str, Any]] = None,
                    use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Получает статистику с указанного уровня (кампания/группа/объявление).
        
        Args:
            level: Уровень статистики (ad, adset, campaign, account)
            fields: Список полей для получения
            params: Параметры запроса
            use_cache: Использовать кэш
            
        Returns:
            List[Dict[str, Any]]: Список с данными статистики
        """
        if fields is None:
            fields = [
                'impressions', 'clicks', 'spend',
                'reach', 'frequency', 'cpm',
                'cpc', 'ctr', 'cost_per_inline_link_click',
                'cost_per_inline_post_engagement',
                'cost_per_unique_click', 'actions'
            ]
        
        if params is None:
            params = {
                'level': level,
                'time_increment': 1,
                'date_preset': 'last_7d'
            }
        
        # Проверяем кэш
        cache_key = f"{level}_{json.dumps(fields)}_{json.dumps(params)}"
        if use_cache and cache_key in self._insights_cache:
            cache_time, cache_data = self._insights_cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < 300:
                return cache_data
        
        retries = 0
        while retries < MAX_RETRIES:
            try:
                logger.info(f"Запрашиваем статистику уровня {level} для аккаунта {self.ad_account_id}")
                insights = [
                    insight.export_all_data()
                    for insight in self.ad_account.get_insights(
                        fields=fields,
                        params=params
                    )
                ]
                
                if use_cache:
                    self._insights_cache[cache_key] = (datetime.now(), insights)
                
                return insights
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    raise
        
        return []
    
    def get_campaign_insights(self,
                            campaign_id: str,
                            fields: Optional[List[str]] = None,
                            params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Получает статистику для конкретной кампании.
        
        Args:
            campaign_id: ID кампании
            fields: Список полей для получения
            params: Параметры запроса
            
        Returns:
            List[Dict[str, Any]]: Статистика кампании
        """
        retries = 0
        while retries < MAX_RETRIES:
            try:
                campaign = Campaign(campaign_id, api=self.api_instance)
                return [
                    insight.export_all_data()
                    for insight in campaign.get_insights(
                        fields=fields,
                        params=params
                    )
                ]
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    raise
        
        return []
    
    def get_ad_set_insights(self,
                           ad_set_id: str,
                           fields: Optional[List[str]] = None,
                           params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Получает статистику для конкретной группы объявлений.
        
        Args:
            ad_set_id: ID группы объявлений
            fields: Список полей для получения
            params: Параметры запроса
            
        Returns:
            List[Dict[str, Any]]: Статистика группы объявлений
        """
        retries = 0
        while retries < MAX_RETRIES:
            try:
                ad_set = AdSet(ad_set_id, api=self.api_instance)
                return [
                    insight.export_all_data()
                    for insight in ad_set.get_insights(
                        fields=fields,
                        params=params
                    )
                ]
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    raise
        
        return []
    
    def get_ad_insights(self,
                       ad_id: str,
                       fields: Optional[List[str]] = None,
                       params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Получает статистику для конкретного объявления.
        
        Args:
            ad_id: ID объявления
            fields: Список полей для получения
            params: Параметры запроса
            
        Returns:
            List[Dict[str, Any]]: Статистика объявления
        """
        retries = 0
        while retries < MAX_RETRIES:
            try:
                ad = Ad(ad_id, api=self.api_instance)
                return [
                    insight.export_all_data()
                    for insight in ad.get_insights(
                        fields=fields,
                        params=params
                    )
                ]
                
            except FacebookRequestError as e:
                retries += 1
                if e.api_error_code() == 17:
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    time.sleep(RETRY_DELAY)
                if retries == MAX_RETRIES:
                    raise
        
        return []
    
    def clear_cache(self) -> None:
        """Очищает кэш статистики."""
        self._insights_cache.clear()
        logger.debug("Кэш статистики очищен")


# Функции для обратной совместимости
def get_account_insights(ad_account_id: str,
                        api_instance=None,
                        fields: Optional[List[str]] = None,
                        params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Получает статистику по рекламному аккаунту.
    
    Args:
        ad_account_id: ID рекламного аккаунта
        api_instance: Экземпляр API Facebook
        fields: Список полей для получения
        params: Параметры запроса
        
    Returns:
        List[Dict[str, Any]]: Статистика аккаунта
    """
    manager = InsightsManager(ad_account_id, api_instance)
    return manager.get_insights(level='account', fields=fields, params=params)
