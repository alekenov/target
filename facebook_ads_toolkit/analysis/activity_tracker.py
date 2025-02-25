"""
Модуль для отслеживания активности и изменений в рекламном кабинете Facebook.
Позволяет получать историю изменений рекламных кампаний, групп объявлений и объявлений.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.api import FacebookAdsApi

from facebook_ads_toolkit.utils.cache_handler import CacheHandler
from facebook_ads_toolkit.utils.api_helpers import retry_on_api_error

logger = logging.getLogger(__name__)

class ActivityTracker:
    """Класс для отслеживания активности и изменений в рекламном кабинете."""
    
    def __init__(self, account: AdAccount, api: FacebookAdsApi = None, use_cache: bool = True):
        """
        Инициализация трекера активности.
        
        Args:
            account: Инициализированный рекламный аккаунт
            api: Инициализированный Facebook API
            use_cache: Использовать ли кэширование запросов к API
        """
        self.account = account
        self.api = api or FacebookAdsApi.get_default_api()
        self.use_cache = use_cache
        
        # Инициализируем обработчик кэша, если нужно
        if self.use_cache:
            self.cache_handler = CacheHandler(expiration_time=3600)
            logger.info("Кэширование запросов к API включено")
    
    @retry_on_api_error
    def get_account_activity(self, days: int = 14) -> List[Dict[str, Any]]:
        """
        Получение активности по рекламному аккаунту за указанный период.
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            List[Dict[str, Any]]: Список активностей
        """
        logger.info(f"Получение активности по аккаунту за последние {days} дней...")
        
        # Определяем временной диапазон
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        time_range = {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        }
        
        # Пробуем получить из кэша
        if self.use_cache:
            cache_params = {
                'account_id': self.account.get_id_assured(),
                'days': days,
                'time_range': time_range
            }
            
            cache_result = self.cache_handler.get_from_cache('account_activity', cache_params)
            if cache_result:
                logger.info(f"Получено {len(cache_result)} активностей из кэша")
                return cache_result
        
        # Получаем активности
        try:
            activities = self.account.get_activities(
                params={
                    'time_range': time_range,
                    'include_drafts': True,
                    'limit': 1000
                }
            )
            
            result = [activity.export_all_data() for activity in activities]
            
            # Сохраняем в кэш
            if self.use_cache:
                self.cache_handler.save_to_cache('account_activity', cache_params, result)
            
            logger.info(f"Получено {len(result)} активностей по аккаунту")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении активности по аккаунту: {str(e)}")
            return []
    
    @retry_on_api_error
    def get_campaign_changes(self, campaign_id: str, days: int = 14) -> Dict[str, Any]:
        """
        Получение истории изменений кампании.
        
        Args:
            campaign_id: ID кампании
            days: Количество дней для анализа
            
        Returns:
            Dict[str, Any]: История изменений
        """
        logger.info(f"Получение истории изменений кампании {campaign_id} за последние {days} дней...")
        
        # Определяем временной диапазон
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        time_range = {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        }
        
        # Пробуем получить из кэша
        if self.use_cache:
            cache_params = {
                'campaign_id': campaign_id,
                'days': days
            }
            cached_data = self.cache_handler.get_from_cache('campaign_changes', cache_params)
            if cached_data:
                logger.info(f"Получено {len(cached_data['changes'])} изменений кампании из кэша")
                return cached_data
        
        try:
            # Получаем данные кампании
            campaign = Campaign(campaign_id)
            campaign_data = campaign.api_get(
                fields=[
                    'id',
                    'name',
                    'objective',
                    'status',
                    'created_time',
                    'updated_time'
                ]
            ).export_all_data()
            
            # Получаем историю изменений через edge activities
            try:
                # Пробуем получить активности через аккаунт
                activities = self.account.get_activities(
                    params={
                        'time_range': time_range,
                        'limit': 1000,
                        'object_id': campaign_id
                    },
                    fields=[
                        'event_type',
                        'event_time',
                        'object_id',
                        'object_name',
                        'actor_id',
                        'actor_name',
                        'application_id',
                        'application_name',
                        'data'
                    ]
                )
                changes = [activity.export_all_data() for activity in activities]
            except Exception as e:
                logger.warning(f"Не удалось получить активности через аккаунт: {str(e)}")
                # Используем прямой вызов API
                api = FacebookAdsApi.get_default_api()
                
                fields = [
                    'event_type',
                    'event_time',
                    'object_id',
                    'object_name',
                    'actor_id',
                    'actor_name',
                    'application_id',
                    'application_name',
                    'data'
                ]
                
                params = {
                    'time_range': time_range,
                    'limit': 1000,
                    'fields': ','.join(fields)
                }
                
                # Используем объект Campaign для вызова API
                changes = []
                try:
                    response = campaign.get_insights(params=params)
                    if hasattr(response, 'get_data'):
                        changes = response.get_data()
                except Exception as e2:
                    logger.warning(f"Не удалось получить активности через insights: {str(e2)}")
            
            result = {
                'campaign': campaign_data,
                'changes': changes
            }
            
            # Сохраняем в кэш
            if self.use_cache:
                self.cache_handler.save_to_cache('campaign_changes', cache_params, result)
            
            logger.info(f"Получено {len(changes)} изменений кампании")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории изменений кампании {campaign_id}: {str(e)}")
            return {'campaign': {'id': campaign_id}, 'changes': []}
    
    @retry_on_api_error
    def get_adset_changes(self, adset_id: str, days: int = 14) -> Dict[str, Any]:
        """
        Получение истории изменений группы объявлений.
        
        Args:
            adset_id: ID группы объявлений
            days: Количество дней для анализа
            
        Returns:
            Dict[str, Any]: История изменений
        """
        logger.info(f"Получение истории изменений группы объявлений {adset_id} за последние {days} дней...")
        
        # Определяем временной диапазон
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        time_range = {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        }
        
        # Пробуем получить из кэша
        if self.use_cache:
            cache_params = {
                'adset_id': adset_id,
                'days': days
            }
            cached_data = self.cache_handler.get_from_cache('adset_changes', cache_params)
            if cached_data:
                logger.info(f"Получено {len(cached_data['changes'])} изменений группы объявлений из кэша")
                return cached_data
        
        try:
            # Получаем данные группы объявлений
            adset = AdSet(adset_id)
            adset_data = adset.api_get(
                fields=[
                    'id',
                    'name',
                    'campaign_id',
                    'status',
                    'created_time',
                    'updated_time',
                    'targeting'
                ]
            ).export_all_data()
            
            # Получаем историю изменений через edge activities
            try:
                # Пробуем получить активности через аккаунт
                activities = self.account.get_activities(
                    params={
                        'time_range': time_range,
                        'limit': 1000,
                        'object_id': adset_id
                    },
                    fields=[
                        'event_type',
                        'event_time',
                        'object_id',
                        'object_name',
                        'actor_id',
                        'actor_name',
                        'application_id',
                        'application_name',
                        'data'
                    ]
                )
                changes = [activity.export_all_data() for activity in activities]
            except Exception as e:
                logger.warning(f"Не удалось получить активности через аккаунт: {str(e)}")
                # Используем прямой вызов API
                changes = []
                try:
                    response = adset.get_insights(
                        params={
                            'time_range': time_range,
                            'limit': 1000
                        }
                    )
                    if hasattr(response, 'get_data'):
                        changes = response.get_data()
                except Exception as e2:
                    logger.warning(f"Не удалось получить активности через insights: {str(e2)}")
            
            result = {
                'adset': adset_data,
                'changes': changes
            }
            
            # Сохраняем в кэш
            if self.use_cache:
                self.cache_handler.save_to_cache('adset_changes', cache_params, result)
            
            logger.info(f"Получено {len(changes)} изменений группы объявлений")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории изменений группы объявлений {adset_id}: {str(e)}")
            return {'adset': {'id': adset_id}, 'changes': []}
    
    @retry_on_api_error
    def get_ad_changes(self, ad_id: str, days: int = 14) -> Dict[str, Any]:
        """
        Получение истории изменений объявления.
        
        Args:
            ad_id: ID объявления
            days: Количество дней для анализа
            
        Returns:
            Dict[str, Any]: История изменений
        """
        logger.info(f"Получение истории изменений объявления {ad_id} за последние {days} дней...")
        
        # Определяем временной диапазон
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        time_range = {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        }
        
        # Пробуем получить из кэша
        if self.use_cache:
            cache_params = {
                'ad_id': ad_id,
                'days': days
            }
            cached_data = self.cache_handler.get_from_cache('ad_changes', cache_params)
            if cached_data:
                logger.info(f"Получено {len(cached_data['changes'])} изменений объявления из кэша")
                return cached_data
        
        try:
            # Получаем данные объявления
            ad = Ad(ad_id)
            ad_data = ad.api_get(
                fields=[
                    'id',
                    'name',
                    'adset_id',
                    'campaign_id',
                    'status',
                    'created_time',
                    'updated_time',
                    'creative'
                ]
            ).export_all_data()
            
            # Получаем историю изменений через edge activities
            try:
                # Пробуем получить активности через аккаунт
                activities = self.account.get_activities(
                    params={
                        'time_range': time_range,
                        'limit': 1000,
                        'object_id': ad_id
                    },
                    fields=[
                        'event_type',
                        'event_time',
                        'object_id',
                        'object_name',
                        'actor_id',
                        'actor_name',
                        'application_id',
                        'application_name',
                        'data'
                    ]
                )
                changes = [activity.export_all_data() for activity in activities]
            except Exception as e:
                logger.warning(f"Не удалось получить активности через аккаунт: {str(e)}")
                # Используем прямой вызов API
                changes = []
                try:
                    response = ad.get_insights(
                        params={
                            'time_range': time_range,
                            'limit': 1000
                        }
                    )
                    if hasattr(response, 'get_data'):
                        changes = response.get_data()
                except Exception as e2:
                    logger.warning(f"Не удалось получить активности через insights: {str(e2)}")
            
            result = {
                'ad': ad_data,
                'changes': changes
            }
            
            # Сохраняем в кэш
            if self.use_cache:
                self.cache_handler.save_to_cache('ad_changes', cache_params, result)
            
            logger.info(f"Получено {len(changes)} изменений объявления")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории изменений объявления {ad_id}: {str(e)}")
            return {'ad': {'id': ad_id}, 'changes': []}
    
    def get_all_changes(self, days: int = 14) -> Dict[str, Any]:
        """
        Получение всех изменений в рекламном кабинете за указанный период.
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Dict[str, Any]: Все изменения
        """
        logger.info(f"Получение всех изменений в рекламном кабинете за последние {days} дней...")
        
        # Получаем активность по аккаунту
        account_activity = self.get_account_activity(days)
        
        # Получаем список активных кампаний
        campaigns = self.account.get_campaigns(
            params={
                'limit': 1000
            },
            fields=[
                'id',
                'name',
                'status',
                'created_time',
                'updated_time'
            ]
        )
        
        # Собираем изменения по всем кампаниям
        campaign_changes = []
        adset_changes = []
        ad_changes = []
        
        for campaign in campaigns:
            # Получаем изменения кампании
            campaign_data = self.get_campaign_changes(campaign['id'], days)
            campaign_changes.append(campaign_data)
            
            # Получаем группы объявлений кампании
            adsets = campaign.get_ad_sets(
                params={
                    'limit': 1000
                },
                fields=[
                    'id',
                    'name',
                    'status'
                ]
            )
            
            for adset in adsets:
                # Получаем изменения группы объявлений
                adset_data = self.get_adset_changes(adset['id'], days)
                adset_changes.append(adset_data)
                
                # Получаем объявления группы
                ads = adset.get_ads(
                    params={
                        'limit': 1000
                    },
                    fields=[
                        'id',
                        'name',
                        'status'
                    ]
                )
                
                for ad in ads:
                    # Получаем изменения объявления
                    ad_data = self.get_ad_changes(ad['id'], days)
                    ad_changes.append(ad_data)
        
        result = {
            'account_activity': account_activity,
            'campaign_changes': campaign_changes,
            'adset_changes': adset_changes,
            'ad_changes': ad_changes
        }
        
        logger.info("Получение всех изменений завершено")
        return result
    
    def analyze_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ изменений в рекламном кабинете.
        
        Args:
            changes: Словарь с изменениями
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        logger.info("Анализ изменений в рекламном кабинете...")
        
        # Анализируем активность по аккаунту
        account_activity = changes.get('account_activity', [])
        
        # Анализируем изменения кампаний
        campaign_changes = changes.get('campaign_changes', [])
        
        # Анализируем изменения групп объявлений
        adset_changes = changes.get('adset_changes', [])
        
        # Анализируем изменения объявлений
        ad_changes = changes.get('ad_changes', [])
        
        # Собираем статистику по изменениям
        stats = {
            'total_activities': len(account_activity),
            'total_campaign_changes': sum(len(c.get('changes', [])) for c in campaign_changes),
            'total_adset_changes': sum(len(a.get('changes', [])) for a in adset_changes),
            'total_ad_changes': sum(len(a.get('changes', [])) for a in ad_changes),
            'campaigns_modified': [],
            'adsets_modified': [],
            'ads_modified': [],
            'users_activity': {}
        }
        
        # Анализируем пользователей, которые вносили изменения
        for activity in account_activity:
            if 'actor_name' in activity:
                user = activity['actor_name']
                if user not in stats['users_activity']:
                    stats['users_activity'][user] = 0
                stats['users_activity'][user] += 1
        
        # Анализируем изменения кампаний
        for campaign_data in campaign_changes:
            campaign = campaign_data.get('campaign', {})
            changes = campaign_data.get('changes', [])
            
            if changes:
                stats['campaigns_modified'].append({
                    'id': campaign.get('id'),
                    'name': campaign.get('name'),
                    'changes_count': len(changes),
                    'last_change': changes[0].get('created_time') if changes else None
                })
        
        # Анализируем изменения групп объявлений
        for adset_data in adset_changes:
            adset = adset_data.get('adset', {})
            changes = adset_data.get('changes', [])
            
            if changes:
                stats['adsets_modified'].append({
                    'id': adset.get('id'),
                    'name': adset.get('name'),
                    'campaign_id': adset.get('campaign_id'),
                    'changes_count': len(changes),
                    'last_change': changes[0].get('created_time') if changes else None
                })
        
        # Анализируем изменения объявлений
        for ad_data in ad_changes:
            ad = ad_data.get('ad', {})
            changes = ad_data.get('changes', [])
            
            if changes:
                stats['ads_modified'].append({
                    'id': ad.get('id'),
                    'name': ad.get('name'),
                    'adset_id': ad.get('adset_id'),
                    'campaign_id': ad.get('campaign_id'),
                    'changes_count': len(changes),
                    'last_change': changes[0].get('created_time') if changes else None
                })
        
        # Сортируем по количеству изменений
        stats['campaigns_modified'].sort(key=lambda x: x['changes_count'], reverse=True)
        stats['adsets_modified'].sort(key=lambda x: x['changes_count'], reverse=True)
        stats['ads_modified'].sort(key=lambda x: x['changes_count'], reverse=True)
        
        # Сортируем пользователей по активности
        stats['users_activity'] = dict(sorted(
            stats['users_activity'].items(),
            key=lambda item: item[1],
            reverse=True
        ))
        
        logger.info("Анализ изменений завершен")
        return stats 