#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для генерации отчетов о рекламных кампаниях Facebook.

Этот модуль содержит функции для получения данных о кампаниях,
их анализа и формирования отчетов.
"""

import os
import logging
import random
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import json
import requests

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth, get_api, get_ad_account

# Настройка логирования
logger = logging.getLogger(__name__)

def get_campaigns_list(campaign_id=None, status=None, fields=None):
    """
    Получает список кампаний из рекламного аккаунта Facebook.
    
    Args:
        campaign_id (str, optional): ID кампании для фильтрации.
        status (str, optional): Статус кампаний для фильтрации (ACTIVE, PAUSED, и т.д.).
        fields (list, optional): Список полей для запроса.
        
    Returns:
        list: Список объектов кампаний.
    """
    try:
        # Получаем API и аккаунт
        api = get_api()
        account = get_ad_account()
        
        account_id = account['id']
        logger.info(f"Используется аккаунт: {account_id}")
        
        # Настраиваем параметры запроса
        if fields is None:
            fields = [
                'id', 'name', 'status', 'objective', 
                'created_time', 'start_time', 'stop_time',
                'daily_budget', 'lifetime_budget',
                'effective_status'
            ]
        
        params = {
            'fields': fields
        }
        
        # Добавляем фильтрацию по статусу, если указан
        if status:
            params['filtering'] = [
                {
                    'field': 'effective_status',
                    'operator': 'EQUAL',
                    'value': status
                }
            ]
        
        # Добавляем фильтрацию по ID кампании, если указан
        if campaign_id:
            params['filtering'] = params.get('filtering', [])
            params['filtering'].append({
                'field': 'id',
                'operator': 'EQUAL',
                'value': campaign_id
            })
        
        logger.info(f"Параметры запроса: {params}")
        
        # Получаем токен доступа для логирования
        access_token = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')
        token_preview = access_token[:10] + '...' if len(access_token) > 10 else access_token
        logger.info(f"Используется токен доступа: {token_preview} (первые 10 символов)")
        
        # Прямой запрос через requests
        try:
            logger.info(f"Выполняем запрос к аккаунту {account_id}")
            
            # Формируем URL для запроса
            api_version = '21.0'  # Используем текущую версию API
            base_url = f"https://graph.facebook.com/v{api_version}"
            endpoint = f"{base_url}/{account_id}/campaigns"
            
            # Подготавливаем параметры запроса
            request_params = {
                'access_token': access_token,
                'fields': ','.join(params['fields'])
            }
            
            # Добавляем фильтрацию, если есть
            if 'filtering' in params:
                request_params['filtering'] = json.dumps(params['filtering'])
            
            # Выполняем запрос
            logger.info(f"URL запроса: {endpoint}")
            logger.info(f"Параметры запроса: {request_params}")
            
            response = requests.get(endpoint, params=request_params)
            
            # Логируем информацию о запросе
            logger.info(f"Статус ответа API: {response.status_code}")
            logger.info(f"Заголовки ответа: {response.headers}")
            
            # Проверяем статус ответа
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"Ответ API: {data}")
                    if 'data' in data and len(data['data']) > 0:
                        logger.info(f"Получено кампаний: {len(data['data'])}")
                        # Преобразуем данные в объекты Campaign
                        campaigns = []
                        for campaign_data in data['data']:
                            campaign = Campaign(campaign_data['id'])
                            for key, value in campaign_data.items():
                                campaign[key] = value
                            campaigns.append(campaign)
                        return campaigns
                    else:
                        logger.warning("API вернул пустой список кампаний")
                        logger.info(f"Полный ответ API: {data}")
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка декодирования JSON: {str(e)}")
                    logger.info(f"Текст ответа: {response.text}")
            else:
                logger.error(f"Ошибка API: {response.status_code}")
                logger.info(f"Текст ответа: {response.text}")
        
        except Exception as e:
            logger.error(f"Ошибка при прямом запросе к API: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Стек вызовов: {traceback.format_exc()}")
        
        # Если прямой запрос не удался, пробуем через SDK
        logger.info("Пробуем запрос через SDK Facebook")
        
        # Для SDK используем другой формат параметров
        sdk_params = {
            'fields': params['fields']
        }
        
        # Для SDK используем другой формат фильтрации
        if status:
            sdk_params['effective_status'] = [status]
        
        if campaign_id:
            sdk_params['id'] = campaign_id
            
        logger.info(f"Параметры SDK запроса: {sdk_params}")
        
        campaigns = account.get_campaigns(params=sdk_params)
        return campaigns
        
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Стек вызовов: {traceback.format_exc()}")
        return []

def get_campaign_data(campaign_id: str = None, days: int = 30, status: str = 'ACTIVE', date_preset: str = None, fields: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Получение данных о кампаниях.
    
    Args:
        campaign_id (str, optional): ID конкретной кампании. Если None, возвращаются данные по всем кампаниям.
        days (int): Количество дней для анализа.
        status (str): Статус кампаний для получения (ACTIVE, PAUSED, ALL).
        date_preset (str, optional): Предустановленный период (yesterday, last_7_days, last_30_days).
        fields (List[str], optional): Список полей для получения.
        
    Returns:
        dict: Словарь с данными о кампании или None в случае ошибки.
    """
    try:
        # Инициализация API
        auth = FacebookAuth()
        auth.initialize()  # Важно вызвать initialize перед использованием API
        api = auth.get_api()
        
        # Если запрашивается конкретная кампания
        if campaign_id:
            # Получаем кампанию
            campaign = Campaign(campaign_id)
            
            # Получаем основные данные о кампании
            campaign_data = campaign.api_get(fields=[
                'id',
                'name',
                'status',
                'objective',
                'created_time',
                'start_time',
                'stop_time',
                'daily_budget',
                'lifetime_budget',
                'targeting'
            ])
            
            # Определяем бюджет
            budget = 0
            if 'daily_budget' in campaign_data:
                budget = float(campaign_data['daily_budget']) / 100  # Конвертируем из центов в доллары
            elif 'lifetime_budget' in campaign_data:
                budget = float(campaign_data['lifetime_budget']) / 100
            
            # Получаем статистику
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            insights = campaign.get_insights(
                fields=[
                    'impressions',
                    'clicks',
                    'ctr',
                    'cpc',
                    'spend',
                    'actions'
                ],
                params={
                    'time_range': {
                        'since': start_date.strftime('%Y-%m-%d'),
                        'until': end_date.strftime('%Y-%m-%d')
                    },
                    'time_increment': 1
                }
            )
            
            # Обрабатываем статистику
            total_impressions = 0
            total_clicks = 0
            total_spend = 0
            total_conversions = 0
            daily_stats = []
            
            for day_data in insights:
                impressions = int(day_data.get('impressions', 0))
                clicks = int(day_data.get('clicks', 0))
                spend = float(day_data.get('spend', 0))
                ctr = float(day_data.get('ctr', 0)) * 100  # Конвертируем в проценты
                cpc = float(day_data.get('cpc', 0))
                
                # Получаем конверсии из actions
                conversions = 0
                if 'actions' in day_data:
                    for action in day_data['actions']:
                        if action['action_type'] in ['offsite_conversion', 'lead', 'purchase']:
                            conversions += int(action['value'])
                
                # Добавляем данные за день
                daily_stats.append({
                    'date': day_data.get('date_start'),
                    'impressions': impressions,
                    'clicks': clicks,
                    'spend': spend,
                    'ctr': ctr,
                    'cpc': cpc,
                    'conversions': conversions
                })
                
                # Суммируем общие показатели
                total_impressions += impressions
                total_clicks += clicks
                total_spend += spend
                total_conversions += conversions
            
            # Рассчитываем общие метрики
            total_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            total_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
            total_cost_per_conversion = (total_spend / total_conversions) if total_conversions > 0 else 0
            
            # Формируем краткое описание таргетинга
            targeting_summary = "Не указано"
            if 'targeting' in campaign_data:
                targeting = campaign_data['targeting']
                targeting_parts = []
                
                if 'geo_locations' in targeting:
                    countries = targeting['geo_locations'].get('countries', [])
                    if countries:
                        targeting_parts.append(f"Страны: {', '.join(countries)}")
                
                if 'age_min' in targeting and 'age_max' in targeting:
                    targeting_parts.append(f"Возраст: {targeting['age_min']}-{targeting['age_max']}")
                
                if 'genders' in targeting:
                    genders = {1: 'М', 2: 'Ж'}
                    gender_list = [genders.get(g, str(g)) for g in targeting['genders']]
                    targeting_parts.append(f"Пол: {', '.join(gender_list)}")
                
                if targeting_parts:
                    targeting_summary = "; ".join(targeting_parts)
            
            # Формируем результат
            return {
                'id': campaign_data['id'],
                'name': campaign_data['name'],
                'status': campaign_data['status'],
                'objective': campaign_data.get('objective', 'Не указано'),
                'created_time': campaign_data.get('created_time', 'Не указано'),
                'start_time': campaign_data.get('start_time', 'Не указано'),
                'stop_time': campaign_data.get('stop_time', 'Не указано'),
                'budget': budget,
                'targeting': targeting_summary,
                'metrics': {
                    'impressions': total_impressions,
                    'clicks': total_clicks,
                    'ctr': total_ctr,
                    'cpc': total_cpc,
                    'spend': total_spend,
                    'conversions': total_conversions,
                    'cost_per_conversion': total_cost_per_conversion
                },
                'daily_stats': daily_stats
            }
        else:
            # Получаем список кампаний
            campaigns_list = get_campaigns_list(status=status)
            
            # Если нужны дополнительные данные для каждой кампании
            if fields:
                result = []
                for campaign in campaigns_list:
                    campaign_id = campaign['id']
                    # Получаем метрики для кампании
                    campaign_metrics = {}
                    
                    # Получаем статистику
                    try:
                        campaign_obj = Campaign(campaign_id)
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=days)
                        
                        # Определяем период на основе date_preset
                        params = {}
                        if date_preset:
                            params['date_preset'] = date_preset
                        else:
                            params['time_range'] = {
                                'since': start_date.strftime('%Y-%m-%d'),
                                'until': end_date.strftime('%Y-%m-%d')
                            }
                        
                        insights = campaign_obj.get_insights(
                            fields=[
                                'impressions',
                                'clicks',
                                'ctr',
                                'cpc',
                                'spend',
                                'actions'
                            ],
                            params=params
                        )
                        
                        if insights:
                            insight = insights[0]  # Берем первый элемент, так как без time_increment возвращается один элемент
                            
                            impressions = int(insight.get('impressions', 0))
                            clicks = int(insight.get('clicks', 0))
                            spend = float(insight.get('spend', 0))
                            ctr = float(insight.get('ctr', 0)) * 100  # Конвертируем в проценты
                            cpc = float(insight.get('cpc', 0))
                            
                            # Получаем конверсии из actions
                            conversions = 0
                            if 'actions' in insight:
                                for action in insight['actions']:
                                    if action['action_type'] in ['offsite_conversion', 'lead', 'purchase']:
                                        conversions += int(action['value'])
                            
                            campaign_metrics = {
                                'impressions': impressions,
                                'clicks': clicks,
                                'ctr': ctr,
                                'cpc': cpc,
                                'spend': spend,
                                'conversions': conversions
                            }
                    except Exception as e:
                        logger.error(f"Ошибка при получении метрик для кампании {campaign_id}: {e}")
                    
                    # Добавляем метрики к данным о кампании
                    campaign['metrics'] = campaign_metrics
                    result.append(campaign)
                
                return result
            
            return campaigns_list
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных о кампании {campaign_id}: {e}")
        logger.info("Попытка повторного подключения к Facebook API...")
        
        try:
            # Повторная инициализация API с обновленным токеном
            auth = FacebookAuth()
            auth.initialize()  # Убран параметр force_refresh
            
            # Повторяем запрос (упрощенный вариант для повторной попытки)
            if campaign_id:
                campaign = Campaign(campaign_id)
                campaign_data = campaign.api_get(fields=['id', 'name', 'status', 'objective', 'daily_budget', 'lifetime_budget'])
                
                # Определяем бюджет
                budget = 0
                if 'daily_budget' in campaign_data:
                    budget = float(campaign_data['daily_budget']) / 100  # Конвертируем из центов в доллары
                elif 'lifetime_budget' in campaign_data:
                    budget = float(campaign_data['lifetime_budget']) / 100
                
                return {
                    'id': campaign_data['id'],
                    'name': campaign_data['name'],
                    'status': campaign_data['status'],
                    'objective': campaign_data.get('objective', 'Не указано'),
                    'budget': budget,
                    'metrics': {
                        'impressions': 0,
                        'clicks': 0,
                        'ctr': 0,
                        'cpc': 0,
                        'spend': 0,
                        'conversions': 0,
                        'cost_per_conversion': 0
                    }
                }
            else:
                return get_campaigns_list(status=status)
                
        except Exception as e2:
            logger.error(f"Повторная ошибка при получении данных о кампании: {e2}")
            return None

def get_campaign_performance(campaign_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Получение данных о производительности кампании или всех кампаний.
    
    Args:
        campaign_id (str, optional): ID кампании. Если не указан, возвращаются данные по всем кампаниям.
        
    Returns:
        Union[Dict[str, Any], List[Dict[str, Any]]]: Данные о производительности кампании или список данных о кампаниях.
    """
    try:
        # Инициализация API
        auth = FacebookAuth()
        auth.initialize()
        
        if campaign_id:
            # Получаем данные по конкретной кампании
            campaign = Campaign(campaign_id)
            
            # Получаем основные данные о кампании
            campaign_data = campaign.api_get(fields=['id', 'name', 'status', 'objective', 'daily_budget', 'lifetime_budget'])
            
            # Определяем бюджет
            budget = 0
            if 'daily_budget' in campaign_data:
                budget = float(campaign_data['daily_budget']) / 100  # Конвертируем из центов в доллары
            elif 'lifetime_budget' in campaign_data:
                budget = float(campaign_data['lifetime_budget']) / 100
            
            # Получаем метрики производительности
            try:
                insights = campaign.get_insights(fields=[
                    'impressions',
                    'clicks',
                    'ctr',
                    'cpc',
                    'spend',
                    'conversions',
                    'cost_per_conversion'
                ], params={
                    'date_preset': 'last_30_days'
                })
                
                # Форматируем метрики
                metrics = {
                    'impressions': 0,
                    'clicks': 0,
                    'ctr': 0,
                    'cpc': 0,
                    'spend': 0,
                    'conversions': 0,
                    'cost_per_conversion': 0
                }
                
                if insights and len(insights) > 0:
                    impressions = int(insights[0].get('impressions', 0))
                    clicks = int(insights[0].get('clicks', 0))
                    ctr = float(insights[0].get('ctr', 0)) * 100  # Конвертируем в проценты
                    cpc = float(insights[0].get('cpc', 0))  # В долларах
                    spend = float(insights[0].get('spend', 0))  # В долларах
                    conversions = int(insights[0].get('conversions', 0))
                    cost_per_conversion = float(insights[0].get('cost_per_conversion', 0))  # В долларах
                    
                    metrics = {
                        'impressions': impressions,
                        'clicks': clicks,
                        'ctr': ctr,
                        'cpc': cpc,
                        'spend': spend,
                        'conversions': conversions,
                        'cost_per_conversion': cost_per_conversion
                    }
            except Exception as e:
                logger.error(f"Ошибка при получении метрик для кампании {campaign_id}: {e}")
            
            # Формируем результат
            return {
                'id': campaign_data['id'],
                'name': campaign_data['name'],
                'status': campaign_data['status'],
                'objective': campaign_data.get('objective', 'Не указано'),
                'budget': budget,
                'metrics': metrics
            }
        else:
            # Получаем данные по всем кампаниям
            campaigns_list = get_campaigns_list('ALL')
            
            # Если нет кампаний, возвращаем пустой список
            if not campaigns_list:
                return []
            
            # Для каждой кампании получаем метрики
            result = []
            for campaign in campaigns_list:
                campaign_id = campaign['id']
                
                # Получаем метрики производительности
                campaign_metrics = {
                    'impressions': 0,
                    'clicks': 0,
                    'ctr': 0,
                    'cpc': 0,
                    'spend': 0,
                    'conversions': 0,
                    'cost_per_conversion': 0
                }
                
                try:
                    campaign_obj = Campaign(campaign_id)
                    insights = campaign_obj.get_insights(fields=[
                        'impressions',
                        'clicks',
                        'ctr',
                        'cpc',
                        'spend',
                        'conversions',
                        'cost_per_conversion'
                    ], params={
                        'date_preset': 'last_30_days'
                    })
                    
                    if insights and len(insights) > 0:
                        impressions = int(insights[0].get('impressions', 0))
                        clicks = int(insights[0].get('clicks', 0))
                        ctr = float(insights[0].get('ctr', 0)) * 100  # Конвертируем в проценты
                        cpc = float(insights[0].get('cpc', 0))  # В долларах
                        spend = float(insights[0].get('spend', 0))  # В долларах
                        conversions = int(insights[0].get('conversions', 0))
                        cost_per_conversion = float(insights[0].get('cost_per_conversion', 0))  # В долларах
                        
                        campaign_metrics = {
                            'impressions': impressions,
                            'clicks': clicks,
                            'ctr': ctr,
                            'cpc': cpc,
                            'spend': spend,
                            'conversions': conversions,
                            'cost_per_conversion': cost_per_conversion
                        }
                except Exception as e:
                    logger.error(f"Ошибка при получении метрик для кампании {campaign_id}: {e}")
                
                # Добавляем метрики к данным о кампании
                campaign['metrics'] = campaign_metrics
                result.append(campaign)
            
            return result
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных о кампании {campaign_id}: {e}")
        logger.info("Попытка повторного подключения к Facebook API...")
        
        try:
            # Повторная инициализация API с обновленным токеном
            auth = FacebookAuth()
            auth.initialize()  # Убран параметр force_refresh
            
            # Повторяем запрос (упрощенный вариант для повторной попытки)
            if campaign_id:
                campaign = Campaign(campaign_id)
                campaign_data = campaign.api_get(fields=['id', 'name', 'status', 'objective', 'daily_budget', 'lifetime_budget'])
                
                # Определяем бюджет
                budget = 0
                if 'daily_budget' in campaign_data:
                    budget = float(campaign_data['daily_budget']) / 100  # Конвертируем из центов в доллары
                elif 'lifetime_budget' in campaign_data:
                    budget = float(campaign_data['lifetime_budget']) / 100
                
                return {
                    'id': campaign_data['id'],
                    'name': campaign_data['name'],
                    'status': campaign_data['status'],
                    'objective': campaign_data.get('objective', 'Не указано'),
                    'budget': budget,
                    'metrics': {
                        'impressions': 0,
                        'clicks': 0,
                        'ctr': 0,
                        'cpc': 0,
                        'spend': 0,
                        'conversions': 0,
                        'cost_per_conversion': 0
                    }
                }
            else:
                # Для всех кампаний возвращаем пустой список
                return []
                
        except Exception as e2:
            logger.error(f"Повторная ошибка при получении данных о кампании: {e2}")
            # Возвращаем пустой результат
            if campaign_id:
                return {}
            else:
                return []

def _get_test_campaigns(count: int, status_type: str) -> List[Dict[str, Any]]:
    """
    Генерация тестовых данных о кампаниях для отладки.
    
    Args:
        count (int): Количество кампаний для генерации.
        status_type (str): Тип статуса (ACTIVE, PAUSED, MIXED).
        
    Returns:
        list: Список словарей с тестовыми данными о кампаниях.
    """
    result = []
    objectives = ['CONVERSIONS', 'LINK_CLICKS', 'BRAND_AWARENESS', 'REACH']
    
    for i in range(1, count + 1):
        if status_type == 'MIXED':
            status = 'ACTIVE' if i % 2 == 0 else 'PAUSED'
        else:
            status = status_type
        
        campaign_id = f"12345678{i:02d}"
        result.append({
            'id': campaign_id,
            'name': f"Тестовая кампания {i}",
            'status': status,
            'objective': random.choice(objectives),
            'created_time': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'start_time': (datetime.now() - timedelta(days=29)).strftime('%Y-%m-%d'),
            'stop_time': None if status == 'ACTIVE' else datetime.now().strftime('%Y-%m-%d'),
            'budget': random.uniform(1000, 5000)
        })
    
    return result

def _get_test_campaign_data(campaign_id: str) -> Dict[str, Any]:
    """
    Генерация тестовых данных о конкретной кампании для отладки.
    
    Args:
        campaign_id (str): ID кампании.
        
    Returns:
        dict: Словарь с тестовыми данными о кампании.
    """
    # Базовые данные о кампании
    campaign_data = {
        'id': campaign_id,
        'name': f"Тестовая кампания {campaign_id[-2:]}",
        'status': 'ACTIVE',
        'objective': 'CONVERSIONS',
        'created_time': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'start_time': (datetime.now() - timedelta(days=29)).strftime('%Y-%m-%d'),
        'stop_time': None,
        'budget': random.uniform(1000, 5000),
        'targeting_summary': "Страны: Россия; Возраст: 25-45; Пол: М, Ж"
    }
    
    # Генерация статистики
    total_impressions = 0
    total_clicks = 0
    total_spend = 0
    total_conversions = 0
    daily_stats = []
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    current_date = start_date
    while current_date <= end_date:
        # Генерируем случайные данные с некоторой тенденцией
        day_of_week = current_date.weekday()
        day_factor = 1.0 + (day_of_week % 3) * 0.2  # Выше в начале недели
        
        impressions = int(random.uniform(800, 1500) * day_factor)
        ctr = random.uniform(0.8, 2.5)
        clicks = int(impressions * ctr / 100)
        cpc = random.uniform(30, 80)
        spend = clicks * cpc
        conversions = int(clicks * random.uniform(0.05, 0.15))
        
        daily_stats.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'impressions': impressions,
            'clicks': clicks,
            'spend': spend,
            'ctr': ctr,
            'cpc': cpc,
            'conversions': conversions
        })
        
        total_impressions += impressions
        total_clicks += clicks
        total_spend += spend
        total_conversions += conversions
        
        current_date += timedelta(days=1)
    
    # Рассчитываем общие метрики
    total_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    total_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    total_cost_per_conversion = (total_spend / total_conversions) if total_conversions > 0 else 0
    
    # Добавляем статистику в результат
    campaign_data.update({
        'impressions': total_impressions,
        'clicks': total_clicks,
        'spend': total_spend,
        'ctr': total_ctr,
        'cpc': total_cpc,
        'conversions': total_conversions,
        'cost_per_conversion': total_cost_per_conversion,
        'daily_stats': daily_stats
    })
    
    return campaign_data 