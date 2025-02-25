import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def main():
    # Загружаем данные из последнего JSON файла
    with open('active_ads_analysis_20250216_225127.json', 'r', encoding='utf-8') as f:
        ads_data = json.load(f)
    
    analyze_detailed_results(ads_data)

if __name__ == "__main__":
    main() 