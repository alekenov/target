#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с Facebook Ads API.
Содержит функции для получения данных о группах объявлений, объявлениях и статистике.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError

from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.utils.api_error_handler import ApiErrorHandler, with_error_handling
from facebook_ads_toolkit.utils.logging_utils import log_execution_time, get_logger

# Настройка логирования
logger = get_logger(__name__)

# Инициализация общего обработчика ошибок
error_handler = ApiErrorHandler(
    max_retries=3,
    initial_delay=1,
    max_delay=10,
    special_error_delays={
        4: 60,  # Превышение лимита запросов - ждем 60 секунд
        2: 5,   # Временная ошибка - ждем 5 секунд
        190: 0  # Проблемы с токеном - не повторяем
    }
)

@with_error_handling(error_handler)
@log_execution_time()
def get_all_ad_sets(account_id: str, status_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Получает все группы объявлений из аккаунта.
    
    Args:
        account_id (str): ID рекламного аккаунта
        status_filter (List[str], optional): Фильтр по статусу (ACTIVE, PAUSED, ARCHIVED, etc.)
    
    Returns:
        List[Dict[str, Any]]: Список групп объявлений
    """
    logger.info(f"Запрос групп объявлений для аккаунта {account_id}, статус: {status_filter}")
    
    account = AdAccount(account_id)
    params = {
        'fields': [
            'id',
            'name',
            'campaign_id',
            'status',
            'daily_budget',
            'lifetime_budget',
            'targeting',
            'bid_amount',
            'billing_event',
            'optimization_goal',
            'start_time',
            'end_time'
        ]
    }
    
    if status_filter:
        params['filtering'] = [{'field': 'status', 'operator': 'IN', 'value': status_filter}]
        
    ad_sets = account.get_ad_sets(params=params)
    result = [ad_set.export_all_data() for ad_set in ad_sets]
    
    logger.info(f"Получено {len(result)} групп объявлений для аккаунта {account_id}")
    return result

@with_error_handling(error_handler)
@log_execution_time()
def get_all_ads(account_id: str, status_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Получает все объявления из аккаунта.
    
    Args:
        account_id (str): ID рекламного аккаунта
        status_filter (List[str], optional): Фильтр по статусу (ACTIVE, PAUSED, ARCHIVED, etc.)
    
    Returns:
        List[Dict[str, Any]]: Список объявлений
    """
    logger.info(f"Запрос объявлений для аккаунта {account_id}, статус: {status_filter}")
    
    account = AdAccount(account_id)
    params = {
        'fields': [
            'id',
            'name',
            'adset_id',
            'campaign_id',
            'status',
            'creative',
            'tracking_specs',
            'created_time',
            'updated_time'
        ]
    }
    
    if status_filter:
        params['filtering'] = [{'field': 'status', 'operator': 'IN', 'value': status_filter}]
        
    ads = account.get_ads(params=params)
    result = [ad.export_all_data() for ad in ads]
    
    logger.info(f"Получено {len(result)} объявлений для аккаунта {account_id}")
    return result

@with_error_handling(error_handler)
@log_execution_time()
def get_ads_insights_batch(
    account_id: str,
    start_date: datetime,
    end_date: datetime,
    level: str = 'ad',
    fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Получает статистику по объявлениям пакетным запросом.
    
    Args:
        account_id (str): ID рекламного аккаунта
        start_date (datetime): Начальная дата
        end_date (datetime): Конечная дата
        level (str): Уровень статистики (ad, adset, campaign, account)
        fields (List[str], optional): Список полей для получения
        
    Returns:
        List[Dict[str, Any]]: Список статистики
    """
    logger.info(
        f"Запрос статистики для аккаунта {account_id} с {start_date.strftime('%Y-%m-%d')} "
        f"по {end_date.strftime('%Y-%m-%d')}, уровень: {level}"
    )
    
    account = AdAccount(account_id)
    
    if fields is None:
        fields = [
            'account_id',
            'campaign_id',
            'campaign_name',
            'adset_id',
            'adset_name',
            'ad_id',
            'ad_name',
            'impressions',
            'clicks',
            'spend',
            'reach',
            'frequency',
            'cpc',
            'cpm',
            'ctr',
            'unique_clicks',
            'unique_ctr',
            'actions',
            'action_values',
            'cost_per_action_type',
            'website_purchase_roas'
        ]
    
    params = {
        'time_range': {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        },
        'level': level,
        'fields': fields,
        'time_increment': 1  # Разбивка по дням
    }
    
    insights = account.get_insights(params=params)
    result = [insight.export_all_data() for insight in insights]
    
    logger.info(f"Получено {len(result)} записей статистики для аккаунта {account_id}")
    return result

@with_error_handling(error_handler)
@log_execution_time()
def get_ad_creatives_batch(account_id: str, ad_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Получает креативы для списка объявлений пакетным запросом.
    
    Args:
        account_id (str): ID рекламного аккаунта
        ad_ids (List[str]): Список ID объявлений
        
    Returns:
        List[Dict[str, Any]]: Список креативов
    """
    logger.info(f"Запрос креативов для аккаунта {account_id}, количество объявлений: {len(ad_ids)}")
    
    account = AdAccount(account_id)
    
    params = {
        'fields': [
            'id',
            'name',
            'title',
            'body',
            'image_url',
            'video_id',
            'call_to_action_type',
            'object_story_spec',
            'url_tags',
            'template_url'
        ]
    }
    
    creatives = []
    # Разбиваем запрос на пакеты по 50 объявлений (ограничение API)
    for i in range(0, len(ad_ids), 50):
        batch_ids = ad_ids[i:i + 50]
        params['filtering'] = [{'field': 'id', 'operator': 'IN', 'value': batch_ids}]
        batch_creatives = account.get_ad_creatives(params=params)
        creatives.extend([creative.export_all_data() for creative in batch_creatives])
        logger.debug(f"Получен пакет креативов {i // 50 + 1}, размер: {len(batch_creatives)}")
    
    logger.info(f"Всего получено {len(creatives)} креативов для аккаунта {account_id}")
    return creatives

@with_error_handling(error_handler)
@log_execution_time()
def get_account_summary(account_id: str) -> Dict[str, Any]:
    """
    Получает сводную информацию по рекламному аккаунту.
    
    Args:
        account_id (str): ID рекламного аккаунта
        
    Returns:
        Dict[str, Any]: Сводная информация по аккаунту
    """
    logger.info(f"Запрос сводки по аккаунту {account_id}")
    
    account = AdAccount(account_id)
    
    # Получаем основную информацию об аккаунте
    account_fields = [
        'name',
        'account_id',
        'account_status',
        'amount_spent',
        'balance',
        'currency',
        'timezone_name',
        'business_country_code',
        'disable_reason',
        'spend_cap'
    ]
    
    account_info = account.api_get(fields=account_fields)
    
    # Получаем статистику за последние 30 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    params = {
        'time_range': {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        },
        'fields': [
            'spend',
            'impressions',
            'clicks',
            'reach',
            'cpm',
            'cpc',
            'ctr',
            'frequency'
        ],
        'level': 'account'
    }
    
    try:
        insights = account.get_insights(params=params)
        insights_data = insights[0].export_all_data() if insights else {}
    except Exception as e:
        logger.warning(f"Не удалось получить статистику аккаунта: {str(e)}")
        insights_data = {}
    
    # Объединяем данные
    result = {
        **account_info,
        'insights': insights_data
    }
    
    logger.info(f"Получена сводка по аккаунту {account_id}")
    return result

@with_error_handling(error_handler)
@log_execution_time()
def get_campaign_by_id(campaign_id: str) -> Dict[str, Any]:
    """
    Получает информацию о кампании по ID.
    
    Args:
        campaign_id (str): ID рекламной кампании
        
    Returns:
        Dict[str, Any]: Информация о кампании
    """
    logger.info(f"Запрос информации о кампании {campaign_id}")
    
    campaign = Campaign(campaign_id)
    
    fields = [
        'id',
        'name',
        'status',
        'objective',
        'special_ad_categories',
        'daily_budget',
        'lifetime_budget',
        'start_time',
        'stop_time',
        'created_time',
        'updated_time'
    ]
    
    campaign_data = campaign.api_get(fields=fields)
    logger.info(f"Получена информация о кампании {campaign_id}: {campaign_data.get('name')}")
    return campaign_data

@with_error_handling(error_handler)
@log_execution_time()
def get_ad_set_by_id(ad_set_id: str) -> Dict[str, Any]:
    """
    Получает информацию о группе объявлений по ID.
    
    Args:
        ad_set_id (str): ID группы объявлений
        
    Returns:
        Dict[str, Any]: Информация о группе объявлений
    """
    logger.info(f"Запрос информации о группе объявлений {ad_set_id}")
    
    ad_set = AdSet(ad_set_id)
    
    fields = [
        'id',
        'name',
        'campaign_id',
        'status',
        'targeting',
        'daily_budget',
        'lifetime_budget',
        'bid_amount',
        'bid_strategy',
        'billing_event',
        'optimization_goal',
        'start_time',
        'end_time',
        'created_time',
        'updated_time'
    ]
    
    ad_set_data = ad_set.api_get(fields=fields)
    logger.info(f"Получена информация о группе объявлений {ad_set_id}: {ad_set_data.get('name')}")
    return ad_set_data

@with_error_handling(error_handler)
@log_execution_time()
def get_ad_by_id(ad_id: str) -> Dict[str, Any]:
    """
    Получает информацию об объявлении по ID.
    
    Args:
        ad_id (str): ID объявления
        
    Returns:
        Dict[str, Any]: Информация об объявлении
    """
    logger.info(f"Запрос информации об объявлении {ad_id}")
    
    ad = Ad(ad_id)
    
    fields = [
        'id',
        'name',
        'adset_id',
        'campaign_id',
        'status',
        'creative',
        'tracking_specs',
        'created_time',
        'updated_time'
    ]
    
    ad_data = ad.api_get(fields=fields)
    logger.info(f"Получена информация об объявлении {ad_id}: {ad_data.get('name')}")
    return ad_data 