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
from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_all_ad_sets(account_id: str, status_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Получает все группы объявлений из аккаунта.
    
    Args:
        account_id (str): ID рекламного аккаунта
        status_filter (List[str], optional): Фильтр по статусу (ACTIVE, PAUSED, ARCHIVED, etc.)
    
    Returns:
        List[Dict[str, Any]]: Список групп объявлений
    """
    try:
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
        return [ad_set.export_all_data() for ad_set in ad_sets]
        
    except Exception as e:
        logger.error(f"Ошибка при получении групп объявлений: {e}")
        return []

def get_all_ads(account_id: str, status_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Получает все объявления из аккаунта.
    
    Args:
        account_id (str): ID рекламного аккаунта
        status_filter (List[str], optional): Фильтр по статусу (ACTIVE, PAUSED, ARCHIVED, etc.)
    
    Returns:
        List[Dict[str, Any]]: Список объявлений
    """
    try:
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
        return [ad.export_all_data() for ad in ads]
        
    except Exception as e:
        logger.error(f"Ошибка при получении объявлений: {e}")
        return []

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
    try:
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
        return [insight.export_all_data() for insight in insights]
        
    except Exception as e:
        logger.error(f"Ошибка при получении пакетной статистики: {e}")
        return []

def get_ad_creatives_batch(account_id: str, ad_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Получает креативы для списка объявлений пакетным запросом.
    
    Args:
        account_id (str): ID рекламного аккаунта
        ad_ids (List[str]): Список ID объявлений
        
    Returns:
        List[Dict[str, Any]]: Список креативов
    """
    try:
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
            
        return creatives
        
    except Exception as e:
        logger.error(f"Ошибка при получении пакета креативов: {e}")
        return []

def get_account_summary(account_id: str) -> Dict[str, Any]:
    """
    Получает сводную информацию по рекламному аккаунту.
    
    Args:
        account_id (str): ID рекламного аккаунта
        
    Returns:
        Dict[str, Any]: Сводная информация по аккаунту
    """
    try:
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
                'frequency',
                'cpc',
                'cpm',
                'ctr'
            ]
        }
        
        insights = account.get_insights(params=params)
        insights_data = [insight.export_all_data() for insight in insights]
        
        return {
            'account_info': account_info,
            'last_30_days_insights': insights_data
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении сводки по аккаунту: {e}")
        return {} 