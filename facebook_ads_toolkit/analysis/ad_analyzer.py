"""
Модуль для анализа рекламных данных из Facebook API.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.data_handlers import calculate_metrics, format_currency
from .data_fetchers import AdDataFetcher

logger = logging.getLogger(__name__)

class AdAnalyzer:
    """Класс для анализа данных о рекламе."""
    
    def __init__(self, ad_data: Optional[Dict[str, Any]] = None):
        """
        Инициализация анализатора рекламы.
        
        Args:
            ad_data: Предварительно загруженные данные о рекламе (опционально)
        """
        self.ad_data = ad_data
        self.analysis_results = {}
    
    def set_data(self, ad_data: Dict[str, Any]):
        """
        Установка данных для анализа.
        
        Args:
            ad_data: Данные о рекламе
        """
        self.ad_data = ad_data
    
    def analyze(self) -> Dict[str, Any]:
        """
        Выполнение анализа данных о рекламе.
        
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        if not self.ad_data:
            logger.error("Нет данных для анализа")
            return {}
        
        logger.info("Начинаем анализ рекламных данных...")
        
        # Рассчитываем основные метрики
        metrics = calculate_metrics(self.ad_data)
        
        # Анализ эффективности кампаний
        campaign_performance = self._analyze_campaign_performance()
        
        # Анализ эффективности групп объявлений
        adset_performance = self._analyze_adset_performance()
        
        # Анализ эффективности объявлений
        ad_performance = self._analyze_ad_performance()
        
        # Формируем результаты анализа
        self.analysis_results = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'time_range': self.ad_data.get('time_range', {}),
            'metrics': metrics,
            'campaign_performance': campaign_performance,
            'adset_performance': adset_performance,
            'ad_performance': ad_performance
        }
        
        logger.info("Анализ рекламных данных завершен")
        
        return self.analysis_results
    
    def _analyze_campaign_performance(self) -> Dict[str, Any]:
        """
        Анализ эффективности кампаний.
        
        Returns:
            Dict[str, Any]: Результаты анализа кампаний
        """
        if 'campaigns' not in self.ad_data:
            return {}
        
        campaigns = self.ad_data['campaigns']
        
        # Собираем данные по кампаниям
        campaign_data = {}
        
        for campaign in campaigns:
            campaign_id = campaign.get('id')
            if not campaign_id:
                continue
                
            insights = campaign.get('insights', {})
            
            performance = {
                'id': campaign_id,
                'name': campaign.get('name', 'Неизвестная кампания'),
                'status': campaign.get('status'),
                'objective': campaign.get('objective'),
                'spend': float(insights.get('spend', 0)),
                'impressions': int(insights.get('impressions', 0)),
                'clicks': int(insights.get('clicks', 0)),
                'ctr': float(insights.get('ctr', 0)),
                'cpc': float(insights.get('cpc', 0)) if insights.get('cpc') else 0,
                'reach': int(insights.get('reach', 0)),
                'frequency': float(insights.get('frequency', 0)),
                'daily_budget': campaign.get('daily_budget'),
                'lifetime_budget': campaign.get('lifetime_budget'),
                'adsets_count': 0,
                'ads_count': 0,
                'active_adsets_count': 0,
                'active_ads_count': 0
            }
            
            # Рассчитываем ROI/ROAS если доступны данные о конверсиях и их значении
            action_values = insights.get('action_values', [])
            if action_values:
                total_value = sum(float(value.get('value', 0)) for value in action_values)
                performance['conversion_value'] = total_value
                if performance['spend'] > 0:
                    performance['roas'] = total_value / performance['spend']
            
            campaign_data[campaign_id] = performance
        
        # Считаем количество групп и объявлений для каждой кампании
        if 'adsets' in self.ad_data:
            for adset in self.ad_data['adsets']:
                campaign_id = adset.get('campaign_id')
                if campaign_id in campaign_data:
                    campaign_data[campaign_id]['adsets_count'] += 1
                    if adset.get('status') == 'ACTIVE':
                        campaign_data[campaign_id]['active_adsets_count'] += 1
        
        if 'ads' in self.ad_data:
            for ad in self.ad_data['ads']:
                campaign_id = ad.get('campaign_id')
                if campaign_id in campaign_data:
                    campaign_data[campaign_id]['ads_count'] += 1
                    if ad.get('status') == 'ACTIVE':
                        campaign_data[campaign_id]['active_ads_count'] += 1
        
        # Сортируем кампании по эффективности (CTR)
        sorted_campaigns = sorted(
            campaign_data.values(),
            key=lambda x: x['ctr'] if x['impressions'] > 0 else 0,
            reverse=True
        )
        
        # Формируем итоговый результат
        result = {
            'all_campaigns': list(campaign_data.values()),
            'top_campaigns_by_ctr': sorted_campaigns[:5],
            'top_campaigns_by_spend': sorted(
                campaign_data.values(),
                key=lambda x: x['spend'],
                reverse=True
            )[:5],
            'top_campaigns_by_clicks': sorted(
                campaign_data.values(),
                key=lambda x: x['clicks'],
                reverse=True
            )[:5]
        }
        
        return result
    
    def _analyze_adset_performance(self) -> Dict[str, Any]:
        """
        Анализ эффективности групп объявлений.
        
        Returns:
            Dict[str, Any]: Результаты анализа групп объявлений
        """
        if 'adsets' not in self.ad_data:
            return {}
        
        adsets = self.ad_data['adsets']
        
        # Собираем данные по группам объявлений
        adset_data = {}
        
        for adset in adsets:
            adset_id = adset.get('id')
            if not adset_id:
                continue
                
            insights = adset.get('insights', {})
            
            performance = {
                'id': adset_id,
                'name': adset.get('name', 'Неизвестная группа'),
                'campaign_id': adset.get('campaign_id'),
                'status': adset.get('status'),
                'optimization_goal': adset.get('optimization_goal'),
                'bid_strategy': adset.get('bid_strategy'),
                'spend': float(insights.get('spend', 0)),
                'impressions': int(insights.get('impressions', 0)),
                'clicks': int(insights.get('clicks', 0)),
                'ctr': 0,
                'cpc': 0,
                'ads_count': 0,
                'active_ads_count': 0
            }
            
            # Рассчитываем CTR и CPC
            if performance['impressions'] > 0:
                performance['ctr'] = performance['clicks'] / performance['impressions'] * 100
            
            if performance['clicks'] > 0 and performance['spend'] > 0:
                performance['cpc'] = performance['spend'] / performance['clicks']
            
            adset_data[adset_id] = performance
        
        # Считаем количество объявлений для каждой группы
        if 'ads' in self.ad_data:
            for ad in self.ad_data['ads']:
                adset_id = ad.get('adset_id')
                if adset_id in adset_data:
                    adset_data[adset_id]['ads_count'] += 1
                    if ad.get('status') == 'ACTIVE':
                        adset_data[adset_id]['active_ads_count'] += 1
        
        # Сортируем группы по эффективности (CTR)
        sorted_adsets = sorted(
            adset_data.values(),
            key=lambda x: x['ctr'] if x['impressions'] > 0 else 0,
            reverse=True
        )
        
        # Формируем итоговый результат
        result = {
            'all_adsets': list(adset_data.values()),
            'top_adsets_by_ctr': sorted_adsets[:10],
            'top_adsets_by_spend': sorted(
                adset_data.values(),
                key=lambda x: x['spend'],
                reverse=True
            )[:10],
            'adsets_by_optimization_goal': {}
        }
        
        # Группируем по целям оптимизации
        for adset in adset_data.values():
            goal = adset.get('optimization_goal', 'Unknown')
            if goal not in result['adsets_by_optimization_goal']:
                result['adsets_by_optimization_goal'][goal] = []
            result['adsets_by_optimization_goal'][goal].append(adset)
        
        return result
    
    def _analyze_ad_performance(self) -> Dict[str, Any]:
        """
        Анализ эффективности объявлений.
        
        Returns:
            Dict[str, Any]: Результаты анализа объявлений
        """
        if 'ads' not in self.ad_data:
            return {}
        
        ads = self.ad_data['ads']
        
        # Собираем данные по объявлениям
        ad_data = {}
        
        for ad in ads:
            ad_id = ad.get('id')
            if not ad_id:
                continue
                
            insights = ad.get('insights', {})
            
            performance = {
                'id': ad_id,
                'name': ad.get('name', 'Неизвестное объявление'),
                'adset_id': ad.get('adset_id'),
                'campaign_id': ad.get('campaign_id'),
                'status': ad.get('status'),
                'effective_status': ad.get('effective_status'),
                'spend': float(insights.get('spend', 0)),
                'impressions': int(insights.get('impressions', 0)),
                'clicks': int(insights.get('clicks', 0)),
                'ctr': 0,
                'cpc': 0,
                'creative': ad.get('creative', {})
            }
            
            # Рассчитываем CTR и CPC
            if performance['impressions'] > 0:
                performance['ctr'] = performance['clicks'] / performance['impressions'] * 100
            
            if performance['clicks'] > 0 and performance['spend'] > 0:
                performance['cpc'] = performance['spend'] / performance['clicks']
            
            ad_data[ad_id] = performance
        
        # Сортируем объявления по эффективности (CTR)
        sorted_ads = sorted(
            ad_data.values(),
            key=lambda x: x['ctr'] if x['impressions'] > 0 else 0,
            reverse=True
        )
        
        # Формируем итоговый результат
        result = {
            'all_ads': list(ad_data.values()),
            'top_ads_by_ctr': sorted_ads[:15],
            'top_ads_by_clicks': sorted(
                ad_data.values(),
                key=lambda x: x['clicks'],
                reverse=True
            )[:15],
            'underperforming_ads': sorted(
                [ad for ad in ad_data.values() if ad['impressions'] >= 100],
                key=lambda x: x['ctr']
            )[:10]
        }
        
        return result
    
    def print_summary(self):
        """Вывод сводки по результатам анализа."""
        if not self.analysis_results:
            logger.warning("Нет результатов анализа для вывода")
            return
        
        metrics = self.analysis_results.get('metrics', {})
        
        print("\n=== Общая статистика ===")
        print(f"Всего активных кампаний: {metrics.get('active_campaigns', 0)}/{metrics.get('total_campaigns', 0)}")
        print(f"Всего активных групп объявлений: {metrics.get('active_adsets', 0)}/{metrics.get('total_adsets', 0)}")
        print(f"Всего активных объявлений: {metrics.get('active_ads', 0)}/{metrics.get('total_ads', 0)}")
        
        print(f"\nРасходы: {format_currency(metrics.get('total_spend', 0))}")
        print(f"Показы: {metrics.get('total_impressions', 0):,}")
        print(f"Клики: {metrics.get('total_clicks', 0):,}")
        print(f"Средний CTR: {metrics.get('avg_ctr', 0):.2f}%")
        print(f"Средний CPC: {format_currency(metrics.get('avg_cpc', 0))}")
        
        print("\n=== Топ-3 кампании по CTR ===")
        top_campaigns = self.analysis_results.get('campaign_performance', {}).get('top_campaigns_by_ctr', [])
        for i, campaign in enumerate(top_campaigns[:3], 1):
            print(f"{i}. {campaign.get('name')} - CTR: {campaign.get('ctr', 0):.2f}%, "
                  f"Клики: {campaign.get('clicks', 0)}, "
                  f"Расходы: {format_currency(campaign.get('spend', 0))}")
        
        print("\n=== Топ-3 объявления по CTR ===")
        top_ads = self.analysis_results.get('ad_performance', {}).get('top_ads_by_ctr', [])
        for i, ad in enumerate(top_ads[:3], 1):
            print(f"{i}. {ad.get('name')} - CTR: {ad.get('ctr', 0):.2f}%, "
                  f"Клики: {ad.get('clicks', 0)}, "
                  f"Расходы: {format_currency(ad.get('spend', 0))}")
    
    @staticmethod
    def run_analysis(account, time_range=None) -> Dict[str, Any]:
        """
        Статический метод для запуска полного анализа.
        
        Args:
            account: Инициализированный рекламный аккаунт
            time_range: Временной диапазон (опционально)
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        # Создаем сборщик данных
        fetcher = AdDataFetcher(account)
        
        # Устанавливаем временной диапазон
        if time_range:
            fetcher.set_time_range(time_range['since'], time_range['until'])
        
        # Получаем данные
        logger.info("Получение данных о рекламе...")
        ad_data = fetcher.fetch_all_batch()
        
        # Анализируем данные
        analyzer = AdAnalyzer(ad_data)
        results = analyzer.analyze()
        
        # Выводим сводку
        analyzer.print_summary()
        
        return results 