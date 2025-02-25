"""
Модуль для получения данных о рекламе из Facebook API.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
import time

from ..utils.api_helpers import retry_on_api_error, chunk_list, batch_process, parallel_process

logger = logging.getLogger(__name__)

class AdDataFetcher:
    """Класс для получения данных о рекламе из Facebook API."""
    
    def __init__(self, account: AdAccount, api: FacebookAdsApi = None, use_cache: bool = True, cache_expiration: int = 3600):
        """
        Инициализация сборщика данных рекламы.
        
        Args:
            account: Инициализированный рекламный аккаунт
            api: Инициализированный Facebook API
            use_cache: Использовать ли кэширование запросов к API
            cache_expiration: Время жизни кэша в секундах (по умолчанию 1 час)
        """
        self.account = account
        self.api = api or FacebookAdsApi.get_default_api()
        self.time_range = None
        self.use_cache = use_cache
        self.cache_expiration = cache_expiration
        
        # Инициализируем обработчик кэша, если нужно
        if self.use_cache:
            from ..utils.cache_handler import CacheHandler
            self.cache_handler = CacheHandler(expiration_time=cache_expiration)
            logger.info("Кэширование запросов к API включено")
        
        self.set_default_time_range()
    
    def set_default_time_range(self, days_ago: int = 30):
        """
        Установка временного диапазона по умолчанию.
        
        Args:
            days_ago: Количество дней назад для начала диапазона
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_ago)
        
        self.time_range = {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        }
        
        logger.info(f"Установлен временной диапазон: {self.time_range['since']} - {self.time_range['until']}")
    
    def set_time_range(self, start_date: str, end_date: str):
        """
        Установка произвольного временного диапазона.
        
        Args:
            start_date: Начальная дата в формате YYYY-MM-DD
            end_date: Конечная дата в формате YYYY-MM-DD
        """
        self.time_range = {
            'since': start_date,
            'until': end_date
        }
        logger.info(f"Установлен временной диапазон: {start_date} - {end_date}")
    
    @retry_on_api_error
    def get_active_campaigns(self, limit: int = 1000, year_filter: str = '2025') -> List[Dict[str, Any]]:
        """
        Получение списка активных кампаний.
        
        Args:
            limit: Максимальное количество кампаний для получения
            year_filter: Фильтрация по году (по умолчанию - 2025)
            
        Returns:
            List[Dict[str, Any]]: Список данных о кампаниях
        """
        logger.info(f"Получение активных кампаний за {year_filter} год (лимит: {limit})...")
        
        campaign_fields = [
            'id',
            'name',
            'objective',
            'status',
            'daily_budget',
            'lifetime_budget',
            'created_time',
            'updated_time',
            'start_time',
            'stop_time',
            'spend_cap'
        ]
        
        # Создаем параметры для запроса и кэша
        params = {
            'effective_status': ['ACTIVE'],
            'limit': limit,
            'fields': campaign_fields,
            'time_range': self.time_range,
            'year_filter': year_filter
        }
        
        # Проверяем, можно ли использовать кэш
        if self.use_cache:
            # Пытаемся получить данные из кэша
            cache_data = self.cache_handler.get_from_cache('campaigns', params)
            if cache_data:
                logger.info(f"Загружено {len(cache_data)} кампаний из кэша")
                return cache_data
        
        # Делаем запрос к API
        campaigns = self.account.get_campaigns(
            params={
                'effective_status': ['ACTIVE'],
                'limit': limit,
                'fields': campaign_fields
            }
        )
        
        # Фильтруем кампании по году
        filtered_campaigns = []
        for campaign in campaigns:
            campaign_data = campaign.export_all_data()
            # Проверяем, есть ли в данных о кампании информация о created_time и относится ли она к 2025 году
            if 'created_time' in campaign_data:
                campaign_year = campaign_data['created_time'][:4]  # Берем первые 4 символа (год)
                if year_filter is None or campaign_year == year_filter:
                    filtered_campaigns.append(campaign_data)
            elif year_filter is None:
                filtered_campaigns.append(campaign_data)
        
        logger.info(f"Получено {len(filtered_campaigns)} активных кампаний за {year_filter} год")
        
        # Сохраняем результаты в кэш, если кэширование включено
        if self.use_cache:
            self.cache_handler.save_to_cache('campaigns', params, filtered_campaigns)
            logger.debug("Данные о кампаниях сохранены в кэш")
        
        return filtered_campaigns
    
    @retry_on_api_error
    def get_campaign_adsets(self, campaign_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Получение групп объявлений для кампании.
        
        Args:
            campaign_id: ID кампании
            limit: Максимальное количество групп для получения
            
        Returns:
            List[Dict[str, Any]]: Список данных о группах объявлений
        """
        logger.info(f"Получение групп объявлений для кампании {campaign_id}...")
        
        adset_fields = [
            'id',
            'name',
            'campaign_id',
            'status',
            'targeting',
            'optimization_goal',
            'bid_strategy',
            'daily_budget',
            'lifetime_budget',
            'billing_event',
            'bid_amount',
            'start_time',
            'end_time'
        ]
        
        # Создаем параметры для запроса и кэша
        params = {
            'campaign_id': campaign_id,
            'effective_status': ['ACTIVE'],
            'limit': limit,
            'fields': adset_fields,
            'time_range': self.time_range
        }
        
        # Проверяем, можно ли использовать кэш
        if self.use_cache:
            # Пытаемся получить данные из кэша
            cache_data = self.cache_handler.get_from_cache('adsets', params)
            if cache_data:
                logger.info(f"Загружено {len(cache_data)} групп объявлений из кэша для кампании {campaign_id}")
                return cache_data
        
        # Делаем запрос к API
        adsets = Campaign(campaign_id).get_ad_sets(
            params={
                'effective_status': ['ACTIVE'],
                'limit': limit,
                'fields': adset_fields
            }
        )
        
        adset_data = [adset.export_all_data() for adset in adsets]
        logger.info(f"Получено {len(adset_data)} групп объявлений для кампании {campaign_id}")
        
        # Сохраняем результаты в кэш, если кэширование включено
        if self.use_cache:
            self.cache_handler.save_to_cache('adsets', params, adset_data)
            logger.debug(f"Данные о группах объявлений для кампании {campaign_id} сохранены в кэш")
        
        return adset_data
    
    @retry_on_api_error
    def get_adset_ads(self, adset_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Получение объявлений для группы.
        
        Args:
            adset_id: ID группы объявлений
            limit: Максимальное количество объявлений для получения
            
        Returns:
            List[Dict[str, Any]]: Список данных об объявлениях
        """
        logger.info(f"Получение объявлений для группы {adset_id}...")
        
        ad_fields = [
            'id',
            'name',
            'adset_id',
            'campaign_id',
            'status',
            'effective_status',
            'creative',
            'created_time',
            'updated_time'
        ]
        
        # Создаем параметры для запроса и кэша
        params = {
            'adset_id': adset_id,
            'effective_status': ['ACTIVE'],
            'limit': limit,
            'fields': ad_fields,
            'time_range': self.time_range
        }
        
        # Проверяем, можно ли использовать кэш
        if self.use_cache:
            # Пытаемся получить данные из кэша
            cache_data = self.cache_handler.get_from_cache('ads', params)
            if cache_data:
                logger.info(f"Загружено {len(cache_data)} объявлений из кэша для группы {adset_id}")
                return cache_data
        
        # Делаем запрос к API
        ads = AdSet(adset_id).get_ads(
            params={
                'effective_status': ['ACTIVE'],
                'limit': limit,
                'fields': ad_fields
            }
        )
        
        ad_data = [ad.export_all_data() for ad in ads]
        logger.info(f"Получено {len(ad_data)} объявлений для группы {adset_id}")
        
        # Сохраняем результаты в кэш, если кэширование включено
        if self.use_cache:
            self.cache_handler.save_to_cache('ads', params, ad_data)
            logger.debug(f"Данные об объявлениях для группы {adset_id} сохранены в кэш")
        
        return ad_data
    
    @retry_on_api_error
    def get_insights(self, ad_object_id: str, ad_object_type: str) -> Dict[str, Any]:
        """
        Получение статистики для объекта рекламы.
        
        Args:
            ad_object_id: ID объекта (кампании/группы/объявления)
            ad_object_type: Тип объекта ('campaign', 'adset', 'ad')
            
        Returns:
            Dict[str, Any]: Статистика объекта
        """
        insights_fields = [
            'spend',
            'impressions',
            'clicks',
            'ctr',
            'cpc',
            'reach',
            'frequency',
            'cost_per_action_type',
            'actions',
            'action_values'
        ]
        
        insights_params = {
            'time_range': self.time_range,
            'fields': insights_fields
        }
        
        # Создаем параметры для кэша
        cache_params = {
            'ad_object_id': ad_object_id,
            'ad_object_type': ad_object_type,
            'time_range': self.time_range,
            'fields': insights_fields
        }
        
        # Проверяем, можно ли использовать кэш
        if self.use_cache:
            # Пытаемся получить данные из кэша
            cache_data = self.cache_handler.get_from_cache('insights', cache_params)
            if cache_data:
                logger.debug(f"Загружены инсайты из кэша для {ad_object_type} {ad_object_id}")
                return cache_data
        
        try:
            if ad_object_type == 'campaign':
                insights = Campaign(ad_object_id).get_insights(params=insights_params)
            elif ad_object_type == 'adset':
                insights = AdSet(ad_object_id).get_insights(params=insights_params)
            elif ad_object_type == 'ad':
                insights = Ad(ad_object_id).get_insights(params=insights_params)
            else:
                logger.error(f"Неизвестный тип объекта: {ad_object_type}")
                return {}
            
            result = {}
            if insights and len(insights) > 0:
                result = insights[0].export_all_data()
                
                # Сохраняем результаты в кэш, если кэширование включено
                if self.use_cache:
                    self.cache_handler.save_to_cache('insights', cache_params, result)
                    logger.debug(f"Инсайты для {ad_object_type} {ad_object_id} сохранены в кэш")
                
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики для {ad_object_type} {ad_object_id}: {str(e)}")
            return {}
    
    def fetch_all_ad_data(self) -> Dict[str, Any]:
        """
        Получение полных данных о рекламе.
        
        Returns:
            Dict[str, Any]: Словарь с данными о кампаниях, группах и объявлениях
        """
        logger.info("Начало получения данных о рекламе...")
        
        # Получаем все активные кампании
        campaigns = self.get_active_campaigns()
        
        # Дополняем данные статистикой
        for campaign in campaigns:
            campaign['insights'] = self.get_insights(campaign['id'], 'campaign')
        
        # Получаем группы объявлений для каждой кампании
        all_adsets = []
        for campaign in campaigns:
            adsets = self.get_campaign_adsets(campaign['id'])
            for adset in adsets:
                adset['insights'] = self.get_insights(adset['id'], 'adset')
                all_adsets.append(adset)
        
        # Получаем объявления для каждой группы
        all_ads = []
        for adset in all_adsets:
            ads = self.get_adset_ads(adset['id'])
            for ad in ads:
                ad['insights'] = self.get_insights(ad['id'], 'ad')
                all_ads.append(ad)
        
        # Формируем итоговый набор данных
        ad_data = {
            'campaigns': campaigns,
            'adsets': all_adsets,
            'ads': all_ads,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'time_range': self.time_range
        }
        
        logger.info(f"Получены данные: {len(campaigns)} кампаний, {len(all_adsets)} групп, {len(all_ads)} объявлений")
        
        return ad_data
    
    def fetch_all_batch(self, batch_size: int = 10, pause_between_batches: float = 3.0) -> Dict[str, Any]:
        """
        Получение полных данных о рекламе в режиме batch.
        
        Args:
            batch_size: Размер пакета для обработки (уменьшен для снижения нагрузки)
            pause_between_batches: Пауза между пакетами в секундах
            
        Returns:
            Dict[str, Any]: Словарь с данными о кампаниях, группах и объявлениях
        """
        logger.info("Начало получения данных о рекламе в режиме batch...")
        
        # Получаем только активные кампании за 2025 год
        campaigns = self.get_active_campaigns(year_filter='2025')
        
        # Подготавливаем запросы для получения статистики кампаний
        campaign_ids = [campaign['id'] for campaign in campaigns]
        
        # Получаем статистику кампаний пакетно
        def process_campaign_insights_batch(campaign_batch):
            results = []
            for campaign_id in campaign_batch:
                insights = self.get_insights(campaign_id, 'campaign')
                results.append((campaign_id, insights))
            return results
        
        campaign_insights = batch_process(
            campaign_ids, 
            process_campaign_insights_batch,
            batch_size=batch_size,
            pause_between_batches=pause_between_batches
        )
        
        # Применяем полученные данные
        campaign_insights_dict = dict(campaign_insights)
        for campaign in campaigns:
            campaign['insights'] = campaign_insights_dict.get(campaign['id'], {})
        
        # Получаем группы объявлений для всех кампаний пакетно
        def process_adsets_batch(campaign_batch):
            results = []
            for campaign_id in campaign_batch:
                adsets = self.get_campaign_adsets(campaign_id)
                for adset in adsets:
                    results.append(adset)
            return results
        
        all_adsets = batch_process(
            campaign_ids,
            process_adsets_batch,
            batch_size=batch_size,
            pause_between_batches=pause_between_batches
        )
        
        # Получаем статистику для групп объявлений пакетно
        adset_ids = [adset['id'] for adset in all_adsets]
        
        def process_adset_insights_batch(adset_batch):
            results = []
            for adset_id in adset_batch:
                insights = self.get_insights(adset_id, 'adset')
                results.append((adset_id, insights))
            return results
        
        adset_insights = batch_process(
            adset_ids,
            process_adset_insights_batch,
            batch_size=batch_size,
            pause_between_batches=pause_between_batches
        )
        
        # Применяем полученные данные
        adset_insights_dict = dict(adset_insights)
        for adset in all_adsets:
            adset['insights'] = adset_insights_dict.get(adset['id'], {})
        
        # Получаем объявления для всех групп пакетно
        def process_ads_batch(adset_batch):
            results = []
            for adset_id in adset_batch:
                ads = self.get_adset_ads(adset_id)
                for ad in ads:
                    results.append(ad)
            return results
        
        all_ads = batch_process(
            adset_ids,
            process_ads_batch,
            batch_size=batch_size,
            pause_between_batches=pause_between_batches
        )
        
        # Получаем статистику для объявлений пакетно
        ad_ids = [ad['id'] for ad in all_ads]
        
        def process_ad_insights_batch(ad_batch):
            results = []
            for ad_id in ad_batch:
                insights = self.get_insights(ad_id, 'ad')
                results.append((ad_id, insights))
            return results
        
        ad_insights = batch_process(
            ad_ids,
            process_ad_insights_batch,
            batch_size=batch_size,
            pause_between_batches=pause_between_batches
        )
        
        # Применяем полученные данные
        ad_insights_dict = dict(ad_insights)
        for ad in all_ads:
            ad['insights'] = ad_insights_dict.get(ad['id'], {})
        
        # Формируем итоговый набор данных
        ad_data = {
            'campaigns': campaigns,
            'adsets': all_adsets,
            'ads': all_ads,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'time_range': self.time_range
        }
        
        logger.info(f"Получены данные в batch-режиме: {len(campaigns)} кампаний, "
                   f"{len(all_adsets)} групп, {len(all_ads)} объявлений")
        
        return ad_data
    
    def fetch_all_parallel(self, max_workers: int = 2) -> Dict[str, Any]:
        """
        Получение полных данных о рекламе с использованием параллельной обработки.
        Оптимизировано для снижения нагрузки на API.
        
        Args:
            max_workers: Максимальное количество рабочих потоков
            
        Returns:
            Dict[str, Any]: Словарь с данными о кампаниях, группах и объявлениях
        """
        from ..utils.api_helpers import parallel_process
        
        logger.info("Начало получения данных о рекламе (параллельный режим)...")
        
        # Получаем только активные кампании за 2025 год
        campaigns = self.get_active_campaigns(year_filter='2025')
        campaign_ids = [campaign['id'] for campaign in campaigns]
        logger.info(f"Для обработки отобрано {len(campaign_ids)} кампаний за 2025 год")
        
        # Уменьшаем количество кампаний для обработки, если их слишком много
        if len(campaign_ids) > 30:
            logger.warning(f"Слишком много кампаний ({len(campaign_ids)}). Ограничиваем до 30 для снижения нагрузки на API.")
            campaign_ids = campaign_ids[:30]
        
        # Функция для получения данных об одной кампании, ее группах и объявлениях
        def process_campaign(campaign_id):
            try:
                # Небольшая задержка перед началом обработки для распределения нагрузки
                time.sleep(0.5)
                
                # Получаем группы объявлений для кампании
                adsets = self.get_campaign_adsets(campaign_id)
                
                # Ограничиваем количество групп объявлений, если их слишком много
                if len(adsets) > 10:
                    logger.warning(f"Слишком много групп объявлений ({len(adsets)}) для кампании {campaign_id}. Ограничиваем до 10.")
                    adsets = adsets[:10]
                
                # Получаем объявления для каждой группы
                ads = []
                for adset in adsets:
                    # Делаем паузу между запросами групп объявлений
                    time.sleep(1)
                    
                    adset_ads = self.get_adset_ads(adset['id'])
                    
                    # Ограничиваем количество объявлений, если их слишком много
                    if len(adset_ads) > 5:
                        adset_ads = adset_ads[:5]
                    
                    # Добавляем статистику для каждого объявления с паузами
                    for ad in adset_ads:
                        # Пауза перед запросом инсайтов объявления
                        time.sleep(0.5)
                        ad['insights'] = self.get_insights(ad['id'], 'ad')
                    
                    # Добавляем статистику для группы объявлений
                    adset['insights'] = self.get_insights(adset['id'], 'adset')
                    adset['ads'] = adset_ads
                    ads.extend(adset_ads)
                
                # Находим соответствующую кампанию
                campaign = next((c for c in campaigns if c['id'] == campaign_id), None)
                if campaign:
                    campaign['insights'] = self.get_insights(campaign_id, 'campaign')
                    campaign['adsets'] = adsets
                    
                logger.info(f"Обработана кампания {campaign_id}: {len(adsets)} групп, {len(ads)} объявлений")
                return {'campaign_id': campaign_id, 'adsets': adsets, 'ads': ads}
            
            except Exception as e:
                logger.error(f"Ошибка при обработке кампании {campaign_id}: {str(e)}")
                return None
        
        # Запускаем параллельную обработку кампаний с ограниченным количеством потоков
        results = parallel_process(campaign_ids, process_campaign, max_workers)
        
        # Объединяем результаты
        all_adsets = []
        all_ads = []
        
        for result in results:
            if result:
                all_adsets.extend(result['adsets'])
                all_ads.extend(result['ads'])
        
        # Формируем итоговый словарь данных
        ad_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'time_range': self.time_range,
            'campaigns': campaigns,
            'adsets': all_adsets,
            'ads': all_ads
        }
        
        logger.info(f"Завершено получение данных: {len(campaigns)} кампаний, "
                   f"{len(all_adsets)} групп, {len(all_ads)} объявлений")
        
        return ad_data 