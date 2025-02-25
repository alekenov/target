#!/usr/bin/env python
"""
Скрипт для пошагового анализа отдельных рекламных кампаний Facebook.
Анализирует одну кампанию за раз с сохранением результатов.
"""

import sys
import os
import time
import json
import logging
import argparse
from datetime import datetime, timedelta

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_ads_toolkit.utils.cache_handler import CacheHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_active_campaigns(account, year_filter='2025', cache_handler=None):
    """
    Получение списка активных кампаний.
    
    Args:
        account: Объект рекламного аккаунта
        year_filter: Год для фильтрации
        cache_handler: Обработчик кэша
        
    Returns:
        list: Список активных кампаний
    """
    logger.info(f"Получение списка активных кампаний за {year_filter} год...")
    
    fields = [
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
    
    # Пробуем получить из кэша
    if cache_handler:
        cache_params = {
            'account_id': account.get_id_assured(),
            'year_filter': year_filter,
            'fields': fields
        }
        
        cache_result = cache_handler.get_from_cache('active_campaigns', cache_params)
        if cache_result:
            logger.info(f"Получено {len(cache_result)} кампаний из кэша")
            return cache_result
    
    # Получаем данные из API
    campaigns = account.get_campaigns(
        params={
            'effective_status': ['ACTIVE'],
            'limit': 100
        },
        fields=fields
    )
    
    # Фильтруем по году
    result = []
    
    for campaign in campaigns:
        data = campaign.export_all_data()
        
        if 'created_time' in data:
            campaign_year = data['created_time'][:4]
            
            if year_filter is None or campaign_year == year_filter:
                result.append(data)
    
    # Сохраняем в кэш
    if cache_handler:
        cache_handler.save_to_cache('active_campaigns', cache_params, result)
    
    logger.info(f"Получено {len(result)} активных кампаний за {year_filter} год")
    return result

def analyze_single_campaign(campaign_id, access_token, days=14, output_dir='reports'):
    """
    Анализ одной рекламной кампании.
    
    Args:
        campaign_id: ID кампании для анализа
        access_token: Токен доступа к API
        days: Количество дней для анализа
        output_dir: Директория для сохранения отчетов
        
    Returns:
        dict: Результаты анализа
    """
    logger.info(f"Начало анализа кампании {campaign_id}")
    
    # Инициализация API
    FacebookAdsApi.init(access_token=access_token)
    
    # Получаем информацию о кампании
    campaign = Campaign(campaign_id)
    
    try:
        # Определяем временной диапазон
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        time_range = {
            'since': start_date.strftime('%Y-%m-%d'),
            'until': end_date.strftime('%Y-%m-%d')
        }
        
        logger.info(f"Временной диапазон: {time_range['since']} - {time_range['until']}")
        
        # Получаем основную информацию о кампании
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
            'bid_strategy'
        ]).export_all_data()
        
        # Получаем статистику
        logger.info(f"Получение статистики для кампании {campaign_id}...")
        insights_fields = [
            'spend', 
            'impressions', 
            'clicks', 
            'ctr', 
            'cpc',
            'reach',
            'frequency'
        ]
        
        insights = campaign.get_insights(
            params={
                'time_range': time_range,
                'fields': insights_fields
            }
        )
        
        if insights and len(insights) > 0:
            campaign_data['insights'] = insights[0].export_all_data()
        else:
            campaign_data['insights'] = {}
        
        # Пауза перед следующим запросом
        time.sleep(5)
        
        # Получаем группы объявлений
        logger.info(f"Получение групп объявлений для кампании {campaign_id}...")
        adsets = campaign.get_ad_sets(fields=[
            'id',
            'name',
            'status',
            'daily_budget',
            'lifetime_budget',
            'bid_amount',
            'bid_strategy',
            'targeting',
            'optimization_goal'
        ])
        
        campaign_data['adsets'] = []
        
        # Анализируем группы объявлений
        for adset in adsets:
            adset_data = adset.export_all_data()
            
            # Получаем статистику для группы
            try:
                time.sleep(5)
                adset_insights = adset.get_insights(
                    params={
                        'time_range': time_range,
                        'fields': insights_fields
                    }
                )
                
                if adset_insights and len(adset_insights) > 0:
                    adset_data['insights'] = adset_insights[0].export_all_data()
                else:
                    adset_data['insights'] = {}
            except Exception as e:
                logger.error(f"Ошибка при получении статистики для группы {adset.get_id()}: {str(e)}")
                adset_data['insights'] = {}
            
            campaign_data['adsets'].append(adset_data)
        
        # Проводим анализ
        analysis = {
            'campaign_id': campaign_data['id'],
            'campaign_name': campaign_data['name'],
            'objective': campaign_data['objective'],
            'status': campaign_data['status'],
            'created_time': campaign_data['created_time'],
            'performance': analyze_performance(campaign_data),
            'adsets_analysis': []
        }
        
        # Анализ групп объявлений
        for adset in campaign_data['adsets']:
            adset_analysis = {
                'adset_id': adset['id'],
                'adset_name': adset['name'],
                'status': adset['status'],
                'performance': analyze_performance(adset)
            }
            
            # Добавляем таргетинг, если есть
            if 'targeting' in adset:
                adset_analysis['targeting'] = analyze_targeting(adset['targeting'])
            
            analysis['adsets_analysis'].append(adset_analysis)
        
        # Общая оценка
        analysis['assessment'] = assess_campaign(analysis)
        
        # Сохраняем результаты
        save_analysis(analysis, output_dir)
        
        # Выводим сводку
        print_campaign_summary(analysis)
        
        return analysis
    
    except Exception as e:
        logger.error(f"Ошибка при анализе кампании {campaign_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {'error': str(e), 'campaign_id': campaign_id}

def analyze_performance(data):
    """
    Анализ показателей эффективности.
    
    Args:
        data: Данные объекта с показателями
        
    Returns:
        dict: Результаты анализа
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
        'kpis': {}
    }
    
    # Рассчитываем KPI
    try:
        if float(performance['impressions']) > 0:
            performance['kpis']['ctr'] = float(performance['clicks']) / float(performance['impressions']) * 100
        
        if float(performance['clicks']) > 0:
            performance['kpis']['cpc'] = float(performance['spend']) / float(performance['clicks'])
        
        if float(performance['reach']) > 0:
            performance['kpis']['frequency'] = float(performance['impressions']) / float(performance['reach'])
            performance['kpis']['cpr'] = float(performance['spend']) / float(performance['reach'])
    except (ValueError, ZeroDivisionError):
        pass
    
    return performance

def analyze_targeting(targeting):
    """
    Анализ настроек таргетинга.
    
    Args:
        targeting: Данные таргетинга
        
    Returns:
        dict: Результаты анализа
    """
    result = {
        'locations': [],
        'demographics': {},
        'interests': []
    }
    
    # Анализируем локации
    if 'geo_locations' in targeting:
        geo = targeting['geo_locations']
        
        if 'countries' in geo:
            result['locations'].append(f"Страны: {', '.join(geo['countries'])}")
        
        if 'cities' in geo:
            cities = [f"{city.get('name', '')} ({city.get('region', '')})" for city in geo['cities']]
            result['locations'].append(f"Города: {', '.join(cities)}")
    
    # Анализируем демографию
    if 'age_min' in targeting and 'age_max' in targeting:
        result['demographics']['age'] = f"{targeting['age_min']}-{targeting['age_max']}"
    
    if 'genders' in targeting:
        genders = []
        if 1 in targeting['genders']:
            genders.append('мужчины')
        if 2 in targeting['genders']:
            genders.append('женщины')
        
        result['demographics']['gender'] = ', '.join(genders)
    
    # Анализируем интересы
    if 'interests' in targeting:
        for interest in targeting['interests']:
            result['interests'].append({
                'name': interest.get('name', ''),
                'id': interest.get('id', '')
            })
    
    return result

def assess_campaign(analysis):
    """
    Общая оценка эффективности кампании.
    
    Args:
        analysis: Результаты анализа
        
    Returns:
        dict: Оценка и рекомендации
    """
    assessment = {
        'effectiveness': 'Средняя',
        'strengths': [],
        'weaknesses': [],
        'recommendations': []
    }
    
    performance = analysis['performance']
    
    # Оценка CTR
    try:
        ctr = performance['kpis'].get('ctr', 0)
        cpc = performance['kpis'].get('cpc', 0)
        
        if ctr >= 1.5:
            assessment['strengths'].append('Высокий CTR')
            assessment['effectiveness'] = 'Высокая'
        elif ctr <= 0.5:
            assessment['weaknesses'].append('Низкий CTR')
            assessment['effectiveness'] = 'Низкая'
            assessment['recommendations'].append('Улучшите креативы для повышения CTR')
        
        # Оценка CPC
        if cpc > 0:
            if cpc < 15:
                assessment['strengths'].append('Низкая стоимость клика')
            elif cpc > 50:
                assessment['weaknesses'].append('Высокая стоимость клика')
                assessment['recommendations'].append('Оптимизируйте таргетинг для снижения CPC')
    except (KeyError, TypeError):
        assessment['recommendations'].append('Недостаточно данных для полной оценки')
    
    # Рекомендации в зависимости от цели
    objective = analysis['objective']
    if objective == 'OUTCOME_TRAFFIC':
        assessment['recommendations'].append('Для цели трафика оптимизируйте по показателю CPC')
    elif objective == 'OUTCOME_ENGAGEMENT':
        assessment['recommendations'].append('Для цели взаимодействия улучшайте креативы для повышения CTR')
    elif objective == 'MESSAGES':
        assessment['recommendations'].append('Для цели сообщений добавьте ясный призыв к действию')
    
    return assessment

def save_analysis(analysis, output_dir='reports'):
    """
    Сохранение результатов анализа в файл.
    
    Args:
        analysis: Результаты анализа
        output_dir: Директория для сохранения
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Формируем имя файла
    campaign_id = analysis['campaign_id']
    campaign_name = analysis['campaign_name'].replace(' ', '_').replace('/', '-')
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    filename = f"{output_dir}/analysis_{campaign_id}_{campaign_name}_{date_str}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Результаты анализа сохранены в файл: {filename}")
    return filename

def print_campaign_summary(analysis):
    """
    Вывод сводки по рекламной кампании.
    
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
        print(f"{i}. {adset['adset_name']} - {adset['status']}")
    
    # Общая оценка
    print("\nОБЩАЯ ОЦЕНКА:")
    assessment = analysis['assessment']
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

def main():
    """Основная функция для запуска анализа."""
    parser = argparse.ArgumentParser(description="Пошаговый анализ рекламных кампаний Facebook")
    
    parser.add_argument("--campaign-id", type=str,
                        help="ID конкретной кампании для анализа")
    
    parser.add_argument("--year", type=str, default="2025",
                        help="Год для фильтрации кампаний (по умолчанию 2025)")
    
    parser.add_argument("--days", type=int, default=14,
                        help="Количество дней для анализа (по умолчанию 14)")
    
    parser.add_argument("--output-dir", type=str, default="reports",
                        help="Директория для сохранения отчетов (по умолчанию 'reports')")
    
    parser.add_argument("--use-cache", action="store_true",
                        help="Использовать кэширование")
    
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
    
    args = parser.parse_args()
    
    # Настройка уровня логирования
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Включен режим отладки")
    
    # Инициализация кэша
    cache_handler = None
    if args.use_cache:
        cache_handler = CacheHandler(expiration_time=3600)
        logger.info("Кэширование включено")
        
        if args.clear_cache:
            cache_handler.clear_cache()
            logger.info("Кэш очищен")
    
    try:
        # Инициализация API
        FacebookAdsApi.init(access_token=args.access_token)
        account = AdAccount(args.account_id)
        
        if args.campaign_id:
            # Анализ одной указанной кампании
            logger.info(f"Запуск анализа для заданной кампании: {args.campaign_id}")
            analyze_single_campaign(
                args.campaign_id,
                args.access_token,
                days=args.days,
                output_dir=args.output_dir
            )
        else:
            # Получаем список кампаний
            campaigns = get_active_campaigns(account, args.year, cache_handler)
            
            if not campaigns:
                logger.warning(f"Активные кампании за {args.year} год не найдены")
                return 0
            
            logger.info(f"Найдено {len(campaigns)} кампаний для анализа")
            
            # Анализируем каждую кампанию по очереди
            for i, campaign in enumerate(campaigns, 1):
                campaign_id = campaign['id']
                logger.info(f"Анализ кампании {i}/{len(campaigns)}: {campaign['name']} (ID: {campaign_id})")
                
                try:
                    analyze_single_campaign(
                        campaign_id,
                        args.access_token,
                        days=args.days,
                        output_dir=args.output_dir
                    )
                    
                    # Ждем перед следующей кампанией
                    if i < len(campaigns):
                        logger.info(f"Пауза {args.wait_time} секунд перед анализом следующей кампании...")
                        time.sleep(args.wait_time)
                
                except Exception as e:
                    logger.error(f"Ошибка при анализе кампании {campaign_id}: {str(e)}")
                    
                    # Пауза в случае ошибки (возможно, превышение лимита API)
                    error_wait_time = 300  # 5 минут
                    logger.info(f"Ждем {error_wait_time} секунд перед продолжением...")
                    time.sleep(error_wait_time)
            
            logger.info("Анализ всех кампаний завершен")
        
        return 0
    
    except Exception as e:
        logger.error(f"Ошибка при работе скрипта: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 