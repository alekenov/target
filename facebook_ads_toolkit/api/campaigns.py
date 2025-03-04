#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с кампаниями Facebook Ads.
Предоставляет функции для получения, создания и обновления рекламных кампаний.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import json
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)

# Константы для повторных попыток
MAX_RETRIES = 3
RETRY_DELAY = 5  # секунды
RATE_LIMIT_DELAY = 60  # секунды

class CampaignManager:
    """
    Менеджер для работы с кампаниями Facebook Ads.
    """
    
    def __init__(self, ad_account_id: str, api_instance=None):
        """
        Инициализация менеджера кампаний.
        
        Args:
            ad_account_id: ID рекламного аккаунта (с или без префикса 'act_')
            api_instance: Экземпляр API Facebook (если None, будет использован глобальный)
        """
        self.ad_account_id = ad_account_id if ad_account_id.startswith('act_') else f'act_{ad_account_id}'
        self.api_instance = api_instance
        self.ad_account = AdAccount(self.ad_account_id, api=self.api_instance)
        self._campaign_cache = {}  # Кэш для кампаний
    
    def get_campaigns(self, 
                     fields: Optional[List[str]] = None, 
                     params: Optional[Dict[str, Any]] = None,
                     use_cache: bool = True,
                     cache_ttl: int = 300) -> List[Dict[str, Any]]:
        """
        Получает список кампаний с обработкой ошибок и кэшированием.
        
        Args:
            fields: Список полей для получения
            params: Параметры запроса
            use_cache: Использовать кэш
            cache_ttl: Время жизни кэша в секундах
            
        Returns:
            List[Dict[str, Any]]: Список кампаний
        """
        # Значения по умолчанию
        if fields is None:
            fields = [
                'id', 'name', 'status', 'objective', 
                'daily_budget', 'lifetime_budget',
                'start_time', 'stop_time', 'created_time'
            ]
        
        if params is None:
            params = {
                'limit': 100,
                'effective_status': ['ACTIVE', 'PAUSED', 'ARCHIVED']
            }
        
        # Проверяем кэш
        cache_key = f"{json.dumps(fields)}_{json.dumps(params)}"
        if use_cache and cache_key in self._campaign_cache:
            cache_time, cache_data = self._campaign_cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < cache_ttl:
                logger.debug(f"Используем кэшированные данные для кампаний ({len(cache_data)} записей)")
                return cache_data
        
        # Получаем данные с повторными попытками
        campaigns = []
        retries = 0
        
        while retries < MAX_RETRIES:
            try:
                logger.info(f"Запрашиваем кампании для аккаунта {self.ad_account_id}")
                campaign_iter = self.ad_account.get_campaigns(
                    fields=fields,
                    params=params
                )
                
                # Собираем все кампании
                campaigns = [campaign.export_all_data() for campaign in campaign_iter]
                logger.info(f"Получено {len(campaigns)} кампаний")
                
                # Сохраняем в кэш
                if use_cache:
                    self._campaign_cache[cache_key] = (datetime.now(), campaigns)
                
                break
            
            except FacebookRequestError as e:
                retries += 1
                error_message = f"Ошибка Facebook API при получении кампаний: {str(e)}"
                
                # Обработка ошибок в зависимости от кода
                if e.api_error_code() == 17:  # Rate limit
                    logger.warning(f"{error_message} (Rate limit). Ожидание {RATE_LIMIT_DELAY} секунд...")
                    time.sleep(RATE_LIMIT_DELAY)
                elif e.api_error_code() in [1, 2]:  # Временные ошибки сервера
                    logger.warning(f"{error_message} (Временная ошибка). Повторная попытка {retries}/{MAX_RETRIES}...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"{error_message} (Код: {e.api_error_code()})")
                    if retries >= MAX_RETRIES:
                        raise
                    time.sleep(RETRY_DELAY)
            
            except Exception as e:
                retries += 1
                logger.error(f"Неожиданная ошибка при получении кампаний: {str(e)}")
                if retries >= MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY)
        
        return campaigns
    
    def get_campaign_by_id(self, 
                          campaign_id: str, 
                          fields: Optional[List[str]] = None,
                          use_cache: bool = True) -> Dict[str, Any]:
        """
        Получает информацию о конкретной кампании по ID.
        
        Args:
            campaign_id: ID кампании
            fields: Список полей для получения
            use_cache: Использовать кэш
            
        Returns:
            Dict[str, Any]: Данные кампании
        """
        if fields is None:
            fields = [
                'id', 'name', 'status', 'objective', 
                'daily_budget', 'lifetime_budget',
                'start_time', 'stop_time', 'created_time',
                'updated_time', 'budget_remaining', 'buying_type',
                'configured_status', 'effective_status'
            ]
        
        # Проверяем кэш для одной кампании
        cache_key = f"campaign_{campaign_id}_{json.dumps(fields)}"
        if use_cache and cache_key in self._campaign_cache:
            cache_time, cache_data = self._campaign_cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < 300:  # TTL 5 минут
                logger.debug(f"Используем кэшированные данные для кампании {campaign_id}")
                return cache_data
        
        # Получаем данные с повторными попытками
        retries = 0
        
        while retries < MAX_RETRIES:
            try:
                logger.info(f"Запрашиваем кампанию {campaign_id}")
                campaign = Campaign(campaign_id, api=self.api_instance)
                campaign_data = campaign.api_get(fields=fields).export_all_data()
                
                # Сохраняем в кэш
                if use_cache:
                    self._campaign_cache[cache_key] = (datetime.now(), campaign_data)
                
                return campaign_data
            
            except FacebookRequestError as e:
                retries += 1
                error_message = f"Ошибка Facebook API при получении кампании {campaign_id}: {str(e)}"
                
                if e.api_error_code() == 17:  # Rate limit
                    logger.warning(f"{error_message} (Rate limit). Ожидание {RATE_LIMIT_DELAY} секунд...")
                    time.sleep(RATE_LIMIT_DELAY)
                elif e.api_error_code() in [1, 2]:  # Временные ошибки сервера
                    logger.warning(f"{error_message} (Временная ошибка). Повторная попытка {retries}/{MAX_RETRIES}...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"{error_message} (Код: {e.api_error_code()})")
                    if retries >= MAX_RETRIES:
                        raise
                    time.sleep(RETRY_DELAY)
            
            except Exception as e:
                retries += 1
                logger.error(f"Неожиданная ошибка при получении кампании {campaign_id}: {str(e)}")
                if retries >= MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY)
        
        raise Exception(f"Не удалось получить кампанию {campaign_id} после {MAX_RETRIES} попыток")
    
    def update_campaign_status(self, campaign_id: str, status: str) -> bool:
        """
        Обновляет статус кампании.
        
        Args:
            campaign_id: ID кампании
            status: Новый статус (ACTIVE, PAUSED, ARCHIVED)
            
        Returns:
            bool: True, если обновление выполнено успешно
        """
        retries = 0
        
        while retries < MAX_RETRIES:
            try:
                logger.info(f"Обновляем статус кампании {campaign_id} на {status}")
                campaign = Campaign(campaign_id, api=self.api_instance)
                result = campaign.api_update(
                    params={'status': status}
                )
                
                # Инвалидируем кэш для этой кампании
                for key in list(self._campaign_cache.keys()):
                    if f"campaign_{campaign_id}" in key:
                        del self._campaign_cache[key]
                
                logger.info(f"Статус кампании {campaign_id} успешно обновлен на {status}")
                return result.success()
            
            except FacebookRequestError as e:
                retries += 1
                error_message = f"Ошибка Facebook API при обновлении статуса кампании {campaign_id}: {str(e)}"
                
                if e.api_error_code() == 17:  # Rate limit
                    logger.warning(f"{error_message} (Rate limit). Ожидание {RATE_LIMIT_DELAY} секунд...")
                    time.sleep(RATE_LIMIT_DELAY)
                elif e.api_error_code() in [1, 2]:  # Временные ошибки сервера
                    logger.warning(f"{error_message} (Временная ошибка). Повторная попытка {retries}/{MAX_RETRIES}...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"{error_message} (Код: {e.api_error_code()})")
                    if retries >= MAX_RETRIES:
                        return False
                    time.sleep(RETRY_DELAY)
            
            except Exception as e:
                retries += 1
                logger.error(f"Неожиданная ошибка при обновлении статуса кампании {campaign_id}: {str(e)}")
                if retries >= MAX_RETRIES:
                    return False
                time.sleep(RETRY_DELAY)
        
        return False
    
    def create_campaign(self, 
                       name: str, 
                       objective: str, 
                       status: str = 'PAUSED',
                       daily_budget: Optional[float] = None,
                       lifetime_budget: Optional[float] = None,
                       special_ad_categories: Optional[List[str]] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       additional_params: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Создает новую рекламную кампанию.
        
        Args:
            name: Название кампании
            objective: Цель кампании (REACH, LINK_CLICKS, и т.д.)
            status: Статус кампании (ACTIVE, PAUSED)
            daily_budget: Дневной бюджет в центах
            lifetime_budget: Общий бюджет в центах
            special_ad_categories: Специальные категории рекламы
            start_time: Время начала кампании
            end_time: Время окончания кампании
            additional_params: Дополнительные параметры
            
        Returns:
            Optional[str]: ID созданной кампании или None в случае ошибки
        """
        # Проверка обязательных параметров
        if not daily_budget and not lifetime_budget:
            raise ValueError("Необходимо указать daily_budget или lifetime_budget")
        
        # Подготовка параметров
        params = {
            'name': name,
            'objective': objective,
            'status': status,
            'special_ad_categories': special_ad_categories or []
        }
        
        # Добавление бюджета
        if daily_budget:
            params['daily_budget'] = int(daily_budget * 100)  # Конвертация в центы
        
        if lifetime_budget:
            params['lifetime_budget'] = int(lifetime_budget * 100)  # Конвертация в центы
        
        # Добавление времени
        if start_time:
            params['start_time'] = start_time.strftime('%Y-%m-%dT%H:%M:%S%z')
        
        if end_time:
            params['end_time'] = end_time.strftime('%Y-%m-%dT%H:%M:%S%z')
        
        # Добавление дополнительных параметров
        if additional_params:
            params.update(additional_params)
        
        # Создание кампании с повторными попытками
        retries = 0
        
        while retries < MAX_RETRIES:
            try:
                logger.info(f"Создаем новую кампанию '{name}' с целью '{objective}'")
                result = self.ad_account.create_campaign(
                    params=params
                )
                
                campaign_id = result['id']
                logger.info(f"Кампания успешно создана с ID: {campaign_id}")
                
                # Инвалидируем кэш для списка кампаний
                self._campaign_cache = {k: v for k, v in self._campaign_cache.items() if not k.startswith('[')}
                
                return campaign_id
            
            except FacebookRequestError as e:
                retries += 1
                error_message = f"Ошибка Facebook API при создании кампании: {str(e)}"
                
                if e.api_error_code() == 17:  # Rate limit
                    logger.warning(f"{error_message} (Rate limit). Ожидание {RATE_LIMIT_DELAY} секунд...")
                    time.sleep(RATE_LIMIT_DELAY)
                elif e.api_error_code() in [1, 2]:  # Временные ошибки сервера
                    logger.warning(f"{error_message} (Временная ошибка). Повторная попытка {retries}/{MAX_RETRIES}...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"{error_message} (Код: {e.api_error_code()})")
                    if retries >= MAX_RETRIES:
                        return None
                    time.sleep(RETRY_DELAY)
            
            except Exception as e:
                retries += 1
                logger.error(f"Неожиданная ошибка при создании кампании: {str(e)}")
                if retries >= MAX_RETRIES:
                    return None
                time.sleep(RETRY_DELAY)
        
        return None
    
    def clear_cache(self) -> None:
        """Очищает кэш кампаний."""
        self._campaign_cache.clear()
        logger.debug("Кэш кампаний очищен")


# Функции для обратной совместимости
def get_campaigns(ad_account_id: str, 
                 api_instance=None, 
                 fields: Optional[List[str]] = None, 
                 params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Получает список кампаний для указанного рекламного аккаунта.
    
    Args:
        ad_account_id: ID рекламного аккаунта
        api_instance: Экземпляр API Facebook
        fields: Список полей для получения
        params: Параметры запроса
        
    Returns:
        List[Dict[str, Any]]: Список кампаний
    """
    manager = CampaignManager(ad_account_id, api_instance)
    return manager.get_campaigns(fields, params)


def get_campaign_by_id(campaign_id: str, 
                      api_instance=None, 
                      fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Получает информацию о конкретной кампании по ID.
    
    Args:
        campaign_id: ID кампании
        api_instance: Экземпляр API Facebook
        fields: Список полей для получения
        
    Returns:
        Dict[str, Any]: Данные кампании
    """
    # Для этой функции не нужен ad_account_id, поэтому используем фиктивное значение
    manager = CampaignManager('act_placeholder', api_instance)
    return manager.get_campaign_by_id(campaign_id, fields)


def update_campaign_status(campaign_id: str, 
                          status: str, 
                          api_instance=None) -> bool:
    """
    Обновляет статус кампании.
    
    Args:
        campaign_id: ID кампании
        status: Новый статус (ACTIVE, PAUSED, ARCHIVED)
        api_instance: Экземпляр API Facebook
        
    Returns:
        bool: True, если обновление выполнено успешно
    """
    manager = CampaignManager('act_placeholder', api_instance)
    return manager.update_campaign_status(campaign_id, status)
