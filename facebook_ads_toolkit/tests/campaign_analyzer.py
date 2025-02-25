#!/usr/bin/env python
"""
Скрипт для пошагового анализа рекламных кампаний Facebook.
Анализирует по одной кампании за раз с соблюдением лимитов API.
"""

import sys
import os
import time
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_ads_toolkit.utils.cache_handler import CacheHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CampaignAnalyzer:
    """Класс для пошагового анализа рекламных кампаний."""
    
    def __init__(self, access_token: str, account_id: str, use_cache: bool = True, cache_ttl: int = 3600):
        """
        Инициализация анализатора.
        
        Args:
            access_token: Токен доступа к API Facebook
            account_id: ID рекламного аккаунта
            use_cache: Использовать ли кэширование
            cache_ttl: Время жизни кэша в секундах
        """
        self.access_token = access_token
        self.account_id = account_id
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.cache_handler = CacheHandler(expiration_time=cache_ttl) if use_cache else None
        
        # Инициализация API
        FacebookAdsApi.init(access_token=access_token)
        self.account = AdAccount(account_id)
        
        # Для хранения временного диапазона
        self.time_range = None
        self.set_default_time_range(days=14)
        
        logger.info(f"Анализатор инициализирован для аккаунта {account_id}")
        if use_cache:
            logger.info(f"Кэширование включено (TTL: {cache_ttl} секунд)")
    
    def set_default_time_range(self, days: int = 14):
        """
        Установка временного диапазона.
        
        Args:
            days: Количество дней для анализа
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        self.time_range = {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        }
        logger.info(f"Установлен временной диапазон: {self.time_range['since']} - {self.time_range['until']}")
    
    def get_active_campaigns(self, year_filter: str = '2025', limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение списка активных кампаний с фильтрацией по году.
        
        Args:
            year_filter: Год для фильтрации (по умолчанию 2025)
            limit: Максимальное количество кампаний
            
        Returns:
            List[Dict[str, Any]]: Список данных о кампаниях
        """
        logger.info(f"Получение активных кампаний за {year_filter} год...")
        
        # Поля для запроса
        campaign_fields = [
            'id',
            'name',
            'objective',
            'status',
            'daily_budget',
            'lifetime_budget',
            'created_time',
            'updated_time',
            'start_time'
        ]
        
        # Параметры для кэширования
        cache_params = {
            'account_id': self.account_id,
            'effective_status': ['ACTIVE'],
            'year_filter': year_filter,
            'limit': limit,
            'fields': campaign_fields
        }
        
        # Проверяем кэш
        if self.use_cache:
            cache_data = self.cache_handler.get_from_cache('campaigns_list', cache_params)
            if cache_data:
                logger.info(f"Загружено {len(cache_data)} кампаний из кэша")
                return cache_data
        
        # Запрашиваем данные из API
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
            
            if 'created_time' in campaign_data:
                campaign_year = campaign_data['created_time'][:4]  # Берем первые 4 символа (год)
                
                if year_filter is None or campaign_year == year_filter:
                    filtered_campaigns.append(campaign_data)
        
        # Сохраняем в кэш
        if self.use_cache:
            self.cache_handler.save_to_cache('campaigns_list', cache_params, filtered_campaigns)
        
        logger.info(f"Получено {len(filtered_campaigns)} активных кампаний за {year_filter} год")
        return filtered_campaigns
    
    def get_campaign_details(self, campaign_id: str) -> Dict[str, Any]:
        """
        Получение подробной информации о рекламной кампании.
        
        Args:
            campaign_id: ID кампании
        
        Returns:
            Dict[str, Any]: Подробная информация о кампании
        """
        logger.info(f"Получение подробной информации о кампании {campaign_id}...")
        
        # Параметры для кэширования
        cache_params = {
            'campaign_id': campaign_id,
            'time_range': self.time_range
        }
        
        # Проверяем кэш
        if self.use_cache:
            cache_data = self.cache_handler.get_from_cache('campaign_details', cache_params)
            if cache_data:
                logger.info(f"Загружены детали кампании {campaign_id} из кэша")
                return cache_data
        
        # Собираем информацию о кампании
        campaign = Campaign(campaign_id)
        campaign_data = campaign.api_get(fields=[
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
            'spend_cap',
            'bid_strategy'
        ]).export_all_data()
        
        # Получаем статистику (insights)
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
        
        try:
            insights = campaign.get_insights(params=insights_params)
            if insights and len(insights) > 0:
                campaign_data['insights'] = insights[0].export_all_data()
            else:
                campaign_data['insights'] = {}
        except Exception as e:
            logger.error(f"Ошибка при получении статистики для кампании {campaign_id}: {str(e)}")
            campaign_data['insights'] = {}
        
        # Получаем группы объявлений
        try:
            time.sleep(5)  # Пауза перед запросом групп объявлений
            
            adsets = campaign.get_ad_sets(fields=[
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
            ])
            
            campaign_data['adsets'] = []
            
            for adset in adsets:
                adset_data = adset.export_all_data()
                
                # Получаем статистику для группы объявлений
                time.sleep(5)  # Пауза перед запросом статистики
                
                try:
                    adset_insights = adset.get_insights(params=insights_params)
                    if adset_insights and len(adset_insights) > 0:
                        adset_data['insights'] = adset_insights[0].export_all_data()
                    else:
                        adset_data['insights'] = {}
                except Exception as e:
                    logger.error(f"Ошибка при получении статистики для группы объявлений {adset.get_id()}: {str(e)}")
                    adset_data['insights'] = {}
                
                # Получаем объявления для группы
                time.sleep(5)  # Пауза перед запросом объявлений
                
                try:
                    ads = adset.get_ads(fields=[
                        'id',
                        'name',
                        'adset_id',
                        'campaign_id',
                        'status',
                        'effective_status',
                        'creative',
                        'created_time',
                        'updated_time'
                    ])
                    
                    adset_data['ads'] = []
                    
                    for ad in ads:
                        ad_data = ad.export_all_data()
                        
                        # Получаем статистику для объявления
                        time.sleep(5)  # Пауза перед запросом статистики
                        
                        try:
                            ad_insights = ad.get_insights(params=insights_params)
                            if ad_insights and len(ad_insights) > 0:
                                ad_data['insights'] = ad_insights[0].export_all_data()
                            else:
                                ad_data['insights'] = {}
                        except Exception as e:
                            logger.error(f"Ошибка при получении статистики для объявления {ad.get_id()}: {str(e)}")
                            ad_data['insights'] = {}
                        
                        adset_data['ads'].append(ad_data)
                    
                except Exception as e:
                    logger.error(f"Ошибка при получении объявлений для группы {adset.get_id()}: {str(e)}")
                    adset_data['ads'] = []
                
                campaign_data['adsets'].append(adset_data)
            
        except Exception as e:
            logger.error(f"Ошибка при получении групп объявлений для кампании {campaign_id}: {str(e)}")
            campaign_data['adsets'] = []
        
        # Сохраняем в кэш
        if self.use_cache:
            self.cache_handler.save_to_cache('campaign_details', cache_params, campaign_data)
        
        logger.info(f"Получены детали кампании {campaign_id}, групп объявлений: {len(campaign_data.get('adsets', []))}")
        return campaign_data
    
    def analyze_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ данных рекламной кампании.
        
        Args:
            campaign_data: Данные о кампании
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        logger.info(f"Анализ кампании {campaign_data.get('name', 'Без имени')} (ID: {campaign_data.get('id')})...")
        
        analysis = {
            'campaign_id': campaign_data.get('id'),
            'campaign_name': campaign_data.get('name', 'Без имени'),
            'objective': campaign_data.get('objective'),
            'status': campaign_data.get('status'),
            'created_time': campaign_data.get('created_time'),
            'budget': {
                'daily': campaign_data.get('daily_budget'),
                'lifetime': campaign_data.get('lifetime_budget'),
                'spend_cap': campaign_data.get('spend_cap')
            },
            'performance': self._analyze_performance(campaign_data),
            'adsets_analysis': []
        }
        
        # Анализ групп объявлений
        for adset in campaign_data.get('adsets', []):
            adset_analysis = {
                'adset_id': adset.get('id'),
                'adset_name': adset.get('name', 'Без имени'),
                'status': adset.get('status'),
                'optimization_goal': adset.get('optimization_goal'),
                'bid_strategy': adset.get('bid_strategy'),
                'budget': {
                    'daily': adset.get('daily_budget'),
                    'lifetime': adset.get('lifetime_budget')
                },
                'performance': self._analyze_performance(adset),
                'ads_analysis': []
            }
            
            # Анализ таргетинга
            if 'targeting' in adset:
                adset_analysis['targeting'] = self._analyze_targeting(adset.get('targeting', {}))
            
            # Анализ объявлений
            for ad in adset.get('ads', []):
                ad_analysis = {
                    'ad_id': ad.get('id'),
                    'ad_name': ad.get('name', 'Без имени'),
                    'status': ad.get('status'),
                    'effective_status': ad.get('effective_status'),
                    'performance': self._analyze_performance(ad)
                }
                
                adset_analysis['ads_analysis'].append(ad_analysis)
            
            analysis['adsets_analysis'].append(adset_analysis)
        
        # Общая оценка эффективности кампании
        analysis['overall_assessment'] = self._assess_campaign(analysis)
        
        logger.info(f"Анализ кампании {campaign_data.get('id')} завершен")
        return analysis
    
    def _analyze_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ показателей эффективности.
        
        Args:
            data: Данные объекта (кампании/группы/объявления)
            
        Returns:
            Dict[str, Any]: Результаты анализа эффективности
        """
        insights = data.get('insights', {})
        
        performance = {
            'spend': insights.get('spend', '0'),
            'impressions': insights.get('impressions', '0'),
            'clicks': insights.get('clicks', '0'),
            'ctr': insights.get('ctr', '0'),
            'cpc': insights.get('cpc', '0'),
            'reach': insights.get('reach', '0'),
            'frequency': insights.get('frequency', '0'),
            'actions': {},
            'kpis': {}
        }
        
        # Разбор действий
        for action in insights.get('actions', []):
            if 'action_type' in action and 'value' in action:
                performance['actions'][action['action_type']] = action['value']
        
        # Расчет KPI
        try:
            if float(performance['impressions']) > 0:
                performance['kpis']['ctr'] = float(performance['clicks']) / float(performance['impressions']) * 100
            
            if float(performance['clicks']) > 0:
                performance['kpis']['cpc'] = float(performance['spend']) / float(performance['clicks'])
            
            if float(performance['reach']) > 0:
                performance['kpis']['frequency'] = float(performance['impressions']) / float(performance['reach'])
                performance['kpis']['cpr'] = float(performance['spend']) / float(performance['reach'])
                
            # Оценка эффективности по CTR
            if 'ctr' in performance['kpis']:
                if performance['kpis']['ctr'] >= 1.5:
                    performance['assessment'] = 'Высокий CTR'
                elif performance['kpis']['ctr'] >= 0.8:
                    performance['assessment'] = 'Средний CTR'
                else:
                    performance['assessment'] = 'Низкий CTR'
        except (ValueError, ZeroDivisionError):
            pass
        
        return performance
    
    def _analyze_targeting(self, targeting: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ настроек таргетинга.
        
        Args:
            targeting: Данные о таргетинге
            
        Returns:
            Dict[str, Any]: Результаты анализа таргетинга
        """
        targeting_analysis = {
            'geo_locations': [],
            'demographics': {},
            'interests': [],
            'behaviors': [],
            'potential_reach': targeting.get('reach', 0)
        }
        
        # Анализ географии
        if 'geo_locations' in targeting:
            geo = targeting['geo_locations']
            
            if 'countries' in geo:
                targeting_analysis['geo_locations'].append(f"Страны: {', '.join(geo['countries'])}")
            
            if 'cities' in geo:
                cities = [f"{city.get('name', '')} ({city.get('region', '')})" for city in geo['cities']]
                targeting_analysis['geo_locations'].append(f"Города: {', '.join(cities)}")
        
        # Анализ демографии
        demographics = {}
        
        if 'age_min' in targeting and 'age_max' in targeting:
            demographics['age_range'] = f"{targeting['age_min']}-{targeting['age_max']}"
        
        if 'genders' in targeting:
            genders = []
            if 1 in targeting['genders']:
                genders.append('мужчины')
            if 2 in targeting['genders']:
                genders.append('женщины')
            
            demographics['gender'] = ', '.join(genders)
        
        targeting_analysis['demographics'] = demographics
        
        # Анализ интересов
        if 'interests' in targeting:
            for interest in targeting['interests']:
                targeting_analysis['interests'].append({
                    'name': interest.get('name', ''),
                    'id': interest.get('id', '')
                })
        
        return targeting_analysis
    
    def _assess_campaign(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Общая оценка эффективности кампании.
        
        Args:
            analysis: Результаты анализа кампании
            
        Returns:
            Dict[str, Any]: Общая оценка и рекомендации
        """
        assessment = {
            'effectiveness': 'Средняя',
            'strengths': [],
            'weaknesses': [],
            'recommendations': []
        }
        
        performance = analysis['performance']
        
        # Оценка эффективности
        try:
            ctr = performance['kpis'].get('ctr', 0)
            cpc = performance['kpis'].get('cpc', 0)
            
            # Оценка CTR
            if ctr >= 1.5:
                assessment['strengths'].append('Высокий показатель CTR')
                assessment['effectiveness'] = 'Высокая'
            elif ctr <= 0.5:
                assessment['weaknesses'].append('Низкий показатель CTR')
                assessment['effectiveness'] = 'Низкая'
                assessment['recommendations'].append('Улучшите креативы и таргетинг для повышения CTR')
            
            # Оценка CPC
            if cpc > 0:
                if cpc < 15:
                    assessment['strengths'].append('Низкая стоимость клика')
                elif cpc > 50:
                    assessment['weaknesses'].append('Высокая стоимость клика')
                    assessment['recommendations'].append('Оптимизируйте бюджет и таргетинг для снижения CPC')
            
            # Оценка объявлений
            low_ctr_ads = 0
            for adset in analysis['adsets_analysis']:
                for ad in adset['ads_analysis']:
                    ad_ctr = ad['performance']['kpis'].get('ctr', 0)
                    if ad_ctr < 0.5:
                        low_ctr_ads += 1
            
            if low_ctr_ads > 0:
                assessment['weaknesses'].append(f"Обнаружено {low_ctr_ads} объявлений с низким CTR")
                assessment['recommendations'].append('Приостановите или улучшите объявления с низким CTR')
        
        except (KeyError, TypeError):
            assessment['recommendations'].append('Недостаточно данных для полного анализа')
        
        # Рекомендации в зависимости от цели
        objective = analysis['objective']
        if objective == 'OUTCOME_TRAFFIC':
            assessment['recommendations'].append('Для цели привлечения трафика оптимизируйте по показателю CPC')
        elif objective == 'OUTCOME_ENGAGEMENT':
            assessment['recommendations'].append('Для цели взаимодействия улучшайте креативы для повышения показателя CTR')
        elif objective == 'MESSAGES':
            assessment['recommendations'].append('Для цели получения сообщений добавьте призыв к действию и улучшите целевую страницу')
        
        return assessment
    
    def save_analysis_to_file(self, analysis: Dict[str, Any], output_dir: str = 'reports'):
        """
        Сохранение результатов анализа в файл.
        
        Args:
            analysis: Результаты анализа
            output_dir: Директория для сохранения
        """
        os.makedirs(output_dir, exist_ok=True)
        
        campaign_id = analysis['campaign_id']
        campaign_name = analysis['campaign_name'].replace(' ', '_').replace('/', '-')
        
        # Форматируем имя файла
        filename = f"{output_dir}/campaign_analysis_{campaign_id}_{campaign_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты анализа сохранены в файл: {filename}")
        return filename
        
    def run_campaign_analysis(self, campaign_id: str, save_results: bool = True) -> Dict[str, Any]:
        """
        Запуск полного анализа кампании.
        
        Args:
            campaign_id: ID кампании
            save_results: Сохранять ли результаты в файл
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        # Получаем подробную информацию о кампании
        campaign_data = self.get_campaign_details(campaign_id)
        
        # Анализируем данные
        analysis = self.analyze_campaign(campaign_data)
        
        # Сохраняем результаты
        if save_results:
            self.save_analysis_to_file(analysis)
        
        return analysis
    
    def print_campaign_summary(self, analysis: Dict[str, Any]):
        """
        Вывод сводки по кампании в консоль.
        
        Args:
            analysis: Результаты анализа
        """
        print("\n" + "=" * 80)
        print(f"АНАЛИЗ КАМПАНИИ: {analysis['campaign_name']} (ID: {analysis['campaign_id']})")
        print("=" * 80)
        
        # Основная информация
        print("\nОСНОВНАЯ ИНФОРМАЦИЯ:")
        print(f"Цель: {analysis['objective']}")
        print(f"Статус: {analysis['status']}")
        print(f"Дата создания: {analysis['created_time']}")
        
        # Бюджет
        print("\nБЮДЖЕТ:")
        if analysis['budget']['daily']:
            print(f"Дневной бюджет: {analysis['budget']['daily']}")
        if analysis['budget']['lifetime']:
            print(f"Бюджет на весь период: {analysis['budget']['lifetime']}")
        
        # Эффективность
        print("\nЭФФЕКТИВНОСТЬ:")
        performance = analysis['performance']
        print(f"Расход: {performance['spend']}")
        print(f"Показы: {performance['impressions']}")
        print(f"Клики: {performance['clicks']}")
        print(f"CTR: {performance['kpis'].get('ctr', 0):.2f}%")
        print(f"CPC: {performance['kpis'].get('cpc', 0):.2f}")
        
        # Группы объявлений
        print(f"\nГРУППЫ ОБЪЯВЛЕНИЙ ({len(analysis['adsets_analysis'])}):")
        for i, adset in enumerate(analysis['adsets_analysis'], 1):
            print(f"{i}. {adset['adset_name']} - {len(adset['ads_analysis'])} объявлений")
        
        # Общая оценка
        print("\nОБЩАЯ ОЦЕНКА:")
        assessment = analysis['overall_assessment']
        print(f"Эффективность: {assessment['effectiveness']}")
        
        if assessment['strengths']:
            print("\nСильные стороны:")
            for strength in assessment['strengths']:
                print(f"- {strength}")
        
        if assessment['weaknesses']:
            print("\nСлабые стороны:")
            for weakness in assessment['weaknesses']:
                print(f"- {weakness}")
        
        # Рекомендации
        if assessment['recommendations']:
            print("\nРЕКОМЕНДАЦИИ:")
            for i, recommendation in enumerate(assessment['recommendations'], 1):
                print(f"{i}. {recommendation}")
        
        print("=" * 80 + "\n")

    def clear_cache(self):
        """Очистка кэша."""
        if self.use_cache and self.cache_handler:
            self.cache_handler.clear_cache()
            logger.info("Кэш полностью очищен")

def parse_args():
    """Разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Пошаговый анализ рекламных кампаний Facebook")
    
    parser.add_argument("--year", type=str, default="2025",
                        help="Год для фильтрации кампаний (по умолчанию 2025)")
    
    parser.add_argument("--days", type=int, default=14,
                        help="Количество дней для анализа (по умолчанию 14)")
    
    parser.add_argument("--output-dir", type=str, default="reports",
                        help="Директория для сохранения отчетов (по умолчанию 'reports')")
    
    parser.add_argument("--no-cache", action="store_true",
                        help="Отключить использование кэша")
    
    parser.add_argument("--cache-ttl", type=int, default=3600,
                        help="Время жизни кэша в секундах (по умолчанию 3600)")
    
    parser.add_argument("--clear-cache", action="store_true",
                        help="Очистить кэш перед запуском")
    
    parser.add_argument("--wait-time", type=int, default=60,
                        help="Время ожидания между анализами кампаний в секундах (по умолчанию 60)")
    
    parser.add_argument("--debug", action="store_true",
                        help="Включить расширенное логирование")
    
    parser.add_argument("--access-token", type=str,
                        default="EAAW4km4ocGkBO6v9qhh0gZAnCBxEvQRqNZCZCw1csy8BdJb4HUZBXM0cZBZClJGA8HLiJZAdK24mMXa6PQZBL5LITH3fLyXgreebyE2KHVjUp6JstedJlkZC1zZBifsTsDB4eYSQRxIDCJBSieNTYhJNojWTqoBuVzXYSQ2mGoUTeLiA0NFpcf7BylWNA98xLrPzWV",
                        help="Токен доступа к API Facebook")
    
    parser.add_argument("--account-id", type=str,
                        default="act_259290474190473",
                        help="ID рекламного аккаунта")
    
    return parser.parse_args()

def main():
    """Основная функция для запуска пошагового анализа."""
    
    args = parse_args()
    
    # Настройка уровня логирования
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Включен режим отладки")
    
    try:
        # Создаем анализатор
        analyzer = CampaignAnalyzer(
            access_token=args.access_token,
            account_id=args.account_id,
            use_cache=not args.no_cache,
            cache_ttl=args.cache_ttl
        )
        
        # Устанавливаем временной диапазон
        analyzer.set_default_time_range(days=args.days)
        
        # Очищаем кэш, если запрошено
        if args.clear_cache:
            analyzer.clear_cache()
        
        # Получаем список кампаний за указанный год
        campaigns = analyzer.get_active_campaigns(year_filter=args.year)
        
        if not campaigns:
            logger.warning(f"Активные кампании за {args.year} год не найдены")
            return 0
        
        # Анализируем по одной кампании за раз
        for i, campaign in enumerate(campaigns, 1):
            print(f"\nАнализ кампании {i}/{len(campaigns)}: {campaign.get('name', 'Без имени')} (ID: {campaign.get('id')})")
            
            try:
                # Выполняем полный анализ
                analysis = analyzer.run_campaign_analysis(
                    campaign['id'],
                    save_results=True
                )
                
                # Выводим сводку
                analyzer.print_campaign_summary(analysis)
                
                # Ждем перед переходом к следующей кампании (кроме последней)
                if i < len(campaigns):
                    print(f"Пауза {args.wait_time} секунд перед анализом следующей кампании...")
                    time.sleep(args.wait_time)
            
            except Exception as e:
                logger.error(f"Ошибка при анализе кампании {campaign.get('id')}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Пауза в случае ошибки (возможно, превышение лимита API)
                error_wait_time = 300  # 5 минут
                logger.info(f"Ждем {error_wait_time} секунд перед продолжением...")
                time.sleep(error_wait_time)
        
        print("\nАнализ всех кампаний завершен")
        return 0
    
    except Exception as e:
        logger.error(f"Ошибка при работе скрипта: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 