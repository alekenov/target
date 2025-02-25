from fb_auth import init_facebook_api
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
import json
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_campaign_data(campaign):
    """Получить данные для одной кампании"""
    try:
        campaign_details = campaign.api_get(fields=[
            'name',
            'objective',
            'status',
            'daily_budget',
            'lifetime_budget'
        ])
        
        ad_sets = campaign.get_ad_sets(params={
            'effective_status': ['ACTIVE'],
            'limit': 50,
            'fields': [
                'name',
                'targeting',
                'optimization_goal',
                'bid_strategy',
                'daily_budget',
                'lifetime_budget'
            ]
        })
        
        campaign_data = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        for ad_set in ad_sets:
            ads = ad_set.get_ads(params={
                'effective_status': ['ACTIVE'],
                'limit': 50,
                'fields': [
                    'name',
                    'creative',
                    'status',
                    'effective_status'
                ]
            })
            
            for ad in ads:
                insights = ad.get_insights(params={
                    'time_range': {
                        'since': start_date.strftime('%Y-%m-%d'),
                        'until': end_date.strftime('%Y-%m-%d')
                    },
                    'fields': [
                        'spend',
                        'impressions',
                        'clicks',
                        'ctr',
                        'cpc',
                        'reach',
                        'frequency'
                    ]
                })
                
                ad_data = {
                    'campaign': {
                        'id': campaign_details['id'],
                        'name': campaign_details.get('name'),
                        'objective': campaign_details.get('objective'),
                        'daily_budget': campaign_details.get('daily_budget'),
                        'lifetime_budget': campaign_details.get('lifetime_budget')
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
                    'statistics': insights[0] if insights else None
                }
                campaign_data.append(ad_data)
                logger.info(f"Получены данные для объявления: {ad_data['ad']['name']}")
        
        return campaign_data
    except Exception as e:
        logger.error(f"Ошибка при получении данных кампании {campaign['id']}: {str(e)}")
        return []

def get_active_ads():
    """Получить данные всех активных объявлений"""
    account, api = init_facebook_api()
    if not account:
        return None
    
    try:
        # Получаем все активные кампании
        campaigns = account.get_campaigns(params={
            'effective_status': ['ACTIVE'],
            'limit': 50
        })
        
        active_ads_data = []
        
        # Используем ThreadPoolExecutor для параллельной обработки кампаний
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_campaign = {
                executor.submit(get_campaign_data, campaign): campaign 
                for campaign in campaigns
            }
            
            for future in as_completed(future_to_campaign):
                campaign = future_to_campaign[future]
                try:
                    campaign_data = future.result()
                    active_ads_data.extend(campaign_data)
                except Exception as e:
                    logger.error(f"Ошибка при обработке кампании {campaign['id']}: {str(e)}")
        
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
    """Анализ данных объявлений"""
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
    
    # Сохраняем результаты анализа
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    analysis_data = {
        'timestamp': timestamp,
        'total_stats': {
            'total_ads': total_ads,
            'total_spend': total_spend,
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'average_ctr': (total_clicks/total_impressions*100) if total_impressions > 0 else 0,
            'average_cpc': (total_spend/total_clicks) if total_clicks > 0 else 0
        },
        'campaign_performance': campaign_performance
    }
    
    # Сохраняем в файл
    filename = f'ads_analysis_{timestamp}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2)
    
    # Выводим статистику
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

if __name__ == "__main__":
    logger.info("Начинаем анализ активных объявлений...")
    ads_data = get_active_ads()
    if ads_data:
        analyze_ads_data(ads_data)
    logger.info("Анализ завершен")
