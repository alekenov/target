#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для оптимизированного получения данных из Facebook Ads API.
Включает кэширование, пакетную обработку и механизмы повторных попыток.
"""

import os
import time
import json
import logging
import functools
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import traceback

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError

# Настройка логирования
logger = logging.getLogger(__name__)

def retry_on_api_error(max_retries=3, initial_delay=5, backoff_factor=2):
    """
    Декоратор для повторных попыток при ошибках API Facebook.
    
    Args:
        max_retries (int): Максимальное количество повторных попыток.
        initial_delay (int): Начальная задержка в секундах.
        backoff_factor (int): Множитель для увеличения задержки с каждой попыткой.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except FacebookRequestError as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Превышено максимальное количество попыток ({max_retries}). Последняя ошибка: {str(e)}")
                        raise
                    
                    # Определяем, стоит ли повторять запрос
                    if e.api_error_code() in [1, 2, 4, 17, 341, 368, 613]:
                        # Коды ошибок, которые могут быть временными
                        logger.warning(f"Временная ошибка API (код {e.api_error_code()}): {e.api_error_message()}. "
                                      f"Повторная попытка {retries}/{max_retries} через {delay} сек.")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        # Постоянная ошибка, нет смысла повторять
                        logger.error(f"Постоянная ошибка API (код {e.api_error_code()}): {e.api_error_message()}")
                        raise
                except Exception as e:
                    logger.error(f"Неожиданная ошибка: {str(e)}")
                    raise
                    
        return wrapper
    return decorator

class AdDataFetcher:
    """
    Класс для оптимизированного получения данных из Facebook Ads API.
    Поддерживает кэширование, пакетную обработку и повторные попытки.
    """
    
    def __init__(self, account: AdAccount, use_cache: bool = True, cache_expiration: int = 3600, 
                 cache_dir: str = 'cache'):
        """
        Инициализация объекта для получения данных.
        
        Args:
            account (AdAccount): Объект рекламного аккаунта Facebook.
            use_cache (bool): Использовать ли кэширование.
            cache_expiration (int): Время жизни кэша в секундах.
            cache_dir (str): Директория для хранения кэша.
        """
        self.account = account
        self.use_cache = use_cache
        self.cache_expiration = cache_expiration
        self.cache_dir = cache_dir
        
        # Создаем директорию для кэша, если она не существует
        if self.use_cache and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_key(self, entity_type: str, params: Dict[str, Any]) -> str:
        """
        Генерирует ключ кэша на основе типа сущности и параметров запроса.
        
        Args:
            entity_type (str): Тип сущности (campaigns, adsets, ads, insights).
            params (dict): Параметры запроса.
            
        Returns:
            str: Ключ кэша.
        """
        # Сортируем параметры для обеспечения одинакового ключа при одинаковых параметрах
        params_str = json.dumps(params, sort_keys=True)
        account_id = self.account.get_id()
        
        # Создаем хеш для использования в имени файла
        hash_obj = hashlib.md5(f"{account_id}_{entity_type}_{params_str}".encode())
        return hash_obj.hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """
        Получает путь к файлу кэша.
        
        Args:
            cache_key (str): Ключ кэша.
            
        Returns:
            str: Путь к файлу кэша.
        """
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """
        Проверяет, действителен ли кэш.
        
        Args:
            cache_path (str): Путь к файлу кэша.
            
        Returns:
            bool: True, если кэш действителен, иначе False.
        """
        if not os.path.exists(cache_path):
            return False
        
        # Проверяем время создания файла
        file_time = os.path.getmtime(cache_path)
        current_time = time.time()
        
        return (current_time - file_time) < self.cache_expiration
    
    def _read_from_cache(self, cache_path: str) -> List[Dict[str, Any]]:
        """
        Читает данные из кэша.
        
        Args:
            cache_path (str): Путь к файлу кэша.
            
        Returns:
            list: Данные из кэша.
        """
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при чтении кэша: {str(e)}")
            return []
    
    def _write_to_cache(self, cache_path: str, data: List[Dict[str, Any]]) -> None:
        """
        Записывает данные в кэш.
        
        Args:
            cache_path (str): Путь к файлу кэша.
            data (list): Данные для записи.
        """
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при записи в кэш: {str(e)}")
    
    @retry_on_api_error(max_retries=3, initial_delay=5, backoff_factor=2)
    def fetch_campaigns(self, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Получает список кампаний с учетом кэширования.
        
        Args:
            params (dict): Параметры запроса.
            
        Returns:
            list: Список кампаний.
        """
        if params is None:
            params = {}
        
        # Добавляем базовые поля, если не указаны
        if 'fields' not in params:
            params['fields'] = [
                'id', 'name', 'status', 'objective', 
                'created_time', 'start_time', 'stop_time',
                'daily_budget', 'lifetime_budget', 'effective_status'
            ]
        
        # Проверяем кэш
        cache_key = self._get_cache_key('campaigns', params)
        cache_path = self._get_cache_path(cache_key)
        
        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info(f"Получение кампаний из кэша: {cache_path}")
            return self._read_from_cache(cache_path)
        
        # Получаем данные из API
        logger.info(f"Получение кампаний из API с параметрами: {params}")
        campaigns = self.account.get_campaigns(params=params)
        
        # Преобразуем объекты в словари
        result = [campaign.export_all_data() for campaign in campaigns]
        
        # Сохраняем в кэш
        if self.use_cache:
            self._write_to_cache(cache_path, result)
        
        return result
    
    @retry_on_api_error(max_retries=3, initial_delay=5, backoff_factor=2)
    def fetch_adsets(self, campaign_ids: List[str] = None, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Получает список групп объявлений с учетом кэширования.
        
        Args:
            campaign_ids (list): Список ID кампаний для фильтрации.
            params (dict): Параметры запроса.
            
        Returns:
            list: Список групп объявлений.
        """
        if params is None:
            params = {}
        
        # Добавляем базовые поля, если не указаны
        if 'fields' not in params:
            params['fields'] = [
                'id', 'name', 'status', 'campaign_id', 
                'daily_budget', 'lifetime_budget', 'targeting',
                'bid_amount', 'billing_event', 'optimization_goal',
                'effective_status'
            ]
        
        # Добавляем фильтрацию по кампаниям, если указана
        if campaign_ids:
            params['filtering'] = [
                {
                    'field': 'campaign.id',
                    'operator': 'IN',
                    'value': campaign_ids
                }
            ]
        
        # Проверяем кэш
        cache_key = self._get_cache_key('adsets', params)
        cache_path = self._get_cache_path(cache_key)
        
        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info(f"Получение групп объявлений из кэша: {cache_path}")
            return self._read_from_cache(cache_path)
        
        # Получаем данные из API
        logger.info(f"Получение групп объявлений из API с параметрами: {params}")
        adsets = self.account.get_ad_sets(params=params)
        
        # Преобразуем объекты в словари
        result = [adset.export_all_data() for adset in adsets]
        
        # Сохраняем в кэш
        if self.use_cache:
            self._write_to_cache(cache_path, result)
        
        return result
    
    @retry_on_api_error(max_retries=3, initial_delay=5, backoff_factor=2)
    def fetch_ads(self, adset_ids: List[str] = None, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Получает список объявлений с учетом кэширования.
        
        Args:
            adset_ids (list): Список ID групп объявлений для фильтрации.
            params (dict): Параметры запроса.
            
        Returns:
            list: Список объявлений.
        """
        if params is None:
            params = {}
        
        # Добавляем базовые поля, если не указаны
        if 'fields' not in params:
            params['fields'] = [
                'id', 'name', 'status', 'adset_id', 'campaign_id',
                'creative', 'effective_status'
            ]
        
        # Добавляем фильтрацию по группам объявлений, если указана
        if adset_ids:
            params['filtering'] = [
                {
                    'field': 'adset.id',
                    'operator': 'IN',
                    'value': adset_ids
                }
            ]
        
        # Проверяем кэш
        cache_key = self._get_cache_key('ads', params)
        cache_path = self._get_cache_path(cache_key)
        
        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info(f"Получение объявлений из кэша: {cache_path}")
            return self._read_from_cache(cache_path)
        
        # Получаем данные из API
        logger.info(f"Получение объявлений из API с параметрами: {params}")
        ads = self.account.get_ads(params=params)
        
        # Преобразуем объекты в словари
        result = [ad.export_all_data() for ad in ads]
        
        # Сохраняем в кэш
        if self.use_cache:
            self._write_to_cache(cache_path, result)
        
        return result
    
    @retry_on_api_error(max_retries=3, initial_delay=5, backoff_factor=2)
    def fetch_insights(self, entity_ids: List[str] = None, entity_type: str = 'campaign',
                      start_date: str = None, end_date: str = None, 
                      params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Получает статистику (insights) с учетом кэширования.
        
        Args:
            entity_ids (list): Список ID сущностей для получения статистики.
            entity_type (str): Тип сущности (campaign, adset, ad).
            start_date (str): Начальная дата в формате YYYY-MM-DD.
            end_date (str): Конечная дата в формате YYYY-MM-DD.
            params (dict): Параметры запроса.
            
        Returns:
            list: Список данных статистики.
        """
        if params is None:
            params = {}
        
        # Добавляем базовые поля, если не указаны
        if 'fields' not in params:
            params['fields'] = [
                'impressions', 'clicks', 'spend', 'ctr', 'cpc', 'cpp',
                'reach', 'frequency', 'actions', 'action_values'
            ]
        
        # Добавляем временной диапазон, если указан
        if start_date and end_date:
            params['time_range'] = {
                'since': start_date,
                'until': end_date
            }
        
        # Проверяем кэш
        cache_params = params.copy()
        cache_params['entity_ids'] = entity_ids
        cache_params['entity_type'] = entity_type
        
        cache_key = self._get_cache_key('insights', cache_params)
        cache_path = self._get_cache_path(cache_key)
        
        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info(f"Получение статистики из кэша: {cache_path}")
            return self._read_from_cache(cache_path)
        
        # Получаем данные из API
        logger.info(f"Получение статистики из API для {entity_type} с параметрами: {params}")
        
        result = []
        
        if entity_ids:
            for entity_id in entity_ids:
                try:
                    if entity_type == 'campaign':
                        entity = Campaign(entity_id)
                    elif entity_type == 'adset':
                        entity = AdSet(entity_id)
                    elif entity_type == 'ad':
                        entity = Ad(entity_id)
                    else:
                        raise ValueError(f"Неизвестный тип сущности: {entity_type}")
                    
                    insights = entity.get_insights(params=params)
                    
                    # Преобразуем объекты в словари и добавляем ID сущности
                    for insight in insights:
                        insight_data = insight.export_all_data()
                        insight_data[f'{entity_type}_id'] = entity_id
                        result.append(insight_data)
                        
                except Exception as e:
                    logger.error(f"Ошибка при получении статистики для {entity_type} {entity_id}: {str(e)}")
        else:
            # Если ID не указаны, получаем статистику для всего аккаунта
            insights = self.account.get_insights(params=params)
            result = [insight.export_all_data() for insight in insights]
        
        # Сохраняем в кэш
        if self.use_cache:
            self._write_to_cache(cache_path, result)
        
        return result
    
    def fetch_all_batch(self, entity_type: str = 'campaigns', batch_size: int = 10, 
                       pause_between_batches: float = 3.0, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Получает данные пакетами с паузами между запросами.
        
        Args:
            entity_type (str): Тип сущности (campaigns, adsets, ads, insights).
            batch_size (int): Размер пакета.
            pause_between_batches (float): Пауза между пакетами в секундах.
            params (dict): Параметры запроса.
            
        Returns:
            list: Список данных.
        """
        if params is None:
            params = {}
        
        # Определяем метод получения данных в зависимости от типа сущности
        if entity_type == 'campaigns':
            fetch_method = self.fetch_campaigns
        elif entity_type == 'adsets':
            fetch_method = self.fetch_adsets
        elif entity_type == 'ads':
            fetch_method = self.fetch_ads
        elif entity_type == 'insights':
            fetch_method = self.fetch_insights
        else:
            raise ValueError(f"Неизвестный тип сущности: {entity_type}")
        
        # Проверяем кэш для всего запроса
        cache_key = self._get_cache_key(f'all_{entity_type}', params)
        cache_path = self._get_cache_path(cache_key)
        
        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info(f"Получение всех данных {entity_type} из кэша: {cache_path}")
            return self._read_from_cache(cache_path)
        
        # Получаем данные пакетами
        logger.info(f"Получение всех данных {entity_type} пакетами по {batch_size}")
        
        result = []
        offset = 0
        
        while True:
            # Добавляем параметры пагинации
            batch_params = params.copy()
            batch_params['limit'] = batch_size
            
            if offset > 0:
                # Для Facebook API используется курсор, но мы эмулируем смещение
                batch_params['after'] = f"{offset}"
            
            # Получаем пакет данных
            batch_data = fetch_method(params=batch_params)
            
            if not batch_data:
                break
            
            result.extend(batch_data)
            
            # Если получено меньше данных, чем размер пакета, значит это последний пакет
            if len(batch_data) < batch_size:
                break
            
            # Увеличиваем смещение и делаем паузу
            offset += batch_size
            time.sleep(pause_between_batches)
        
        # Сохраняем все данные в кэш
        if self.use_cache:
            self._write_to_cache(cache_path, result)
        
        return result
    
    def get_campaign_insights(self, campaign_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Получает агрегированные данные статистики для кампании.
        
        Args:
            campaign_id (str): ID кампании.
            start_date (str): Начальная дата в формате YYYY-MM-DD.
            end_date (str): Конечная дата в формате YYYY-MM-DD.
            
        Returns:
            dict: Агрегированные данные статистики.
        """
        params = {
            'fields': [
                'impressions', 'clicks', 'spend', 'ctr', 'cpc', 'cpp',
                'reach', 'frequency', 'actions', 'action_values'
            ],
            'time_range': {
                'since': start_date,
                'until': end_date
            }
        }
        
        insights = self.fetch_insights(entity_ids=[campaign_id], entity_type='campaign', params=params)
        
        if not insights:
            return {}
        
        # Агрегируем данные, если получено несколько записей
        if len(insights) > 1:
            aggregated = {
                'impressions': 0,
                'clicks': 0,
                'spend': 0,
                'reach': 0,
                'actions': []
            }
            
            for insight in insights:
                aggregated['impressions'] += int(insight.get('impressions', 0))
                aggregated['clicks'] += int(insight.get('clicks', 0))
                aggregated['spend'] += float(insight.get('spend', 0))
                aggregated['reach'] += int(insight.get('reach', 0))
                
                if 'actions' in insight:
                    aggregated['actions'].extend(insight['actions'])
            
            # Рассчитываем производные метрики
            if aggregated['impressions'] > 0:
                aggregated['ctr'] = aggregated['clicks'] / aggregated['impressions']
                aggregated['cpp'] = aggregated['spend'] / aggregated['impressions'] * 1000
            else:
                aggregated['ctr'] = 0
                aggregated['cpp'] = 0
                
            if aggregated['clicks'] > 0:
                aggregated['cpc'] = aggregated['spend'] / aggregated['clicks']
            else:
                aggregated['cpc'] = 0
                
            if aggregated['reach'] > 0:
                aggregated['frequency'] = aggregated['impressions'] / aggregated['reach']
            else:
                aggregated['frequency'] = 0
                
            return aggregated
        else:
            # Если получена только одна запись, возвращаем её
            return insights[0]
    
    def clear_cache(self, entity_type: str = None) -> None:
        """
        Очищает кэш для указанного типа сущности или весь кэш.
        
        Args:
            entity_type (str, optional): Тип сущности для очистки кэша.
                Если None, очищается весь кэш.
        """
        if not os.path.exists(self.cache_dir):
            return
        
        if entity_type:
            # Очищаем кэш только для указанного типа сущности
            prefix = f"{entity_type}_"
            for filename in os.listdir(self.cache_dir):
                if filename.startswith(prefix) and filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            logger.info(f"Кэш для {entity_type} очищен")
        else:
            # Очищаем весь кэш
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            logger.info("Весь кэш очищен") 