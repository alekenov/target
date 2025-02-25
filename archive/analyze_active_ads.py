from fb_auth import init_facebook_api
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.api import FacebookAdsApi
import json
from datetime import datetime, timedelta
import logging
import time
from facebook_business.exceptions import FacebookRequestError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_api_call(func, max_retries=5, initial_delay=10):
    """Обработчик API вызовов с повторными попытками и экспоненциальной задержкой"""
    for attempt in range(max_retries):
        try:
            return func()
        except FacebookRequestError as e:
            if e.api_error_code() == 17:  # Rate limit error
                if attempt < max_retries - 1:
                    wait_time = initial_delay * (2 ** attempt)  # Экспоненциальная задержка
                    logger.info(f"Достигнут лимит запросов. Ожидание {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue
            raise e
    return None

def chunk_list(lst, chunk_size):
    """Разбивает список на части указанного размера"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def get_active_ads():
    account, api = init_facebook_api()
    if not account:
        return None
    
    try:
        # Получаем все активные кампании одним запросом
        campaigns = account.get_campaigns(params={
            'effective_status': ['ACTIVE'],
            'limit': 1000,
            'fields': [
                'name',
                'objective',
                'status',
                'daily_budget',
                'lifetime_budget'
            ]
        })
        
        if not campaigns:
            logger.error("Активные кампании не найдены")
            return None
            
        active_ads_data = []
        
        # Разбиваем кампании на группы по 20 для батч-запросов
        campaign_chunks = chunk_list(campaigns, 20)
        ad_sets_by_campaign = {}
        
        for chunk in campaign_chunks:
            batch = api.new_batch()
            
            for campaign in chunk:
                def callback_ad_sets(response, campaign_id=campaign['id']):
                    if response and response.json():
                        ad_sets_by_campaign[campaign_id] = response.json().get('data', [])
                
                campaign.get_ad_sets(
                    params={
                        'effective_status': ['ACTIVE'],
                        'limit': 1000,
                        'fields': [
                            'name',
                            'targeting',
                            'optimization_goal',
                            'bid_strategy',
                            'daily_budget',
                            'lifetime_budget'
                        ]
                    },
                    batch=batch,
                    success=callback_ad_sets
                )
            
            batch.execute()
        
        # Получаем объявления для каждой группы объявлений
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        ads_by_set = {}
        
        # Собираем все ad_sets
        all_ad_sets = []
        for ad_sets in ad_sets_by_campaign.values():
            all_ad_sets.extend(ad_sets)
        
        # Разбиваем ad_sets на группы по 20
        ad_set_chunks = chunk_list(all_ad_sets, 20)
        
        for chunk in ad_set_chunks:
            batch = api.new_batch()
            
            for ad_set in chunk:
                def callback_ads(response, ad_set_id=ad_set['id']):
                    if response and response.json():
                        ads_by_set[ad_set_id] = response.json().get('data', [])
                
                AdSet(ad_set['id']).get_ads(
                    params={
                        'effective_status': ['ACTIVE'],
                        'limit': 1000,
                        'fields': [
                            'name',
                            'creative',
                            'status',
                            'configured_status',
                            'effective_status',
                            'insights.time_range({"since":"' + start_date.strftime('%Y-%m-%d') + '","until":"' + end_date.strftime('%Y-%m-%d') + '"}).fields(spend,impressions,clicks,ctr,cpc,reach,frequency)'
                        ]
                    },
                    batch=batch,
                    success=callback_ads
                )
            
            batch.execute()
        
        # Собираем все данные вместе
        for campaign in campaigns:
            campaign_id = campaign['id']
            if campaign_id not in ad_sets_by_campaign:
                continue
                
            for ad_set in ad_sets_by_campaign[campaign_id]:
                ad_set_id = ad_set['id']
                if ad_set_id not in ads_by_set:
                    continue
                    
                for ad in ads_by_set[ad_set_id]:
                    insights = ad.get('insights', {}).get('data', [{}])[0] if 'insights' in ad else {}
                    
                    ad_data = {
                        'campaign': {
                            'id': campaign['id'],
                            'name': campaign.get('name'),
                            'objective': campaign.get('objective'),
                            'daily_budget': campaign.get('daily_budget'),
                            'lifetime_budget': campaign.get('lifetime_budget')
                        },
                        'ad_set': {
                            'id': ad_set['id'],
                            'name': ad_set.get('name'),
                            'optimization_goal': ad_set.get('optimization_goal'),
                            'bid_strategy': ad_set.get('bid_strategy'),
                            'daily_budget': ad_set.get('daily_budget'),
                            'lifetime_budget': ad_set.get('lifetime_budget'),
                            'targeting': ad_set.get('targeting')
                        },
                        'ad': {
                            'id': ad['id'],
                            'name': ad.get('name'),
                            'status': ad.get('status'),
                            'effective_status': ad.get('effective_status')
                        },
                        'statistics': insights
                    }
                    
                    active_ads_data.append(ad_data)
                    logger.info(f"Получены данные для объявления: {ad_data['ad']['name']}")
        
        # Сохраняем результаты в файл
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'active_ads_analysis_{timestamp}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(active_ads_data, f, ensure_ascii=False, indent=2)
        
        return active_ads_data
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {str(e)}")
        return None

def analyze_ads_data(ads_data):
    if not ads_data:
        logger.error("Нет данных для анализа")
        return
    
    total_ads = len(ads_data)
    total_spend = 0
    total_impressions = 0
    total_clicks = 0
    
    campaign_performance = {}
    
    for ad in ads_data:
        stats = ad.get('statistics', {})
        if not stats:
            continue
        
        campaign_id = ad['campaign']['id']
        campaign_name = ad['campaign']['name']
        
        spend = float(stats.get('spend', 0))
        impressions = int(stats.get('impressions', 0))
        clicks = int(stats.get('clicks', 0))
        
        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        
        if campaign_id not in campaign_performance:
            campaign_performance[campaign_id] = {
                'name': campaign_name,
                'spend': 0,
                'impressions': 0,
                'clicks': 0,
                'ads_count': 0
            }
        
        campaign_performance[campaign_id]['spend'] += spend
        campaign_performance[campaign_id]['impressions'] += impressions
        campaign_performance[campaign_id]['clicks'] += clicks
        campaign_performance[campaign_id]['ads_count'] += 1
    
    logger.info("\n=== Общая статистика ===")
    logger.info(f"Всего активных объявлений: {total_ads}")
    logger.info(f"Общие расходы: ${total_spend:.2f}")
    logger.info(f"Общие показы: {total_impressions:,}")
    logger.info(f"Общие клики: {total_clicks:,}")
    if total_impressions > 0:
        logger.info(f"Средний CTR: {(total_clicks/total_impressions*100):.2f}%")
    if total_clicks > 0:
        logger.info(f"Средний CPC: ${(total_spend/total_clicks):.2f}")
    
    logger.info("\n=== Статистика по кампаниям ===")
    for campaign_data in campaign_performance.values():
        logger.info(f"\nКампания: {campaign_data['name']}")
        logger.info(f"Количество объявлений: {campaign_data['ads_count']}")
        logger.info(f"Расходы: ${campaign_data['spend']:.2f}")
        logger.info(f"Показы: {campaign_data['impressions']:,}")
        logger.info(f"Клики: {campaign_data['clicks']:,}")
        if campaign_data['impressions'] > 0:
            ctr = campaign_data['clicks']/campaign_data['impressions']*100
            logger.info(f"CTR: {ctr:.2f}%")
        if campaign_data['clicks'] > 0:
            cpc = campaign_data['spend']/campaign_data['clicks']
            logger.info(f"CPC: ${cpc:.2f}")

def analyze_detailed_results(ads_data):
    """Анализ лучших и худших результатов рекламы"""
    # Подготовка данных для анализа
    ads_performance = []
    for ad in ads_data:
        stats = ad.get('statistics', {})
        if not stats:
            continue
            
        spend = float(stats.get('spend', 0))
        impressions = int(stats.get('impressions', 0))
        clicks = int(stats.get('clicks', 0))
        ctr = float(stats.get('ctr', 0))
        cpc = float(stats.get('cpc', 0)) if clicks > 0 else 0
        reach = int(stats.get('reach', 0))
        frequency = float(stats.get('frequency', 0))
        
        performance = {
            'campaign_name': ad['campaign']['name'],
            'ad_set_name': ad['ad_set']['name'],
            'ad_name': ad['ad']['name'],
            'spend': spend,
            'impressions': impressions,
            'clicks': clicks,
            'ctr': ctr,
            'cpc': cpc,
            'reach': reach,
            'frequency': frequency,
            'conversion_rate': clicks / impressions * 100 if impressions > 0 else 0
        }
        ads_performance.append(performance)
    
    # Сортировка по разным метрикам
    by_ctr = sorted(ads_performance, key=lambda x: x['ctr'], reverse=True)
    by_cpc = sorted(ads_performance, key=lambda x: x['cpc'] if x['cpc'] > 0 else float('inf'))
    by_spend = sorted(ads_performance, key=lambda x: x['spend'], reverse=True)
    by_clicks = sorted(ads_performance, key=lambda x: x['clicks'], reverse=True)
    
    logger.info("\n=== Топ 5 объявлений по CTR ===")
    for ad in by_ctr[:5]:
        logger.info(f"\nКампания: {ad['campaign_name']}")
        logger.info(f"Объявление: {ad['ad_name']}")
        logger.info(f"CTR: {ad['ctr']:.2f}%")
        logger.info(f"Клики: {ad['clicks']}")
        logger.info(f"Показы: {ad['impressions']:,}")
        logger.info(f"Расходы: ${ad['spend']:.2f}")
        logger.info(f"CPC: ${ad['cpc']:.2f}")
    
    logger.info("\n=== Топ 5 объявлений по кликам ===")
    for ad in by_clicks[:5]:
        logger.info(f"\nКампания: {ad['campaign_name']}")
        logger.info(f"Объявление: {ad['ad_name']}")
        logger.info(f"Клики: {ad['clicks']}")
        logger.info(f"CTR: {ad['ctr']:.2f}%")
        logger.info(f"Показы: {ad['impressions']:,}")
        logger.info(f"Расходы: ${ad['spend']:.2f}")
        logger.info(f"CPC: ${ad['cpc']:.2f}")
    
    logger.info("\n=== Топ 5 самых эффективных по CPC ===")
    for ad in by_cpc[:5]:
        if ad['clicks'] > 0:  # Показываем только те, у которых были клики
            logger.info(f"\nКампания: {ad['campaign_name']}")
            logger.info(f"Объявление: {ad['ad_name']}")
            logger.info(f"CPC: ${ad['cpc']:.2f}")
            logger.info(f"Клики: {ad['clicks']}")
            logger.info(f"CTR: {ad['ctr']:.2f}%")
            logger.info(f"Расходы: ${ad['spend']:.2f}")
    
    logger.info("\n=== Топ 5 по расходам ===")
    for ad in by_spend[:5]:
        logger.info(f"\nКампания: {ad['campaign_name']}")
        logger.info(f"Объявление: {ad['ad_name']}")
        logger.info(f"Расходы: ${ad['spend']:.2f}")
        logger.info(f"Клики: {ad['clicks']}")
        logger.info(f"CTR: {ad['ctr']:.2f}%")
        logger.info(f"CPC: ${ad['cpc']:.2f}")
        logger.info(f"Показы: {ad['impressions']:,}")

if __name__ == "__main__":
    logger.info("Начинаем анализ активных объявлений...")
    ads_data = get_active_ads()
    if ads_data:
        analyze_ads_data(ads_data)
        analyze_detailed_results(ads_data)
    logger.info("Анализ завершен")
